#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 10:56:28 2017

Basic dock widget for pysigview

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

from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDockWidget


class PysigviewDockWidget(QDockWidget):
    """Subclass to override needed methods"""

    # Signals
    plugin_closed = pyqtSignal()

    # Dock defaults
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable

    def __init__(self, title, parent):
        super(PysigviewDockWidget, self).__init__(title, parent)

        # Covenience transcripts
        self.title = title
        self.main = parent
        self.dock_tabbar = None

    def closeEvent(self, event):
        """
        Reimplement Qt method to send a signal on close so that "Panes" main
        window menu can be updated correctly
        """
        self.plugin_closed.emit()
