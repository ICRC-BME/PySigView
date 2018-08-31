#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  6 09:27:15 2017

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
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QColorDialog, QPushButton

# Local imports
from pysigview.config.utils import get_image_path


class ColorButton(QPushButton):

    color_changed = pyqtSignal(QColor, name='color_changed')

    def __init__(self, init_color=(1., 0., 0., 1.)):
        super(ColorButton, self).__init__()

        # Set button parameters
        self.setFixedWidth(20)
        self.setFixedHeight(20)
        self.setStyleSheet("QPushButton{border: 0px;}")

        # Create icon
        img_path = get_image_path('circle.svg')
        self.pixmap = QIcon(img_path).pixmap(20)
        self.mask = self.pixmap.createMaskFromColor(QColor(0, 0, 0, 0))

        r = int(init_color[0]*255)
        g = int(init_color[1]*255)
        b = int(init_color[2]*255)
        a = int(init_color[3]*255)

        self.pixmap.fill(QColor(r, g, b, a))
        self.pixmap.setMask(self.mask)

        self.setIcon(QIcon(self.pixmap))

        self.clicked.connect(self.change_color)

    def set_color(self, color):
        r = int(color[0]*255)
        g = int(color[1]*255)
        b = int(color[2]*255)
        a = int(color[3]*255)

        self.pixmap.fill(QColor(r, g, b, a))
        self.pixmap.setMask(self.mask)

        self.setIcon(QIcon(self.pixmap))

    def change_color(self):

        self.color_dialog = QColorDialog()
        res = self.color_dialog.exec_()

        if not res:
            return

        new_color = QColor(self.color_dialog.selectedColor())

        self.pixmap.fill(new_color)
        self.pixmap.setMask(self.mask)

        self.setIcon(QIcon(self.pixmap))

        self.color_changed.emit(new_color)
