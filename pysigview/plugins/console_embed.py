#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  5 13:01:34 2018

Plugin - Internal IPython console for PySigView

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
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget

from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.manager import QtKernelManager

# Local imports
from pysigview.plugins.base import BasePluginWidget
from pysigview.utils.qthelpers import create_toolbutton, create_plugin_layout

# The ID of an installed kernel, e.g. 'bash' or 'ir'.
USE_KERNEL = 'python3'


def make_jupyter_widget_with_kernel():
    """Start a kernel, connect to it, and create a RichJupyterWidget to use it
    """
    kernel_manager = QtKernelManager(kernel_name=USE_KERNEL)
    kernel_manager.start_kernel()

    kernel_client = kernel_manager.client()
    kernel_client.start_channels()

    jupyter_widget = RichJupyterWidget()
    jupyter_widget.kernel_manager = kernel_manager
    jupyter_widget.kernel_client = kernel_client
    return jupyter_widget


class QIPythonWidget(QWidget):

    def __init__(self, parent, customBanner=None, *args, **kwargs):
        super(QIPythonWidget, self).__init__(parent)

        self.plugin = parent

        if customBanner is not None:
            self.banner = customBanner

        kernel_manager = QtKernelManager(kernel_name=USE_KERNEL)
        kernel_manager.start_kernel()

        kernel_client = kernel_manager.client()
        kernel_client.start_channels()

        jupyter_widget = RichJupyterWidget()
        jupyter_widget.kernel_manager = kernel_manager
        jupyter_widget.kernel_client = kernel_client

        layout = QVBoxLayout()
        layout.addWidget(jupyter_widget)

        self.setLayout(layout)


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

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # ----- Toolbar -----
        self.tool_buttons = []
        self.setup_buttons()
        btn_layout = QHBoxLayout()
        for btn in self.tool_buttons:
            btn.setAutoRaise(True)
            btn.setIconSize(QSize(20, 20))
            btn_layout.addWidget(btn)

        btn_layout.setAlignment(Qt.AlignLeft)

#        self.jupyter_console s= make_jupyter_widget_with_kernel()
        self.jupyter_console = QIPythonWidget(self, 'PySigView console')
        layout = create_plugin_layout(btn_layout, self.jupyter_console)

        # ----- Set layout -----
        self.setLayout(layout)

    def setup_buttons(self):
        update_variables = create_toolbutton(self, icon='reload.svg',
                                             tip='Update variables',
                                             triggered=self.update_variables)

        return [update_variables]

    def update_variables(self):
        return
#        self.jupyter_console.push_variables({'bu':5})
#        self.jupyter_console.print_text("\nVariables updated\n")

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
