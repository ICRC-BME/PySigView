#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 09:28:14 2017

Core plugin navigation bar

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

# Standard library imports
from datetime import datetime

# Third party imports
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout,
                             QWidget, QLineEdit, QLabel, QRadioButton)
from PyQt5.QtGui import QIntValidator, QDoubleValidator

from vispy import scene
from vispy.scene import LinearRegion

import numpy as np

# Local imports
from pysigview.plugins.base import BasePluginWidget
from pysigview.cameras.navigation import NavigationCamera
from pysigview.config.main import CONF
from pysigview.core import source_manager as sm
from pysigview.utils.qthelpers import hex2rgba


class LoadedDataBar(LinearRegion):

    def __init__(self, color_arr, parent):
        super(LinearRegion, self).__init__([0, 0], color_arr, parent=parent)


class BarWidget(QWidget):

    # Signals
    bar_slider_changed = pyqtSignal(name='')

    def __init__(self, parent):
        super(BarWidget, self).__init__(parent)

        # Widget configuration
        self.setMaximumHeight(30)
        self.setMinimumHeight(30)

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Covenience transcripts
        self.main = self.parent().main

        self.recording_duration = None
        self.recording_start = None
        self.recording_span = None
        self.previous_view_span = 0
        self.metadata_reload_flag = False

        self.discont_thresh = CONF.get(self.parent().CONF_SECTION,
                                       'discontinuity_limit')

        # Camera
        self.camera = NavigationCamera(self)

        # Vispy canvas
        self.canvas = scene.SceneCanvas(show=True, keys='interactive',
                                        parent=self,
                                        bgcolor=CONF.get(self.parent().
                                                         CONF_SECTION,
                                                         'bgcolor'))

        self.nav_view = self.canvas.central_widget.add_view(camera=self.camera)

        layout.addWidget(self.canvas.native)

        # ---- Linear regions for tracking -----

        # Linear region for buffer
        pos = np.array([0, 0], dtype=np.float32)
        self.buffer_rgba = hex2rgba(CONF.get(self.parent().CONF_SECTION,
                                             'buffer_bar_color'))
        self.buffer_carray = np.array([self.buffer_rgba,
                                       self.buffer_rgba])

        self.buffer_bar = LinearRegion(pos, self.buffer_carray,
                                       parent=self.nav_view.scene)

        # Linear region for displayed signal
        pos = np.array([0, 0], dtype=np.float32)
        self.view_rgba = hex2rgba(CONF.get(self.parent().CONF_SECTION,
                                           'view_bar_color'))
        self.view_carray = np.array([self.view_rgba,
                                     self.view_rgba])
        self.view_bar = LinearRegion(pos, self.view_carray,
                                     parent=self.nav_view.scene)
        self.view_bar.transform = scene.transforms.STTransform(scale=(1, 1))

        # Linear region for discontinuities
        pos = np.arange(self.nav_view.size[0])
        color = np.zeros([self.nav_view.size[0], 4])
        self.disc_bar = LinearRegion(pos, color, parent=self.nav_view.scene)
        self.disc_bar.transform = scene.transforms.STTransform(scale=(1, 1))

        # TODO - nigh and day regions

        self.discontinuities = []
        self.discont_region = []
        self.discont_colors = []

        self.setLayout(layout)

    def check_uutc(self, uutc):
        """
        Makes sure the uutc time resultion corresponds with sampling frequency
        """
        max_fsamp = max(self.main.signal_display.data_map['fsamp'])
        us_time_res = int(1e6/max_fsamp)

        return int(uutc - ((uutc-self.recording_start) % us_time_res))

    # TODO: introduce rounding to the hihghest sampling frequency of channels
    # TODO: handling contracted discontinuities
    def uutc_to_pos(self, uutc):
        """
        Maps uutc to position in nav bar
        """

        uutc = self.check_uutc(uutc)
        rel_time = uutc - self.recording_start

        pos = rel_time / self.recording_span

        return pos

    def pos_to_uutc(self, pos):
        """
        Maps position in nav bar to uutc
        """

        rel_time = pos * self.recording_span
        uutc = int(rel_time + self.recording_start)

        uutc = self.check_uutc(uutc)

        return uutc

    # TODO: universal bar function with assigned data_map and create bar class
    def update_buffer_bar(self):

        if not self.main.source_opened:
            return

        dm = sm.PDS.data_map
        if not any(dm['ch_set']):
            return

        uutc = dm.get_active_largest_ss()
        if not any(uutc):
            return

        pos = np.array([self.uutc_to_pos(x) for x in uutc])

        # Check if pos is large enough for at least one pixel
        w = self.canvas.central_widget.width
        if np.diff(pos) * w < 1:
            pos = np.array([pos[0], pos[0] + 1 / w])

        self.buffer_bar.set_data(pos, self.buffer_carray)
        self.buffer_bar.update()

    def update_view_bar(self):
        dm = self.main.signal_display.data_map
        uutc = dm.get_active_largest_ss()
        if not any(uutc):
            return

        pos = np.array([self.uutc_to_pos(x) for x in uutc])

        # Check if pos is large enough for at least one pixel
        w = self.canvas.central_widget.width
        if np.diff(pos) * w < 1:
            pos = np.array([pos[0], pos[0] + 1 / w])

        self.view_bar.set_data(pos, self.view_rgba)
        self.view_bar.update()

    def plot_disconts(self):

        dm = self.main.signal_display.data_map
        uutc = dm.get_active_largest_ss()
        view_span = np.diff(uutc)

        if not self.metadata_reload_flag:
            if self.previous_view_span == view_span:
                return

        self.previous_view_span = view_span

        if self.main.signal_display.cong_discontinuities is None:
            self.disc_bar.visible = False
            return
        else:
            self.disc_bar.visible = True

        # Big discontinuities that will trigger skipping
        cong_disconts = self.main.signal_display.cong_discontinuities
        large_disconts_idxs = np.diff(cong_disconts) > view_span
        large_disconts_idxs = large_disconts_idxs.ravel()
        large_disconts = cong_disconts[large_disconts_idxs]

        disc_color = hex2rgba(CONF.get(self.parent().CONF_SECTION,
                                       'discontinuity_color'))

        pos = np.zeros(len(large_disconts)*4)
        self.discont_colors = np.zeros([len(large_disconts)*4, 4])
        for i, gen_discont in enumerate(large_disconts):

            pos[i*4 + 0] = self.uutc_to_pos(gen_discont[0])
            pos[i*4 + 1] = self.uutc_to_pos(gen_discont[0])
            pos[i*4 + 2] = self.uutc_to_pos(gen_discont[1])
            pos[i*4 + 3] = self.uutc_to_pos(gen_discont[1])
            self.discont_colors[i*4 + 1] = disc_color
            self.discont_colors[i*4 + 2] = disc_color

        # Create a big linear region
        self.disc_bar.set_data(pos, color=self.discont_colors)

        return

    def set_location(self, pos):
        x_pos = pos[0]

        # Calculate the relative position in recording
        rel_pos = x_pos / self.nav_view.size[0]
        midpoint = self.recording_start + (rel_pos * self.recording_span)
        midpoint = self.parent().tools_widget._correct_time(midpoint)

        self.main.signal_display.move_to_time(midpoint)


class ToolsWidget(QWidget):

    def __init__(self, parent):
        super(ToolsWidget, self).__init__(parent)

        # Widget configuration
        self.setMinimumHeight(0)

        # Widget layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Covenience transcripts
        self.main = self.parent().main

        # ----- Location -----

        self.location_label = QLabel('Time:')
        # Edit field for start
        self.location_le = QLineEdit(self)
        self.location_validator = QIntValidator(self)
        self.location_le.returnPressed.connect(self.set_location)
#        self.location.textChanged.connect(self.location_format_check)
#        self.location_state = True

        # ----- Location switch -----
        self.radio_to_date = QRadioButton('Date')
        self.radio_to_date.clicked.connect(self.update_view_times)

        self.radio_to_uutc = QRadioButton('uUTC')
        self.radio_to_uutc.clicked.connect(self.update_view_times)
        self.radio_to_uutc.setChecked(True)

        # ----- Span -----

        self.span_label = QLabel('Time span:')
        # Edit field for span
        self.span_le = QLineEdit(self)
        self.span_validator = QDoubleValidator(self)
        self.span_le.returnPressed.connect(self.set_span)

        # Switcher between samples, uutc and rec time

        # ----- Set layout -----
        layout.addWidget(self.location_label)
        layout.addWidget(self.location_le)
        layout.addWidget(self.radio_to_date)
        layout.addWidget(self.radio_to_uutc)
        layout.addWidget(self.span_label)
        layout.addWidget(self.span_le)
        self.setLayout(layout)

    def _correct_time(self, uutc):
        # Get maximum sampling frequency
        fsamps = [pc.fsamp for pc in
                  self.main.signal_display.get_plot_containers()]
        min_step = 1e6 / np.max(fsamps)

        return int(uutc // min_step * min_step)

    def uutc_to_date(self, uutc):

        dt_str = datetime.fromtimestamp(uutc/1e6
                                        ).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        return dt_str

    def date_to_uutc(self, dt_str):
        if '.' not in dt_str:
            dt_str += '.0'
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S.%f')
#        timestamp = dt.replace(tzinfo=timezone.utc).timestamp()
        timestamp = dt.timestamp()
        timestamp *= 1e6

        return int(timestamp)

    def update_view_times(self):
        dm = self.main.signal_display.data_map
        uutc_map = dm.get_active_uutc_ss()
        if not len(uutc_map):
            return
        tracker_i = np.argmax([x[1]-x[0] for x in uutc_map])
        tracker = uutc_map[tracker_i]

        span = (tracker[1]-tracker[0])/1e6
        loc = int(tracker[0])
        loc = self._correct_time(loc)
        if self.radio_to_date.isChecked():
            loc_str = self.uutc_to_date(loc)
        else:
            loc_str = str(loc)
        span_str = str(span)

        # Get subtimes (zooms and magnifies)
        rect = self.main.signal_display.camera.rect

        if rect.width != 1:
            span_substr = ' ('+str(round(rect.width * span, 3))+')'
        else:
            span_substr = ''

        if rect.left != 0:
            if self.radio_to_date.isChecked():
                loc_substr = ' ('+self.uutc_to_date(loc
                                                    + int(rect.left
                                                          * span * 1e6))+')'
            else:
                loc_substr = ' ('+str(loc + int(rect.left * span * 1e6))+')'

        else:
            loc_substr = ''

        self.location_le.setText(loc_str + loc_substr)
        self.span_le.setText(span_str + span_substr)

#    def location_format_check(self, text):
#        print(self.main.recording_info['recording_start'])
#        print(self.location_validator.bottom())
#        print(self.location_validator.validate(text,1))
#        return

    def set_location(self):
        if self.radio_to_date.isChecked():
            midpoint = self.date_to_uutc(self.location_le.text())
        else:
            midpoint = int(self.location_le.text())

        midpoint = self._correct_time(midpoint)

        if self.radio_to_date.isChecked():
            loc_str = self.uutc_to_date(midpoint)
        else:
            loc_str = str(midpoint)
        self.location_le.setText(loc_str)

        self.main.signal_display.move_to_time(midpoint)

    def span_format_check(self, text):
        return

    def set_span(self):
        self.span_format_check(self.span_le.text())
        new_span = int(float(self.span_le.text()) * 1e6)

        self.main.signal_display.set_time_span_all(new_span)


class NavigationBar(BasePluginWidget):

    # Attributes
    CONF_SECTION = 'navigation_bar'
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    shortcut = None

    def __init__(self, parent):
        BasePluginWidget.__init__(self, parent)

        # Widget configiration
        self.ALLOWED_AREAS = Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea
        self.LOCATION = Qt.BottomDockWidgetArea
        self.setMinimumHeight(30)
        self.setMaximumHeight(62)

        # Presets for the main winow
        self.title = 'Navigation bar'
        self.main = parent
        self.ri = sm.ODS.recording_info

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.tools_widget = ToolsWidget(self)
        layout.addWidget(self.tools_widget)

        self.bar_widget = BarWidget(self)
        layout.addWidget(self.bar_widget)

        self.setLayout(layout)

    def resizeEvent(self, event):

        if event.size().height() < 60:
            self.tools_widget.close()
        elif event.size().height() > 60:
            self.tools_widget.show()

    def connect_navigation(self):

        # Navigation bar
        self.main.signal_display.data_map_changed.connect(self.bar_widget.
                                                          update_view_bar)
        self.ri = sm.ODS.recording_info
        self.bar_widget.recording_duration = self.ri['recording_duration']
        self.bar_widget.recording_start = self.ri['recording_start']
        self.bar_widget.recording_span = (self.ri['recording_end']
                                          - self.ri['recording_start'])

        # Buffer bars
        if CONF.get('data_management', 'use_memory_buffer'):
            sm.PDS.state_changed.connect(self.bar_widget.update_buffer_bar)

#        self.bar_widget.plot_disconts()

        # Tools widget
        self.main.signal_display.data_map_changed.connect(self.tools_widget.
                                                          update_view_times)
        self.main.signal_display.subview_changed.connect(self.tools_widget.
                                                         update_view_times)

#        self.tools_widget.set_location_validator()

    def update_navigation(self):
        self.bar_widget.metadata_reload_flag = True
        print('------------------------------')
        print(sm.ODS)
        self.bar_widget.recording_duration = self.ri['recording_duration']
        self.bar_widget.recording_start = self.ri['recording_start']
        self.bar_widget.recording_span = (self.ri['recording_end']
                                          - self.ri['recording_start'])

        self.bar_widget.update_view_bar()
#        self.main.signal_display.create_conglomerate_disconts()
        self.bar_widget.plot_disconts()
        self.bar_widget.metadata_reload_flag = False

    # ------ PysigviewPluginWidget API ----------------------------------------
    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        pass

    def get_plugin_title(self):
        """Return widget title"""
        return 'Navigation bar'

    def get_plugin_icon(self):
        """Return widget icon"""
#        return ima.icon('help')
        return None

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return None

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def register_plugin(self):
        """Register plugin in Pysigview's main window"""

        self.create_toggle_view_action()

        self.main.sig_file_opened.connect(self.connect_navigation)
        self.main.metadata_reloaded.connect(self.update_navigation)
        self.main.signal_display.plots_changed.connect(self.bar_widget.
                                                       plot_disconts)

        self.main.add_dockwidget(self)

    def delete_plugin_data(self):
        """Deletes plugin data"""

        c = self.bar_widget.buffer_rgba
        self.bar_widget.buffer_bar.set_data([0, 0], np.array([c, c]))

        c = self.bar_widget.view_rgba
        self.bar_widget.view_bar.set_data([0, 0], np.array([c, c]))

        pos = np.arange(self.bar_widget.nav_view.size[0])
        color = np.zeros([self.bar_widget.nav_view.size[0], 4])
        self.bar_widget.disc_bar.set_data(pos, color)

        return

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
