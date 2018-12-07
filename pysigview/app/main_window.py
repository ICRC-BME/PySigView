#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 12 21:50:25 2017

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

PySigView
=====

Python signal viewer based on PyQt and Vispy.

Plugin management, configuration management and some other concepts were
taken and modified from Spyder IDE which is licensed under MIT license
(https://github.com/spyder-ide/)

"""

# =============================================================================
# Stdlib imports
# =============================================================================
import sys
import pickle
import os
import webbrowser

# =============================================================================
# Check requirements
# =============================================================================
# TODO

# =============================================================================
# PyQt imports
# =============================================================================
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSize, QPoint, QByteArray
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox,
                             QSplashScreen, QFileDialog, QInputDialog,
                             QDockWidget, QDialog, QFormLayout, QLineEdit,
                             QLabel, QPushButton, QComboBox)

# =============================================================================
# Local imports
# =============================================================================
from pysigview.core.file_formats.formats import extension_evaluator
from pysigview.core.clients.clients import client_type_evaluator

from pysigview.core import source_manager as sm
from pysigview.core.buffer_handler import MemoryBuffer
from pysigview.core.thread_workers import TimerWorker
from pysigview.config.utils import get_image_path, get_home_dir

# from pysigview.config.system import SYS_INFO
from pysigview.utils.qthelpers import add_actions, create_action
from pysigview.widgets.dir_tree_dialog import DirTreeDialog

# =============================================================================
# Get configuration
# =============================================================================
from pysigview.config.main import CONF

# =============================================================================
# Initialize QApp
# =============================================================================
MAIN_APP = QApplication(sys.argv)
APP_ICON = QIcon(get_image_path("pysigview.svg"))
MAIN_APP.setWindowIcon(APP_ICON)

# =============================================================================
# Createspash screen
# =============================================================================
SPLASH = QSplashScreen(QPixmap(get_image_path('splash.png')))
SPLASH_FONT = SPLASH.font()
SPLASH_FONT.setPixelSize(10)
SPLASH.setFont(SPLASH_FONT)
SPLASH.show()
SPLASH.showMessage("Initializing...", Qt.AlignBottom | Qt.AlignCenter |
                   Qt.AlignAbsolute, QColor(Qt.black))
QApplication.processEvents()

# =============================================================================
# Main window
# =============================================================================


class MainWindow(QMainWindow):
    """Pysigview main window"""

    # Attributes
    DOCKOPTIONS = (QMainWindow.AllowTabbedDocks
                   | QMainWindow.AnimatedDocks
                   | QMainWindow.AllowNestedDocks)

    # Signals
    sig_file_opened = pyqtSignal()
    metadata_reloaded = pyqtSignal()
    stop_metadata_worker = pyqtSignal()
    start_metadata_worker = pyqtSignal()

    def __init__(self, options=None):
        QMainWindow.__init__(self)

        # Ensure bottom and top docks strech only to central widget size
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        # Menu bars
        self.file_menu = None
        self.file_menu_actions = []
        self.plugins_menu = None
        self.plugins_menu_actions = []
        self.help_menu = None
        self.help_menu_actions = []

        # Status bars
        self.mem_status = None
        self.cpu_status = None

        # Tool bars TODO

        # Set window title and icon
        title = "PySigView"
        self.base_title = title
        self.update_window_title()
#        icon = ima.icon('pymef', resample=resample)

        # Show splashscreen
        self.splash = SPLASH

        # List of widgets
        self.plugin_list = []

        # Closing flags to remember the layout
        self.already_closed = False
        self.is_starting_up = True
        self.is_setting_up = True

#        self.dockwidgets_locked = CONF.get('main', 'panes_locked')
        self.floating_dockwidgets = []
        self.window_size = None
#        self.prefs_dialog_size = None
        self.window_position = None
        self.state_before_maximizing = None
        self.current_quick_layout = None
        self.previous_layout_settings = None
        self.last_plugin = None
        self.fullscreen_flag = None  # isFullscreen does not work as expected
        self.maximized_flag = None

        # To keep track of the last focused widget
        self.last_focused_widget = None
        self.previous_focused_widget = None

        # Session path
        self.session_path = None

        # File path
        self.file_path = None

        # Metadata reload thread
        self.metadata_worker_stopped = True
        self.metadata_worker = TimerWorker(10)  # TODO: this should be i config
        self.metadata_worker_thread = QThread()
        self.metadata_worker.moveToThread(self.metadata_worker_thread)
        self.start_metadata_worker.connect(self.metadata_worker.run)
        self.stop_metadata_worker.connect(self.metadata_worker.interupt)
        self.metadata_worker.time_started.connect(self.reload_metadata)
        self.metadata_worker_thread.start()

        # Server IP / port
        self.ip_le = None
        self.port_le = None
        self.server_ip = None
        self.server_port = None
        self.server_path = None

        # Metadata info
        self.recording_info = None
        self.channels_info = None

        # Flags
        self.source_opened = False

#    def create_toolbar(self, title, object_name, iconsize=24):
#        """Create and return toolbar with *title* and *object_name*"""
#        toolbar = self.addToolBar(title)
#        toolbar.setObjectName(object_name)
#        toolbar.setIconSize(QSize(iconsize, iconsize))
#        self.toolbarslist.append(toolbar)
#        return toolbar

    # Main window setup
    def setup(self):
        """Setup main window"""

        # File menu
        self.file_menu = self.menuBar().addMenu('&File')
#        self.file_toolbar = self.create_toolbar("File toolbar",
#                                                "file_toolbar")

        # Plugin menu
        self.plugins_menu = self.menuBar().addMenu('&Plugins')

        # Help menu
        self.help_menu = self.menuBar().addMenu('&Help')

        # Status bar
        status = self.statusBar()
        status.setObjectName("StatusBar")
        status.showMessage("Welcome to PySigView!", 5000)

        # TODO - move action craeteing to utils like in spyder

        # ----- Load configuration file

        # TODO: this will contain key_map, parameters

        # ----- Main widget
        self.set_splash("Setting up canvas ...")

        from pysigview.widgets.signal_display import SignalDisplay
        self.signal_display = SignalDisplay(self)
        self.setCentralWidget(self.signal_display)

        # ----- Plugins
        self.set_splash("Loading plugins ...")

        # Set docking options
        self.setDockOptions(self.DOCKOPTIONS)

        # TODO - automatically add plugins

        # Channels - core plugin, always preseent
        from pysigview.plugins.channels import Channels
        self.channels = Channels(self)
        self.channels.register_plugin()

        # Navigation bar - core plugin, always present
        from pysigview.plugins.navigation_bar import NavigationBar
        self.navigation_bar = NavigationBar(self)
        self.navigation_bar.register_plugin()

        # Annotations
        from pysigview.plugins.annotations import Annotations
        self.annotations = Annotations(self)
        self.annotations.register_plugin()

        # Database
        from pysigview.plugins.database import Database
        self.database = Database(self)
        self.database.register_plugin()

        # Transforms
        from pysigview.plugins.transforms import Transforms
        self.transforms = Transforms(self)
        self.transforms.register_plugin()

        # IPython console
        from pysigview.plugins.console import Console
        self.console = Console(self)
        self.console.register_plugin()

        # Measurement
        from pysigview.plugins.measurement import Measurement
        self.measurement = Measurement(self)
        self.measurement.register_plugin()

        # ----- Menu bar actions ----
        self.set_splash("Setting up main window menus...")

        # File menu
#        open_f_button = QAction(QIcon('exit24.png'),'&Open file(s)', self)
#        open_f_button.setShortcut('Ctrl+O')
#        open_f_button.triggered.connect(self.open_file)
        open_f_action = create_action(self, '&Open file(s)',
                                      icon=None,
                                      tip='Open file(s)',
                                      triggered=self.open_file,
                                      context=Qt.ApplicationShortcut)

        open_s_action = create_action(self, '&Open mef session',
                                      icon=None,
                                      tip='&Open mef session',
                                      triggered=self.open_session,
                                      context=Qt.ApplicationShortcut)

        connect_s_action = create_action(self, '&Connect to pysigview server',
                                         icon=None,
                                         tip='&Connect to pysigview server',
                                         triggered=self.show_conn_dialog,
                                         context=Qt.ApplicationShortcut)

        open_ss_action = create_action(self, '&Open pysigview session',
                                       icon=None,
                                       tip='&Open pysigview session',
                                       triggered=self.open_pysigview_session,
                                       context=Qt.ApplicationShortcut)

        save_ss_action = create_action(self, '&Save pysigview session',
                                       icon=None,
                                       tip='&Save pysigview session',
                                       triggered=self.save_pysigview_session,
                                       context=Qt.ApplicationShortcut)

        exit_action = create_action(self, '&Exit',
                                    icon=None,
                                    tip='&Exit',
                                    triggered=self.close,
                                    context=Qt.ApplicationShortcut)

        self.file_menu_actions = [open_f_action, open_s_action, None,
                                  connect_s_action, None,
                                  open_ss_action, save_ss_action, None,
                                  exit_action]

        self.set_splash("")
        self.splash.hide()

        # Plugin menu
        # Created in pos_visible_setup otherwise not working properly at start

        # Tools menu
        # Preferences...what else?
#        preferences

        # Help menu
        report_bug_action = create_action(self, '&Report bug',
                                          icon=None,
                                          tip='&Report bug',
                                          triggered=self.report_bug,
                                          context=Qt.ApplicationShortcut)

        self.help_menu_actions = [report_bug_action]

        # Layout menu - can be used to save / load custom layouts - might have
        # to be moved after the setup - when the window is initiated

        self.is_starting_up = False

        # Filling menu / toolbar entries
        add_actions(self.file_menu, self.file_menu_actions)
        add_actions(self.help_menu, self.help_menu_actions)

        # Window set-up
        self.setup_layout(default=False)

    def post_visible_setup(self):
        """Actions to be performed only after the main window's `show` method
        was triggered"""

        # Create plugins menu
        self.create_plugins_menu()

        return

    # ----- Auxiliary functions

    def add_path_to_title(self):
        if self.session_path:
            self.base_title = self.session_path + ' - PySigView'
        elif self.file_path:
            self.base_title = self.file_path + ' - PySigView'
        elif self.server_ip:
            self.base_title = (self.server_path + ' at ' + self.server_ip,
                               ':' + self.server_port + ' - PySigView')
        self.update_window_title()

    # ----- File menu actions

    # Files and sessions

    def open_session(self, path=None):

        load_dialog = QFileDialog(self)

        if path:
            self.session_path = path
        else:
            diag_title = 'Select mef session directory'
            diag_path = str(load_dialog.getExistingDirectory(self,
                                                             diag_title,
                                                             get_home_dir()))
            self.session_path = diag_path

        if self.session_path:
            self.open_data_source(self.session_path)
        else:
            return

    def open_file(self, path):

        load_dialog = QFileDialog(self)

        if path:
            self.file_path = path
        else:
            diag_title = 'Select file'
            diag_path = str(load_dialog.getExistingDirectory(self,
                                                             diag_title,
                                                             get_home_dir()))
            self.file_path = diag_path

        if self.file_path:
            self.open_data_source(self.file_path)
        else:
            return

    def open_data_source(self, path):

        sm.ODS, ext = extension_evaluator(path)

        if not sm.ODS:
            QMessageBox.warning(self, "Unrecognized file")
            return

        # Assign session or file path if not already set
        if ext == '.mefd':

            # Open a pop-up window to enter password
            passwd, ok = QInputDialog.getText(self, "MEF password",
                                              "Please type MEF password")
            if ok:
                if not sm.ODS.password_check(passwd):
                    QMessageBox.warning(self, "Password incorrect",
                                        "The password is incorrect")
                    return
                else:
                    sm.ODS.password = passwd
                    self.session_path = path
            else:
                return

        elif not self.file_path:
            self.file_path = path

        # ----- Delete previous data -----

        # Delete any previous buffers
        if isinstance(sm.PDS, MemoryBuffer):
            sm.PDS.terminate_buffer()
            sm.PDS.terminate_monitor_thread()
            sm.PDS.purge_data()

        # Delete data from plugins to be able to open new data source
        for plugin in self.plugin_list:
            plugin.delete_plugin_data()

        # Delete data from signal_display
        self.signal_display.initialize_data_map()
        self.signal_display.update_signals()
        self.signal_display.data_array = None

        # -----

        self.statusBar().showMessage('Loading metadata')
        sm.ODS.load_metadata()
        self.statusBar().showMessage('Loading annotatios')
        # Try to get annotations
        if getattr(self, "annotations", None) is not None:
            if getattr(sm.ODS, "get_annotations", None) is not None:

                ann_groups = sm.ODS.get_annotations()

                for ann_group in ann_groups.items():
                    self.annotations.add_annotation_set(ann_group[1],
                                                        ann_group[0])

        # Fork for buffer usage
        if CONF.get('data_management', 'use_memory_buffer'):
            sm.PDS = MemoryBuffer(self)
        else:
            sm.PDS = sm.ODS

        self.statusBar().showMessage('')

        self.source_opened = True
        self.add_path_to_title()
        self.sig_file_opened.emit()

    def reload_metadata(self):

        if not sm.ODS:
            return

        self.statusBar().showMessage('Updating metadata', 1000)
        sm.ODS.load_metadata()
        self.metadata_reloaded.emit()

    def ss_reaload_worker(self):
        if self.metadata_worker_stopped:
            self.start_metadata_worker.emit()
            self.metadata_worker_stopped = False
        else:
            self.stop_metadata_worker.emit()
            self.metadata_worker_stopped = True

    # Clients

    def show_conn_dialog(self):

        server_dialog = QDialog()
        server_dialog.setModal(True)
        server_dialog.accepted.connect(self.process_server_conn_input)
        server_dialog.accepted.connect(self.connect_to_server)

        layout = QFormLayout(server_dialog)

        layout.addRow(QLabel('Please specify the server type,',
                             ' IP address and port'))

        self.sv_type_cb = QComboBox()
        self.sv_type_cb.addItem('pysigview')  # TODO - this should be automated
        layout.addRow('Client type:', self.sv_type_cb)

        self.ip_le = QLineEdit()
        layout.addRow('IP Address:', self.ip_le)

        self.port_le = QLineEdit()
        layout.addRow('Port:', self.port_le)

        clc_btn = QPushButton("Cancel")
        clc_btn.clicked.connect(server_dialog.reject)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(server_dialog.accept)

        layout.addRow(clc_btn, ok_btn)

        server_dialog.exec()

    def process_server_conn_input(self):

        self.server_ip = self.ip_le.text()
        self.server_port = self.port_le.text()
        self.server_type = self.sv_type_cb.currentText()

    # TODO - tear_down for server
    def connect_to_server(self):

        print('Connecting to '+self.server_type,
              ' server: tcp://'+self.server_ip+':'+self.server_port)

        sm.ODS = client_type_evaluator(self.server_type)
        print('Original data source', sm.ODS.name)
        if self.server_ip:
            sm.ODS.client.ip = self.server_ip
        if self.server_port:
            sm.ODS.client.port = self.server_port

        sm.ODS.connect()

        # TODO: On successful connection store the input

        # Bring up the directory tree
        dt = sm.ODS.get_directory_tree()

        dir_tree_dialog = DirTreeDialog()
        dir_tree_dialog.dir_tree_widget.add_elemtens(dt.d)
        if dir_tree_dialog.exec():
            self.server_path = dir_tree_dialog.return_tree_widget_path()

        # TODO: check iit is a proper session item

        passwd, ok = QInputDialog.getText(self, "MEF password",
                                          "Please type MEF password")
        if ok:
            if not sm.ODS.set_file_handler(self.server_path, passwd):
                QMessageBox.warning(self, "Password incorrect",
                                    "The password is incorrect")
                return
        else:
            return

        # ----- Delete previous data -----

        # Delete any previous buffers
        if isinstance(sm.PDS, MemoryBuffer):
            sm.PDS.terminate_buffer()
            sm.PDS.terminate_monitor_thread()
            sm.PDS.purge_data()

        # Delete data from plugins to be able to open new data source
        for plugin in self.plugin_list:
            plugin.delete_plugin_data()

        # Delete data from signal_display
        self.signal_display.initialize_data_map()
        self.signal_display.update_signals()
        self.signal_display.data_array = None

        # -----

        self.statusBar().showMessage('Loading metadata')
        sm.ODS.load_metadata()
        self.statusBar().showMessage('Loading annotatios')
        # Try to get annotations
        if getattr(self, "annotations", None) is not None:
            if getattr(sm.ODS, "get_annotations", None) is not None:

                ann_groups = sm.ODS.get_annotations()

                for ann_group in ann_groups.items():
                    self.annotations.add_annotation_set(ann_group[1],
                                                        ann_group[0])

        # Fork for buffer usage

        if CONF.get('data_management', 'use_memory_buffer'):
            sm.PDS = MemoryBuffer(self)
        else:
            sm.PDS = sm.ODS

        self.source_opened = True
        self.add_path_to_title()
        self.sig_file_opened.emit()  # TODO change this to source opened

    # Pysigview sessions

    def open_pysigview_session(self):

        load_dialog = QFileDialog(self)
        load_path = load_dialog.getOpenFileName(self, 'Load pysigview session',
                                                get_home_dir(),
                                                "Pysigview session (*.sps)")

        if not load_path:
            return

        with open(load_path[0], 'rb') as fid:
            ss = pickle.load(fid)

        print(ss['main'].keys())

        # TODO - if the path is missing user should now the original path
        if 'session_path' in ss['main'].keys():
            if os.path.exists(ss['main']['session_path']):
                self.open_session(ss['main']['session_path'])
            else:
                self.open_session()
        elif 'file_path' in ss['main'].keys():
            if os.path.exists(ss['main']['file_path']):
                self.open_file(ss['main']['file_path'])
            else:
                self.open_file()
        else:
            return

        for plugin in ss['plugins']:
            plugin_name = list(plugin.keys())[0]
            plugin_data = plugin[plugin_name]

            plugin_instance = getattr(self, plugin_name)
            plugin_instance.load_plugin_data(plugin_data)

            # Trigger signal_display parameter loading ater channels
            if plugin_name == 'channels':
                sd = self.signal_display
                master_pc_pos = ss['signal_display']['master_pc_pos']
                curr_pc_pos = ss['signal_display']['curr_pc_pos']
                for pc in sd.get_plot_containers():
                    if pc.plot_position == master_pc_pos:
                        sd.master_pc = pc
                    if pc.plot_position == curr_pc_pos:
                        sd.curr_pc = pc
                sd.camera.rect = ss['signal_display']['camera_rect']
                if ss['signal_display']['grid_on']:
                    sd.show_grid()

    def save_pysigview_session(self):

        # Bring up save dialog
        save_dialog = QFileDialog(self)
        save_dialog.setDefaultSuffix(".sps")
        save_path = save_dialog.getSaveFileName(self, 'Save pysigview session',
                                                get_home_dir(),
                                                "Pysigview session (*.sps)")
        if not save_path:
            return

        path = save_path[0]
        if path[-4:] != '.sps':
            path += '.sps'

        ss = {'main': {},
              'signal_display': {},
              'plugins': {}}

        # Main
        if self.session_path:
            ss['main']['session_path'] = self.session_path
        elif self.file_path:
            ss['main']['file_path'] = self.file_path
        else:
            return

        # TODO - run this automatically but channels have to be first!
        # Plugins
        ss['plugins'] = [{'channels': self.channels.save_plugin_data()},
                         {'annotations': self.annotations.save_plugin_data()},
                         {'measurement': self.measurement.save_plugin_data()}]

        # Signal display
        sd = self.signal_display
        if sd.curr_pc is None:
            ss['signal_display']['master_pc_pos'] = None
        else:
            ss['signal_display']['master_pc_pos'] = sd.curr_pc.plot_position
        if sd.curr_pc is None:
            ss['signal_display']['curr_pc_pos'] = None
        else:
            ss['signal_display']['curr_pc_pos'] = sd.curr_pc.plot_position
        ss['signal_display']['camera_rect'] = sd.camera.rect
        ss['signal_display']['grid_on'] = sd.grid is not None

        with open(path, 'wb') as fid:
            pickle.dump(ss, fid)

        return

    # ----- Help menu actions

    def report_bug(self):
        webbrowser.open('https://github.com/ICRC-BME/PySigView/issues/'
                        'new?template=bug_report.md')

    # ----- Window settings
    def load_window_settings(self, prefix, default=False, section='main'):
        """Load window layout settings from userconfig-based configuration
        with *prefix*, under *section*
        default: if True, do not restore inner layout"""
        get_func = CONF.get_default if default else CONF.get
        window_size = get_func(section, prefix+'size')
        prefs_dialog_size = get_func(section, prefix+'prefs_dialog_size')
        if default:
            hexstate = None
        else:
            hexstate = get_func(section, prefix+'state', None)
        pos = get_func(section, prefix+'position')

        # It's necessary to verify if the window/position value is valid
        # with the current screen. See issue 3748
        width = pos[0]
        height = pos[1]
        screen_shape = QApplication.desktop().geometry()
        current_width = screen_shape.width()
        current_height = screen_shape.height()
        if current_width < width or current_height < height:
            pos = CONF.get_default(section, prefix+'position')

        is_maximized = get_func(section, prefix+'is_maximized')
        is_fullscreen = get_func(section, prefix+'is_fullscreen')
        return hexstate, window_size, prefs_dialog_size, pos, is_maximized, \
            is_fullscreen

    def get_window_settings(self):
        """Return current window settings
        Symetric to the 'set_window_settings' setter"""
        window_size = (self.window_size.width(), self.window_size.height())
        is_fullscreen = self.isFullScreen()
        if is_fullscreen:
            is_maximized = self.maximized_flag
        else:
            is_maximized = self.isMaximized()
        pos = (self.window_position.x(), self.window_position.y())
        prefs_dialog_size = (self.prefs_dialog_size.width(),
                             self.prefs_dialog_size.height())
        qba = self.saveState()
        hexstate = str(bytes(qba.toHex().data()).decode())
        return (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
                is_fullscreen)

    def set_window_settings(self, hexstate, window_size, prefs_dialog_size,
                            pos, is_maximized, is_fullscreen):
        """Set window settings
        Symetric to the 'get_window_settings' accessor"""
        self.setUpdatesEnabled(False)
        self.window_size = QSize(window_size[0], window_size[1])  # w, h
        self.prefs_dialog_size = QSize(prefs_dialog_size[0],
                                       prefs_dialog_size[1])  # w, h
        self.window_position = QPoint(pos[0], pos[1])  # x,y
        self.setWindowState(Qt.WindowNoState)
        self.resize(self.window_size)
        self.move(self.window_position)

        # Window layout
        if hexstate:
            self.restoreState(QByteArray().fromHex(
                str(hexstate).encode('utf-8')))
            # [Workaround for Issue 880]
            # QDockWidget objects are not painted if restored as floating
            # windows, so we must dock them before showing the mainwindow.
            for widget in self.children():
                if isinstance(widget, QDockWidget) and widget.isFloating():
                    self.floating_dockwidgets.append(widget)
                    widget.setFloating(False)

        # Is fullscreen?
        if is_fullscreen:
            self.setWindowState(Qt.WindowFullScreen)
#        self.__update_fullscreen_action()

        # Is maximized?
        if is_fullscreen:
            self.maximized_flag = is_maximized
        elif is_maximized:
            self.setWindowState(Qt.WindowMaximized)
        self.setUpdatesEnabled(True)

    def save_current_window_settings(self, prefix, section='main'):
        """Save current window settings with *prefix* in
        the userconfig-based configuration, under *section*"""
        self.get_window_settings()
        win_size = self.window_size
#        prefs_size = self.prefs_dialog_size

        CONF.set(section, prefix+'size', (win_size.width(), win_size.height()))
#        CONF.set(section, prefix+'prefs_dialog_size',
#                 (prefs_size.width(), prefs_size.height()))
        CONF.set(section, prefix+'is_maximized', self.isMaximized())
        CONF.set(section, prefix+'is_fullscreen', self.isFullScreen())
        pos = self.window_position
        CONF.set(section, prefix+'position', (pos.x(), pos.y()))
#        self.maximize_dockwidget(restore=True)# Restore non-maximized layout
        qba = self.saveState()
        hexstate = str(bytes(qba.toHex().data()).decode())
        CONF.set(section, prefix+'state', hexstate)
        CONF.set(section, prefix+'statusbar', not self.statusBar().isHidden())

    # --- Layouts
    def setup_layout(self, default=False):
        """Setup window layout"""
        prefix = 'window' + '/'
        settings = self.load_window_settings(prefix, default)

        hexstate = settings[0]

        self.set_window_settings(*settings)

        self.first_pysigview_run = False
        if hexstate is None:
            # First Pysigview execution:
            self.setWindowState(Qt.WindowMaximized)
            self.first_pysigview_run = True

            # store the initial layout as the default in pysigview
            prefix = 'layout_default/'
            section = 'quick_layouts'
            self.save_current_window_settings(prefix, section)
            self.current_quick_layout = 'default'
            CONF.set(section, prefix+'state', None)

            # Regenerate menu
#            self.quick_layout_set_menu()
#        self.set_window_settings(*settings)

#        for plugin in self.plugin_list:
#            try:
#                plugin.initialize_plugin_in_mainwindow_layout()
#            except Exception as error:
#                print("%s: %s" % (plugin, str(error)), file=STDERR)
#                traceback.print_exc(file=STDERR)

    def create_plugins_menu(self):
        order = ['channels', 'navigation_bar']
        for plugin in self.plugin_list:
            action = plugin.toggle_view_action
            action.setChecked(plugin.dockwidget.isVisible())
            try:
                name = plugin.CONF_SECTION
                pos = order.index(name)
            except ValueError:
                pos = None
            if pos is not None:
                order[pos] = action
            else:
                order.append(action)
        actions = order[:]
        for action in order:
            if type(action) is str:
                actions.remove(action)
        self.plugins_menu_actions = actions
        add_actions(self.plugins_menu, actions)

    def update_window_title(self):
        """Update main spyder window title based on projects."""
        title = self.base_title
#        if self.projects is not None:
#            path = self.projects.get_active_project_path()
#            if path:
#                path = path.replace(get_home_dir(), '~')
#                title = '{0} - {1}'.format(path, title)
        self.setWindowTitle(title)

    def set_splash(self, message):
        """Set splash message"""
        if self.splash is None:
            return
#        if message:
#            self.debug_print(message)
        self.splash.show()
        self.splash.showMessage(message, Qt.AlignBottom | Qt.AlignCenter |
                                Qt.AlignAbsolute, QColor(Qt.black))
        QApplication.processEvents()

    def closing(self, cancelable=True):
        """Exit tasks"""
        if self.already_closed or self.is_starting_up:
            return True
        if cancelable:  # and CONF.get('main', 'prompt_on_exit'):
            reply = QMessageBox.critical(self, 'PySigView',
                                         'Do you really want to exit?',
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return False
        prefix = 'window' + '/'
        self.save_current_window_settings(prefix)

#        for plugin in self.thirdparty_plugins:
#            if not plugin.closing_plugin(cancelable):
#                return False

        for plugin in self.plugin_list:
            if not plugin.closing_plugin(cancelable):
                return False

#        self.dialog_manager.close_all()
#        if self.toolbars_visible:
#            self.save_visible_toolbars()

        if isinstance(sm.PDS, MemoryBuffer):
            sm.PDS.terminate_buffer()
            sm.PDS.terminate_monitor_thread()
            sm.PDS.purge_data()

        self.already_closed = True
        return True

    def add_dockwidget(self, child):
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.create_dockwidget()
#        if CONF.get('main', 'vertical_dockwidget_titlebars'):
#            dockwidget.setFeatures(dockwidget.features()|
#                                   QDockWidget.DockWidgetVerticalTitleBar)
        self.addDockWidget(location, dockwidget)
        self.plugin_list.append(child)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.fullscreen_flag = False
            self.showNormal()
            if self.maximized_flag:
                self.showMaximized()
        else:
            self.maximized_flag = self.isMaximized()
            self.fullscreen_flag = True
            self.showFullScreen()
        self.__update_fullscreen_action()

    # ----- Preferences

    # ----- Shortcuts

    def run_pysigview(app, options, args):
        """
        Create and show Pysigview's main window
        Start QApplication event loop
        """
        main = MainWindow(options)
#        try:
        main.setup()
#        except BaseException:
#            if main.console is not None:
#                try:
#                    main.console.shell.exit_interpreter()
#                except BaseException:
#                    pass
#            raise

        main.show()
        main.post_visible_setup()

    # XXX - can be used to open data files in the future
#        if args:
#            for a in args:
#                main.open_external_file(a)

        app.exec_()
        return main

    # ----- Event reimplementation

    def resizeEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.fullscreen_flag:
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)

    def moveEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.fullscreen_flag:
            self.window_position = self.pos()
        QMainWindow.moveEvent(self, event)

    def closeEvent(self, event):

        if self.closing():
            event.accept()
        else:
            event.ignore()


# Main
def main():

    app = MAIN_APP
    options = None
    args = None
#    if options.reset_config_files:
#        reset_config_files()
#        return

    main = None
    main = MainWindow.run_pysigview(app, options, args)
    if main is None:
        # An exception occured
        if SPLASH is not None:
            SPLASH.hide()
            return

    # start_app(main)
    # QTimer.singleShot(1, start_app(main))
    SPLASH.finish(main)
    sys.exit()
    #    app.exec()


if __name__ == '__main__':
    main()
