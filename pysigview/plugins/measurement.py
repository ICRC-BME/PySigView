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
from PyQt5.QtWidgets import (QVBoxLayout, QWidget, QComboBox, QLineEdit,
                             QFormLayout, QHBoxLayout)
from vispy import scene
from vispy.scene import Line, AxisWidget
from vispy.scene.cameras import PanZoomCamera
from vispy.visuals.transforms import STTransform

# Local imports
from pysigview.plugins.base import BasePluginWidget
from pysigview.cameras.signal_camera import SignalCamera
from pysigview.visuals.spectrogram_visual import Spectrogram


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
        self.spect_type = 'spectrum'  # spectrum, spectrogram

        # Spectrum variables
        self.low_lim = None
        self.high_lim = None

        # Setup camera
        self.signal_camera = PanZoomCamera()
        self.spectrum_camera = PanZoomCamera()

        self.canvas = scene.SceneCanvas(show=True, keys='interactive',
                                        parent=self)

        self.view_grid = self.canvas.central_widget.add_grid(margin=10)

        # Signal
        self.signal_view = self.view_grid.add_view(row=0, col=1, row_span=2,
                                                   camera=self.signal_camera)
        self.signal_yaxis = AxisWidget(orientation='left',
                                       axis_label='Amplitude',
                                       axis_font_size=12,
                                       tick_label_margin=5)
        self.signal_yaxis.width_max = 60
        self.view_grid.add_widget(self.signal_yaxis, row=0, col=0, row_span=2)

        self.signal_xaxis = scene.AxisWidget(orientation='bottom',
                                             axis_label='Time [s]',
                                             axis_font_size=12,
                                             tick_label_margin=5)

        self.signal_xaxis.height_max = 55
        self.view_grid.add_widget(self.signal_xaxis, row=2, col=1)

        self.signal_yaxis.link_view(self.signal_view)
        self.signal_xaxis.link_view(self.signal_view)

        # Spectrum
        self.spectrum_view = self.view_grid.add_view(row=3, col=1, row_span=2,
                                                     camera=self.
                                                     spectrum_camera)

        self.spectrum_yaxis = AxisWidget(orientation='left',
                                         axis_label='Amplitude',
                                         axis_font_size=12,
                                         tick_label_margin=5)
        self.spectrum_yaxis.width_max = 60
        self.view_grid.add_widget(self.spectrum_yaxis, row=3, col=0,
                                  row_span=2)

        self.spectrum_xaxis = scene.AxisWidget(orientation='bottom',
                                               axis_label='Frequency [Hz]',
                                               axis_font_size=12)

        self.spectrum_xaxis.height_max = 55
        self.view_grid.add_widget(self.spectrum_xaxis, row=5, col=1)

        self.spectrum_yaxis.link_view(self.spectrum_view)
        self.spectrum_xaxis.link_view(self.spectrum_view)

        self.signal_line = Line(parent=self.signal_view.scene, width=1)
        self.spectrum_line = Line(parent=self.spectrum_view.scene, width=1)
        self.spectrogram = Spectrogram(parent=self.spectrum_view.scene)

        # ----- Set layout -----
        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.canvas.native)

        # Set the whole layout
        self.setLayout(layout)

    def set_spect_type(self, stype):
        self.spect_type = stype
        if stype == 'spectrum':
            self.spectrum_line.visible = True
            self.spectrogram.visible = False
        elif stype == 'spectrogram':
            self.spectrogram.visible = True
            self.spectrum_line.visible = False

        self.update_signals()

    def recieve_input(self, event):
        if event.type == 'key_press' and event.key == 'control':
            self.measurement_mode = True
            self.sig_start = None
            self.sig_stop = None
        elif event.type == 'key_release' and event.key == 'control':
            self.measurement_mode = False


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
            self.spectrogram.fs = self.curr_pc.fsamp

        if self.curr_pc is not None:
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

        if self.sig_start is None or self.sig_stop is None:
            return

        if self.sig_start < self.sig_stop:
            data = self.curr_pc.data[self.sig_start:self.sig_stop]
        elif self.sig_start > self.sig_stop:
            data = self.curr_pc.data[self.sig_stop:self.sig_start]
        else:
            return

        if len(data) < 2:
            return

        # Signal line

        s_x = 1/self.curr_pc.fsamp
        s_y = 1/(np.max(data)-np.min(data))
        s_z = 0
        scale = [s_x, 1, 1]

        # Translate
        t_x = 0
        t_y = -np.min(data)
        t_z = 0
        translate = [t_x, t_y, t_z]

        transform = STTransform(scale, translate)

        pos = np.c_[np.arange(len(data)), data]

        self.signal_line.set_data(pos=pos, color=self.curr_pc.line_color)
        self.signal_line.transform = transform

        self.signal_camera.rect = (0, 0), (len(data) * s_x,
                                           np.max(data)-np.min(data))

        if self.spect_type == 'spectrum':
            # Spectrum line

            s = np.abs(np.fft.fft(data))[:int(len(data)/2)]
            s[0] = 0
            freqs = np.fft.fftfreq(data.size, 1 / self.curr_pc.fsamp)
            freqs = freqs[:int(len(freqs)/2)]

            if self.low_lim is not None:
                res = np.where(freqs >= self.low_lim)[0]
                if len(res) > 0:
                    low_lim_idx = res[0]
            else:
                low_lim_idx = 0

            if self.high_lim is not None:
                res = np.where(freqs <= self.high_lim)[0]
                if len(res) > 0:
                    high_lim_idx = res[-1]
            else:
                high_lim_idx = len(freqs)

            s_x = (self.curr_pc.fsamp / 2) / len(s)
            s_y = 1
            s_z = 0
            scale = [s_x, s_y, s_z]

            transform = STTransform(scale)

            pos = np.c_[np.arange(len(s)), s]

            self.spectrum_line.set_data(pos=pos, color=self.curr_pc.line_color)
            self.spectrum_line.transform = transform

            freqs = freqs[low_lim_idx:high_lim_idx]
            pos = (freqs[0], 0)
            size = (freqs[-1] - freqs[0],
                    np.max(s[low_lim_idx:high_lim_idx]))

            self.spectrum_camera.rect = pos, size

        elif self.spect_type == 'spectrogram':

            # TODO change axis lables

            self.spectrogram.x = data

            freqs = self.spectrogram.freqs

            if self.low_lim is not None:
                res = np.where(freqs >= self.low_lim)[0]
                if len(res) > 0:
                    low_lim_idx = res[0]
            else:
                low_lim_idx = 0

            if self.high_lim is not None:
                res = np.where(freqs <= self.high_lim)[0]
                if len(res) > 0:
                    high_lim_idx = res[-1]
            else:
                high_lim_idx = len(freqs)

            n_windows = ((len(data) - self.spectrogram.n_fft)
                         // self.spectrogram.step + 1)
            s_x = (len(data) / n_windows)/self.curr_pc.fsamp
            s_y = (self.curr_pc.fsamp / 2) / len(freqs)
            s_z = 0
            scale = [s_x, s_y, s_z]

            transform = STTransform(scale)

            self.spectrogram.transform = transform

            if len(freqs) == 0:
                return

            freqs = freqs[low_lim_idx:high_lim_idx-1]
            pos = (0, freqs[0])
            size = (n_windows * s_x, freqs[-1] - freqs[0])

            self.spectrum_camera.rect = pos, size


class SpectrumTools(QWidget):

    def __init__(self, parent):
        super(SpectrumTools, self).__init__(parent)


class SpectrogramTools(QWidget):

    def __init__(self, parent):
        super(SpectrogramTools, self).__init__(parent)

        self.spectrocgram = self.parent().plugin.signal_widget.spectrogram

        layout = QFormLayout()

        self.n_fft_le = QLineEdit()
        layout.addRow('NFFT', self.n_fft_le)
        self.n_fft_le.editingFinished.connect(self.set_n_fft)

        self.setLayout(layout)

    def set_n_fft(self):
        self.spectrocgram.n_fft = int(self.n_fft_le.text())
        self.parent().plugin.signal_widget.update_signals()


class ToolsWidget(QWidget):

    def __init__(self, parent):
        super(ToolsWidget, self).__init__(parent)

        self.plugin = self.parent()

        # TODO - input masks for edit fields

        main_layout = QHBoxLayout()

        form_layout = QFormLayout()

        self.cb = QComboBox()
        self.cb.addItems(['Spectrum', 'Spectrogram'])
        self.cb.currentIndexChanged.connect(self.switch_spect_type)
        form_layout.addRow("Transform", self.cb)

        self.low_lim_le = QLineEdit()
        self.high_lim_le = QLineEdit()
        form_layout.addRow("Low limit", self.low_lim_le)
        form_layout.addRow("High limit", self.high_lim_le)

        self.low_lim_le.editingFinished.connect(self.set_low_lim)
        self.high_lim_le.editingFinished.connect(self.set_high_lim)

        self.spectrum_tools = SpectrumTools(self)
        self.spectrogram_tools = SpectrogramTools(self)
        self.specific_tools = [self.spectrum_tools, self.spectrogram_tools]

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.specific_tools[0])

        self.setLayout(main_layout)

    def switch_spect_type(self, idx):
        self.plugin.signal_widget.set_spect_type(self.cb.itemText(idx).lower())
        self.layout().insertWidget(1, self.specific_tools[idx])

    def set_low_lim(self):
        if self.low_lim_le.text() != '':
            self.plugin.signal_widget.low_lim = int(self.low_lim_le.text())
            self.plugin.signal_widget.update_signals()
        else:
            self.plugin.signal_widget.low_lim = None
            self.plugin.signal_widget.update_signals()

    def set_high_lim(self):
        if self.high_lim_le.text() != '':
            self.plugin.signal_widget.high_lim = int(self.high_lim_le.text())
            self.plugin.signal_widget.update_signals()
        else:
            self.plugin.signal_widget.high_lim = None
            self.plugin.signal_widget.update_signals()


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

        self.signal_widget = SignalWidget(self)
        self.tools_widget = ToolsWidget(self)
        
        layout.addWidget(self.tools_widget)
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
