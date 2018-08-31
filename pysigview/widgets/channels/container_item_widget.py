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

# Third pary imports
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QHBoxLayout, QWidget, QLabel, QCheckBox,
                             QLineEdit)

# Local imports
from pysigview.widgets.color_button import ColorButton


class ContainerItemWidget(QWidget):

    def __init__(self, label_text, init_color=(0., 0., 0., 0.)):
        super().__init__()

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignLeft)

        self.check_box = QCheckBox()
#        self.check_box.setMaximumWidth(18)
        self.check_box.setCheckState(Qt.Checked)

        self.color_select = ColorButton(init_color)

        self.label = QLabel(label_text)

        self.setLayout(self.layout)

        self.layout.addWidget(self.check_box)
        self.layout.addWidget(self.color_select)
        self.layout.addWidget(self.label)

    def start_edit_label(self):
        self.line_edit = QLineEdit(self.label.text())
        self.layout.insertWidget(2, self.line_edit)
        self.line_edit.returnPressed.connect(self.finish_edit_label)

    def finish_edit_label(self):
        self.label.setText(self.line_edit.text())
        self.line_edit.hide()

    def set_edit_label(self, text):
        self.label.setText(text)
