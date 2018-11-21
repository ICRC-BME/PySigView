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
import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from vispy import scene
from vispy.scene import Line
from vispy.scene.cameras import PanZoomCamera
from vispy.visuals.transforms import STTransform

# Local imports
from pysigview.plugins.base import BasePluginWidget
from pysigview.cameras.signal_camera import SignalCamera


class SignalWidget(QWidget):

    def __init__(self, parent):
        super(SignalWidget, self).__init__(parent)

        # Useful trnascripts
        self.sd = self.parent().sd

        # Variables
        self.fixed_point = None
        self.measurement_mode = False
        self.curr_pc = None
        self.sig_start = None
        self.sig_stop = None

        # Setup camera
        self.signal_camera = PanZoomCamera()
        self.spectrum_camera = PanZoomCamera()

        self.canvas = scene.SceneCanvas(show=True, keys='interactive',
                                        parent=self)

        # TODO: change this to grid with axes and signal transform
        self.view_grid = self.canvas.central_widget.add_grid()
        self.signal_view = self.view_grid.add_view(camera=self.signal_camera)
        self.fft_view = self.view_grid.add_view(row=1, col=0,
                                                camera=self.spectrum_camera)

#        self.transform_view = self.canvas.central_widget.add_view(
#                    camera=self.camera)

        self.signal_line = Line(parent=self.signal_view.scene, width=1)
        self.spectrum_line = Line(parent=self.fft_view.scene, width=1)

        # ----- Set layout -----
        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.canvas.native)

        # Set the whole layout
        self.setLayout(layout)

    def recieve_input(self, event):
        if event.type == 'key_press' and event.key == 'control':
            self.measurement_mode = True
        elif event.type == 'key_release' and event.key == 'control':
            self.measurement_mode = False
            self.sig_start = None
            self.sig_stop = None

        # TODO: this code is duplicated here, annotations, signal_view widget - carry it out only once!!!

        if event.type == 'mouse_press' and self.measurement_mode is True:
            # Get position relative to zoom
            pos = event.pos[:2]
            w = self.sd.signal_view.width
            h = self.sd.signal_view.height
            rel_w_pos = pos[0] / w
            # TODO: flip Vispy axis
            rel_h_pos = (h-pos[1]) / h
            rect = self.sd.camera.rect
            rect_rel_w_pos = rect.left + (rel_w_pos * rect.width)
            rect_rel_h_pos = rect.bottom + (rel_h_pos * rect.height)

            # Determine the signal plot

            rows = self.sd.visible_channels.get_row_count()
            cols = self.sd.visible_channels.get_col_count()

            sig_w_pos = rect_rel_w_pos * cols
            sig_h_pos = rect_rel_h_pos * rows

            for pc in self.sd.get_plot_containers():

                if ((pc.plot_position[0]
                     < sig_w_pos
                     < pc.plot_position[0]+1)
                    and (pc.plot_position[1]
                         < sig_h_pos
                         < pc.plot_position[1]+1)):

                    self.curr_pc = pc

            self.sig_start = int(rect_rel_w_pos * len(self.curr_pc.data))

        if self.sig_start is not None:
            if event.type == 'mouse_move' and self.measurement_mode is True:
                # Get position relative to zoom
                pos = event.pos[:2]
                w = self.sd.signal_view.width
                h = self.sd.signal_view.height
                rel_w_pos = pos[0] / w
                # TODO: flip Vispy axis
                rel_h_pos = (h-pos[1]) / h
                rect = self.sd.camera.rect
                rect_rel_w_pos = rect.left + (rel_w_pos * rect.width)

                self.sig_stop = int(rect_rel_w_pos * len(self.curr_pc.data))

                self.update_signals()

    def update_signals(self):

        if self.sig_start < self.sig_stop:
            data = self.curr_pc.data[self.sig_start:self.sig_stop]
        elif self.sig_start > self.sig_stop:
            data = self.curr_pc.data[self.sig_stop:self.sig_start]
        else:
            return

        if len(data) < 2:
            return

        # Signal line

        s_x = 1/len(data)
        s_y = 1/(np.max(data)-np.min(data))
        s_z = 0
        scale = [s_x, s_y, s_z]

        # Translate
        t_x = 0
        t_y = -(((np.max(data) + np.min(data)) / 2) * s_y) + 0.5
        t_z = 0
        translate = [t_x, t_y, t_z]

        transform = STTransform(scale, translate)

        pos = np.c_[np.arange(len(data)), data]

        self.signal_line.set_data(pos=pos, color=self.curr_pc.line_color)
        self.signal_line.transform = transform

        # FFT line

        s = np.abs(np.fft.fft(data))[:int(len(data)/2)]
        s[0] = 0
        time_step = 1 / self.curr_pc.fsamp
        freqs = np.fft.fftfreq(data.size, time_step)
        idx = np.argsort(freqs)

        s_x = 1/len(s)
        s_y = 1/(np.max(s)-np.min(s))
        s_z = 0
        scale = [s_x, s_y, s_z]

        # Translate
        t_x = 0
        t_y = 0
        t_z = 0
        translate = [t_x, t_y, t_z]

        transform = STTransform(scale, translate)

        pos = np.c_[np.arange(len(s)), s]

        self.spectrum_line.set_data(pos=pos, color=self.curr_pc.line_color)
        self.spectrum_line.transform = transform


class ToolsWidget(QWidget):

    def __init__(self, parent):
        super(ToolsWidget, self).__init__(parent)
        pass


class Measurement(BasePluginWidget):
    """
    Basic functionality for Pysigview plugin widgets
    """

    CONF_SECTION = 'measurement'
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    shortcut = None

    def __init__(self, parent):
        BasePluginWidget.__init__(self, parent)

        # Presets for the main window
        self.title = 'Measurement'
        self.main = parent
        self.sd = self.main.signal_display

        # Widget configiration
        self.ALLOWED_AREAS = (Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
                              | Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.LOCATION = Qt.RightDockWidgetArea

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.tools_widget = ToolsWidget(self)
        layout.addWidget(self.tools_widget)

        self.signal_widget = SignalWidget(self)
        layout.addWidget(self.signal_widget)

        self.setLayout(layout)

    # ------ PysigviewPluginWidget API ----------------------------------------
    def get_plugin_title(self):
        """
        Return plugin title.
        """
        return self.title

    def get_plugin_icon(self):
        """
        Return plugin icon (QIcon instance).
        """
        return None

    def get_focus_widget(self):
        """
        Return the widget to give focus to.
        """
        return None

    def closing_plugin(self, cancelable=False):
        """
        Perform actions before parent main window is closed.
        """
        return True

    def refresh_plugin(self):
        """Refresh widget."""
        if self._starting_up:
            self._starting_up = False

    def get_plugin_actions(self):
        """
        Return a list of actions related to plugin.
        """
        return []

    def register_plugin(self):
        """Register plugin in Pysigview's main window."""
        self.create_toggle_view_action()

        self.sd.input_recieved.connect(self.signal_widget.recieve_input)

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

    def on_first_registration(self):
        """Action to be performed on first plugin registration."""
        pass
