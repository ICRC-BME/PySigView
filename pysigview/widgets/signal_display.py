#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 10:09:46 2017

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

# Std lib imports
from time import time, sleep
import pickle


# Third party imports
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                             QDialog, QFileDialog, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread
from vispy import scene, color
from vispy.scene import (LinearRegion, Image, Mesh, GridLines, Markers, Axis,
                         Line)
from vispy.util.event import Event
import numpy as np
from scipy.io import savemat
from PIL import Image as pil_Image

# Local imports
from pysigview.cameras.signal_camera import SignalCamera
from pysigview.core.visual_container import SignalContainer
from pysigview.visuals.multicolor_text_visual import MulticolorText
from pysigview.visuals.multiline_visual import Multiline
from pysigview.visuals.crosshair_visual import Crosshair

from pysigview.config.main import CONF
from pysigview.config.utils import get_home_dir
from pysigview.core import source_manager as sm
from pysigview.core.thread_workers import TimerWorker
from pysigview.core.source_manager import DataMap
from pysigview.utils.qthelpers import (hex2rgba, create_toolbutton,
                                       create_plugin_layout)


class SignalDisplay(QWidget):

    # Attributes - tehcnically this is not a plugin but has the same attributes
    CONF_SECTION = 'signal_display'
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    shortcut = None

    # Signals
    data_map_changed = pyqtSignal(DataMap, name='data_map_changed')
    plots_changed = pyqtSignal(name='plots_changed')
    # TODO: This will send a signal to event eveluator in the future
    input_recieved = pyqtSignal(Event, name='input_recieved')
    canvas_resized = pyqtSignal(name='canvas_resized')
    subview_changed = pyqtSignal(name='subview_changed')
    stop_slide_worker = pyqtSignal()
    start_slide_worker = pyqtSignal()

    def __init__(self, parent):
        super(SignalDisplay, self).__init__(parent)

        # Covenience transcripts
        self.main = self.parent()

        # Widget behavior
        self.setAcceptDrops(True)

        # Plot variables
        self.sample_map = []
        self.plot_containers = []
        # TODO: Selected signal plot used for data shifting, colors, etc
        self.master_pc = None
        self.master_plot = None  # TODO - to be deleted
        self.curr_pc = None
        self.rect_rel_w_pos = None
        self.rect_rel_h_pos = None
        self.resize_flag = False
        self.highlight_mode = False
        self.measurement_mode = False
        self.autoscale = False

        self.disconts_processed = False

        self.data_map = DataMap()
        self.data_source = sm.ODS

        self.data_array = None

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # These variables are assigned in channels plugin
        self.hidden_channels = None
        self.visible_channels = None

        # Setup camera
        self.camera = SignalCamera()

        # Autoslide
        self.slide_worker_stopped = True
        # TODO: this should be i config
        self.slide_worker = TimerWorker(1)
        self.slide_worker_thread = QThread()
        self.slide_worker.moveToThread(self.slide_worker_thread)
        self.start_slide_worker.connect(self.slide_worker.run)
        self.stop_slide_worker.connect(self.slide_worker.interupt)
        self.slide_worker.time_passed.connect(self.autoslide)
        self.slide_worker_thread.start()

        # Vispy canvas
        self.canvas = scene.SceneCanvas(show=True, keys='interactive',
                                        parent=self,
                                        bgcolor=CONF.get(self.CONF_SECTION,
                                                         'bgcolor'))

        self.canvas.connect(self.on_key_press)
        self.canvas.connect(self.on_key_release)
        self.canvas.connect(self.on_mouse_move)
        self.canvas.connect(self.on_mouse_press)
        self.canvas.connect(self.on_mouse_release)
        self.canvas.connect(self.on_mouse_wheel)
        self.canvas.connect(self.on_resize)

        # Timer to let the scene redraw if key is hit
        self.event_time = time()
        self.plot_update_done = False

        # ??? Create two viewboxes - for labels and signals

        self.signal_view = self.canvas.central_widget.add_view(
                camera=self.camera)

        self.cong_discontinuities = None

        self.color_coding_mode = 0
        self.color_palette = CONF.get(self.CONF_SECTION, 'color_palette')

        self.update_cam_state()

        # ----- Initial visuals operations-----

        # TODO - Add crosshair color to CONF
        # Measurements
        ch_color = CONF.get(self.CONF_SECTION, 'init_crosshair_color')
        self.crosshair = Crosshair(parent=self.signal_view.scene,
                                   color=hex2rgba(ch_color))
        m_color = CONF.get(self.CONF_SECTION, 'init_marker_color')
        # TODO marker color
        self.marker = Markers(parent=self.signal_view.scene)
        self.xaxis = Axis(parent=self.signal_view.scene,
                          tick_direction=(0., 1.),
                          axis_width=1, tick_width=1,
                          anchors=('center', 'top'),
                          axis_color=m_color,
                          tick_color=m_color)
        self.x_tick_spacing = 1000
        self.yaxis = Axis(parent=self.signal_view.scene,
                          tick_direction=(1., 0.),
                          axis_width=1, tick_width=1,
                          anchors=('left', 'center'),
                          axis_color=m_color,
                          tick_color=m_color)
        self.y_tick_spacing = 100
        self.measure_line = Line(parent=self.signal_view.scene,
                                 width=3, color=m_color)
        # TODO - textbox
        self.describe_text = MulticolorText(anchor_x='left',
                                            anchor_y='bottom',
                                            parent=self.signal_view.scene)

        # Signal highlighting
        self.highlight_rec = Mesh(parent=self.signal_view.scene,
                                  color=np.array([0., 0., 0., 0.]),
                                  mode='triangle_fan')

        # Grid
        self.grid = None

        # Discontinuity
        self.disc_marker = LinearRegion(np.array([0, 0]),
                                        np.array([[0., 0., 0., 0.],
                                                 [0., 0., 0., 0.]]),
                                        parent=self.signal_view.scene)

        self.signal_label_dict = {}
        # Main signal visal with labels
        w = CONF.get(self.CONF_SECTION, 'init_line_width')
        self.signal_visual = Multiline(width=w,
                                       parent=self.signal_view.scene)
        self.label_visual = MulticolorText(anchor_x='left',
                                           anchor_y='top',
                                           parent=self.signal_view.scene)

        # TODO - one set of x and y axes for measurements

        # ----- Tool bar -----
        btn_layout = QHBoxLayout()
        for btn in self.setup_buttons():
            if btn is None:
                continue
            btn.setAutoRaise(True)
            btn.setIconSize(QSize(20, 20))
            btn_layout.addWidget(btn)
#        if options_button:
#            btn_layout.addStretch()
#            btn_layout.addWidget(options_button, Qt.AlignRight)

        # TODO - this is temporary - solve the rendering in different thread
        select_mode = QComboBox(self)
        select_mode.insertItems(0, ['Browse', 'Research'])
        antialias = CONF.get(self.CONF_SECTION, 'antialiasing')
        if antialias == 'filter':
            select_mode.setCurrentIndex(0)
        elif antialias == 'min_max':
            select_mode.setCurrentIndex(1)

        select_mode.currentIndexChanged.connect(self.switch_display_mode)
        btn_layout.addWidget(select_mode)

        # Color coding
        color_code = QComboBox(self)
        color_code.insertItems(0, ['None', 'Channel', 'Group', 'Amplitude'])
        color_code.currentIndexChanged.connect(self.switch_cc_mode)
        btn_layout.addWidget(color_code)

        # Metadata reload button
        btn_layout.setAlignment(Qt.AlignLeft)
        layout = create_plugin_layout(btn_layout)

        # ----- Set layout -----
        layout.addWidget(self.canvas.native)

        # Set the whole layout
        self.setLayout(layout)

        # Connect signals
        self.main.sig_file_opened.connect(self.initialize_data_map)
        self.main.metadata_reloaded.connect(self.create_conglomerate_disconts)
        self.plots_changed.connect(self.set_plot_update)
        self.plots_changed.connect(self.subsample)
        self.plots_changed.connect(self.rescale_grid)
        self.input_recieved.connect(self.set_highlight_mode)
        self.input_recieved.connect(self.show_measure_line)
        self.canvas_resized.connect(self.update_subsample)

    # ----- Setup functions -----
    def setup_buttons(self):
        take_screenshot = create_toolbutton(self, icon='camera.svg',
                                            tip='Take screenshot',
                                            triggered=self.take_screenshot)
        show_grid = create_toolbutton(self, icon='grid.svg',
                                      tip='Show grid',
                                      triggered=self.show_grid)
        autoscale = create_toolbutton(self, icon='autoscale.svg',
                                      tip='Autoscale',
                                      triggered=self.set_autoscale)
        save_data = create_toolbutton(self, icon='floppy-disk.svg',
                                      tip='Save displayed data',
                                      triggered=self.save_displayed_data)

        # ---- TEMP !!!  ------- -> move to the right side (add stretch)
        reload_metadata = create_toolbutton(self, icon='reload.svg',
                                            tip='Reload metadata',
                                            toggled=self.main.
                                            ss_reaload_worker)

        autoslide = create_toolbutton(self, icon='play.svg',
                                      tip='Autoslide',
                                      toggled=self.ss_autoslide_worker)
        # --------------

        return (take_screenshot, show_grid, autoscale, save_data,
                reload_metadata, autoslide)

    # ----- Key bindings -----

    def set_plot_update(self):
        self.plot_update_done = True

    def check_event_timer(self, time):
        if time - self.event_time < .1:
            return False
        else:
            return True

    def set_event_timer(self):
        self.event_time = time()

    def on_key_press(self, event):
        if event.handled:
            return

        modifiers = event.modifiers

        plot_data_operators = ['up', 'down', 'left', 'right', 'q', 'a']

        # TODO: there should be a key mapper in the future! - python dictionary

        if event.type == 'key_press':

            if (event.key in plot_data_operators
                and self.plot_update_done
                    and self.check_event_timer(time())):

                if event.key == 'Up':
                    self.scale_plot_data(True)
                if event.key == 'Down':
                    self.scale_plot_data(False)

                # These operations require data pull, introduced a timer
                # NOTE: we now know that rendering of big data takes time

                if event.key == 'Left':
                    self.plot_update_done = False
                    if 'shift' in modifiers:  # Partial shift
                        self.shift_plot_data(False, 0.5)
                    else:
                        self.shift_plot_data(False)
                if event.key == 'Right':
                    self.plot_update_done = False
                    if 'shift' in modifiers:  # Partial shift
                        self.shift_plot_data(True, 0.5)
                    else:
                        self.shift_plot_data(True)
                if event.key == 'q':
                    self.plot_update_done = False
                    self.change_time_span(True)
                if event.key == 'a':
                    self.plot_update_done = False
                    self.change_time_span(False)

                self.set_event_timer()
                event.handled = True
            else:
                self.input_recieved.emit(event)

        else:
            event.handled = False

    def on_key_release(self, event):
        if event.handled:
            return

        if event.type == 'key_release':
            self.input_recieved.emit(event)
            event.handled = True
        else:
            event.handled = False

    # ----- Highlight / measurement mode , canvas behavior -----

    def set_highlight_mode(self, event):

        if event.type not in ('key_press', 'key_release'):
            return

        if event.key not in ('shift', 'control'):
            return

        if event.type == 'key_press' and event.key == 'shift':
            self.highlight_mode = True
            self.highlight_rec.visible = True
        elif event.type == 'key_press' and event.key == 'control':
            self.measurement_mode = True
            self.crosshair.visible = True
            self.marker.visible = True
            self.xaxis.visible = True
            self.yaxis.visible = True
        elif event.type == 'key_release' and event.key == 'shift':
            self.highlight_mode = False
            self.highlight_rec.visible = False
        elif event.type == 'key_release' and event.key == 'control':
            self.measurement_mode = False
            self.crosshair.visible = False
            self.marker.visible = False
            self.xaxis.visible = False
            self.yaxis.visible = False
            self.measure_line.visible = False
            self.describe_text.visible = False

    def on_mouse_move(self, event):

        if 1 in event.buttons or 2 in event.buttons and not event.modifiers:
            self.subview_changed.emit()

        # Get position relative to zoom
        pos = event.pos[:2]
        w = self.signal_view.width
        h = self.signal_view.height
        rel_w_pos = pos[0] / w
        # TODO: flip Vispy axis
        rel_h_pos = (h-pos[1]) / h
        rect = self.camera.rect
        self.rect_rel_w_pos = rect.left + (rel_w_pos * rect.width)
        self.rect_rel_h_pos = rect.bottom + (rel_h_pos * rect.height)

        # Determine the signal plot

        rows = self.visible_channels.get_row_count()
        cols = self.visible_channels.get_col_count()

        sig_w_pos = self.rect_rel_w_pos * cols
        sig_h_pos = self.rect_rel_h_pos * rows

        for pc in self.get_plot_containers():

            if ((pc.plot_position[0]
                 < sig_w_pos
                 < pc.plot_position[0]+1)
                and (pc.plot_position[1]
                     < sig_h_pos
                     < pc.plot_position[1]+1)):

                self.curr_pc = pc
                break

        # ??? Instead of modes use event.modifiers???

        if self.highlight_mode:

            self.highlight_signal(self.curr_pc)

        if self.measurement_mode:

            self.crosshair.set_data([self.rect_rel_w_pos,
                                     self.rect_rel_h_pos])

            n_channels = self.visible_channels.get_row_count()

            # Get the location of data point
            s_y = self.curr_pc.ufact*self.curr_pc.scale_factor
            t_y = ((-np.nanmean(self.curr_pc.data)
                    * self.curr_pc.ufact
                    * self.curr_pc.scale_factor)
                   + ((0.5+self.curr_pc.plot_position[1]) / n_channels))

            data_pos = self.curr_pc.data[int(self.rect_rel_w_pos
                                             * len(self.curr_pc.data))]
            data_pos *= s_y
            data_pos += t_y

            self.marker.set_data(np.array([[self.rect_rel_w_pos, data_pos]]))

            # TODO: determine margins
            # Axes
            t_y = (self.curr_pc.plot_position[1] / n_channels)
            y_margin = 0
            self.xaxis.pos = [[rect.left,
                               t_y + y_margin],
                              [rect.left+(rect.width*self.x_tick_spacing),
                               t_y + y_margin]]
            rel_diff = (rect.right - rect.left) * np.diff(pc.uutc_ss)
            self.xaxis.domain = tuple([0, rel_diff/1000000])
            s = [1/self.x_tick_spacing, 1]
            t = [rect.left-rect.left*s[0], 0]
            self.xaxis.transform = scene.transforms.STTransform(s, t)

            x_margin = 0
            self.yaxis.pos = [[rect.left + x_margin,
                               t_y],
                              [rect.left + x_margin,
                               t_y + ((1/n_channels)*self.y_tick_spacing)]]
            s = [1, 1/self.y_tick_spacing]
            t = [0, t_y-t_y*s[1]]
            self.yaxis.transform = scene.transforms.STTransform(s, t)

            lpos = self.measure_line.pos
            if lpos is not None:
                fixed = lpos[0]
                right_angle = np.array([fixed[0], data_pos])
                moving = np.array([self.rect_rel_w_pos, data_pos])
                whole_line = np.vstack([fixed, right_angle, moving])
                self.measure_line.set_data(pos=whole_line)

                # Time
                max_step = 1/self.curr_pc.fsamp
                time_dist = moving[0]-fixed[0]
                time_dist -= time_dist % max_step
                oround = int(np.ceil((np.log10(self.curr_pc.fsamp))))
                time_str = format(time_dist, '.'+str(oround)+'f')+' s'
                time_str_pos = moving.copy()

                # Amplitude
                max_step = self.curr_pc.ufact
                amp_dist = (moving[1] - fixed[1]) / s_y
                amp_dist *= max_step
                amp_dist -= amp_dist % amp_dist
                amp_str = (format(amp_dist, '.5f') + ' ' + self.curr_pc.unit)
                amp_str_pos = moving.copy()
                amp_str_pos[0] = moving[0]
                fsize = self.describe_text.font_size
                amp_str_pos[1] += (((fsize+1)*rect.height)
                                   / self.signal_view.height)

                self.describe_text.text = [time_str, amp_str]
                self.describe_text.pos = [time_str_pos, amp_str_pos]
                self.describe_text.color = np.array([[1., 1., 1., 1.],
                                                     [1., 1., 1., 1.]],
                                                    dtype=np.float32)

        self.input_recieved.emit(event)

    def show_measure_line(self, event):

        if event.type != 'mouse_press':
            return

        modifiers = event.modifiers

        if 'control' in modifiers:

            # Get position relative to zoom
            self.measure_line.visible = True
            pos = self.marker._data['a_position'][0][:2]
            self.measure_line.set_data(pos=np.tile(pos, 3).reshape([3, 2]))

            self.describe_text.visible = True

    def on_mouse_press(self, event):
        self.input_recieved.emit(event)

    def on_mouse_release(self, event):
        self.subsample()
        self.update_labels()

    def on_mouse_wheel(self, event):

        # TODO: subsample for zoom
        # Get x_pos
        x_pos = event.pos[0]

        # Get the zoomed area

    def on_resize(self, event):
        self.resize_flag = True
        if np.any(self.main.signal_display.data_map['ch_set']):
            self.canvas_resized.emit()

    # ----- Screenshot -----

    def save_image(self):
        im = pil_Image.fromarray(self.screen_img)

        save_dialog = QFileDialog(self)
        save_dialog.selectFile('pysigview_screenshot.png')
        save_path = save_dialog.getSaveFileName(self, 'Save File',
                                                get_home_dir(),
                                                "Images (*.png *.tiff *.jpg)")
        path = save_path[0]
        if not any([x for x in ['.png', '.tiff', '.jpg'] if x in path]):
            path += '.png'
        im.save(path)
        return

    def close_screenshot(self):
        self.screenshot_diag.reject()

    def take_screenshot(self):
        self.screen_img = self.canvas.render()

        # Pop the screenshot window
        self.screenshot_diag = QDialog(self)
        self.screenshot_diag.setModal(False)

        # Set the image
        canvas = scene.SceneCanvas(show=True, size=self.canvas.size,
                                   parent=self.screenshot_diag)
        view = canvas.central_widget.add_view()
        Image(self.screen_img, parent=view.scene)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(canvas.native)

        button_layout = QHBoxLayout()

        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.close_screenshot)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton('Save')
        save_btn.clicked.connect(self.save_image)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.screenshot_diag.setLayout(layout)
        self.screenshot_diag.setVisible(True)

    # ----- Grid -----
    def show_grid(self):

        if not len(self.get_plot_containers()):
            return
        if self.grid is None:
            rows = self.visible_channels.get_row_count()
            if rows:
                y_scale = 1/rows
            else:
                y_scale = 1

            if self.master_plot:
                pass  # TODO
            else:
                uutc_ss = self.data_map.get_active_largest_ss()
                span_secs = np.diff(uutc_ss) / 1e6
                order_m = 10 ** (np.floor(np.log10(span_secs)))
                x_scale = order_m / span_secs

            c = CONF.get(self.CONF_SECTION, 'grid_color')
            self.grid = GridLines(scale=(x_scale, y_scale),
                                  color=c,
                                  parent=self.signal_view.scene)
        else:
            self.grid.parent = None
            self.grid = None

    def rescale_grid(self):
        if self.grid is not None:
            self.grid.parent = None
            self.grid = None
            rows = self.visible_channels.get_row_count()
            if rows:
                y_scale = 1/rows
            else:
                y_scale = 1

            if self.master_plot:
                pass  # TODO
            else:
                uutc_ss = self.data_map.get_active_largest_ss()
                span_secs = np.diff(uutc_ss) / 1e6
                order_m = 10 ** (np.floor(np.log10(span_secs)))
                x_scale = order_m / span_secs

            self.grid = GridLines(scale=(x_scale, y_scale),
                                  parent=self.signal_view.scene)

    # ----- Autoscale -----
    def set_autoscale(self):
        pcs = self.get_plot_containers()

        for pc in pcs:
            if pc.autoscale:
                pc.autoscale = False
                pc.scale_factor = 1
            else:
                pc.autoscale = True

        self.update_signals()

    # ----- Save displayed data -----
    def save_displayed_data(self):

        # Bring up save dialog
        save_dialog = QFileDialog(self)
        save_dialog.setDefaultSuffix(".pkl")
        file_types = "Python pickle (*.pkl);;Matlab (*.mat)"
        save_path = save_dialog.getSaveFileName(self, 'Save displayed data',
                                                get_home_dir(),
                                                file_types)

        # Get the data from visuals
        names = []
        data = []
        for pc in self.get_plot_containers():
            names.append(pc.container.item_widget.label.text())
            data.append(self.data_array[pc.data_array_pos][0])

        data = np.vstack(data)

        dict_out = {'channel_names': names,
                    'data': data}

        path = save_path[0]
        # Evaluate the extension and save
        if save_path[1] == "Python pickle (*.pkl)":
            if '.pkl' not in path:
                path += '.pkl'
            with open(path, 'wb') as fid:
                pickle.dump(dict_out, fid)
        elif save_path[1] == "Matlab (*.mat)":
            if '.mat' not in path:
                path += '.mat'
            savemat(path, dict_out)

        return

    # ----- Display mode switch -----

    def switch_display_mode(self, mode):
        if mode == 0:
            CONF.set(self.CONF_SECTION, 'antialiasing', 'filter')

        elif mode == 1:
            CONF.set(self.CONF_SECTION, 'antialiasing', 'min_max')

        self.update_subsample()

        if len(self.data_map.get_active_channels()):
            self.set_plot_data()

        return

    def update_subsample(self):

        antialias = CONF.get(self.CONF_SECTION, 'antialiasing')

        pcs = self.get_plot_containers()
        for pc in pcs:
            if antialias == 'filter':
                pc.N = int(self.canvas.central_widget.width)
            elif antialias == 'min_max':
                pc.N = None

    # ----- Color coding -----
    def switch_cc_mode(self, coding):
        self.color_coding_mode = coding

        self.color_code()

    def color_code(self):

        pcs = self.get_plot_containers()
        if not len(pcs):
            return

        if self.color_coding_mode == 0:
            c = hex2rgba(CONF.get(self.CONF_SECTION, 'init_line_color'))
            for pc in pcs:
                pc.line_color = c
                pc.container.item_widget.color_select.set_color(c)
            self.update_labels()
        elif self.color_coding_mode == 1:
            # Channels
             #TODO - in prefs, color.get_colormaps()
            cm = color.get_colormap(self.color_palette)
            colors = cm[np.linspace(0, 1, len(pcs))]

            for pc, c in zip(pcs, colors):
                pc.line_color = c.rgba[0]
                pc.container.item_widget.color_select.set_color(c.rgba[0])
            self.update_labels()
            # Acquire the colors based on number of channels
            # ???Introduce a limit??? If not the channels might be too simliar
        elif self.color_coding_mode == 2:
            # Groups
            ch_names = [x.orig_channel for x in pcs]
            g_names = []
            for ch_name in ch_names:
                g_name = ''.join([i for i in ch_name if not i.isdigit()])
                g_names.append(g_name)
            g_names = list(set(g_names))

            # TODO - in prefs, color.get_colormaps()
            cm = color.get_colormap(self.color_palette)
            colors = cm[np.linspace(0, 1, len(g_names))]

            for g_name, c in zip(g_names, colors):
                g_pcs = [x for x in pcs
                         if x.orig_channel[:len(g_name)] == g_name]
                for pc in g_pcs:
                    pc.line_color = c.rgba[0]
                    pc.container.item_widget.color_select.set_color(c.rgba[0])
            self.update_labels()

        elif self.color_coding_mode == 3:
            # Amplitude
            pass
        else:
            pass

        self.update_signals()

    # ----- Autoslide -----
    def autoslide(self):
        self.shift_plot_data(True)

    def ss_autoslide_worker(self):
        if self.slide_worker_stopped:
            self.start_slide_worker.emit()
            self.slide_worker_stopped = False
        else:
            self.stop_slide_worker.emit()
            self.slide_worker_stopped = True

    # ----- Camera handling -----
    def reset_cam(self):
        self.camera.set_state(self.orig_cam_state)

    def update_cam_state(self):
        self.orig_cam_state = self.camera.get_state()

    # ----- QT Widget behavior (drag/drops) -----

    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        event.setDropAction(Qt.CopyAction)
        source = event.source()
        # The source of drop fork
        if event.source() is None:  # Dropped from outside of Qt app
            event.accept()
            url = event.mimeData().urls()[0]
            self.main.open_data_source(url.path())
        elif event.source() == self.hidden_channels:  # Hidden channel list
            event.accept()
            self.visible_channels.insert_items([x.text() for x
                                                in source.drag_items])
        else:
            event.ignore()

    def enterEvent(self, event):
        self.canvas.native.setFocus()

    # ----- Data handling -----
    def get_minmax_idxs(self, sig, step):

        N = int(np.ceil(len(sig) / step))

        max_idx = np.empty(N, 'uint32')
        min_idx = np.empty(N, 'uint32')

        trans_sig = np.resize(sig, (N, step))
        max_idx = trans_sig.argmax(1)
        max_idx += (np.arange(N)*step)
        max_idx[max_idx >= len(sig)] = len(sig) - 1
        min_idx = trans_sig.argmin(1)
        min_idx += (np.arange(N)*step)
        min_idx[min_idx >= len(sig)] = len(sig) - 1

        return max_idx, min_idx

    def subsample(self):

        rect = self.signal_view.camera.rect
        w = rect.width
        max_viewed_points = 10000

        right = rect.right
        left = rect.left

        if left < 0:
            left = 0
        if right > 1:
            right = 1

        vis_pos = self.signal_visual.pos
        vis_index = self.signal_visual.index
        indices = np.hstack([0, np.cumsum([len(x) for x in vis_pos])[:-1]])

        for pc in self.get_plot_containers():
            pos_i = pc._visual_array_idx
            line_len = len(vis_pos[pos_i])
            fraction = int((line_len * w) // max_viewed_points)

            li = int(np.floor(left*line_len))
            ri = int(np.floor(right*line_len))

            if fraction <= 1:
                vis_index[indices[pos_i]:indices[pos_i]+line_len] = 0
                vis_index[li + indices[pos_i]:ri + indices[pos_i]] = 1

            else:
                max_idx, min_idx = self.get_minmax_idxs(vis_pos[pos_i][li:ri],
                                                        fraction)

                # Corect the max min indices to line pos
                max_idx += (li + indices[pos_i])
                min_idx += (li + indices[pos_i])

                vis_index[indices[pos_i]:indices[pos_i]+line_len] = 0
                vis_index[(max_idx) & (min_idx)] = 1

        self.signal_visual.index = vis_index

    # ----- Discontinuities -----
    def create_conglomerate_disconts(self):

        # TODO: what if the channels are changed? This should not be run!

        disconts = sm.ODS.data_map['discontinuities']
        chan_mask = self.main.signal_display.data_map['ch_set']
        disconts = disconts[chan_mask]

        # Do not process disconts that are already processed
        if self.disconts_processed:
            proc_start = self.cong_discontinuities[0][0]
            proc_stop = self.cong_discontinuities[-1][-1]
            for i in range(len(disconts)):
                disconts[i] = disconts[i][(disconts[i][:, 0] > proc_start)
                                          & (disconts[i][:, 1] < proc_stop)]

        # Channel with the fewest disconts
        min_disc_ch_idx = np.argmin([len(x) for x in disconts])
        min_disc_ch = disconts[min_disc_ch_idx]

        conglom_discs = []
        # Iterate over the rest of channels
        for di, intersect in enumerate(min_disc_ch):
            ch_count = 1
            for cdi, ch_discs in enumerate(np.delete(disconts,
                                                     min_disc_ch_idx)):
                # Get starts in inclusive intervals
                idx = np.where((intersect[0] <= ch_discs[:, 0])
                               & (ch_discs[:, 0] <= intersect[1]))[0]

                if len(idx):
                    intersect[0] = ch_discs[idx][0][0]

                # Get stops in inclusive intervals
                idx = np.where((intersect[0] <= ch_discs[:, 1])
                               & (ch_discs[:, 1] <= intersect[1]))[0]

                if len(idx):
                    intersect[1] = ch_discs[idx][0][1]

                ch_count += 1

            # Is the discontinuity in all channels?
            if ch_count == len(disconts):
                conglom_discs.append(intersect)

        if self.disconts_processed:
            if len(conglom_discs):
                self.cong_discontinuities = np.concatenate(
                        [self.cong_discontinuities, np.array(conglom_discs)])
        else:
            self.cong_discontinuities = np.array(conglom_discs)
            self.disconts_processed = True

    # ----- Data map operations -----

    def initialize_data_map(self):
        self.data_map.setup_data_map(sm.ODS.data_map._map)
        self.data_map.reset_data_map()

    # TODO: what if there are two channels with the same orig_channels
    # TODO: what if one container has more org_channels (i.e. montage)
    def update_data_map_channels(self):
        """
        Updates data_map from visible_channels pane and reloads the data.
        """

        pcs = self.get_plot_containers()

        # Check if some channels are duplicate
        channels = []
        uutc_ss = []
        for pc in pcs:
            pc_chans = [pc.orig_channel] + pc.add_channels
            # Check if channel is already in the list
            # !!! TODO - TEMP see the todo above function for montage channels
            if any([True for x in pc_chans if x in channels]):

                for o_ch in [x for x in pc_chans if x in channels]:
                    if o_ch in channels:
                        ch_idx = channels.index(o_ch)
                        if np.diff(uutc_ss[ch_idx]) < np.diff(pc.uutc_ss):
                            uutc_ss[ch_idx] = pc.uutc_ss
                    else:
                        channels.append(o_ch)
                        uutc_ss.append(pc.uutc_ss)

            else:
                for o_ch in pc_chans:
                    channels.append(o_ch)
                    uutc_ss.append(pc.uutc_ss)

        self.data_map.reset_data_map()
        self.data_map.set_channel(np.array(channels),
                                  np.array(uutc_ss))

        self.create_conglomerate_disconts()
        self.check_data_map_uutc_ss()
        self.set_plot_data()

        # Reset data_array where the channel is not set
        self.data_array[~self.data_map._map['ch_set']] = np.array(0, 'float32')

    # ----- Load data start -----

    def get_plot_containers(self):
        items = self.visible_channels.get_container_items()
        return [x.pvc for x in items]

    # XXX - this could probably be made into a general plot_container function
    def add_signal_container(self, orig_channel):
        container_items = self.visible_channels.get_container_items()

        mf_scale_fatcor = None
        scale_factors = [x.pvc.scale_factor for x in container_items]
        if scale_factors:
            # In case of half/half, let python choose :-)
            mf_scale_fatcor = max(scale_factors, key=scale_factors.count)

        # Get the max span and assign to new signals
        largest_ss = self.data_map.get_active_largest_ss()

        pc = SignalContainer(orig_channel)
        ci = sm.ODS.data_map['channels'] == pc.orig_channel
        ci_entry = sm.ODS.data_map[ci]
        pc.fsamp = ci_entry['fsamp'][0]
        pc.unit = ci_entry['unit'][0]
        pc.ufact = ci_entry['ufact'][0]
        pc.nsamp = ci_entry['nsamp'][0]
        pc.start_time = ci_entry['uutc_ss'][0][0]

        antialias = CONF.get(self.CONF_SECTION, 'antialiasing')
        if antialias == 'filter':
            pc.N = int(self.canvas.central_widget.width)
        elif antialias == 'min_max':
            pc.N = None

        c = hex2rgba(CONF.get(self.CONF_SECTION, 'init_line_color'))

        pc.line_color = np.array(c)

        pc.data_array_pos = [np.where(ci)[0][0]]

        # Scale factor
        if mf_scale_fatcor:
            pc.scale_factor = mf_scale_fatcor
        # Time span
        init_tscale = CONF.get(self.CONF_SECTION, 'init_time_scale')*1e6
        if np.diff(largest_ss):
            pc.uutc_ss = largest_ss
        else:
            pc.uutc_ss = [pc.start_time, pc.start_time+init_tscale]

        return pc

    def side_flash(self, color=None):

        color = hex2rgba(CONF.get(self.CONF_SECTION, 'side_flash_color'))

        if self.discont_side == 1:  # left
            pos = np.array([0., 0.1])
            color = np.vstack([color,
                               [0., 0., 0., 0.]])
        elif self.discont_side == 2:  # right
            pos = np.array([0.9, 1.0])
            color = np.vstack([[0., 0., 0., 0.],
                               color])
        else:
            pos = np.array([0., 0.])
            color = np.zeros([2, 4])

        self.disc_marker.set_data(pos, color)
        return

    def check_uutc_ss(self, uutc_ss):

        # Checks recording start and stop
        span = np.diff(uutc_ss)[0]
        if uutc_ss[0] < sm.ODS.recording_info['recording_start']:
            uutc_ss[0] = sm.ODS.recording_info['recording_start']
        if span < sm.ODS.recording_info['recording_duration']:
            uutc_ss[1] = uutc_ss[0] + span

        if uutc_ss[1] > sm.ODS.recording_info['recording_end']:
                uutc_ss[1] = sm.ODS.recording_info['recording_end']
        if span < sm.ODS.recording_info['recording_duration']:
            uutc_ss[0] = uutc_ss[1] - span

        self.discont_side = 0

        # Checks for discontinuities
        if self.cong_discontinuities is not None:
            max_span = np.diff(self.data_map.get_active_largest_ss())
            large_disconts_idxs = np.diff(self.cong_discontinuities) > max_span
            large_disconts_idxs = large_disconts_idxs.ravel()
            large_disconts = self.cong_discontinuities[large_disconts_idxs]

            starts = large_disconts[:, 0] <= uutc_ss[0]
            stops = uutc_ss[0] <= large_disconts[:, 1]
            in_discont_idx = np.where(starts & stops)[0]
            if len(in_discont_idx):
                in_discont = large_disconts[in_discont_idx][0]
                uutc_ss[0] = in_discont[1]
                uutc_ss[1] = uutc_ss[0] + span
                self.discont_side = 1  # left side
                self.curr_discont = in_discont

            starts = large_disconts[:, 0] <= uutc_ss[1]
            stops = uutc_ss[1] <= large_disconts[:, 1]
            in_discont_idx = np.where(starts & stops)[0]
            if len(in_discont_idx):
                in_discont = large_disconts[in_discont_idx][0]
                uutc_ss[1] = in_discont[0]
                uutc_ss[0] = uutc_ss[1] - span
                self.discont_side = 2  # right side
                self.curr_discont = in_discont

        return uutc_ss

    def check_data_map_uutc_ss(self):
        corrected_uutc_ss = []
        for uutc_ss in self.data_map.get_active_uutc_ss():
            corrected_uutc_ss.append(self.check_uutc_ss(uutc_ss))

        channels = self.data_map.get_active_channels()
        self.data_map.set_channel(channels, corrected_uutc_ss)
        self.data_map_changed.emit(self.data_map)
        self.side_flash()

    def check_pcs_uutc_ss(self):
        for pc in self.get_plot_containers():
            pc.uutc_ss = self.check_uutc_ss(pc.uutc_ss)

    def calculate_sample(self, pc):
        ch_i = np.where(self.data_map['channels'] == pc.orig_channel)[0]
        dm_uutc_ss = self.data_map['uutc_ss'][ch_i][0]

        start = int(((pc.uutc_ss[0] - dm_uutc_ss[0]) / 1e6) * pc.fsamp)
        stop = int(((pc.uutc_ss[1] - dm_uutc_ss[0]) / 1e6) * pc.fsamp)

        return start, stop

    # TODO - when chnaging individual channel time scale
    # the set_plot_data function is called twice - eliminate
    def set_plot_data(self, uutc_ss=None, channels=None):

        if self.data_array is None:
            first_load = True
        else:
            first_load = False

        # This check whether provider data source is a buffer
        if getattr(sm.PDS, "is_available", None):
            while not sm.PDS.is_available(self.data_map):
                sleep(0.1)
                continue

        self.data_array = sm.PDS.get_data(self.data_map)

        pcs = self.get_plot_containers()
        for pc in pcs:
            start, stop = self.calculate_sample(pc)
            pc.data = np.array([x[start:stop] for x
                                in self.data_array[pc.data_array_pos]])

        if first_load:
            self.autoscale_plot_data(pcs[0])
            for pc in pcs[1:]:
                pc.scale_factor = pcs[0].scale_factor

        self.update_signals()

        if self.resize_flag:
            self.resize_flag = False

        return

    # ----- Signal updating functions -----

    def update_labels(self):
        """
        Update names, positions and labels
        """

        # Get current view left boundry
        rect = self.signal_view.camera.rect
        left = rect.left

        name_list = []
        pos_list = []
        color_list = []
        for pc in self.get_plot_containers():

            if self.signal_visual.visibility[pc._visual_array_idx]:
                name_list.append(pc.name)
                color_list.append(pc.line_color)

                # Label position
                l_x = pc.plot_position[0] + left
                l_y = (pc.plot_position[1]
                       / self.visible_channels.get_row_count())
                l_y += 1 / self.visible_channels.get_row_count()
                y_shift = (pc.plot_position[2]
                           / self.canvas.central_widget.height)
                l_y -= y_shift * self.label_visual.font_size
                pos_list.append([l_x, l_y, 0])

        if len(name_list) == 0:
            self.label_visual.text = None
        else:
            self.label_visual.text = name_list
            self.label_visual.pos = pos_list
            self.label_visual.color = np.c_[color_list]

    def update_signals(self):

        scales = []
        offsets = []
        color_list = []
        data = np.empty(len(self.get_plot_containers()), object)
        visibility = []
        for li, pc in enumerate(self.get_plot_containers()):

            data[li] = pc.data
            pc._visual_array_idx = li

            visibility.append(pc.visible)

            if pc.autoscale:
                self.autoscale_plot_data(pc)

            # Scale
            s_x = 1/len(pc.data)
            s_y = pc.ufact*pc.scale_factor
            s_z = 0
            scales.append([s_x, s_y, s_z])

            # Translate
            t_x = pc.plot_position[0]
            t_y = ((-np.nanmean(pc.data)
                    * pc.ufact
                    * pc.scale_factor)
                   + ((0.5+pc.plot_position[1])
                   / self.visible_channels.get_row_count()))
            t_z = pc.plot_position[2]
            offsets.append([t_x, t_y, t_z])

            color_list.append(pc.line_color)

        if len(data) == 0:
            pos = np.empty(1, dtype=object)
            pos[0] = np.array([0], dtype=np.float32)
            self.signal_visual.pos = pos
        else:
            self.signal_visual.set_data(pos=data,
                                        scales=scales, offsets=offsets,
                                        color=color_list,
                                        visibility=visibility)

        self.update_labels()
        self.plots_changed.emit()

    def move_to_time(self, midpoint):
        """
        Moves the view to requested time(will be in the middle)
        """

        a_channels = self.data_map.get_active_channels()
        a_uutc_ss = self.data_map.get_active_uutc_ss()
        a_spans = np.diff(a_uutc_ss).ravel()

        a_uutc_ss[:, 0] = midpoint - (a_spans / 2)
        a_uutc_ss[:, 1] = midpoint + (a_spans / 2)

        self.data_map.set_channel(a_channels, a_uutc_ss)

        # Update individual plot containers
        for pc in self.main.signal_display.get_plot_containers():
            span = np.diff(pc.uutc_ss)[0]
            pc.uutc_ss[0] = int(midpoint - (span / 2))
            pc.uutc_ss[1] = int(midpoint + (span / 2))

        self.check_pcs_uutc_ss()
        self.check_data_map_uutc_ss()
        self.set_plot_data()

    def shift_plot_data(self, forward=True, shift_span=None):

        # Take care of discontinuities
        if self.discont_side:
            span = np.diff(self.data_map.get_active_largest_ss())[0]
            if self.discont_side == 1 and not forward:
                midpoint_to_go = self.curr_discont[0] - (span / 2)
                self.move_to_time(midpoint_to_go)
                return
            elif self.discont_side == 2 and forward:
                midpoint_to_go = self.curr_discont[1] + (span / 2)
                self.move_to_time(midpoint_to_go)
                return

        if self.master_plot:
            uutc_ss = self.master_plot.uutc_ss
            base_span = np.diff(uutc_ss)
        else:
            base_span = np.diff(self.data_map.get_active_largest_ss())[0]

        if shift_span is None:
            span = base_span
        elif shift_span < 1:
            span = base_span * shift_span
        else:
            span = shift_span

        a_channels = self.data_map.get_active_channels()
        a_uutc_ss = self.data_map.get_active_uutc_ss()

        if forward:
            a_uutc_ss += int(span)
            self.data_map.set_channel(a_channels, a_uutc_ss)
        else:
            a_uutc_ss -= int(span)
            self.data_map.set_channel(a_channels, a_uutc_ss)

        for pc in self.get_plot_containers():
            if forward:
                pc.uutc_ss[0] += int(span)
                pc.uutc_ss[1] += int(span)
            else:
                pc.uutc_ss[0] -= int(span)
                pc.uutc_ss[1] -= int(span)

        self.check_pcs_uutc_ss()
        self.check_data_map_uutc_ss()
        self.set_plot_data()

        return

    def change_time_span(self, up=True, channels=None, scale=2):
        """
        Changes the time scale of plots
        """

        a_channels = self.data_map.get_active_channels()
        a_uutc_ss = self.data_map.get_active_uutc_ss()
        a_spans = np.diff(a_uutc_ss).ravel()
        a_midpoints = np.sum(a_uutc_ss, 1) / 2

        if up:
            a_uutc_ss[:, 0] = a_midpoints - (scale * (a_spans / 2))
            a_uutc_ss[:, 1] = a_midpoints + (scale * (a_spans / 2))
            self.data_map.set_channel(a_channels, a_uutc_ss)
        else:
            a_uutc_ss[:, 0] = a_midpoints - ((1/scale) * (a_spans / 2))
            a_uutc_ss[:, 1] = a_midpoints + ((1/scale) * (a_spans / 2))
            self.data_map.set_channel(a_channels, a_uutc_ss)

        for pc in self.get_plot_containers():
            span = np.diff(pc.uutc_ss)[0]
            midpoint = np.sum(pc.uutc_ss) / 2
            if up:
                pc.uutc_ss[0] = midpoint - (scale * (span / 2))
                pc.uutc_ss[1] = midpoint + (scale * (span / 2))
            else:
                pc.uutc_ss[0] = midpoint - ((1/scale) * (span / 2))
                pc.uutc_ss[1] = midpoint + ((1/scale) * (span / 2))

        self.check_pcs_uutc_ss()
        self.check_data_map_uutc_ss()
        self.set_plot_data()

        return

    def set_time_span_all(self, span):
        a_channels = self.data_map.get_active_channels()
        a_uutc_ss = self.data_map.get_active_uutc_ss()
        a_midpoints = np.sum(a_uutc_ss, 1) / 2

        a_uutc_ss[:, 0] = a_midpoints - (span / 2)
        a_uutc_ss[:, 1] = a_midpoints + (span / 2)
        self.data_map.set_channel(a_channels, a_uutc_ss)

        for pc in self.get_plot_containers():
            midpoint = np.sum(pc.uutc_ss) / 2
            pc.uutc_ss[0] = midpoint - (span / 2)
            pc.uutc_ss[1] = midpoint + (span / 2)

        self.check_pcs_uutc_ss()
        self.check_data_map_uutc_ss()
        self.set_plot_data()

    def scale_plot_data(self, up=True, scale=2):
        for pc in self.get_plot_containers():
            if up:
                pc.scale_factor = pc.scale_factor * scale
            else:
                pc.scale_factor = pc.scale_factor / scale

        self.update_signals()
        return

    def autoscale_plot_data(self, pc):
        amp_span = np.abs(np.nanmax(pc.data)
                          - np.nanmin(pc.data))
        row_span = 1 / self.visible_channels.get_row_count()
        pc.scale_factor = row_span / (amp_span * pc.ufact)

    def highlight_signal(self, pc):

        # Determine the signal rectangle
        w_step = 1/self.visible_channels.get_col_count()
        h_step = 1/self.visible_channels.get_row_count()

        # Pixel rel size to plot in inner rectangle
        pix_w = 1/self.signal_view.width
        pix_h = 1/self.signal_view.height

        rel_sig_w = pc.plot_position[0] * w_step
        rel_sig_h = pc.plot_position[1] * h_step

        left = rel_sig_w + (3*pix_w)
        right = rel_sig_w + w_step - (2*pix_w)
        bottom = rel_sig_h + (2*pix_h)
        top = rel_sig_h + h_step - (3*pix_h)
        pos = np.array([[left, bottom, 10],
                        [right, bottom, 10],
                        [right, top, 10],
                        [left, top, 10]])

        self.highlight_rec.set_data(vertices=pos,
                                    color=np.concatenate([pc.line_color[:-1],
                                                          [0.2]]))

        return
