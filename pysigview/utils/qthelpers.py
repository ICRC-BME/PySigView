#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 10:03:25 2017

Vast majority of this file is adjusted utils subbmodule from
spyder IDE.

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

# TODO - insert spyder license

# Std library imports
import os
import re
import os.path as osp
import sys

# Third party imports
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, QTimer, QVariant
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence, QKeyEvent
from PyQt5.QtWidgets import (QAction, QApplication, QLabel, QMenu, QToolBar,
                             QToolButton, QVBoxLayout)

# Local imports
from pysigview.config.utils import get_image_path, running_in_mac_app


def get_image_label(name, default="not_found.png"):
    """Return image inside a QLabel object"""
    label = QLabel()
    label.setPixmap(QPixmap(get_image_path(name, default)))
    return label


class MacApplication(QApplication):
    """Subclass to be able to open external files with our Mac app"""
    sig_open_external_file = pyqtSignal(str)

    def __init__(self, *args):
        QApplication.__init__(self, *args)

    def event(self, event):
        if event.type() == QEvent.FileOpen:
            fname = str(event.file())
            self.sig_open_external_file.emit(fname)
        return QApplication.event(self, event)


def qapplication(translate=True, test_time=3):
    """
    Return QApplication instance
    Creates it if it doesn't already exist

    test_time: Time to maintain open the application when testing. It's given
    in seconds
    """
    if running_in_mac_app():
        PysigviewApplication = MacApplication
    else:
        PysigviewApplication = QApplication

    app = PysigviewApplication.instance()
    if app is None:
        # Set Application name for Gnome 3
        # https://groups.google.com/forum/#!topic/pyside/24qxvwfrRDs
        app = PysigviewApplication(['Pysigview'])

        # Set application name for KDE (See issue 2207)
        app.setApplicationName('Pysigview')

    test_ci = os.environ.get('TEST_CI_WIDGETS', None)
    if test_ci is not None:
        timer_shutdown = QTimer(app)
        timer_shutdown.timeout.connect(app.quit)
        timer_shutdown.start(test_time*1000)
    return app


def file_uri(fname):
    """Select the right file uri scheme according to the operating system"""
    if os.name == 'nt':
        # Local file
        if re.search(r'^[a-zA-Z]:', fname):
            return 'file:///' + fname
        # UNC based path
        else:
            return 'file://' + fname
    else:
        return 'file://' + fname


def keybinding(attr):
    """Return keybinding"""
    ks = getattr(QKeySequence, attr)
    return (QKeySequence.keyBindings(ks)[0], str)


def _process_mime_path(path, extlist):
    if path.startswith(r"file://"):
        if os.name == 'nt':
            # On Windows platforms, a local path reads: file:///c:/...
            # and a UNC based path reads like: file://server/share
            if path.startswith(r"file:///"):  # this is a local path
                path = path[8:]
            else:  # this is a unc path
                path = path[5:]
        else:
            path = path[7:]
    path = path.replace('%5C', os.sep)  # Transforming backslashes
    if osp.exists(path):
        if extlist is None or osp.splitext(path)[1] in extlist:
            return path


def mimedata2url(source, extlist=None):
    """
    Extract url list from MIME data
    extlist: for example ('.py', '.pyw')
    """
    pathlist = []
    if source.hasUrls():
        for url in source.urls():
            path = _process_mime_path(str(url.toString()), extlist)
            if path is not None:
                pathlist.append(path)
    elif source.hasText():
        for rawpath in str(source.text()).splitlines():
            path = _process_mime_path(rawpath, extlist)
            if path is not None:
                pathlist.append(path)
    if pathlist:
        return pathlist


def keyevent2tuple(event):
    """Convert QKeyEvent instance into a tuple"""
    return (event.type(), event.key(), event.modifiers(), event.text(),
            event.isAutoRepeat(), event.count())


def tuple2keyevent(past_event):
    """Convert tuple into a QKeyEvent instance"""
    return QKeyEvent(*past_event)


def rgba2hex(rgba):
    """Convert RGB to #hex"""
    return '#%02x%02x%02x%02x' % ([int(x*255) for x in rgba])


def hex2rgba(hex_str):
    """Convert #hex to RGB"""
    return tuple(int(hex_str.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4, 6))


def create_toolbutton(parent, text=None, shortcut=None, icon=None, tip=None,
                      toggled=None, triggered=None,
                      autoraise=True, text_beside_icon=False):
    """Create a QToolButton"""
    button = QToolButton(parent)
    if text is not None:
        button.setText(text)
    if icon is not None:
        if str(icon):
            ipath = get_image_path(icon)
            icon = QIcon(ipath)
        button.setIcon(icon)
    if text is not None or tip is not None:
        button.setToolTip(text if tip is None else tip)
    if text_beside_icon:
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setAutoRaise(autoraise)
    if triggered is not None:
        button.clicked.connect(triggered)
    if toggled is not None:
        button.toggled.connect(toggled)
        button.setCheckable(True)
    if shortcut is not None:
        button.setShortcut(shortcut)
    return button


def create_plugin_layout(tools_layout, main_widget=None):
    """
    Returns a layout for a set of controls above a main widget. This is a
    standard layout for many plugin panes (even though, it's currently
    more often applied not to the pane itself but with in the one widget
    contained in the pane.
    tools_layout: a layout containing the top toolbar
    main_widget: the main widget. Can be None, if you want to add this
        manually later on.
    """
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
#    spacing = calc_tools_spacing(tools_layout)
#    if spacing is not None:
#        layout.setSpacing(spacing)

    layout.addLayout(tools_layout)
    if main_widget is not None:
        layout.addWidget(main_widget)
    return layout


def toggle_actions(actions, enable):
    """Enable/disable actions"""
    if actions is not None:
        for action in actions:
            if action is not None:
                action.setEnabled(enable)


def create_action(parent, text, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None, data=None, menurole=None,
                  context=Qt.WindowShortcut):
    """Create a QAction"""
    action = PysigviewAction(text, parent)
    if triggered is not None:
        action.triggered.connect(triggered)
    if toggled is not None:
        action.toggled.connect(toggled)
        action.setCheckable(True)
    if icon is not None:
        if str(icon):
            ipath = get_image_path(icon)
            icon = QIcon(ipath)
        action.setIcon(icon)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if data is not None:
        action.setData(QVariant(data))
    if menurole is not None:
        action.setMenuRole(menurole)

    # Workround for Mac because setting context=Qt.WidgetShortcut
    # there doesn't have any effect
    if sys.platform == 'darwin':
        action._shown_shortcut = None
        if context == Qt.WidgetShortcut:
            if shortcut is not None:
                action._shown_shortcut = shortcut
            else:
                # This is going to be filled by
                # main.register_shortcut
                action._shown_shortcut = 'missing'
        else:
            if shortcut is not None:
                action.setShortcut(shortcut)
            action.setShortcutContext(context)
    else:
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.setShortcutContext(context)

    return action


def add_actions(target, actions, insert_before=None):
    """Add actions to a QMenu or a QToolBar."""
    previous_action = None
    target_actions = list(target.actions())
    if target_actions:
        previous_action = target_actions[-1]
        if previous_action.isSeparator():
            previous_action = None
    for action in actions:
        if (action is None) and (previous_action is not None):
            if insert_before is None:
                target.addSeparator()
            else:
                target.insertSeparator(insert_before)
        elif isinstance(action, QMenu):
            if insert_before is None:
                target.addMenu(action)
            else:
                target.insertMenu(insert_before, action)
        elif isinstance(action, QAction):
            if isinstance(action, PysigviewAction):
                if isinstance(target, QMenu) or not isinstance(target,
                                                               QToolBar):
                    try:
                        action = action.no_icon_action
                    except RuntimeError:
                        continue
            if insert_before is None:
                target.addAction(action)
            else:
                target.insertAction(insert_before, action)
        previous_action = action


class PysigviewAction(QAction):
    """Pysigview QAction class wrapper to handle cross platform patches."""

    def __init__(self, *args, **kwargs):
        """Pysigview QAction class wrapper to handle cross platform patches."""
        super(PysigviewAction, self).__init__(*args, **kwargs)
        self._action_no_icon = None

        if sys.platform == 'darwin':
            self._action_no_icon = QAction(*args, **kwargs)
            self._action_no_icon.setIcon(QIcon())
            self._action_no_icon.triggered.connect(self.triggered)
            self._action_no_icon.toggled.connect(self.toggled)
            self._action_no_icon.changed.connect(self.changed)
            self._action_no_icon.hovered.connect(self.hovered)
        else:
            self._action_no_icon = self

    def __getattribute__(self, name):
        """Intercept method calls and apply to both actions, except signals."""
        attr = super(PysigviewAction, self).__getattribute__(name)

        if hasattr(attr, '__call__') and name not in ['triggered', 'toggled',
                                                      'changed', 'hovered']:
            def newfunc(*args, **kwargs):
                result = attr(*args, **kwargs)
                if name not in ['setIcon']:
                    action_no_icon = self.__dict__['_action_no_icon']
                    attr_no_icon = super(QAction,
                                         action_no_icon).__getattribute__(name)
                    attr_no_icon(*args, **kwargs)
                return result
            return newfunc
        else:
            return attr

    @property
    def no_icon_action(self):
        """Return the action without an Icon."""
        return self._action_no_icon
