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

from pydread import read_d_header, read_d_data

# Local imports
from ..source_manager import FileDataSource


class dHandler(FileDataSource):
    def __init__(self):
        super(dHandler, self).__init__()

        self.name = 'D-file'
        self.extension = '.d'

    def load_metadata(self):

        sh, xh = read_d_header(self._path)

        rec_start = int(xh['time_info'] * 1e6)
        rec_stop = int(rec_start + (sh['nsamp'] / sh['fsamp']) * 1e6)
        rec_dur = rec_stop - rec_start

        # Get information about the recording
        self.recording_info = {}
        self.recording_info['recording_start'] = rec_start
        self.recording_info['recording_end'] = rec_stop
        self.recording_info['recording_duration'] = rec_dur
        self.recording_info['extension'] = '.d'
        self.recording_info['nchan'] = sh['nchan']

        # Get information about channels

        channel_list = xh['channel_names']

        dmap = np.zeros(len(channel_list),
                        dtype=[('fsamp', np.float, 1),
                               ('nsamp', np.int32, 1),
                               ('ufact', np.float, 1),
                               ('unit', np.object, 1),
                               ('channels', np.object, 1),
                               ('discontinuities', np.ndarray, 1),
                               ('ch_set', np.bool, 1),
                               ('uutc_ss', np.int64, 2)])

        for i, channel in enumerate(channel_list):
            fsamp = sh['fsamp']
            nsamp = sh['nsamp']
            ufact = 1/sh['unit']
            unit = 'uV'
            start_time = rec_start
            end_time = rec_stop
            disconts = np.c_[rec_start, rec_start]

            dmap[i] = (fsamp, nsamp, ufact, unit, channel, disconts,
                       True, [start_time, end_time])

        self.data_map.setup_data_map(dmap)

    def get_annotations(self):
        """
        Returns:
        --------
        Annotations - in form of pandas DataFrame(s)
        """

        sh, xh = read_d_header(self._path)
        rec_start = int(xh['time_info']*1e6)

        # Basic annotation columns
        basic_cols = ['start_time', 'end_time', 'channel', 'note']

        df = pd.DataFrame(columns=basic_cols)
        for i, tag in enumerate(xh['tags']):
            time = int(rec_start + (tag[0] / sh['fsamp']) * 1e6)
            col_vals = {'start_time': time,
                        'end_time': np.nan,
                        'channel': np.nan,
                        'note': ''}
            df.loc[i] = col_vals

        dfs_out = {'tags': df}

        # Get tags and convert them to dataframe

        return dfs_out

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

        sh, xh = read_d_header(self._path)

        rec_start = int(xh['time_info'] * 1e6)
        samp_ss = [int(((x-rec_start)/1e6)*sh['fsamp']) for x in uutc_ss]

        channel_idxs = [i for i, x in enumerate(xh['channel_names'])
                        if x in channel_map]

        data = read_d_data(self._path, channel_idxs, samp_ss[0], samp_ss[1])
        data = data.T

        data_out = np.empty(len(data_map), object)
        for i in range(len(data_map)):
            data_out[i] = np.array([], dtype='float32')
        for i, ch in enumerate(channel_map):
            ch_pos = np.argwhere(data_map['channels'] == ch)[0][0]
            data_out[ch_pos] = data[i]

        return data_out
