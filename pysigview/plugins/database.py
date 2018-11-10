#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  8 12:23:24 2017

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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QFormLayout, QLabel, QLineEdit, QPushButton,
                             QComboBox, QMessageBox)

import sqlalchemy as sqla
from sqlalchemy.exc import OperationalError

# Local imports
from pysigview.config.main import CONF

from pysigview.plugins.base import BasePluginWidget


class Database(BasePluginWidget):

    CONF_SECTION = 'database'
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = False
    shortcut = None

    conn_created = pyqtSignal(name='conn_created')
    conn_closed = pyqtSignal(name='conn_closed')

    def __init__(self, parent):
        BasePluginWidget.__init__(self, parent)

        # Widget configiration
        self.ALLOWED_AREAS = Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        self.LOCATION = Qt.RightDockWidgetArea

        # Presets for the main window
        self.title = 'Database'
        self.main = parent
        self.conn = None

        # Create the form layout
        self.win_layout = QFormLayout(self)

        # Create widgets and labels
        db_type_label = QLabel('Database type:')
        self.db_type_cb = QComboBox(self)
        self.db_type_cb.addItem('mysql')
        self.win_layout.addRow(db_type_label, self.db_type_cb)

        host_label = QLabel('Host:')
        self.host_le = QLineEdit(CONF.get(self.CONF_SECTION, 'host'))
        self.win_layout.addRow(host_label, self.host_le)

        port_label = QLabel('Port:')
        self.port_le = QLineEdit(str(CONF.get(self.CONF_SECTION, 'port')))
        self.win_layout.addRow(port_label, self.port_le)

        user_label = QLabel('Username:')
        self.user_le = QLineEdit(CONF.get(self.CONF_SECTION, 'username'))
        self.win_layout.addRow(user_label, self.user_le)

        passwd_label = QLabel('Password:')
        self.passwd_le = QLineEdit()
        self.passwd_le.setEchoMode(QLineEdit.EchoMode(2))
        self.win_layout.addRow(passwd_label, self.passwd_le)

        self.connect_btn = QPushButton('Connect')
        self.connect_btn.clicked.connect(self.create_connection)
        self.win_layout.addRow(self.connect_btn)

        self.disconnect_btn = QPushButton('Disconnect')
        self.disconnect_btn.clicked.connect(self.close_connection)
        self.win_layout.addRow(self.disconnect_btn)

    def store_settings(self):
        CONF.set(self.CONF_SECTION, 'host', self.host_le.text())
        CONF.set(self.CONF_SECTION, 'port', self.port_le.text())
        CONF.set(self.CONF_SECTION, 'username', self.user_le.text())

    def create_connection(self):

        db_type = self.db_type_cb.currentText()

        if db_type == 'mysql':
            conn_str = 'mysql+pymysql://{}:{}@{}:{}'

        # Construct the connection string
        conn_str = conn_str.format(self.user_le.text(),
                                   self.passwd_le.text(),
                                   self.host_le.text(),
                                   self.port_le.text())
        engine = sqla.create_engine(conn_str)

        # Try to connect
        try:
            conn = engine.connect()
        except OperationalError as e:
            print(e.orig)
            QMessageBox.critical(self, "Connection failed",
                                 str(e.orig))
            return

        # Store as default on success
        self.store_settings()

        self.conn = conn
        self.conn_created.emit()
        self.main.statusBar().showMessage('Connection created', 2000)

        return

    def close_connection(self):

        if self.conn is not None:
            self.conn.close()
            self.conn_closed.emit()
            self.main.statusBar().showMessage('Connection closed', 2000)

    # ------ PysigviewPluginWidget API ----------------------------------------
    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        pass

    def get_plugin_title(self):
        """Return widget title"""
        return self.title

    def get_plugin_icon(self):
        """Return widget icon"""
#        return ima.icon('help')
        return None

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        # TODO - focus on channel list
#        self.combo.lineEdit().selectAll()
#        return self.combo
        return None

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def register_plugin(self):
        """Register plugin in Pysigview's main window"""
#        self.focus_changed.connect(self.main.plugin_focus_changed)

        self.create_toggle_view_action()

        # Connect the annotation plugin if present
        if hasattr(self.main, 'annotations'):
            self.conn_created.connect(self.main.annotations.active_db_buttons)

        self.main.add_dockwidget(self)

    def delete_plugin_data(self):
        """Deletes plugin data"""
        return None

    def load_plugin_data(self, data):
        """Function to run when loading session"""
        return None

    def save_plugin_data(self):
        """Function to run when saving session"""
        return None

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def refresh_plugin(self):
        """Refresh widget"""
        if self._starting_up:
            self._starting_up = False
