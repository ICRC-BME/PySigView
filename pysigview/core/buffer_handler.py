# -*- coding: utf-8 -*-
"""
Created on Tue Nov 10 19:55:05 2015

This script maps the formats in file_formats and clients

On request it assigngs the file handler based on extension.

Starts a data loading thread that creates buffers on disk and gets the means to
the parent script to read the data. Issues a signal if the requested data
is out of buffer.

Sends information about the current buffer state.

Ing.,Mgr. (MSc.) Jan Cimbálník
Biomedical engineering
International Clinical Research Center
St. Anne's University Hospital in Brno
Czech Republic
&
Mayo systems electrophysiology lab
Mayo Clinic
200 1st St SW
Rochester, MN
United States
"""

# Standard library imports
from multiprocessing import Process, Lock, Event as pEvent
from multiprocessing.managers import BaseManager
from threading import Event as tEvent
from threading import Thread
from tempfile import gettempdir

# import tempfile - this will be used with bcolz

# Third party imports
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject

# Local imports
from pysigview.core import source_manager as sm
from pysigview.core.source_manager import BufferDataSource
from pysigview.core.pysigviewmultiringbuffer import PysigviewMultiRingBuffer
from pysigview.config.main import CONF


# =============================================================================
# Shared class object
# =============================================================================

class SharedData:
    def __init__(self):
        self.srb = None
        self.chunk_size = 0
        self.data_map = None
        self.current_view_dm = None
        self.size_changed = False

    def set_chunk_size(self, chunk_size):
        self.chunk_size = chunk_size

    def get_chunk_size(self):
        return self.chunk_size

    def set_data_map(self, data_map):
        self.data_map = data_map

    def get_data_map(self):
        return self.data_map

    def set_data_map_start(self, uutc):
        self.data_map['uutc_ss'][:, 0] = uutc

    def set_data_map_stop(self, uutc):
        self.data_map['uutc_ss'][:, 1] = uutc

    def shift_data_map(self, by):
        self.data_map['uutc_ss'] += by

    def shirnk_data_map(self, by, fb_ratio):
        self.data_map['uutc_ss'][:, 0] += int((by * (1-fb_ratio)) + 0.5)
        self.data_map['uutc_ss'][:, 1] -= int((by * fb_ratio) + 0.5)

    def enlarge_data_map(self, by, fb_ratio):
        self.data_map['uutc_ss'][:, 0] -= int((by * (1-fb_ratio)) + 0.5)
        self.data_map['uutc_ss'][:, 1] += int((by * fb_ratio) + 0.5)

    def set_current_view_dm(self, current_view_dm):
        self.current_view_dm = current_view_dm

    def get_current_view_dm(self):
        return self.current_view_dm

    def set_srb(self, srb):
        self.srb = srb

    def get_srb(self):
        return self.srb

    def get_srb_start_stop(self):
        return [self.srb.uutc_ss[:, 0].min(), self.srb.uutc_ss[:, 1].max()]

    def set_srb_data(self, channels, uutc_ss, data):
        # Check that we are not out of buffer
        if (uutc_ss[0] < self.srb._uutc_ss[:, 0].min()
                or uutc_ss[1] > self.srb._uutc_ss[:, 1].max()):
            return

        self.srb[channels, uutc_ss[0]:uutc_ss[1]] = data

    def get_srb_data(self, channels, uutc_ss):
        return self.srb[channels, uutc_ss]

    def roll_srb(self, by):
        self.srb.roll(by)

    def shrink_srb(self, by, fb_ratio):
        elements = np.where(self.data_map['ch_set'])[0]
        self.srb.shrink(by, elements, fb_ratio)

    def enlarge_srb(self, by, fb_ratio):
        elements = np.where(self.data_map['ch_set'])[0]
        self.srb.enlarge(by, elements, fb_ratio)

    def purge_srb(self):
        self.srb.purge_data()

    def get_size_changed(self):
        return self.size_changed

    def set_size_changed(self):
        self.size_changed = True

    def unset_size_changed(self):
        self.size_changed = False


class SharedDataManager(BaseManager):
    pass


SharedDataManager.register("SharedData", SharedData)

# =============================================================================
# Buffering function
# =============================================================================


def fill_roll_buffer(sd, stop_event, proc_lock,
                     chunks_before, chunks_after):

    def check_load_dm(load_dm):

        rec_start = sm.ODS.recording_info['recording_start']
        rec_end = sm.ODS.recording_info['recording_end']

        if any(load_dm['uutc_ss'][:, 0] < rec_start):
            largest_diff = np.max(rec_start - load_dm['uutc_ss'][:, 0])
            load_dm['uutc_ss'] += largest_diff

        if any(load_dm['uutc_ss'][:, 1] > rec_end):
            largest_diff = np.max(load_dm['uutc_ss'][:, 1] - rec_end)
            load_dm['uutc_ss'] -= largest_diff

        return load_dm

    # Some recording info
    rec_start = sm.ODS.recording_info['recording_start']
    rec_end = sm.ODS.recording_info['recording_end']

    # Variables need for the process
    load_dm = sd.get_data_map()
    load_dm['uutc_ss'][:, 1] += sd.get_chunk_size()
    load_dm = check_load_dm(load_dm)
    load_ss = load_dm.get_active_largest_ss()

    while True:

        if stop_event.is_set():
            return

        # No actvie channels
        if not len(load_dm.get_active_channels()):
            continue

        buff_size = ((chunks_before + chunks_after + 1)
                     * sd.get_chunk_size())
        ring_ss = sd.get_srb_start_stop()
        buffer_ss = sd.get_data_map().get_active_largest_ss()

        # ----- Buffer filling -----
        buffer_filled = np.diff(buffer_ss)[0] == buff_size

        if not buffer_filled:

            # ----- Forward direction -----

            load_dm['uutc_ss'][:, 0] = buffer_ss[1]
            load_dm['uutc_ss'][:, 1] = buffer_ss[1] + sd.get_chunk_size()
            load_dm = check_load_dm(load_dm)
            load_ss = load_dm.get_active_largest_ss()

            # Is load data map beyond the ring buffer?
            if not load_ss[0] >= ring_ss[1]:
                # Is only part of load data map is beyond the buffer?
                if load_ss[1] > ring_ss[1]:
                    load_dm['uutc_ss'][:, 1] = ring_ss[1]

                data = sm.ODS.get_data(load_dm)

                # Determine the channels and times
                channels = np.where(load_dm['ch_set'])[0]
                uutc_ss = load_dm.get_active_largest_ss()

                # Update shared memory proxies
                proc_lock.acquire()
                if sd.get_size_changed():
                    sd.unset_size_changed()
                    proc_lock.release()
                    continue

                sd.set_srb_data(channels, uutc_ss, data[channels])

                sd.set_data_map_stop(uutc_ss[1])

                proc_lock.release()

            # ----- Backward direction -----

            load_dm['uutc_ss'][:, 0] = buffer_ss[0] - sd.get_chunk_size()
            load_dm['uutc_ss'][:, 1] = buffer_ss[0]
            load_dm = check_load_dm(load_dm)
            load_ss = load_dm.get_active_largest_ss()

            # Is load data map beyond the ring buffer?
            if not load_ss[1] <= ring_ss[0]:
                # Is only part of load data map is beyond the buffer?
                if load_ss[0] < ring_ss[0]:
                    load_dm['uutc_ss'][:, 0] = ring_ss[0]

                data = sm.ODS.get_data(load_dm)

                # Determine the channels and times
                channels = np.where(load_dm['ch_set'])[0]
                uutc_ss = load_dm.get_active_largest_ss()

                # Update shared memory proxies
                proc_lock.acquire()
                if sd.get_size_changed():
                    sd.unset_size_changed()
                    proc_lock.release()
                    continue

                sd.set_srb_data(channels, uutc_ss, data[channels])

                sd.set_data_map_start(uutc_ss[0])

                proc_lock.release()

            continue

        # ----- Buffer rolling -----

        if sd.get_current_view_dm() is None:
            continue

        # Calculate the non-rolling point

        view_ss = sd.get_current_view_dm().get_active_largest_ss()

        # Determine the nonroling point

        nonr_ss = [buffer_ss[0] + chunks_before * sd.get_chunk_size(),
                   buffer_ss[0] + (chunks_before + 1) * sd.get_chunk_size()]

        midpoint_diff = int(np.sum(view_ss) / 2 - np.sum(nonr_ss) / 2)

        if midpoint_diff > 0 and buffer_ss[1] < rec_end:

            # Determine the loadmap
            load_dm['uutc_ss'][:, 0] = buffer_ss[1]
            load_dm['uutc_ss'][:, 1] = buffer_ss[1] + midpoint_diff
            load_dm = check_load_dm(load_dm)

            # Load data
            data = sm.ODS.get_data(load_dm)

            # Determine the channels and times
            channels = np.where(load_dm['ch_set'])[0]
            uutc_ss = load_dm.get_active_largest_ss()

            # Roll the rolling buffer and upload the data
            proc_lock.acquire()
            if sd.get_size_changed():
                sd.unset_size_changed()
                proc_lock.release()
                continue

            sd.roll_srb(midpoint_diff)
            sd.set_srb_data(channels, uutc_ss, data[channels])

            sd.shift_data_map(midpoint_diff)

            proc_lock.release()

        elif midpoint_diff < 0 and buffer_ss[0] > rec_start:
            # Determine the loadmap
            load_dm['uutc_ss'][:, 1] = buffer_ss[0]
            load_dm['uutc_ss'][:, 0] = buffer_ss[0] + midpoint_diff
            load_dm = check_load_dm(load_dm)

            # Load data
            data = sm.ODS.get_data(load_dm)

            # Determine the channels and times
            channels = np.where(load_dm['ch_set'])[0]
            uutc_ss = load_dm.get_active_largest_ss()

            # Roll the rolling buffer and upload the data
            proc_lock.acquire()
            if sd.get_size_changed():
                sd.unset_size_changed()
                proc_lock.release()
                continue

            sd.roll_srb(midpoint_diff)
            sd.set_srb_data(channels, uutc_ss, data[channels])

            sd.shift_data_map(midpoint_diff)

            proc_lock.release()


class MemoryBuffer(BufferDataSource, QObject):

    state_changed = pyqtSignal(name='state_changed')

    def __init__(self, parent):
        super(MemoryBuffer, self).__init__()
        QObject.__init__(self)

        parent.signal_display.data_map_changed.connect(self.update)

        self.rec_start = sm.ODS.recording_info['recording_start']
        self.rec_end = sm.ODS.recording_info['recording_end']

        # Set the internal data map - keeps buffer times (what has already
        # been loaded and is available)
        # This data map is in main process
        self.data_map.setup_data_map(sm.ODS.data_map._map)
        self.data_map.reset_data_map()
        self.data_map['uutc_ss'][:] = self.rec_start

        self.current_view_dm = None

        self.chunk_size = int(CONF.get('data_management', 'chunk_size')*1e6)
        self.N_chunks_before = CONF.get('data_management', 'n_chunks_before')
        self.N_chunks_after = CONF.get('data_management', 'n_chunks_after')
        self.N_chunks = self.N_chunks_before + self.N_chunks_after + 1
        self.use_disk = CONF.get('data_management', 'use_disk_buffer')

        # ----- Buffer process -----

        if self.use_disk:
            self.datadir = gettempdir()
        else:
            self.datadir = None

        self.buffer_manager = SharedDataManager()
        self.buffer_manager.start()
        self.sd = self.buffer_manager.SharedData()
        self.sd.set_chunk_size(self.chunk_size)
        self.sd.set_data_map(self.data_map)

        self.buffer_stop = None
        self.buffer_process = None

        # Shared dictionary - a dictionary because we have to reasign the
        # so that the proxies are aware that something has changed

        self.start_new_buffer()

    def terminate_buffer(self):
        self.buffer_stop.set()
        self.buffer_process.join()
        return

    def terminate_monitor_thread(self):
        self.thread_stop.set()
        self.monitor_thread.join()
        return

    def purge_data(self):
        self.sd.purge_srb()

    def start_new_buffer(self):
        """
        Starts new buffering process. And kills the previous one.
        """

        # This should finish the process
        if self.buffer_process:
            self.terminate_buffer()
            self.terminate_monitor_thread()

        # Create new process and start it
        self.buffer_stop = pEvent()  # Event to kill the buffer process
        self.buffer_lock = Lock()
        self.setup_buffer_vars()
        self.buffer_process = Process(target=fill_roll_buffer,
                                      args=(self.sd,
                                            self.buffer_stop,
                                            self.buffer_lock,
                                            self.N_chunks_before,
                                            self.N_chunks_after),
                                      daemon=True)
        self.buffer_process.start()

        self.thread_stop = tEvent()
        self.monitor_thread = Thread(target=self.monitor_buffer,
                                     daemon=True)
        self.monitor_thread.start()

    def setup_buffer_vars(self):

        n_elem = len(self.data_map)

        fsamps = sm.ODS.data_map['fsamp']

        uutc_ss = np.zeros(2, 'int64')
        if self.sd.get_current_view_dm() is None:
            uutc_ss[:] = self.rec_start
        else:
            self.data_map['uutc_ss'][:] = self.curr_view_times[0]
            uutc_ss[:] = self.data_map.get_active_largest_ss()[0]

        uutc_ss[0] -= int(self.N_chunks_before * self.chunk_size)
        uutc_ss[1] += int((self.N_chunks_after + 1) * self.chunk_size)

        # Recording start/stop
        if uutc_ss[0] < self.rec_start:
            uutc_diff = self.rec_start - uutc_ss[0]
            uutc_ss[0] = self.rec_start
            uutc_ss[1] += uutc_diff
        if uutc_ss[1] > self.rec_end:
            uutc_diff = uutc_ss[1] - self.rec_end
            uutc_ss[0] -= uutc_diff
            uutc_ss[1] = self.rec_end

        sizes = (np.ones(n_elem)*fsamps*np.diff(uutc_ss)/1e6).astype('int64')
        sizes[~self.data_map['ch_set']] = 0

        srb = PysigviewMultiRingBuffer(n_elem, sizes, float, uutc_ss,
                                       fsamps, self.datadir)

        self.sd.set_data_map(self.data_map)
        self.sd.set_srb(srb)

    def monitor_buffer(self):
        prev_ss = self.sd.get_data_map().get_active_largest_ss()
        while True:
            if self.thread_stop.is_set():
                return
            prox_ss = self.sd.get_data_map().get_active_largest_ss()
            if np.any(prev_ss != prox_ss):
                self.data_map = self.sd.get_data_map()
                self.state_changed.emit()
                prev_ss = self.sd.get_data_map().get_active_largest_ss()

    def update(self, view_dm):
        """
        Function to update the ring buffer, alternatively start new process
        """

        self.buffer_lock.acquire()

        self.data_map = self.sd.get_data_map()

        self.curr_view_times = view_dm.get_active_largest_ss()

        # ----- Tackling the channel changes -----
        if np.any(self.data_map['ch_set'] != view_dm['ch_set']):

            # Find the changed channels
            changed_chans = (self.data_map['ch_set']
                             != view_dm['ch_set'])
            added_chans = (view_dm['ch_set'] & changed_chans)
            removed_chans = (self.data_map['ch_set'] & changed_chans)

            # Remove channels
            self.data_map['ch_set'][removed_chans] = False

            # Add channels
            self.data_map['ch_set'][added_chans] = True

            self.sd.set_current_view_dm(view_dm)
            self.sd.set_data_map(self.data_map)

            self.buffer_lock.release()
            self.start_new_buffer()
            return

        # ----- Tackling the time changes -----
        new_chunk_size = np.diff(self.curr_view_times)
        chunk_diff = new_chunk_size - self.chunk_size

        # Shrink & enlarge
        if chunk_diff < 0 or chunk_diff > 0:
            self.chunk_size = new_chunk_size
            if self._is_in_buffer(view_dm):

                new_front_point = (self.curr_view_times[1]
                                   + (self.N_chunks_after * self.chunk_size))
                new_back_point = (self.curr_view_times[0]
                                  - (self.N_chunks_before * self.chunk_size))

                # Check if we are before the rec start
                if new_back_point < self.rec_start:
                    add_to_front = self.rec_start - new_back_point
                    new_back_point = self.rec_start
                else:
                    add_to_front = 0

                # Check if we are before the rec stop
                if new_front_point > self.rec_end:
                    add_to_back = new_front_point - self.rec_end
                    new_front_point = self.rec_end
                else:
                    add_to_back = 0

                dm_ss = self.data_map.get_active_largest_ss()
                front_portion = dm_ss[1] - new_front_point
                back_portion = new_back_point - dm_ss[0]

                front_portion += add_to_front
                back_portion += add_to_back

                fb_ratio = front_portion / (front_portion + back_portion)

                # Shrink
                if chunk_diff < 0:
                    self.sd.shrink_srb(-chunk_diff*self.N_chunks,
                                       fb_ratio)
                    self.sd.shirnk_data_map(-chunk_diff*self.N_chunks,
                                            fb_ratio)
                # Enlarge
                else:
                    self.sd.enlarge_srb(chunk_diff*self.N_chunks,
                                        fb_ratio)

                self.sd.set_size_changed()

            else:
                self.sd.set_current_view_dm(view_dm)
                self.buffer_lock.release()
                self.start_new_buffer()
                return

        # Shift
        else:
            if not self._is_in_buffer(view_dm):
                self.sd.set_current_view_dm(view_dm)
                self.buffer_lock.release()
                self.start_new_buffer()
                return

        self.sd.set_chunk_size(self.chunk_size)
        self.sd.set_current_view_dm(view_dm)
        self.sd.set_data_map(self.data_map)

        self.buffer_lock.release()

    def _is_in_buffer(self, dm):
        """
        Determines if the requested datamap is in the currently loaded buffer.
        """

        c_ss = self.data_map.get_active_largest_ss()
        n_ss = dm.get_active_largest_ss()

        if (c_ss[0] <= n_ss[0] <= c_ss[1]) and (c_ss[0] <= n_ss[1] <= c_ss[1]):
            return True
        else:
            return False

    # ----- DataSource API -----

    def get_data(self, req_data_map):

        read_ch_idcs = np.where(self.data_map['ch_set'])[0]
        uutc_ss = req_data_map['uutc_ss'][read_ch_idcs]
        obj_uutc_ss = np.empty(len(read_ch_idcs), 'object')
        for i in range(len(read_ch_idcs)):
            obj_uutc_ss[i] = slice(uutc_ss[i][0], uutc_ss[i][1])

        data_out = np.empty(len(self.data_map), object)
        data_out[read_ch_idcs] = self.sd.get_srb_data(read_ch_idcs,
                                                      obj_uutc_ss)

        return data_out
