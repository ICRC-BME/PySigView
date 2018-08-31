#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 22 13:14:09 2017

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

# Local imports

# =============================================================================
# Data maps
# =============================================================================


class DataMap:
    """
    Class to store channel maps and uutc maps
    """
    def __init__(self):
        super(DataMap, self).__init__()

        self._map = np.array([], dtype=[('channels', object, 1),
                                        ('ch_set', np.bool, 1),
                                        ('uutc_ss', np.int64, 2)])

    def __getitem__(self, item):
        return self._map[item]

    def __setitem__(self, item, value):
        self._map[item] = value
        return

    def __len__(self):
        return len(self._map)

#    def __repr__(self):
#        return self.print_data_map()
#
#    def __str__(self):
#        return self.print_data_map()
#
#    def print_data_map(self):
#        header = self._map.dtype.names
#        row_format ="{:>15}" * (len(header) + 1)
#        print(row_format.format('', *header))
#        for i in range(len(self)):
#            self[i]

    def setup_data_map(self, dmap):
        self._map = np.copy(dmap)
        return

    def set_data_map(self, channels, uutc_sss):
        for channel, uutc_ss in zip(channels, uutc_sss):
            self.set_channel(channel, uutc_ss)
        return

    def reset_data_map(self):
        for channel in self._map['channels']:
            self.remove_channel(channel)
        return

    def remove_channel(self, channel):
        ci = np.in1d(self._map['channels'], channel)
        self._map['ch_set'][ci] = False
        self._map['uutc_ss'][ci] = [0, 0]
        return

    def set_channel(self, channel, uutc_ss):
        ci = np.in1d(self._map['channels'], channel)
        self._map['ch_set'][ci] = True
        self._map['uutc_ss'][ci] = uutc_ss
        return

    def get_active_channels(self):
        return self._map['channels'][self._map['ch_set']]

    def get_active_uutc_ss(self):
        return self._map['uutc_ss'][self._map['ch_set']]

    def get_active_largest_ss(self):
        uutc_ss = self.get_active_uutc_ss()
        if len(uutc_ss):
            return np.array([np.min(uutc_ss[:, 0]), np.max(uutc_ss[:, 1])])
        else:
            return np.array([0, 0])


# =============================================================================
# Data sources
# =============================================================================

class DataSource:
    """
    Superclass for data sources (files, clients, streams, buffers)
    """
    def __init__(self):
        super(DataSource, self).__init__()

#        self.ODS_name = None
        self.data_map = DataMap()
        self.recording_info = None

    def load_metadata(self):
        return None

    def get_metadata(self):
        return None

    def get_data(self):
        return None


class FileDataSource(DataSource):
    """
    Class for source that will read data directly from the disk
    """
    def __init__(self):
        super(FileDataSource, self).__init__()

        self.extension = None
        self._path = None
        self._password = None

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = password


class ClientDataSource(DataSource):
    """
    Class for source that will read from server
    """
    def __init__(self, ip=None, port=None):
        super(ClientDataSource, self).__init__()

        self._ip = ip
        self._port = port

    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, ip):
        self._ip = ip

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    def connect(self):
        return None

    def get_directory_tree(self):
        return None


class StreamDataSource(DataSource):
    """
    Class for source that will read from server
    """
    def __init__(self):
        super(StreamDataSource, self).__init__()


class BufferDataSource(DataSource):
    """
    Superclass for buffer data sources
    """
    def __init__(self):
        super(BufferDataSource, self).__init__()

    def is_available(self, check_dm):
        """
        Compares check_dm with the intrnal data map
        """

        # First find out whether the check_dm channels are in
        if sum(check_dm['ch_set']
               & self.data_map['ch_set']) != sum(check_dm['ch_set']):
            return False

        # Now find out whether the check_dm uutc_sss are in
        for loc, check in zip(self.data_map['uutc_ss'][check_dm['ch_set']],
                              check_dm['uutc_ss'][check_dm['ch_set']]):

            if not (loc[0] <= check[0] <= loc[1]
                    and loc[0] <= check[1] <= loc[1]):
                return False

        return True


# =============================================================================
# Cross-module constants
# =============================================================================

# Original data source (i.e: file/stream/client)
ODS = DataSource()

# Provider data source (i.e: the above + buffers)
PDS = DataSource()
