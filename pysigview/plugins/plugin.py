"""
Created on Wed Nov  5 18:34:43 2015

File containing classes and functions common for all plugins.

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

from PyQt5 import QtGui

import plugins.common

import functools


# Class for plugin info
class plugin_info:
    def __init__(self, title, dock_widget, area):
        self.title = title
        self.dock_widget = dock_widget
        self.area = area


# This function adds plugins into Plugin menu
def register_plugins(main_window, plugin_menu):
    plugin_list = plugins.common.plugin_list
    for plugin in plugin_list:
        pluginButton = QtGui.QAction(plugin.title, plugin_menu)
        # open_fileButton.setShortcut('Ctrl+O') - could be invoked from plugin
        # plugin_button.setStatusTip('Open file')
        # open_plugin(main_window,plugin)
        pluginButton.triggered.connect(functools.partial(plugin.
                                                         dock_widget.
                                                         setVisible, True))
        plugin_menu.addAction(pluginButton)
        main_window.addDockWidget(plugin.area, plugin.dock_widget)
        main_window.plugin_list.append(plugin)
        plugin.dock_widget.setVisible(True)
