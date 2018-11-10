#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  5 13:01:34 2018

Plugin - Internal IPython console for Pysigview

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
import os
import sys
import threading

# Third pary imports
from PyQt5.QtCore import Qt, QSize, QObject, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QWidget

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from qtconsole.manager import QtKernelManager

import numpy as np

# Local imports
from pysigview.plugins.base import BasePluginWidget
from pysigview.utils.qthelpers import create_toolbutton, create_plugin_layout

os.environ['QT_API'] = 'pyqt5'
USE_KERNEL = 'python3'


# Taken from Spyder
class SysOutput(QObject):
    """Handle standard I/O queue"""
    data_avail = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        self.queue = []
        self.lock = threading.Lock()

    def write(self, val):
        self.lock.acquire()
        self.queue.append(val)
        self.lock.release()
        self.data_avail.emit()

    def empty_queue(self):
        self.lock.acquire()
        s = "".join(self.queue)
        self.queue = []
        self.lock.release()
        return s

    # We need to add this method to fix Issue 1789
    def flush(self):
        pass

    # This is needed to fix Issue 2984
    @property
    def closed(self):
        return False


# Alternative - embedded widget - this should run in separte process
class QIPythonWidget_embed(QWidget):

    def __init__(self, parent=None, custom_banner=None, **kwargs):
        super(QIPythonWidget_embed, self).__init__(parent=parent, **kwargs)

        self.plugin = parent

        kernel_manager = QtKernelManager(kernel_name=USE_KERNEL)
        kernel_manager.start_kernel()

        kernel_client = kernel_manager.client()
        kernel_client.start_channels()

        self.jupyter_widget = RichJupyterWidget()
        self.jupyter_widget.kernel_manager = kernel_manager
        self.jupyter_widget.kernel_client = kernel_client

        if custom_banner is not None:
            self.jupyter_widget.banner = custom_banner

        layout = QHBoxLayout()
        layout.addWidget(self.jupyter_widget)

    def push_variables(self, variableDict):
        """ Given a dictionary containing name / value pairs,
        push those variables to the IPython console widget """
        self.jupyter_widget.kernel_manager.kernel.shell.push(variableDict)

    def clear_terminal(self):
        """ Clears the terminal """
        self.jupyter_widget._control.clear()

    def print_text(self, text):
        """ Prints some plain text to the console """
        self.jupyter_widget._append_plain_text(text, True)

    def execute_command(self, command):
        """ Execute a command in the frame of the console widget """
        self.jupyter_widget._execute(command, False)


# !!! This might be neccessary
# global ipython_widget  # Prevent from being garbage collected
class QIPythonWidget(RichJupyterWidget):

    def __init__(self, parent=None, custom_banner=None, **kwargs):
        super(QIPythonWidget, self).__init__(parent=parent, **kwargs)

        self.plugin = parent

        if custom_banner is not None:
            self.banner = custom_banner

        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel_manager.kernel.gui = 'qt'
        self.kernel_client = self._kernel_manager.client()
        self.kernel_client.start_channels()

        def stop():
            self.kernel_client.stop_channels()
            self.kernel_manager.shutdown_kernel()

        self.exit_requested.connect(stop)

    def push_variables(self, variableDict):
        """ Given a dictionary containing name / value pairs,
        push those variables to the IPython console widget """
        self.kernel_manager.kernel.shell.push(variableDict)

    def clear_terminal(self):
        """ Clears the terminal """
        self._control.clear()

    def print_text(self, text):
        """ Prints some plain text to the console """
        self._append_plain_text(text, True)

    def execute_command(self, command):
        """ Execute a command in the frame of the console widget """
        self._execute(command, False)


class Console(BasePluginWidget):

    CONF_SECTION = 'ipython_console'
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    shortcut = None

    def __init__(self, parent):
        BasePluginWidget.__init__(self, parent)

        # Widget configiration
        self.ALLOWED_AREAS = Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        self.LOCATION = Qt.RightDockWidgetArea

        # Presets for the main window
        self.title = 'IPython console'
        self.main = parent

        # Capture all interactive input/output
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin

        # Create communication pipes
        pr, pw = os.pipe()
        self.stdin_read = os.fdopen(pr, "r")
        self.stdin_write = os.fdopen(pw, "wb", 0)
        self.stdout_write = SysOutput()
        self.stderr_write = SysOutput()

        self.stdout_write.data_avail.connect(self.stdout_avail)
        self.stderr_write.data_avail.connect(self.stderr_avail)

        self.debug = False

        # ----- Toolbar -----
        self.tool_buttons = []
        self.setup_buttons()
        btn_layout = QHBoxLayout()
        for btn in self.tool_buttons:
            btn.setAutoRaise(True)
            btn.setIconSize(QSize(20, 20))
            btn_layout.addWidget(btn)

        btn_layout.setAlignment(Qt.AlignLeft)

        self.jupyter_console = QIPythonWidget(self, "PySigView Console\n")

        # TODO: tool bar not visible
        layout = create_plugin_layout(btn_layout, self.jupyter_console)

        # ----- Set layout -----
        self.setLayout(layout)

        # TODO: this should be only for debugging
        # Push the main app
        self.jupyter_console.push_variables({'main': self.main})

        # Push the API functions
        self.jupyter_console.push_variables({'get_displayed_raw_data':
                                             self.get_displayed_raw_data,
                                             'get_displayed_metadata':
                                             self.get_displayed_metadata,
                                             'get_annotations':
                                             self.get_annotations,
                                             'set_annotations':
                                             self.set_annotations,
                                             'signal_plots_changed':
                                             self.main.signal_display.
                                             plots_changed})

#        self.redirect_stds()

    def setup_buttons(self):
        update_variables = create_toolbutton(self, icon='reload.svg',
                                             tip='Update variables',
                                             triggered=self.update_variables)

        return [update_variables]

    def set_debug(self):
        if self.debug:
            self.debug = False
            self.restore_stds()
        else:
            self.debug = True
            self.redirect_stds()

    def update_variables(self):
        return

    # ----- Stds pipes -----
    # TODO: does not work dinamically!!!
    def redirect_stds(self):
        """Redirects stds"""
#        if self.debug:
        print('Redirect 1')
        sys.stdout = self.stdout_write
        sys.stderr = self.stderr_write
        sys.stdin = self.stdin_read
        print('Redirect 2')

    def restore_stds(self):
        """Restore stds"""
#        if not self.debug:
        print('Restore 1')
        sys.stdout = self.initial_stdout
        sys.stderr = self.initial_stderr
        sys.stdin = self.initial_stdin
        print('Restore 2')

    def stdout_avail(self):
        """Data is available in stdout, let's empty the queue and write it!"""
        data = self.stdout_write.empty_queue()
        if data:
            # self.write(data)
            self.jupyter_console.print_text(data)

    def stderr_avail(self):
        """Data is available in stderr, let's empty the queue and write it!"""
        data = self.stderr_write.empty_queue()
        if data:
            # self.write(data, error=True)
            # self.flush(error=True)
            self.jupyter_console.print_text(data)

    # ----- User convenience API -----
    def get_displayed_raw_data(self):

        pcs = self.main.signal_display.get_plot_containers()
        pos = np.zeros(len(pcs), dtype=np.int)

        for i, pc in enumerate(pcs):
            pos[i] = pc.data_array_pos[0]

        return self.main.signal_display.data_array[pos]

    def get_displayed_metadata(self):

        pcs = self.main.signal_display.get_plot_containers()

        md = np.zeros(len(pcs),
                      dtype=[('fsamp', np.float, 1),
                             ('ufact', np.float, 1),
                             ('unit', np.object, 1),
                             ('channel', np.object, 1),
                             ('uutc_ss', np.int64, 2)])

        for i, pc in enumerate(pcs):
            md[i] = (pc.fsamp,
                     pc.ufact,
                     pc.unit,
                     pc.orig_channel,
                     pc.uutc_ss)

        return md

    def get_annotations(self):

        if not hasattr(self.main, 'annotations'):
            raise RuntimeError("Annotation plugin is missing")
            return

        ann_its = self.main.annotations.annotation_list.get_annotation_items()

        df_list = []
        for ann_it in ann_its:
            if hasattr(ann_it, 'df'):
                df_list.append(ann_it.df)

        return df_list

    def set_annotations(self, df, name='NA'):

        self.main.annotations.add_annotation_set(df, name)

        return

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
        self.create_toggle_view_action()

        self.main.add_dockwidget(self)

    def delete_plugin_data(self):
        """Deletes plugin data"""
        return None

    def load_plugin_data(self, data):
        """Function to run when loading session"""
        return

    def save_plugin_data(self):
        """Function to run when saving session"""
        return

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def refresh_plugin(self):
        """Refresh widget"""
        if self._starting_up:
            self._starting_up = False
