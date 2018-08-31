#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 09:23:17 2017

Annotations plugin for pysigview

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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout,
                             QWidget, QLineEdit,
                             QComboBox, QLabel, QMessageBox, QPushButton)

from scipy.signal import butter, filtfilt

# Local imports
from pysigview.core.plot_transform import BasePlotTransform


class FilterTransform(BasePlotTransform):

    def __init__(self, parent):
        super().__init__(parent)

        self.a = None
        self.b = None

    def apply_transform(self, data):
        return filtfilt(self.b, self.a, data)


class Filters(QWidget):

    # Attributes
    CONF_SUBSECTION = 'filters'
    IMG_PATH = 'images'
    shortcut = None

    # Signals
    filters_transform_changed = pyqtSignal(name='filters_transform_changed')

    def __init__(self, parent):
        super(Filters, self).__init__(parent)

        self.transform_list_stack = self.parent()
        self.preview = self.transform_list_stack.parent().signal_preview
        self.main = self.transform_list_stack.main

        self.title = 'Filters'

        # Transform
        self.preview_transform = None

        # Master layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Filter design widget layout
        filter_layout = QVBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)

        # Filter selector
        self.filter_selector_label = QLabel('Select filter type:', self)
        self.filter_selector = QComboBox(self)
        self.filter_selector.addItem('Butterworth')

        # Filter cut-offs
        self.low_cutoff_label = QLabel('Low cutoff:', self)
        self.low_cutoff_le = QLineEdit(self)

        self.high_cutoff_label = QLabel('High cutoff:', self)
        self.high_cutoff_le = QLineEdit(self)

        # Poles
        self.poles_label = QLabel('N poles:', self)
        self.poles_le = QLineEdit(self)

        # Set button
        self.set_button = QPushButton('Set', self)

        # Vipy canvas with axes for FFT

        #TODO - filter for number only in lineedits
        # Asseble the layout
        filter_layout.addWidget(self.filter_selector_label)
        filter_layout.addWidget(self.filter_selector)

        filter_layout.addWidget(self.low_cutoff_label)
        filter_layout.addWidget(self.low_cutoff_le)

        filter_layout.addWidget(self.high_cutoff_label)
        filter_layout.addWidget(self.high_cutoff_le)

        filter_layout.addWidget(self.poles_label)
        filter_layout.addWidget(self.poles_le)

        filter_layout.addWidget(self.set_button)

        layout.addLayout(filter_layout)
        layout.setAlignment(Qt.AlignTop)

        self.setLayout(layout)

        # Connect signals
        self.filter_selector.currentIndexChanged.connect(
                self.set_preview_transform)
        self.low_cutoff_le.returnPressed.connect(self.set_preview_transform)
        self.high_cutoff_le.returnPressed.connect(self.set_preview_transform)
        self.poles_le.returnPressed.connect(self.set_preview_transform)
        self.set_button.clicked.connect(self.set_preview_transform)

    def create_transform(self, vc):

        fs = vc.fsamp
        if fs is None:
            return

        # Design the filter
        selected_filter = self.filter_selector.currentText()
        low_fc_str = self.low_cutoff_le.text()
        high_fc_str = self.high_cutoff_le.text()
        poles_str = self.poles_le.text()

        if poles_str == '':
            QMessageBox.Warning('Number of poles must by specified')
            return
        else:
            poles = int(poles_str)

        if low_fc_str == '':
            low_fc = None
        else:
            low_fc = float(low_fc_str)
        if high_fc_str == '':
            high_fc = None
        else:
            high_fc = float(high_fc_str)

        if low_fc is not None and high_fc is not None and low_fc >= high_fc:
            QMessageBox.Warning('Low cut-off frequency cannot be higher',
                                'than high cut-off frequency')
            return

        if selected_filter == 'Butterworth':
            if low_fc and high_fc:
                b, a = butter(poles, [low_fc/(fs/2),
                                      high_fc/(fs/2)], 'bandpass')
            elif low_fc and not high_fc:
                b, a = butter(poles, low_fc/(fs/2), 'highpass')
            elif not low_fc and high_fc:
                b, a = butter(poles, high_fc/(fs/2), 'lowpass')
            else:
                return

        # Greate the transform object
        transform = FilterTransform(self)
        transform.a = a
        transform.b = b
        transform.name = (' / ' + selected_filter + '; '
                          + '-'.join([low_fc_str, high_fc_str]) + 'Hz')
        # Set directly - we do not want to modify the original container!
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

        return
