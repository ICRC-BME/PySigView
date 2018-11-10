# -*- coding: utf-8 -*-
"""
Created on Thu Nov  5 16:19:07 2015

Base plugin class for individual plugin superclasses

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

# Third party imports
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QWidget

# Local imports
from pysigview.widgets.dock import PysigviewDockWidget
from pysigview.utils.qthelpers import create_action


class BasePluginWidget(QWidget):
    """
    Basic functionality for Pysigview plugin widgets
    """

    # Widget constants
    # Name of the configuration section that's going to be
    # used to record the plugin's permanent data in Pysigview
    # config system (i.e. in pysigview.ini)
    # Status: Required
    CONF_SECTION = None

    # Widget to be used as entry in Pysigview Preferences
    # dialog
    # Status: Optional
    CONFIGWIDGET_CLASS = None

    # Path for images relative to the plugin path
    # Status: Optional
    IMG_PATH = 'images'

    # Control the size of the fonts used in the plugin
    # relative to the fonts defined in Pysigview
    # Status: Optional
    FONT_SIZE_DELTA = 0
    RICH_FONT_SIZE_DELTA = 0

    # Disable actions in Pysigview main menus when the plugin
    # is not visible
    # Status: Optional
    DISABLE_ACTIONS_WHEN_HIDDEN = True

    # Shortcut to give focus to the plugin. In Pysigview we try
    # to reserve shortcuts that start with Ctrl+Shift+... for
    # these actions
    # Status: Optional
    shortcut = None

    def initialize_plugin_in_mainwindow_layout(self):
        """
        If this is the first time the plugin is shown, perform actions to
        initialize plugin position in Pysigview's window layout.
        Use on_first_registration to define the actions to be run
        by your plugin
        """
        if self.get_option('first_time', True):
            try:
                self.on_first_registration()
            except NotImplementedError:
                return
            self.set_option('first_time', False)

    def update_plugin_title(self):
        """Update plugin title, i.e. dockwidget or mainwindow title"""
        if self.dockwidget is not None:
            win = self.dockwidget
        elif self.mainwindow is not None:
            win = self.mainwindow
        else:
            return
        win.setWindowTitle(self.get_plugin_title())

    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""

        dock = PysigviewDockWidget(self.get_plugin_title(), self.main)

        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(self.ALLOWED_AREAS)
        # dock.setFeatures(self.FEATURES)
        dock.setWidget(self)
        dock.plugin_closed.connect(self.plugin_closed)
        self.dockwidget = dock

        return (dock, self.LOCATION)

    def create_configwidget(self, parent):
        """Create configuration dialog box page widget"""
        if self.CONFIGWIDGET_CLASS is not None:
            configwidget = self.CONFIGWIDGET_CLASS(self, parent)
            configwidget.initialize()
            return configwidget

    def switch_to_plugin(self):
        """Switch to plugin
        This method is called when pressing plugin's shortcut key"""
        if not self.ismaximized:
            self.dockwidget.show()
        if not self.toggle_view_action.isChecked():
            self.toggle_view_action.setChecked(True)
        self.visibility_changed(True)

    def plugin_closed(self):
        """DockWidget was closed"""
        self.toggle_view_action.setChecked(False)

#    def get_plugin_font(self, rich_text=False):
#        """
#        Return plugin font option.
#        All plugins in Pysigview use a global font. This is a convenience
#        method in case some plugins will have a delta size based on the
#        default size.
#        """
#
#        if rich_text:
#            option = 'rich_font'
#            font_size_delta = self.RICH_FONT_SIZE_DELTA
#        else:
#            option = 'font'
#            font_size_delta = self.FONT_SIZE_DELTA
#
#        return get_font(option=option, font_size_delta=font_size_delta)
#
#    def set_plugin_font(self):
#        """
#        Set plugin font option.
#        Note: All plugins in Pysigview use a global font. To define a
#        different size, the plugin must define a 'FONT_SIZE_DELTA' class
#        variable.
#        """
#        raise Exception("Plugins font is based on the general settings, "
#                        "and cannot be set directly on the plugin."
#                        "This method is deprecated.")

    def show_message(self, message, timeout=0):
        """Show message in main window's status bar"""
        self.main.statusBar().showMessage(message, timeout)

    def create_toggle_view_action(self):
        """Associate a toggle view action with each plugin"""
        title = self.get_plugin_title()

        if self.shortcut is not None:
            action = create_action(self, title,
                                   toggled=lambda checked:
                                   self.toggle_view(checked),
                                   shortcut=QKeySequence(self.shortcut),
                                   context=Qt.WidgetShortcut)
        else:
            action = create_action(self, title, toggled=lambda checked:
                                   self.toggle_view(checked))
        self.toggle_view_action = action

    def toggle_view(self, checked):
        """Toggle view"""
        if not self.dockwidget:
            return
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
        else:
            self.dockwidget.hide()

    # -------------------------------- API ------------------------------------
    def get_plugin_title(self):
        """
        Return plugin title.
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute
        """
        raise NotImplementedError

    def get_plugin_icon(self):
        """
        Return plugin icon (QIcon instance).
        Note: this is required for plugins creating a main window
              (see PysigviewPluginMixin.create_mainwindow)
              and for configuration dialog widgets creation
        """
        return NotImplementedError  # return ima.icon('outline_explorer')

    def get_focus_widget(self):
        """
        Return the widget to give focus to.
        This is applied when plugin's dockwidget is raised on top-level.
        """
        pass

    def closing_plugin(self, cancelable=False):
        """
        Perform actions before parent main window is closed.
        Return True or False whether the plugin may be closed immediately or
        not
        Note: returned value is ignored if *cancelable* is False
        """
        return True

    def refresh_plugin(self):
        """Refresh widget."""
        raise NotImplementedError

    def get_plugin_actions(self):
        """
        Return a list of actions related to plugin.
        Note: these actions will be enabled when plugin's dockwidget is visible
              and they will be disabled when it's hidden
        """
        raise NotImplementedError

    def register_plugin(self):
        """Register plugin in Pysigview's main window."""
        raise NotImplementedError

    def delete_plugin_data(self):
        """Deletes plugin data"""
        return None

    def load_plugin_data(self, data):
        """Function to run when loading session"""
        return None

    def save_plugin_data(self):
        """Function to run when saving session"""
        return None

    def on_first_registration(self):
        """Action to be performed on first plugin registration."""
        raise NotImplementedError

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings."""
        raise NotImplementedError

    def update_font(self):
        """
        This must be reimplemented by plugins that need to adjust their fonts.
        """
        pass

    def check_compatibility(self):
        """
        This method can be implemented to check compatibility of a plugin
        for a given condition.
        `message` should give information in case of non compatibility:
        For example: 'This plugin does not work with Qt4'
        """
        message = ''
        valid = True
        return valid, message
