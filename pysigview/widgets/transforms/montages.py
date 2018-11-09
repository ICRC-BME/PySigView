#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 09:23:17 2017

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

# Third party imports
import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout, QWidget, QComboBox, QLabel,
                             QPushButton)

# Local imports
from pysigview.core.plot_transform import BasePlotTransform
from pysigview.core import source_manager as sm


class MontageTransform(BasePlotTransform):

    def __init__(self, parent):
        super().__init__(parent)

        self.second_channel = None
        self.second_channel_pos = None

    def apply_transform(self, data):

        # We are likely in preview mode in that case load the data directly
        if data.ndim == 1:
            sd = self.parent.main.signal_display
            second_cd_data = sd.data_array[self.second_channel_pos]
            print('Second data is', second_cd_data)
            if type(second_cd_data) == float:
                # We have to load the data here!
                dm = sm.DataMap()
                dm.setup_data_map(sd.data_map._map)
                dm.reset_data_map()
                dm.set_channel(self.second_channel,
                               self.visual_container.uutc_ss)
                second_cd_data = sm.PDS.get_data(dm)[self.second_channel_pos]
                print('Second data is', second_cd_data)

            return data - second_cd_data
        else:
            return data[0] - data[1]

    # Reimplement from the base transform
    def modify_visual_container(self):
        self._vc.add_channels.append(self.second_channel)
        self._vc.data_array_pos.append(self.second_channel_pos)


class Montages(QWidget):

    # Attributes
    CONF_SUBSECTION = 'montages'
    IMG_PATH = 'images'
    shortcut = None

    # Signals
    filters_transform_changed = pyqtSignal(name='filters_transform_changed')

    def __init__(self, parent):
        super(Montages, self).__init__(parent)

        self.transform_list_stack = self.parent()
        self.preview = self.transform_list_stack.parent().signal_preview
        self.main = self.transform_list_stack.main

        self.title = 'Montages'

        # Transform
        self.preview_transform = None

        # Master layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Filter design widget layout
        montage_layout = QVBoxLayout()
        montage_layout.setContentsMargins(0, 0, 0, 0)

        # Montage selector
        self.montage_selector_label = QLabel('Select montage type:', self)
        self.montage_selector = QComboBox(self)
        self.montage_selector.addItem('Unipolar')

        # Channel selector for montage
        self.channel_selector_label = QLabel('Select channel:', self)
        self.channel_selector = QComboBox(self)

        # Set button
        self.set_button = QPushButton('Set', self)

        # Asseble the layout
        montage_layout.addWidget(self.montage_selector_label)
        montage_layout.addWidget(self.montage_selector)
        montage_layout.addWidget(self.channel_selector_label)
        montage_layout.addWidget(self.channel_selector)
        montage_layout.addWidget(self.set_button)

        layout.addLayout(montage_layout)
        layout.setAlignment(Qt.AlignTop)

        self.setLayout(layout)

        # Connect signals
        self.montage_selector.currentIndexChanged.connect(self.set_m_layout)
        self.channel_selector.currentIndexChanged.connect(
                self.set_second_channel)
        self.set_button.clicked.connect(self.set_preview_transform)

    def set_m_layout(self, int):
        return

    def set_second_channel(self, ch_idx):
        if ch_idx < 0:
            return
        self.second_channel = self.channel_selector.itemText(ch_idx)
        self.second_channel_pos = np.where(sm.PDS.data_map['channels']
                                           == self.second_channel)[0][0]

    def set_channels(self):
        # TODO: Show only channels that can be montaged!!! - same fs
        self.channel_selector.clear()
        for channel in sm.ODS.data_map['channels']:
            self.channel_selector.addItem(channel)

    def create_transform(self, vc):

        # Design the filter
        selected_channel = self.channel_selector.currentText()

        # Greate the transform object
        transform = MontageTransform(self)
        transform.second_channel = self.second_channel
        transform.second_channel_pos = self.second_channel_pos
        transform.name = '-'+selected_channel
        transform._vc = vc

        return transform

    # ??? Should be part of transforms API??
    def set_preview_transform(self):

        vc = self.preview.preview_pvc
        self.preview.preview_temp_transform = self.create_transform(vc)
        self.preview.update_trans_sig()

    # ----- Transforms API -----
    def get_transform_title(self):
        """Return widget title"""
        return self.title

    def register_transform(self):
        """
        Register transform in Transforms plugin.
        """

        # Connect signals
        self.main.sig_file_opened.connect(self.set_channels)

        return
