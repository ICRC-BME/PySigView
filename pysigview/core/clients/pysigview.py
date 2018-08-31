#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 16:03:39 2018

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
from pysigview_cs.cs.client import PysigviewClient

# Local imports
from ..source_manager import ClientDataSource


class pysigviewHandler(ClientDataSource):
    def __init__(self):
        super(pysigviewHandler, self).__init__()

        self.name = 'Pysigview client'
        self.type = 'Pysigview'

        self.client = PysigviewClient()

    def connect(self):
        if self._ip:
            self.client.ip = self._ip
        if self._port:
            self.client.port = self._port

        self.client.connect()

    def get_directory_tree(self):
        return self.client.request_directory_tree()

    def set_file_handler(self, path, password):
        return self.client.set_file_handler(path, password)

    def load_metadata(self):

        ri, dm = self.client.request_metadata()

        self.recording_info = self.client.recording_metadata
        self.data_map.setup_data_map(self.client.data_map)

    def get_annotations(self):
        """
        Returns:
        --------
        Annotations - in form of pandas DataFrame(s)
        """

        return self.client.request_annotations()

    def get_data(self, data_map):
        """
        Parameters:
        -----------
        data_map - DataMap instance for loading

        Returns:
        --------
        The data in a list specified by channel_map
        """

        return self.client.request_data_data_map(data_map)
