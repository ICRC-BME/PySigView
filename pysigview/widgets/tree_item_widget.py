#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 08:37:21 2017

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
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QHBoxLayout, QWidget, QLabel, QCheckBox)

# Local imports
from pysigview.widgets.color_button import ColorButton


class TreeItemWidget(QWidget):
    def __init__(self, label_text):
        super().__init__()

        self.layout = QHBoxLayout()

        self.check_box = QCheckBox()
        self.check_box.setMaximumWidth(18)
        self.check_box.setCheckState(Qt.Checked)

        self.color_select = ColorButton()

        self.label = QLabel(label_text)

        self.layout.addWidget(self.check_box)
        self.layout.addWidget(self.color_select)
        self.layout.addWidget(self.label)

        self.setLayout(self.layout)
