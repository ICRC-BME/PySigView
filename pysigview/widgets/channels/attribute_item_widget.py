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
from PyQt5.QtWidgets import (QHBoxLayout, QWidget, QLabel, QLineEdit,
                             QCheckBox)
from PyQt5.QtCore import pyqtSignal

# Local imports


class AttributeItemWidget(QWidget):

    item_changed = pyqtSignal(name='items_changed')

    def __init__(self, label_text, value, editable):
        super().__init__()

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self._value = value
        self._is_bool = isinstance(value, bool)

        self.label = QLabel(label_text)
        if isinstance(self._value, bool):
            self.value_field = QCheckBox()
            self.value_field.setChecked(self._value)
            self.value_field.setCheckable(~editable)
            self.value_field.clicked.connect(self.emit_field_changed)
        else:
            self.value_field = QLineEdit(str(self._value))
            self.value_field.setReadOnly(editable)
            self.value_field.returnPressed.connect(self.emit_field_changed)

        self.setLayout(self.layout)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.value_field)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self._is_bool:
            self.value_field.setChecked(value)
        else:
            self.value_field.setText(str(value))

    def emit_field_changed(self):
        if self._is_bool:
            self._value = self.value_field.isChecked()
        else:
            self._value = self.value_field.text()
        self.item_changed.emit()
