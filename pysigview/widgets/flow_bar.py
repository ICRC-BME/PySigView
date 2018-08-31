#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 09:24:25 2017

Widget to indicate that application is busy

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
from PyQt5.QtWidgets import QProgressDialog, QProgressBar

# Local imports


class FlowBar(QProgressDialog):
    def __init__(self):
        super().__init__()

        self.pbar = QProgressBar()
        self.pbar.setRange(0, 1)
        self.setBar(self.pbar)

        self.setAutoClose(True)
