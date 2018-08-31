#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Power signal transform

Vladimir Sladky
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
from numpy import abs
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QCheckBox,
                             QWidget, QComboBox, QLabel, QPushButton)

from scipy.signal import hilbert

# Local imports
from pysigview.core.plot_transform import BasePlotTransform


# TODO - move this to plugins subfolder
class EnvelopeTransform(BasePlotTransform):

    def __init__(self, parent):
        super().__init__(parent)

        self.pow = 1

    def apply_transform(self, data):

        return abs(hilbert(data))**self.pow


class Envelopes(QWidget):
    # Attributes
    CONF_SUBSECTION = 'envelopes'
    IMG_PATH = 'images'
    shortcut = None

    # Signals
    filters_transform_changed = pyqtSignal(name='filters_transform_changed')

    def __init__(self, parent):
        super(Envelopes, self).__init__(parent)

        self.transform_list_stack = self.parent()
        self.preview = self.transform_list_stack.parent().signal_preview
        self.main = self.transform_list_stack.main

        self.title = 'Envelopes'

        # Transform
        self.preview_transform = None

        # Master layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Envelope design widget layout
        envelope_layout = QVBoxLayout()
        envelope_layout.setContentsMargins(0, 0, 0, 0)

        # Envelope selector
        self.envelope_selector_label = QLabel('Select envelope type:', self)
        self.envelope_selector = QComboBox(self)
        self.envelope_selector.addItem('Hilbert')

        # Checkbox Power sublayout
        envelope_sublayout = QHBoxLayout()
        envelope_sublayout.setContentsMargins(0, 0, 0, 0)

        self.envelope_check_label = QLabel('Use Power:', self)
        self.envelope_check_power = QCheckBox(self)

        # Set button
        self.set_button = QPushButton('Set', self)

        # Vipy canvas with axes for FFT

        # Assemble the layout
        envelope_layout.addWidget(self.envelope_selector_label)
        envelope_layout.addWidget(self.envelope_selector)

        envelope_sublayout.addWidget(self.envelope_check_label)
        envelope_sublayout.addWidget(self.envelope_check_power)

        envelope_layout.addLayout(envelope_sublayout)
        envelope_layout.addWidget(self.set_button)

        layout.addLayout(envelope_layout)
        layout.setAlignment(Qt.AlignTop)

        self.setLayout(layout)

        # Connect signals
        self.envelope_selector.currentIndexChanged.connect(
                self.set_preview_transform)
        # TODO how connect checkbox to preview, should it be even connected?

        self.set_button.clicked.connect(self.set_preview_transform)

    def create_transform(self, vc):

        fs = vc.fsamp
        if fs is None:
            return

        # Create the transform object
        transform = EnvelopeTransform(self)

        if self.envelope_check_power.isChecked():
            transform.pow = 2

        transform.name = ('/SignalEnvelope')
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
