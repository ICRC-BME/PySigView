#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 13:10:38 2018

Thread workers

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
import time

# Third pary imports
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from PyQt5.QtWidgets import QApplication

# Local imports


class TimerWorker(QObject):
    """
    Worker for sending signals after some time hase passed
    """

    time_started = pyqtSignal()
    time_passed = pyqtSignal()

    def __init__(self, loop_time):
        super().__init__()
        self._interupt_flag = False
        self._loop_time = loop_time

    @pyqtSlot()
    def run(self):
        while True:
            self.time_started.emit()
            time.sleep(self._loop_time)
            QApplication.processEvents()
            if self._interupt_flag:
                break
            self.time_passed.emit()

        self._interupt_flag = False

        return

    @pyqtSlot()
    def interupt(self):
        self._interupt_flag = True

    @pyqtSlot()
    def set_loop_time(self, time):
        self._loop_time = time
