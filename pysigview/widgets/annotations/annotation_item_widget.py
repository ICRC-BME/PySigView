#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 20 15:52:24 2017

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

# Third pary imports
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QHBoxLayout, QWidget, QLabel, QCheckBox,
                             QPushButton, QLineEdit)
from PyQt5.QtGui import QIcon

# Local imports
from pysigview.widgets.color_button import ColorButton
from pysigview.config.utils import get_image_path


class AnnotationItemWidget(QWidget):
    def __init__(self, label_text, count=0):
        super().__init__()

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignLeft)

        self.check_box = QCheckBox()
        self.check_box.setMaximumWidth(18)
        self.check_box.setCheckState(Qt.Checked)

        self.color_select = ColorButton()

        self.label = QLabel(label_text)

        self.setLayout(self.layout)

        self.count_label = QLabel(str(count))

        img_path = get_image_path('spreadsheet.svg')
        self.view_btn = QPushButton()
        self.view_btn.setFixedWidth(20)
        self.view_btn.setFixedHeight(20)
        self.view_btn.setStyleSheet("QPushButton{border: 0px;}")
        self.view_btn.setIcon(QIcon(img_path))

        self.layout.addWidget(self.check_box)
        self.layout.addWidget(self.color_select)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.count_label)
        self.layout.addWidget(self.view_btn)

    def set_count(self, count):
        self.count_label.setText(str(count))

    def start_edit_label(self):
        self.line_edit = QLineEdit(self.label.text())
        self.layout.insertWidget(2, self.line_edit)
        self.line_edit.returnPressed.connect(self.finish_edit_label)

    def finish_edit_label(self):
        self.label.setText(self.line_edit.text())
        self.line_edit.hide()
