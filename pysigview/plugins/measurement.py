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
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (QVBoxLayout, QWidget, QComboBox, QLineEdit,
                             QCheckBox, QFormLayout, QHBoxLayout, QSlider)
from vispy import scene, color
from vispy.scene import Line, AxisWidget
from vispy.visuals.transforms import STTransform

# Local imports
from pysigview.config.main import CONF

from pysigview.plugins.base import BasePluginWidget
from pysigview.cameras.signal_camera import SignalCamera
from pysigview.visuals.spectrogram_visual import Spectrogram


class SignalWidget(QWidget):

    def __init__(self, parent):
        super(SignalWidget, self).__init__(parent)

        # Useful trnascripts
        self.plugin = self.parent()
        self.sd = self.plugin.sd
        self.CONF_SECTION = self.parent().CONF_SECTION

        # Variables
        self.measurement_mode = False
        self.curr_pc = None
        self.sig_start = None
        self.sig_stop = None
        self.spect_type = 'spectrum'  # spectrum, spectrogram

        # General variables
        self.low_lim = None
        self.high_lim = None

        # Sepctrum variables
        self.mean_filter = None

        # Setup camera
        self.signal_camera = SignalCamera()
        self.spectrum_camera = SignalCamera()

        self.canvas = scene.SceneCanvas(show=True, keys='interactive',
                                        parent=self,
                                        bgcolor=CONF.get(self.CONF_SECTION,
                                                         'bgcolor'))

        self.view_grid = self.canvas.central_widget.add_grid(margin=10)

        # Signal
        self.signal_view = self.view_grid.add_view(row=0, col=1, row_span=2,
                                                   camera=self.signal_camera)
        axis_color = CONF.get(self.CONF_SECTION, 'axis_color')
        self.signal_yaxis = AxisWidget(orientation='left',
                                       axis_label='Amplitude',
                                       axis_font_size=12,
                                       tick_label_margin=5,
                                       axis_color=axis_color,
                                       tick_color=axis_color)
        self.signal_yaxis.width_max = 60
        self.view_grid.add_widget(self.signal_yaxis, row=0, col=0, row_span=2)

        self.signal_xaxis = scene.AxisWidget(orientation='bottom',
                                             axis_label='Time [s]',
                                             axis_font_size=12,
                                             tick_label_margin=5,
                                             axis_color=axis_color,
                                             tick_color=axis_color)

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
        self.spectrogram = Spectrogram([0], parent=self.spectrum_view.scene)
        self.spectrogram.visible = False
        # FIXME: we have to introduce dummy data ot spectrogram, othrewise
        # the scalling is messed up - this is a Vispy visual problem

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

        if event.type == 'mouse_press' and self.measurement_mode is True:
            self.curr_pc = self.sd.curr_pc
            rect_rel_w_pos = self.sd.rect_rel_w_pos

            self.sig_start = int(rect_rel_w_pos * len(self.curr_pc.data))
            self.spectrogram.fs = self.curr_pc.fsamp

        if self.curr_pc is not None:

            if self.curr_pc.fsamp != self.sd.curr_pc.fsamp:
                self.low_lim = None
                self.high_lim = None
                self.curr_pc = self.sd.curr_pc

            if self.low_lim is None:
                self.plugin.tools_widget.general_tools \
                    .low_lim_le.setText('0')
                self.plugin.tools_widget.general_tools \
                    .low_lim_le_validator.setRange(0, self.curr_pc.fsamp/2, 1)
            if self.high_lim is None:
                self.plugin.tools_widget.general_tools \
                    .high_lim_le.setText(str(self.curr_pc.fsamp/2))
                self.plugin.tools_widget.general_tools \
                    .high_lim_le_validator.setRange(0, self.curr_pc.fsamp/2, 1)

            if event.type == 'mouse_move' and self.measurement_mode is True:
                self.sig_stop = int(self.sd.rect_rel_w_pos
                                    * len(self.curr_pc.data))

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
        self.signal_camera.limit_rect = self.signal_camera.rect

        if self.spect_type == 'spectrum':
            # Spectrum line

            s = np.abs(np.fft.fft(data))[:int(len(data)/2)]
            s[0] = 0
            freqs = np.fft.fftfreq(data.size, 1 / self.curr_pc.fsamp)
            freqs = freqs[:int(len(freqs)/2)]

            if self.mean_filter is not None and self.mean_filter > 1:
                s = np.convolve(s,
                                np.ones((self.mean_filter,))/self.mean_filter,
                                mode='valid')

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
            s_z = 1
            scale = [s_x, s_y, s_z]

            pos = np.c_[np.arange(len(s)), s]

            self.spectrum_line.set_data(pos=pos, color=self.curr_pc.line_color)
            self.spectrum_line.transform = STTransform(scale)

            # Adjust camera limits
            pos = (0, 0)
            size = (freqs[-1], np.max(s))
            self.spectrum_camera.limit_rect = pos, size

            # Adjust camera view
            freqs = freqs[low_lim_idx:high_lim_idx]
            if len(freqs) == 0:
                return
            pos = (freqs[0], 0)
            size = (freqs[-1] - freqs[0],
                    np.max(s[low_lim_idx:high_lim_idx]))
            self.spectrum_camera.rect = pos, size

        elif self.spect_type == 'spectrogram':

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

            if n_windows == 0 or len(freqs) == 0:
                return

            s_x = len(data) / self.curr_pc.fsamp
            s_y = (self.curr_pc.fsamp / 2) / len(freqs)
            s_z = 1
            scale = [s_x, s_y, s_z]
            self.spectrogram.transform = STTransform(scale)

            # Adjust camera limits
            pos = (0, 0)
            size = (s_x, freqs[-1])
            self.spectrum_camera.limit_rect = pos, size

            # Adjust camera view
            freqs = freqs[low_lim_idx:high_lim_idx-1]
            pos = (0, freqs[0])
            size = (s_x, freqs[-1] - freqs[0])
            self.spectrum_camera.rect = pos, size


class GeneralTools(QWidget):

    def __init__(self, parent):
        super(GeneralTools, self).__init__(parent)

        self.plugin = self.parent().plugin

        layout = QFormLayout()

        self.cb = QComboBox()
        self.cb.addItems(['Spectrum', 'Spectrogram'])
        self.cb.currentIndexChanged.connect(self.switch_spect_type)
        layout.addRow("Transform", self.cb)

        self.low_lim_le = QLineEdit()
        self.low_lim_le_validator = QDoubleValidator()
        self.low_lim_le.setValidator(self.low_lim_le_validator)

        self.high_lim_le = QLineEdit()
        self.high_lim_le_validator = QDoubleValidator()
        self.high_lim_le.setValidator(self.high_lim_le_validator)

        layout.addRow("Low limit", self.low_lim_le)
        layout.addRow("High limit", self.high_lim_le)

        self.low_lim_le.editingFinished.connect(self.set_low_lim)
        self.high_lim_le.editingFinished.connect(self.set_high_lim)

        self.setMaximumWidth(260)

        self.setLayout(layout)

    def switch_spect_type(self, idx):
        self.parent().curr_tools_widget.setParent(None)
        self.plugin.signal_widget.set_spect_type(self.cb.itemText(idx).lower())
        self.parent().layout().insertWidget(1,
                                            self.parent().specific_tools[idx])
        self.parent().curr_tools_widget = self.parent().specific_tools[idx]
        # TODO change axis lables

    def set_low_lim(self):
        if self.low_lim_le.text() != '':
            self.plugin.signal_widget.low_lim = float(self.low_lim_le.text())
            self.plugin.signal_widget.update_signals()
        else:
            self.plugin.signal_widget.low_lim = None
            self.plugin.signal_widget.update_signals()

    def set_high_lim(self):
        if self.high_lim_le.text() != '':
            self.plugin.signal_widget.high_lim = float(self.high_lim_le.text())
            self.plugin.signal_widget.update_signals()
        else:
            self.plugin.signal_widget.high_lim = None
            self.plugin.signal_widget.update_signals()


class SpectrumTools(QWidget):

    def __init__(self, parent):
        super(SpectrumTools, self).__init__(parent)

        self.sw = self.parent().plugin.signal_widget

        layout = QFormLayout()

        self.mean_le = QLineEdit()
        layout.addRow('Mean smooth', self.mean_le)
        self.mean_le.editingFinished.connect(self.set_mean_smooth)

        self.setLayout(layout)

    def set_mean_smooth(self):
        if self.mean_le.text() != '':
            self.sw.mean_filter = int(self.mean_le.text())
            self.sw.update_signals()
        else:
            self.sw.mean_filter = None
            self.sw.update_signals()


class SpectrogramTools(QWidget):

    def __init__(self, parent):
        super(SpectrogramTools, self).__init__(parent)

        self.spectrogram = self.parent().plugin.signal_widget.spectrogram

        layout = QFormLayout()

        self.n_fft_le = QLineEdit(str(self.spectrogram.n_fft))
        self.n_fft_le_validator = QIntValidator(8, 1024)
        self.n_fft_le.setValidator(self.n_fft_le_validator)
        layout.addRow('NFFT', self.n_fft_le)
        self.n_fft_le.editingFinished.connect(self.set_n_fft)

        self.step_le = QLineEdit(str(self.spectrogram.step))
        self.step_le_validator = QIntValidator(1, 128)
        self.step_le.setValidator(self.step_le_validator)
        layout.addRow('Step', self.step_le)
        self.step_le.editingFinished.connect(self.set_step)

        self.cmap_cb = QComboBox()
        layout.addRow('Colormap', self.cmap_cb)
#        curr_cmap = [x[0] for x in color.get_colormaps().items() \
#                     if x[1] == self.spectrogram.cmap][0]
        cmap_list = list(color.get_colormaps().keys())
        cmap_list.sort()
#        curr_idx = cmap_list.index(curr_cmap)
        self.cmap_cb.addItems(cmap_list)
#        self.cmap_cb.setCurrentIndex(curr_idx)
        self.cmap_cb.currentIndexChanged.connect(self.set_cmap)

        self.interp_cb = QComboBox()
        layout.addRow('Interpolation', self.interp_cb)
        interp_list = ['nearest', 'bilinear', 'hanning', 'hamming', 'hermite',
                       'kaiser', 'quadric', 'bicubic', 'catrom', 'mitchell',
                       'spline16', 'spline36', 'gaussian', 'bessel',
                       'sinc', 'lanczos', 'blackman']
        self.interp_cb.addItems(interp_list)
        self.interp_cb.currentIndexChanged.connect(self.set_interpolation)

        self.normalize_chb = QCheckBox()
        layout.addRow('Normalize', self.normalize_chb)
        self.normalize_chb.setCheckState(self.spectrogram.normalize)
        self.normalize_chb.stateChanged.connect(self.set_normalize)

        clim_low_layout = QHBoxLayout()

        self.clim_low_s = QSlider(Qt.Horizontal)
        self.clim_low_s.setMinimum(0)
        self.clim_low_s.setMaximum(100)
        self.clim_low_s.setValue(0)
        self.clim_low_s.setTickInterval(1)
        self.clim_low_s.valueChanged.connect(self.set_clim_low_s)

        self.clim_low_le = QLineEdit('0')
        self.clim_low_le_validator = QIntValidator(1, 100)
        self.clim_low_le.setValidator(self.clim_low_le_validator)
        self.clim_low_le.editingFinished.connect(self.set_clim)
        self.clim_low_le.setMaximumWidth(40)

        clim_low_layout.addWidget(self.clim_low_s)
        clim_low_layout.addWidget(self.clim_low_le)

        layout.addRow('Color limit low', clim_low_layout)

        clim_high_layout = QHBoxLayout()

        self.clim_high_s = QSlider(Qt.Horizontal)
        self.clim_high_s.setMinimum(0)
        self.clim_high_s.setMaximum(100)
        self.clim_high_s.setValue(100)
        self.clim_high_s.setTickInterval(1)
        self.clim_high_s.valueChanged.connect(self.set_clim_high_s)

        self.clim_high_le = QLineEdit('100')
        self.clim_high_le_validator = QIntValidator(1, 100)
        self.clim_high_le.setValidator(self.clim_high_le_validator)
        self.clim_high_le.editingFinished.connect(self.set_clim)
        self.clim_high_le.setMaximumWidth(40)

        clim_high_layout.addWidget(self.clim_high_s)
        clim_high_layout.addWidget(self.clim_high_le)

        layout.addRow('Color limit high', clim_high_layout)

        self.setLayout(layout)

    def set_n_fft(self):
        self.spectrogram.n_fft = int(self.n_fft_le.text())
        self.step_le_validator.setTop(self.spectrogram.n_fft - 1)
        self.parent().plugin.signal_widget.update_signals()

    def set_step(self):
        self.spectrogram.step = int(self.step_le.text())
        self.parent().plugin.signal_widget.update_signals()

    def set_cmap(self, idx):
        self.spectrogram.cmap = self.cmap_cb.itemText(idx)

    def set_interpolation(self, idx):
        self.spectrogram.interpolation = self.interp_cb.itemText(idx)

    def set_normalize(self, state):
        if state:
            self.spectrogram.normalize = True
        else:
            self.spectrogram.normalize = False

    def set_clim_low_s(self, val):
        low = int(val)
        high = int(self.clim_high_le.text())

        # Adjust validators
        self.clim_high_le_validator.setBottom(low)

        # Adjust text
        self.clim_low_le.setText(str(low))

        if self.spectrogram.data is None:
            return

        d_min = np.min(self.spectrogram.data)
        d_max = np.max(self.spectrogram.data)
        d_diff = d_max - d_min
        low = ((low/100) * d_diff) + d_min
        high = ((high/100) * d_diff) + d_min
        self.spectrogram.clim = (low, high)

    def set_clim_high_s(self, val):
        low = int(self.clim_low_le.text())
        high = int(val)

        # Adjust validators
        self.clim_low_le_validator.setTop(high)

        # Adjust text
        self.clim_high_le.setText(str(high))

        if self.spectrogram.data is None:
            return

        d_min = np.min(self.spectrogram.data)
        d_max = np.max(self.spectrogram.data)
        d_diff = d_max - d_min
        low = ((low/100) * d_diff) + d_min
        high = ((high/100) * d_diff) + d_min
        self.spectrogram.clim = (low, high)

    def set_clim(self):
        low = int(self.clim_low_le.text())
        high = int(self.clim_high_le.text())

        # Adjust validators
        self.clim_low_le_validator.setTop(high)
        self.clim_high_le_validator.setBottom(low)

        # Adjust the sliders
        self.clim_low_s.setValue(low)
        self.clim_high_s.setValue(high)

        if self.spectrogram.data is None:
            return

        d_min = np.min(self.spectrogram.data)
        d_max = np.max(self.spectrogram.data)
        d_diff = d_max - d_min
        low = ((low/100) * d_diff) + d_min
        high = ((high/100) * d_diff) + d_min
        self.spectrogram.clim = (low, high)


class ToolsWidget(QWidget):

    def __init__(self, parent):
        super(ToolsWidget, self).__init__(parent)

        self.plugin = self.parent()

        main_layout = QHBoxLayout()

        self.general_tools = GeneralTools(self)

        self.spectrum_tools = SpectrumTools(self)
        self.spectrogram_tools = SpectrogramTools(self)
        self.specific_tools = [self.spectrum_tools, self.spectrogram_tools]

        self.curr_tools_widget = self.spectrum_tools

        main_layout.addWidget(self.general_tools)
        main_layout.addWidget(self.curr_tools_widget)

        self.setLayout(main_layout)


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

    def conn_disconn_signals(self, visible):
        if visible:
            self.sd.input_recieved.connect(self.signal_widget.recieve_input)
        else:
            self.sd.input_recieved.disconnect(self.signal_widget.recieve_input)

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

        self.main.add_dockwidget(self)

        self.dockwidget.visibilityChanged.connect(self.conn_disconn_signals)

    def delete_plugin_data(self):
        """Deletes plugin data"""
        return None

    def load_plugin_data(self, data):
        """Function to run when loading session"""

        tw = self.tools_widget
        sw = self.signal_widget

        sw.sig_start = data['signal']['sig_start']
        sw.sig_stop = data['signal']['sig_stop']
        sw.curr_pc = self.sd.curr_pc
        sw.spectrogram.fs = self.sd.curr_pc.fsamp

        gt = data['tools']['general']
        tw.general_tools.cb.setCurrentIndex(gt['spect_type'])
        tw.general_tools.low_lim_le.setText(gt['low_lim'])
        tw.general_tools.high_lim_le.setText(gt['high_lim'])
        tw.general_tools.set_low_lim()
        tw.general_tools.set_high_lim()

        st = data['tools']['spectrum']
        tw.spectrum_tools.mean_le.setText(st['mean_smooth'])
        tw.spectrum_tools.set_mean_smooth()

        st = data['tools']['spectrogram']
        tw.spectrogram_tools.n_fft_le.setText(st['n_fft'])
        tw.spectrogram_tools.step_le.setText(st['step'])
        tw.spectrogram_tools.cmap_cb.setCurrentIndex(st['cmap'])
        tw.spectrogram_tools.interp_cb.setCurrentIndex(st['interp_cb'])
        tw.spectrogram_tools.normalize_chb.setCheckState(st['normalize_chb'])
        tw.spectrogram_tools.clim_low_le.setText(str(st['clim_low_le']))
        tw.spectrogram_tools.clim_high_le.setText(str(st['clim_high_le']))
        tw.spectrogram_tools.set_n_fft()
        tw.spectrogram_tools.set_step()
        tw.spectrogram_tools.set_cmap(st['cmap'])
        tw.spectrogram_tools.set_interpolation(st['interp_cb'])
        tw.spectrogram_tools.set_normalize(st['normalize_chb'])
        tw.spectrogram_tools.set_clim()

    def save_plugin_data(self):
        """Function to run when saving session"""

        tw = self.tools_widget
        sw = self.signal_widget

        general_tools = {}
        general_tools['spect_type'] = tw.general_tools.cb.currentIndex()
        general_tools['low_lim'] = tw.general_tools.low_lim_le.text()
        general_tools['high_lim'] = tw.general_tools.high_lim_le.text()

        spectrum_tools = {}
        spectrum_tools['mean_smooth'] = tw.spectrum_tools.mean_le.text()

        spectrogram_tools = {}
        spectrogram_tools['n_fft'] = tw.spectrogram_tools.n_fft_le.text()
        spectrogram_tools['step'] = tw.spectrogram_tools.step_le.text()
        spectrogram_tools['cmap'] = tw.spectrogram_tools.cmap_cb.currentIndex()
        spectrogram_tools['interp_cb'] = (tw.spectrogram_tools.
                                          interp_cb.currentIndex())
        spectrogram_tools['normalize_chb'] = (tw.spectrogram_tools.
                                              normalize_chb.isChecked())
        spectrogram_tools['clim_low_le'] = int((tw.spectrogram_tools.
                                                clim_low_le.text()))
        spectrogram_tools['clim_high_le'] = int((tw.spectrogram_tools.
                                                 clim_high_le.text()))

        tools = {'general': general_tools,
                 'spectrum': spectrum_tools,
                 'spectrogram': spectrogram_tools}

        signal_props = {'sig_start': sw.sig_start,
                        'sig_stop': sw.sig_stop}

        out_dict = {'tools': tools,
                    'signal': signal_props}

        return out_dict

    def on_first_registration(self):
        """Action to be performed on first plugin registration."""
        pass
