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
from PyQt5.QtWidgets import (QHBoxLayout, QWidget, QLabel, QLineEdit)

# Local imports


class AttributeItemWidget(QWidget):
    def __init__(self, label_text, value, editable):
        super().__init__()

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)


#        self.check_box = QCheckBox()
#        self.check_box.setMaximumWidth(18)
#        self.check_box.setCheckState(Qt.Checked)

#        self.color_select = ColorButton(init_color)

        self.label = QLabel(label_text)

        self.value_le = QLineEdit(str(value))
        self.value_le.setReadOnly(editable)

        self.setLayout(self.layout)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.value_le)
