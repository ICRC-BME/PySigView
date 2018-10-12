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
from multiprocessing import Process, Manager, Lock, Event as pEvent
from threading import Event as tEvent
from threading import Thread
from time import time
from tempfile import gettempdir

# import tempfile - this will be used with bcolz

# Third party imports
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject

# Local imports
from pysigview.core import source_manager as sm
from pysigview.core.source_manager import BufferDataSource
from pysigview.core.pysigviewmultiringbuffer import PysigviewMultiRingBuffer


def fill_roll_buffer(proxy_sd, stop_event, proc_lock,
                     chunks_before, chunks_after):

    # Some recording info
    rec_start = sm.ODS.recording_info['recording_start']
    rec_end = sm.ODS.recording_info['recording_end']

    # Internal shared dictionary
    subp_sd = dict()

    # ----- Initiate the proxy functions -----
    def download_proxy():
        subp_sd['srb'] = proxy_sd['srb']
        subp_sd['chunk_size'] = proxy_sd['chunk_size']
        subp_sd['data_map'] = proxy_sd['data_map']
        subp_sd['current_view_dm'] = proxy_sd['current_view_dm']

    def upload_proxy():
        proxy_sd['srb'] = subp_sd['srb']
        proxy_sd['chunk_size'] = subp_sd['chunk_size']
        proxy_sd['data_map'] = subp_sd['data_map']

    download_proxy()

    # ----- Revise this section for unnecessary variables -----

    # Variables need for the process run
    load_dm = subp_sd['data_map']
    load_dm['uutc_ss'][:, 1] += subp_sd['chunk_size']
    load_ss = load_dm.get_active_largest_ss()

    # -------------

    if subp_sd['chunk_size'] == proxy_sd['chunk_size']:
        print('Variable synch succesfull!')
        print('Data dm active channels')
        print(subp_sd['data_map'].get_active_channels())

    while True:

        download_proxy()

        if stop_event.is_set():
            return

        # No actvie channels
        if not len(load_dm.get_active_channels()):
            continue

        buff_size = (chunks_before + chunks_after + 1) * subp_sd['chunk_size']
        ring_ss = [subp_sd['srb'].uutc_ss[:, 0].min(),
                   subp_sd['srb'].uutc_ss[:, 1].max()]
        buffer_ss = subp_sd['data_map'].get_active_largest_ss()

        # ----- Buffer filling -----
        buffer_filled = np.diff(buffer_ss)[0] == buff_size

        if not buffer_filled:

            # ----- Forward direction -----

            load_dm['uutc_ss'][:, 0] = buffer_ss[1]
            load_dm['uutc_ss'][:, 1] = buffer_ss[1] + subp_sd['chunk_size']
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
                # print('Channels:',channels)
                # print('UUTC_ss:',uutc_ss)
                subp_sd['srb'][channels,
                               uutc_ss[0]:uutc_ss[1]] = data[channels]
                subp_sd['data_map']['uutc_ss'][:, 1] = uutc_ss[1]
                upload_proxy()
                proc_lock.release()

            # ----- Backward direction -----

            load_dm['uutc_ss'][:, 0] = buffer_ss[0] - subp_sd['chunk_size']
            load_dm['uutc_ss'][:, 1] = buffer_ss[0]
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
                # print('Channels:',channels)
                # print('UUTC_ss:',uutc_ss)
                subp_sd['srb'][channels,
                               uutc_ss[0]:uutc_ss[1]] = data[channels]
                subp_sd['data_map']['uutc_ss'][:, 0] = uutc_ss[0]
                upload_proxy()
                proc_lock.release()

            continue

        # ----- Buffer rolling -----

        if subp_sd['current_view_dm'] is None:
            continue

        # Calculate the non-rolling point

        view_ss = subp_sd['current_view_dm'].get_active_largest_ss()

        # Determine the nonroling point
        nonr_ss = [buffer_ss[0] + chunks_before * subp_sd['chunk_size'],
                   buffer_ss[0] + (chunks_before + 1) * subp_sd['chunk_size']]

        midpoint_diff = int(np.sum(view_ss) / 2 - np.sum(nonr_ss) / 2)

        if midpoint_diff > 0 and buffer_ss[1] < rec_end:

            # Determine the loadmap
            load_dm['uutc_ss'][:, 0] = buffer_ss[1]
            load_dm['uutc_ss'][:, 1] = buffer_ss[1] + midpoint_diff

            # Load data
            data = sm.ODS.get_data(load_dm)

            # Determine the channels and times
            channels = np.where(load_dm['ch_set'])[0]
            uutc_ss = load_dm.get_active_largest_ss()

            # Roll the rolling buffer and upload the data
            proc_lock.acquire()
            subp_sd['srb'].roll(midpoint_diff)
            subp_sd['srb'][channels, uutc_ss[0]:uutc_ss[1]] = data[channels]
            subp_sd['data_map']['uutc_ss'] += midpoint_diff
            upload_proxy()
            proc_lock.release()

        elif midpoint_diff < 0 and buffer_ss[0] > rec_start:

            # Determine the loadmap
            load_dm['uutc_ss'][:, 1] = buffer_ss[0]
            load_dm['uutc_ss'][:, 0] = buffer_ss[0] + midpoint_diff

            # Load data
            data = sm.ODS.get_data(load_dm)

            # Determine the channels and times
            channels = np.where(load_dm['ch_set'])[0]
            uutc_ss = load_dm.get_active_largest_ss()

            # Roll the rolling buffer and upload the data
            proc_lock.acquire()
            subp_sd['srb'].roll(midpoint_diff)
            subp_sd['srb'][channels, uutc_ss[0]:uutc_ss[1]] = data[channels]
            subp_sd['data_map']['uutc_ss'] += midpoint_diff
            upload_proxy()
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

        self.chunk_size = int(10*1e6)  # Will be at CONF
        self.N_chunks_before = 1  # Will be at CONF
        self.N_chunks_after = 10  # Will be at CONF
        self.N_chunks = self.N_chunks_before + self.N_chunks_after + 1
        self.use_disk = True

        # ----- Buffer process -----

        self.buffer_manager = Manager()

        self.buffer_stop = None
        self.buffer_process = None
        self.srb = None

        # Shared dictionary - a dictionary because we have to reasign the
        # so that the proxies are aware that something has changed

        self.proxy_sd = self.buffer_manager.dict()
        self.upload_proxy()
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
        self.proxy_sd['srb'].purge_data()

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
                                      args=(self.proxy_sd,
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
        if self.current_view_dm is None:
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

        if self.use_disk:
            datadir = gettempdir()
        else:
            datadir = None

        self.srb = PysigviewMultiRingBuffer(n_elem, sizes, float, uutc_ss,
                                            fsamps, datadir)

        self.upload_proxy()

    def monitor_buffer(self):
        prev_ss = self.proxy_sd['data_map'].get_active_largest_ss()
        while True:
            if self.thread_stop.is_set():
                return
            prox_ss = self.proxy_sd['data_map'].get_active_largest_ss()
            if np.any(prev_ss != prox_ss):
                self.download_proxy()
                self.state_changed.emit()
                prev_ss = self.proxy_sd['data_map'].get_active_largest_ss()

    def download_proxy(self):

        self.srb = self.proxy_sd['srb']
        self.chunk_size = self.proxy_sd['chunk_size']
        self.data_map = self.proxy_sd['data_map']

    def upload_proxy(self):

        self.proxy_sd['srb'] = self.srb
        self.proxy_sd['chunk_size'] = self.chunk_size
        self.proxy_sd['data_map'] = self.data_map
        self.proxy_sd['current_view_dm'] = self.current_view_dm

    def update(self, view_dm):
        """
        Function to update the ring buffer, alternatively start new process
        """

        self.buffer_lock.acquire()

        self.download_proxy()

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

            self.current_view_dm = view_dm
            self.buffer_lock.release()
            self.start_new_buffer()
            return

        # ----- Tackling the time changes -----
        new_chunk_size = np.diff(self.curr_view_times)
        chunk_diff = new_chunk_size - self.chunk_size

        # TODO - put enalarge and shrink into same block of code
        # it is essentially the same thing. is different for the basic
        # ring buffer. tackle problems with rounding

        # Shrink & enlarge
        if chunk_diff < 0:
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

                self.srb.shrink(-chunk_diff*self.N_chunks,
                                fb_ratio=fb_ratio)

                self._shirnk_data_map(-chunk_diff*self.N_chunks, fb_ratio)

            else:
                self.buffer_lock.release()
                self.start_new_buffer()
                return

        # Enlarge
        elif chunk_diff > 0:
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

                self.srb.enlarge(chunk_diff*self.N_chunks,
                                 fb_ratio=fb_ratio)
            else:
                self.buffer_lock.release()
                self.start_new_buffer()
                return

        # Shift
        else:
            if not self._is_in_buffer(view_dm):
                self.buffer_lock.release()
                self.start_new_buffer()
                return

        self.current_view_dm = view_dm

        # Update proxies
        self.upload_proxy()

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

    def _change_data_map_size(self, by, fb_ratio):
        self.data_map['uutc_ss'][:, 0] -= int((by * (1-fb_ratio)) + 0.5)
        self.data_map['uutc_ss'][:, 1] += int((by * fb_ratio) + 0.5)

    def _shirnk_data_map(self, by, fb_ratio):
        self.data_map['uutc_ss'][:, 0] += int((by * (1-fb_ratio)) + 0.5)
        self.data_map['uutc_ss'][:, 1] -= int((by * fb_ratio) + 0.5)

    def _enlarge_data_map(self, by, fb_ratio):
        self.data_map['uutc_ss'][:, 0] -= int((by * (1-fb_ratio)) + 0.5)
        self.data_map['uutc_ss'][:, 1] += int((by * fb_ratio) + 0.5)

    # ----- DataSource API -----

    def get_data(self, req_data_map):
        
        t = time()
                
        print('Proxy sync in',time()-t)
        
        t = time()
        
        read_ch_idcs = np.where(self.data_map['ch_set'])[0]
        uutc_ss = req_data_map['uutc_ss'][read_ch_idcs]
        obj_uutc_ss = np.empty(len(read_ch_idcs), 'object')
        for i in range(len(read_ch_idcs)):
            obj_uutc_ss[i] = slice(uutc_ss[i][0], uutc_ss[i][1])

        data_out = np.empty(len(self.data_map), object)
        for i in range(len(data_out)):
            data_out[i] = np.array([], dtype='float32')
            
        print('Array and indices preparation',time()-t)
                     
        t = time()
            
        data_out[read_ch_idcs] = self.proxy_sd['srb'][read_ch_idcs,
                                                      obj_uutc_ss]

        print('Data from ring buffer in',time()-t)

        return data_out
