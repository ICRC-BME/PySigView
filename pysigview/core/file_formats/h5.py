#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 13:49:27 2018

Ing.,Mgr. (MSc.) Jan Cimbálník, PhD.
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

# Std imports

# Third pary imports
import numpy as np
import pandas as pd

import h5py

# Local imports
from ..source_manager import FileDataSource


class h5Handler(FileDataSource):
    def __init__(self):
        super(h5Handler, self).__init__()

        self.name = 'SignalPlant HDF'
        self.extension = '.h5'

        self.hf = None

    def load_metadata(self):

        if self.hf is None:
            self.hf = h5py.File(self._path, 'r')

        try:
            dataset = self.hf['Data']
        except:
            dataset = self.hf['data']

        nsamp = dataset.shape[1]

        if self.hf.attrs.get('time_info'):
            rec_start = int(self.hf.attrs['time_info'] * 1e6)
        else:
            rec_start = 0
        rec_stop = int(rec_start + (nsamp / self.hf.attrs['Fs']) * 1e6)
        rec_dur = rec_stop - rec_start

        # Get information about the recording
        self.recording_info = {}
        self.recording_info['recording_start'] = rec_start
        self.recording_info['recording_end'] = rec_stop
        self.recording_info['recording_duration'] = rec_dur
        self.recording_info['extension'] = '.h5'
        self.recording_info['nchan'] = len(self.hf['Info'])

        # Get information about channels

        channel_list = [x for x in self.hf['Info']]

        dmap = np.zeros(len(channel_list),
                        dtype=[('fsamp', np.float, 1),
                               ('nsamp', np.int32, 1),
                               ('ufact', np.float, 1),
                               ('unit', np.object, 1),
                               ('channels', np.object, 1),
                               ('discontinuities', np.ndarray, 1),
                               ('ch_set', np.bool, 1),
                               ('uutc_ss', np.int64, 2)])

        for i, channel_info in enumerate(self.hf['Info']):
            fsamp = self.hf.attrs['Fs']
            if self.hf.attrs.get('unit'):
                ufact = 1/self.hf.attrs['unit']
            else:
                ufact = 1
            unit = channel_info[2].decode('UTF-8')
            start_time = rec_start
            end_time = rec_stop
            disconts = np.c_[rec_start, rec_start]

            dmap[i] = (fsamp, nsamp, ufact, unit,
                       channel_info[0].decode('UTF-8'), disconts,
                       True, [start_time, end_time])

        self.data_map.setup_data_map(dmap)

    def get_annotations(self):
        """
        Returns:
        --------
        Annotations - in form of pandas DataFrame(s)
        """

        return None

    def get_data(self, data_map):
        """
        Parameters:
        -----------
        data_map - DataMap instance for loading

        Returns:
        --------
        The data in a list specified by channel_map
        """

        channel_map = data_map.get_active_channels()
        uutc_ss = data_map.get_active_largest_ss()

        if self.hf is None:
            self.hf = h5py.File(self._path, 'r')

        channels = [x[0].decode('UTF-8') for x in self.hf['Info']]

        if self.hf.attrs.get('time_info') is not None:
            rec_start = int(self.hf.attrs['time_info'] * 1e6)
        else:
            rec_start = 0
        samp_ss = [int(((x-rec_start)/1e6)*self.hf.attrs['Fs'])
                   for x in uutc_ss]

        channel_idxs = [i for i, x in enumerate(channels)
                        if x in channel_map]

        try:
            dataset = self.hf['Data']
        except:
            dataset = self.hf['data']
        dmat = dataset.value[channel_idxs, samp_ss[0]: samp_ss[1]]

        data_out = np.empty(len(data_map), object)
        for i in range(len(data_map)):
            data_out[i] = np.array([], dtype='float32')
        for i, ch in enumerate(channel_map):
            ch_pos = np.argwhere(data_map['channels'] == ch)[0][0]
            data_out[ch_pos] = dmat[i]

        return data_out
