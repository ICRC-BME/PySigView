#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 09:23:17 2017

Annotations plugin for pysigview

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

# Third party imports
import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QHBoxLayout, QPushButton,
                             QFileDialog, QLineEdit, QDialog,
                             QFormLayout, QLabel, QMessageBox,
                             QMenu, QCheckBox)

from vispy.scene import Line, LinearRegion

import pandas as pd
from pandas import DataFrame, read_sql

# Local imports
from pysigview.config.main import CONF

from pysigview.plugins.base import BasePluginWidget
from pysigview.utils.qthelpers import hex2rgba
from pysigview.widgets.dataframe_view import DataFrameView
from pysigview.utils.qthelpers import (add_actions, create_action,
                                       create_toolbutton, create_plugin_layout)
from pysigview.config.utils import get_home_dir
from pysigview.widgets.annotations.dialogs import (ConditionDialog,
                                                   HistogramDialog,
                                                   CathegoricalDialog)

from pysigview.widgets.annotations.annotation_item_widget import (
        AnnotationItemWidget)


class AnnotationList(QTreeWidget):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.main = self.parent().main

        # Hide the header for now
        self.header().close()

        # Connection
        self.itemClicked.connect(self.parent().set_active_set)
        self.itemDoubleClicked.connect(self.edit_item_label)

        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

    def enterEvent(self, event):
        self.setFocus()

    def dropEvent(self, e):
        e.setDropAction(Qt.CopyAction)

        # The source of drop fork
        if e.source() is None:  # Dropped from outside of Qt app
            e.accept()
            url = e.mimeData().urls()[0]
            # TODO - determine the type of the item dropped - file ot session
            self.parent().open_file(url.path())
        else:
            e.ignore()

    def edit_item_label(self, item, column):
        item.edit_label()

    def plot_annotations(self):
        root = self.invisibleRootItem()
        child_count = root.childCount()
        for i in range(child_count):
            ann_set = root.child(i)
            ann_set.plot_set()

#    def update_counts(self):
#        root = self.invisibleRootItem()
#        child_count = root.childCount()
#        for i in range(child_count):
#            ann_set = root.child(i)
#            ann_set.update_count()

    # TODO - adopt spyder's create shortcut system
    def open_context_menu(self, pos):
        indexes = self.selectedIndexes()
        item = self.currentItem()

        if len(indexes) == 0:
            return

        menu = QMenu()
        if type(item) == AnnotationSet:
            condition = create_action(self, '&Add condition subset',
                                      icon=None,
                                      tip='Add new subset',
                                      triggered=item.add_subsets,
                                      context=Qt.ApplicationShortcut)

            histogram = create_action(self, '&Add histogram subsets',
                                      icon=None,
                                      tip='Add histogram subsets',
                                      triggered=item.show_histogram_dialog,
                                      context=Qt.ApplicationShortcut)

            categoric = create_action(self, '&Add cathegorical subsets',
                                      icon=None,
                                      tip='Add cathegorical subsets',
                                      triggered=item.show_cathegorical_dialog,
                                      context=Qt.ApplicationShortcut)

            actions = [condition, histogram, categoric]

        elif type(item) == AnnotationSubset:
            edit = create_action(self, '&Edit condition',
                                 icon=None,
                                 tip='Edit condition',
                                 triggered=item.show_condition_dialog,
                                 context=Qt.ApplicationShortcut)

            actions = [edit]

        actions.append(None)
        delete_item = create_action(self, '&Delete item',
                                    icon=None,
                                    tip='Delete item',
                                    triggered=self.remove_selected_item,
                                    context=Qt.ApplicationShortcut)

        actions.append(delete_item)

        add_actions(menu, actions)

        menu.exec_(self.viewport().mapToGlobal(pos))

    def remove_selected_item(self):
        item = self.currentItem()
        item_idx = self.indexOfTopLevelItem(item)
        if item_idx < 0:  # Subset
            root = self.invisibleRootItem()
            child_count = root.childCount()
            for i in range(child_count):
                ann_set = root.child(i)
                ch_idx = ann_set.indexOfChild(item)
                if ch_idx >= 0:
                    ann_set.takeChild(ch_idx)
        else:
            item.plot_data = False
            item.plot_set()
            item.ann_lines.parent = None
            item.ann_reg.parent = None
            self.takeTopLevelItem(item_idx)
            self.parent().active_set = None

    def get_annotation_items(self):
        annotations = []
        for ann_i in range(self.topLevelItemCount()):
            annotations.append(self.topLevelItem(ann_i))
        return annotations


class AnnotationSet(QTreeWidgetItem):
    """
    This class holds annotations in form of pandas DataFrame and can hold
    subsets.
    """

    set_changed = pyqtSignal(name='set_changed')

    def __init__(self, parent=None, data_frame=None, df_name=None, **kwargs):
        super().__init__(parent, 1003, **kwargs)

        self.annotation_list = parent # !!! self.parent() not working??
        self.plugin = parent.parent() # !!! self.parent() not working??
        self.main = parent.main  # !!! self.parent() not working??
        self.main_scene = self.main.signal_display.signal_view.scene
        self.sd = self.main.signal_display

        if data_frame is None:
            self.df = DataFrame(columns=('start_time', 'end_time', 'channel'))
        else:
            self.df = data_frame

        if df_name is None:
            self.label_text = 'Unknown type'
        else:
            self.label_text = df_name

        self.plot_data = True

        # Widget settings
        self.item_widget = AnnotationItemWidget(self.label_text, len(self.df))
        self.treeWidget().setItemWidget(self, 0, self.item_widget)

        # Connect signals
        self.item_widget.color_select.color_changed.connect(self.change_color)
        self.item_widget.check_box.stateChanged.connect(self.evaluate_check)
        self.item_widget.view_btn.clicked.connect(self.show_df_view)

        # ----- Visuals -----
        self.ann_lines = Line(antialias=True, parent=self.main_scene)
        self.ann_reg = LinearRegion(pos=np.array([0], 'float32'),
                                    parent=self.main_scene)

        # TODO - put in conf?
        self.color = np.array([1., 0., 0., 1.], dtype=np.float32)

    def edit_label(self):
        self.item_widget.start_edit_label()

    def set_label(self, text):
        self.item_widget.label.setText(text)

    def update_count(self):
        self.item_widget.set_count(len(self.df))
        child_count = self.childCount()
        for i in range(child_count):
            ann_subset = self.child(i)
            ann_subset.update_df_map()

    def show_df_view(self):

        self.pop_diag = QDialog()
        self.pop_diag.setModal(False)

        layout = QVBoxLayout()
        self.df_view = DataFrameView(self.df, self)
        self.df_view.row_selected.connect(self.shift_to_annot)
        # FIXME: this does not wotk when edited
        self.df_view.data_changed.connect(self.plot_set)
        layout.addWidget(self.df_view)

        self.browse_cb = QCheckBox("Browse mode", self.pop_diag)
        self.browse_cb.stateChanged.connect(self.df_view.set_selection_mode)
        layout.addWidget(self.browse_cb)

        self.pop_diag.setLayout(layout)
        self.pop_diag.setVisible(True)

    def shift_to_annot(self, idx):

        # Update signal_display - data_map
        start_time = self.df.loc[idx, 'start_time']
        end_time = self.df.loc[idx, 'end_time']
        if np.isnan(end_time):
            midpoint = int(start_time)
        else:
            midpoint = int((start_time + end_time) / 2)

        self.main.signal_display.move_to_time(midpoint)

    def evaluate_check(self):
        if self.item_widget.check_box.checkState():
            self.plot_data = True
            self.plot_set()

            # Perform plot_set on annotation sets below this one
            annot_sets_n = self.annotation_list.topLevelItemCount()
            self_i = self.annotation_list.indexOfTopLevelItem(self)
            for i in range(annot_sets_n):
                ann_set = self.annotation_list.topLevelItem(i)
                if i > self_i:
                    ann_set.plot_set()

        else:
            self.plot_data = False
            self.plot_set()

            # Perform plot_set on other annotation sets
            annot_sets_n = self.annotation_list.topLevelItemCount()
            for i in range(annot_sets_n):
                ann_set = self.annotation_list.topLevelItem(i)
                if ann_set is not self:
                    ann_set.plot_set()

    def name_changed(self):
        return

    def change_color(self, color):
        self.color = hex2rgba(color.name()+'ff')
        self.plot_set()

    def plot_set(self):

        # No data has been loaded yet
        if not len(self.main.signal_display.data_map):
            return

        # No signals have been ploted yet
        if not len(self.main.signal_display.data_map.get_active_channels()):
            return

        # Gat the position inthe treewidget so that we have the order for draw
        annotation_items = self.plugin.annotation_list.get_annotation_items()
        z_pos = [i for i, x in enumerate(annotation_items) if x == self][0]
        plot_dfs = []
        colors = []
        plot_flags = []
        z_poss = []

        # TODO - master channel
        # Get pandas annotations in given times
        view_ss = self.main.signal_display.data_map.get_active_largest_ss()
#        if self.plot_data:
        view_df = self.df.loc[((self.df['start_time'] > view_ss[0])
                               & (self.df['start_time'] < view_ss[1]))
                              | ((self.df['end_time'] > view_ss[0])
                                 & (self.df['end_time'] < view_ss[1]))]

        plot_dfs.append(view_df)
        colors.append(self.color)
        plot_flags.append(self.plot_data)
        # TODO - finish for subsets and in plot_annotations function
        z_poss.append(z_pos)

        # Get subset annotations (flipped so that the bottom one is draw first)
        for child_i in range(self.childCount(), 0, -1):
            subset_item = self.child(child_i-1)
            sub_df = self.df.loc[subset_item.df_map]
            sub_df = sub_df.loc[((sub_df['start_time'] > view_ss[0])
                                 & (sub_df['start_time'] < view_ss[1]))
                                | ((sub_df['end_time'] > view_ss[0])
                                   & (sub_df['end_time'] < view_ss[1]))]
            z_pos = child_i / (self.childCount() + 1)

            plot_dfs.append(sub_df)
            colors.append(np.array(subset_item.color))
            plot_flags.append(subset_item.plot_data)
            z_poss.append(z_pos)

        self.plot_annotations(list(zip(plot_dfs, colors, plot_flags, z_poss)))

    def plot_annotations(self, plot_info):

        if not len(plot_info):
            return

        view_ss = self.main.signal_display.data_map.get_active_largest_ss()

        uni_dfs_pos = []
        uni_dfs_colors = []
        uni_dfs_conns = []

        bi_dfs_pos = []
        bi_dfs_colors = []

        # Lists for signal visual
        line_idxs = []
        line_starts = []
        line_stops = []
        line_colors = []

        for df, color, plot_flag, z_pos in plot_info:

            # ----- Channel non-specific -----

            ch_non_spec = df.loc[df['channel'].isnull()]

            if plot_flag:
                N_uni_annot = sum(ch_non_spec['end_time'].isnull())
                N_bi_annot = sum(~ch_non_spec['end_time'].isnull())

                # Uni
                pos_ch_non_spec_uni = np.zeros([2*N_uni_annot, 3])
                conn_ch_non_spec_uni = np.ones(2*N_uni_annot, 'bool')
                conn_ch_non_spec_uni[1::2] = 0

                # Bi
                pos_ch_non_spec_bi = np.zeros([4*N_bi_annot])

            else:
                # Uni
                pos_ch_non_spec_uni = np.zeros([0, 3])
                conn_ch_non_spec_uni = np.ones(0, 'bool')

                # Bi
                pos_ch_non_spec_bi = np.zeros([0])

            i_uni = 0
            i_bi = 0
            for i, ann in ch_non_spec.iterrows():
                # Uni
                if np.isnan(ann['end_time']):
                    x_pos = (ann['start_time'] - view_ss[0]) / np.diff(view_ss)

                    # We are plotting
                    if plot_flag:
                        pos_ch_non_spec_uni[i_uni] = [x_pos, 0, 0]
                        i_uni += 1
                        pos_ch_non_spec_uni[i_uni] = [x_pos, 1, 0]
                        i_uni += 1

                    # We are deleting
                    else:
                        if self.ann_lines.pos is not None:
                            an_pos = self.ann_lines.pos
                            an_color = self.ann_lines.color
                            an_conn = self.ann_lines.connect
                            pos_bool = ~((an_pos == [x_pos,
                                                     0,
                                                     z_pos]).all(1)
                                         & (an_pos == [x_pos,
                                                       1,
                                                       z_pos]).all(1))
                            self.ann_lines.set_data(pos=an_pos[pos_bool],
                                                    color=an_color[pos_bool],
                                                    connect=an_conn[pos_bool])
                # Bi
                else:
                    for t in ['start_time', 'end_time']:
                        x_pos = (ann[t] - view_ss[0]) / np.diff(view_ss)

                        # We are plotting (twice is correct)
                        if plot_flag:
                            pos_ch_non_spec_bi[i_bi] = x_pos
                            i_bi += 1
                            pos_ch_non_spec_bi[i_bi] = x_pos
                            i_bi += 1

                        # We are deleting
                        else:
                            an_pos = self.ann_reg.pos
                            an_color = self.ann_reg.color
                            pos_bool = ~(an_pos == x_pos)
                            self.ann_reg.set_data(pos=an_pos[pos_bool],
                                                  color=an_color[pos_bool])

            # ----- Channel specific -----

            # TODO: once we have multiple columns we will have to change x_pos
            view_dm = self.main.signal_display.data_map
            active_channels = view_dm.get_active_channels()
            ch_spec = df.loc[((~df['channel'].isnull())
                              & (df['channel'].isin(active_channels)))]
            N_uni_annot = sum(ch_spec['end_time'].isnull())
            N_bi_annot = sum(~ch_spec['end_time'].isnull())

            if plot_flag:
                pos_ch_spec_uni = np.zeros([2*N_uni_annot, 3])
                conn_ch_spec_uni = np.ones(2*N_uni_annot, 'bool')
                conn_ch_spec_uni[1::2] = 0
            else:
                pos_ch_spec_uni = np.zeros([0, 3])
                conn_ch_spec_uni = np.ones(0, 'bool')

            i_uni = 0
            cell_size = 1 / len(active_channels)
            for ch in ch_spec.channel.unique():

                # Get channel fs
                # fs = view_dm['fsamp'][view_dm['channels'] == ch]
                # fs = fs[0]

                # # Get channel ss
                # ch_ss = view_dm['uutc_ss'][view_dm['channels'] == ch][0]

                # Get channel location
                pc = None
                for pc in self.main.signal_display.get_plot_containers():
                    if pc.name == ch:
                        break

                # Get channel ss
                ch_ss = view_dm['uutc_ss'][view_dm['channels'] == ch][0]

                # Get number of samples
                n_samp = len(self.sd.signal_visual.pos[pc._visual_array_idx])

                for i, ann in ch_spec[ch_spec.channel == ch].iterrows():
                    # Uni
                    if np.isnan(ann['end_time']):
                        x_pos = (ann['start_time'] - ch_ss[0]) / np.diff(ch_ss)
                        y_pos_1 = pc.plot_position[1] * cell_size
                        y_pos_2 = (pc.plot_position[1]+1) * cell_size
                        z_pos = pc.plot_position[2]
                        if plot_flag:
                            pos_ch_spec_uni[i_uni] = [x_pos, y_pos_1, z_pos]
                            i_uni += 1
                            pos_ch_spec_uni[i_uni] = [x_pos, y_pos_2, z_pos]
                            i_uni += 1
                        else:
                            an_pos = self.ann_lines.pos
                            an_color = self.ann_lines.color
                            an_conn = self.ann_lines.connect
                            pos_bool = ~((an_pos == [x_pos,
                                                     y_pos_1,
                                                     z_pos]).all(1)
                                         & (an_pos == [x_pos,
                                                       y_pos_2,
                                                       z_pos]).all(1))
                            self.ann_lines.set_data(pos=an_pos[pos_bool],
                                                    color=an_color[pos_bool],
                                                    connect=an_conn[pos_bool])

                    # Bi
                    else:
                        # Colored signal

                        view_start = ann['start_time'] - ch_ss[0]
                        view_stop = ann['end_time'] - ch_ss[0]
                        start = int((view_start / np.diff(ch_ss)) * n_samp)
                        stop = int((view_stop / np.diff(ch_ss)) * n_samp)

                        if start < 0:
                            start = 0
                        if stop > n_samp:
                            stop = n_samp

                        if plot_flag:
                            line_idxs.append(pc._visual_array_idx)
                            line_starts.append(start)
                            line_stops.append(stop)
                            line_colors.append(color)

                        else:
                            line_idxs.append(pc._visual_array_idx)
                            line_starts.append(start)
                            line_stops.append(stop)
                            line_colors.append(pc.line_color)

            # Uni lines
            pos_uni = np.concatenate((pos_ch_non_spec_uni,
                                      pos_ch_spec_uni))
            conn_uni = np.concatenate((conn_ch_non_spec_uni,
                                       conn_ch_spec_uni)).astype('bool')

            if len(pos_uni) != 0:
                uni_color_arr = np.tile(color,
                                        len(pos_uni)).reshape(len(pos_uni), 4)

                uni_dfs_pos.append(pos_uni)
                uni_dfs_colors.append(uni_color_arr)
                uni_dfs_conns.append(conn_uni)

            # Bi regions
            pos_bi = pos_ch_non_spec_bi

            # Transparent - lower alpha
            reg_color = np.copy(color)
            reg_color[-1] = 0.2
            if len(pos_bi) != 0:
                color_tile = np.concatenate(([0., 0., 0., 0.], reg_color,
                                             reg_color, [0., 0., 0., 0.]))

                bi_color_arr = np.tile(color_tile,
                                       int(len(pos_bi)/4)).reshape(len(pos_bi),
                                                                   4)
                bi_dfs_pos.append(pos_bi)
                bi_dfs_colors.append(bi_color_arr)

        # Set signal coloring
        if len(line_idxs):
            self.sd.signal_visual.set_line_color(line_colors,
                                                 line_idxs,
                                                 line_starts,
                                                 line_stops)

        # Uni
        if len(uni_dfs_pos):
            pos = np.concatenate(uni_dfs_pos)
            color = np.concatenate(uni_dfs_colors)
            conn = np.concatenate(uni_dfs_conns)

            self.ann_lines.visible = True
            self.ann_lines.set_data(pos=pos,
                                    color=color,
                                    connect=conn)
        else:
            self.ann_lines.visible = False

        # Bi
        if len(bi_dfs_pos):
            pos = np.concatenate(bi_dfs_pos)
            color = np.concatenate(bi_dfs_colors)

            self.ann_reg.visible = True
            self.ann_reg.set_data(pos=pos, color=color)

        else:
            self.ann_reg.visible = False

    def add_new_subset(self):
        new_subset = AnnotationSubset(self)
        self.addChild(new_subset)
        new_subset.show_condition_dialog()

    def add_subsets(self, cond_strs_names=None):

        if not cond_strs_names:
            new_subset = AnnotationSubset(self)
            self.addChild(new_subset)
            new_subset.show_condition_dialog()
        else:
            for eval_str_name in cond_strs_names:

                new_subset = AnnotationSubset(self)
                if type(eval_str_name) == str:
                    eval_str = eval_str_name
                else:
                    eval_str = eval_str_name[0]
                    name = eval_str_name[1]
                    new_subset.set_label(name)
                self.addChild(new_subset)
                new_subset.condition_str = eval_str
                new_subset.update_df_map()

    # ----- Histogram subsets -----
    def show_histogram_dialog(self):

        # Show histogram dialog - N bins, adjustable boarders
        self.pop_diag = HistogramDialog(self.df)
        self.pop_diag.histogram_strs_created.connect(self.add_subsets)
        self.pop_diag.setModal(False)
        self.pop_diag.setVisible(True)

        return

    # ----- Cathegorical subsets -----
    def show_cathegorical_dialog(self):

        self.pop_diag = CathegoricalDialog(self.df)
        self.pop_diag.categories_strs_created.connect(self.add_subsets)
        self.pop_diag.setModal(False)
        self.pop_diag.setVisible(True)

        return


class AnnotationSubset(QTreeWidgetItem):
    """
    This class holds indices into parent AnnotationSet in form bool array
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, 1004, **kwargs)

        self.df_map = np.zeros(len(self.parent().df), bool)

        self.condition_str = ''

        self.label_text = 'NA'

        self.plot_data = True

        self.annotation_list = self.parent().annotation_list

        # Widget settings
        self.item_widget = AnnotationItemWidget(self.label_text)
        self.treeWidget().setItemWidget(self, 0, self.item_widget)

        # Connect signals
        self.item_widget.color_select.color_changed.connect(self.change_color)
        self.item_widget.check_box.stateChanged.connect(self.evaluate_check)
        self.item_widget.view_btn.clicked.connect(self.show_df_view)

        self.color = np.array([1., 0., 0., 1.], dtype=np.float32)

        # ----- Connect signals -----
        # FIXME - this is not working
        # self.parent().set_changed.connect(self.update_df_map)

    def edit_label(self):
        self.item_widget.start_edit_label()

    def set_label(self, text):
        self.item_widget.label.setText(text)

    def update_count(self):
        self.item_widget.set_count(sum(self.df_map))

    def change_color(self, color):
        self.color = hex2rgba(color.name()+'ff')
        self.parent().plot_set()

    def evaluate_check(self):
        if self.item_widget.check_box.checkState():
            self.plot_data = True
            self.parent().plot_set()

            # Perform plot_set on annotation sets below this one
            annot_sets_n = self.annotation_list.topLevelItemCount()
            self_i = self.annotation_list.indexOfTopLevelItem(self)
            for i in range(annot_sets_n):
                ann_set = self.annotation_list.topLevelItem(i)
                if i > self_i:
                    ann_set.plot_set()

        else:
            self.plot_data = False
            self.parent().plot_set()

            # Deleting - perform plot_set on other annotation sets
            annot_sets_n = self.parent().annotation_list.topLevelItemCount()
            for i in range(annot_sets_n):
                ann_set = self.parent().annotation_list.topLevelItem(i)
                if ann_set is not self:
                    ann_set.plot_set()

    def show_df_view(self):

        self.pop_diag = QDialog()
        self.pop_diag.setModal(False)

        layout = QVBoxLayout()
        self.df_view = DataFrameView(self.parent().df[self.df_map], self)
        self.df_view.row_selected.connect(self.parent().shift_to_annot)
        # FIXME: this does not wotk when edited
        self.df_view.data_changed.connect(self.parent().plot_set)
        layout.addWidget(self.df_view)

        self.browse_cb = QCheckBox("Browse mode", self.pop_diag)
        self.browse_cb.stateChanged.connect(self.df_view.set_selection_mode)
        layout.addWidget(self.browse_cb)

        self.pop_diag.setLayout(layout)
        self.pop_diag.setVisible(True)

    def show_condition_dialog(self):

        self.pop_diag = ConditionDialog(list(self.parent().df.columns),
                                        self.condition_str)
        self.pop_diag.condition_created.connect(self.create_conditions)
        self.pop_diag.setModal(False)
        self.pop_diag.setVisible(True)

        return

    def create_conditions(self, condition_str):

        self.condition_str = condition_str
        self.update_df_map()

    def update_df_map(self):

        try:
            self.df_map = eval(self.condition_str)
            self.update_count()
        except Exception:
            return

        return


class Annotations(BasePluginWidget):

    # Attributes
    CONF_SECTION = 'annotations'
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    shortcut = None

    def __init__(self, parent):
        BasePluginWidget.__init__(self, parent)

        # Widget configiration
        self.ALLOWED_AREAS = Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        self.LOCATION = Qt.RightDockWidgetArea

        # Presets for the main winow
        self.title = 'Annotations'
        self.main = parent
        self.sd = self.main.signal_display

        # TODO toolbar - adopt from Spyder
        # ----- Toolbar -----
        self.tool_buttons = []
        self.setup_buttons()
        btn_layout = QHBoxLayout()
        for btn in self.tool_buttons:
            btn.setAutoRaise(True)
            btn.setIconSize(QSize(20, 20))
            btn_layout.addWidget(btn)
#        if options_button:
#            btn_layout.addStretch()
#            btn_layout.addWidget(options_button, Qt.AlignRight)

        btn_layout.setAlignment(Qt.AlignLeft)

        # Start with database buttons inactive
        self.tool_buttons[2].setEnabled(False)
        self.tool_buttons[3].setEnabled(False)

        self.annotation_list = AnnotationList(self)
#        self.channel_list.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.annotation_mode = False
        self.user_annotation = np.array([np.nan, np.nan])
        self.user_pc = np.nan
        self.active_set = None
        self.user_annotation_type = None

        # ----- Set layout -----
        layout = create_plugin_layout(btn_layout, self.annotation_list)
#        layout.addWidget(self.annotation_list)

        self.setLayout(layout)

    def setup_buttons(self):
        open_file = create_toolbutton(self, icon='file.svg',
                                      tip='Open file',
                                      triggered=self.open_file)
        save_file = create_toolbutton(self, icon='floppy-disk.svg',
                                      tip='Open file',
                                      triggered=self.save_file)
        db_down = create_toolbutton(self, icon='database_down.svg',
                                    tip='Query database',
                                    triggered=self.show_db_down_dialog)
        dp_up = create_toolbutton(self, icon='database_up.svg',
                                  tip='Upload to database',
                                  triggered=self.show_db_up_dialog)
        add_annot = create_toolbutton(self, icon='plus.svg',
                                      tip='Add annotation set',
                                      triggered=self.add_annotation_set)

        self.tool_buttons = [open_file, save_file, db_down, dp_up, add_annot]

    def open_file(self):
        load_dialog = QFileDialog(self)

        file_types = "Python pickle (*.pkl);;CSV (*.csv)"
        load_path = load_dialog.getOpenFileName(self, 'Load annotation set',
                                                get_home_dir(),
                                                file_types)
        path = load_path[0]
        if path.endswith('pkl'):
            df = pd.read_pickle(path)
        elif path.endswith('csv'):
            df = pd.read_csv(path, skipinitialspace=True)
        else:
            QMessageBox.critical(self, "open message",
                                 "File format not supported")
            return

        self.add_annotation_set(df)

        return

    def save_file(self):

        # Check if we have an annotation set selected
        if self.active_set is None:
            QMessageBox.information(self, "No annotation set selected",
                                    "Please select an annotation set.")
            return

        # Bring up save dialog
        save_dialog = QFileDialog(self)
        save_dialog.setDefaultSuffix(".pkl")
        file_types = "Python pickle (*.pkl);;CSV (*.csv)"
        save_path = save_dialog.getSaveFileName(self, 'Save annotation set',
                                                get_home_dir(),
                                                file_types)
        path = save_path[0]
        if '.' not in path:
            path += '.pkl'

        if path.endswith('pkl'):
            self.active_set.df.to_pickle(path)
        elif path.endswith('csv'):
            self.active_set.df.to_csv(path, index=False)
        else:
            QMessageBox.critical(self, "File format not supported")

        return

    # ----- New annotations -----
    def add_annotation_set(self, df=None, name='NA'):

        if df is None or df is False:
            df = DataFrame(columns=('start_time', 'end_time', 'channel'))

        ann_group_item = AnnotationSet(self.annotation_list, df, name)
        self.annotation_list.addTopLevelItem(ann_group_item)
        ann_group_item.plot_set()

        return ann_group_item

    def set_active_set(self, item, column):

        if isinstance(item, AnnotationSubset):
            self.active_set = item.parent()
        else:
            self.active_set = item

    def recieve_input(self, event):
        if event.type == 'key_press' and event.key == 'shift':
            self.annotation_mode = True

        elif event.type == 'key_release' and event.key == 'shift':
            self.annotation_mode = False

            # If we have just start, insert uni
            if ~np.isnan(self.user_annotation[0]):
                if self.user_annotation_type == 'channel':
                    self.add_annotation(self.user_annotation,
                                        self.user_pc.orig_channel)
                elif self.user_annotation_type == 'recording':
                    self.add_annotation(self.user_annotation,
                                        np.nan)
                self.user_annotation = np.array([np.nan, np.nan])
                self.active_set.plot_set()

        if event.type != 'mouse_press' or self.annotation_mode is False:
            return
        if self.active_set is None:
            self.main.signal_display.highlight_mode = False
            self.main.signal_display.highlight_rec.color = (0, 0, 0, 0.00001)
            self.annotation_mode = False

            QMessageBox.information(self, "No annotation set selected",
                                    "Please select an annotation set.")
            event.handled = True

            return

        if event.button == 1:
            self.user_annotation_type = 'channel'
        elif event.button == 2:
            self.user_annotation_type = 'recording'

        self.user_pc = self.sd.curr_pc
        rect_rel_w_pos = self.sd.rect_rel_w_pos

        # Determine the time
        dm_pos = np.argmax(self.sd.data_map['channels']
                           == self.user_pc.orig_channel)
        uutc_ss = self.sd.data_map['uutc_ss'][dm_pos]
        uutc = int(uutc_ss[0] + (np.diff(uutc_ss) * rect_rel_w_pos))

        if np.isnan(self.user_annotation[0]):
            self.user_annotation[0] = uutc
        else:
            self.user_annotation[1] = uutc
            if self.user_annotation_type == 'channel':
                self.add_annotation(self.user_annotation,
                                    self.user_pc.orig_channel)
            elif self.user_annotation_type == 'recording':
                self.add_annotation(self.user_annotation,
                                    np.nan)
            self.user_annotation = np.array([np.nan, np.nan])
            self.active_set.plot_set()

    def add_annotation(self, uutc_ss, channel):
        df = self.active_set.df
        idx = len(df)
        df.loc[idx, ['start_time', 'end_time']] = uutc_ss
        df.loc[idx, 'channel'] = channel

        self.active_set.update_count()

    # ----- Database interface -----

    def active_db_buttons(self):
        self.tool_buttons[1].setEnabled(True)
        self.tool_buttons[2].setEnabled(True)

    def query_database(self):

        # Construct query
        print('Reading query')

        query = 'SELECT * FROM {}.{}'.format(self.db_le.text(),
                                             self.tb_le.text())

        if self.wh_le.text():
            query += ' WHERE '+self.wh_le.text()

        try:
            df = read_sql(query, self.main.database.conn)
        except Exception as e:
            QMessageBox.critical(self, "Query failed",
                                 str(e.orig))
            return

        # Check that field exists
        if not self.as_le.text() in df.keys():
            QMessageBox.critical(self, "Column missing",
                                 'Annotation start is not in table')
            return

        if not self.ae_le.text() in df.keys():
            QMessageBox.critical(self, "Column missing",
                                 'Annotation stop is not in table')
            return

        if not self.ac_le.text() in df.keys():
            QMessageBox.critical(self, "Column missing",
                                 'Annotation channel is not in table')
            return

        # Rename the fields
        rename_dict = {}
        if self.as_le.text():
            rename_dict[self.as_le.text()] = 'start_time'
        if self.ae_le.text():
            rename_dict[self.ae_le.text()] = 'end_time'
        if self.ac_le.text():
            rename_dict[self.ac_le.text()] = 'channel'
        df.rename(columns=rename_dict, inplace=True)

        # This only a one point annotation
        if not self.ae_le.text():
            df['end_time'] = np.nan

        self.add_annotation_set(df, self.tb_le.text())

        return

    def save_db_settings(self):

        prefix = 'database' + '/'

        CONF.set(self.CONF_SECTION, prefix+'database', self.db_le.text())
        CONF.set(self.CONF_SECTION, prefix+'table', self.tb_le.text())
        CONF.set(self.CONF_SECTION, prefix+'start_column', self.as_le.text())
        CONF.set(self.CONF_SECTION, prefix+'end_column', self.ae_le.text())
        CONF.set(self.CONF_SECTION, prefix+'channel_column', self.ac_le.text())
        CONF.set(self.CONF_SECTION, prefix+'where_clause', self.wh_le.text())

    def show_db_up_dialog(self):
        return

    def show_db_down_dialog(self):

        prefix = 'database' + '/'

        self.pop_diag = QDialog(self)
        self.pop_diag.setModal(True)
        self.pop_diag.accepted.connect(self.save_db_settings)
        self.pop_diag.accepted.connect(self.query_database)

        form = QFormLayout(self.pop_diag)

        # Create widgets and labels
        db_label = QLabel('Database:')
        self.db_le = QLineEdit(CONF.get(self.CONF_SECTION,
                                        prefix+'database'))
        form.addRow(db_label, self.db_le)

        tb_label = QLabel('Table:')
        self.tb_le = QLineEdit(CONF.get(self.CONF_SECTION,
                                        prefix+'table'))
        form.addRow(tb_label, self.tb_le)

        as_label = QLabel('Annotation start column:')
        self.as_le = QLineEdit(CONF.get(self.CONF_SECTION,
                                        prefix+'start_column'))
        form.addRow(as_label, self.as_le)

        ae_label = QLabel('Annotation end column:')
        self.ae_le = QLineEdit(CONF.get(self.CONF_SECTION,
                                        prefix+'end_column'))
        form.addRow(ae_label, self.ae_le)

        ac_label = QLabel('Annotation channel column:')
        self.ac_le = QLineEdit(CONF.get(self.CONF_SECTION,
                                        prefix+'channel_column'))
        form.addRow(ac_label, self.ac_le)

        wh_label = QLabel('Where cluase:')
        self.wh_le = QLineEdit(CONF.get(self.CONF_SECTION,
                                        prefix+'where_clause'))

        form.addRow(wh_label, self.wh_le)

        # OK / cancel button
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.pop_diag.accept)

        clc_btn = QPushButton('Cancel')
        clc_btn.clicked.connect(self.pop_diag.reject)

        form.addRow(ok_btn, clc_btn)

        self.pop_diag.setVisible(True)

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
        return None

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def register_plugin(self):
        """Register plugin in Pysigview's main window"""
#        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.create_toggle_view_action()

        # Plot annotations when view times are changed
        self.main.signal_display.plots_changed.connect(self.
                                                       annotation_list.
                                                       plot_annotations)
        self.main.signal_display.input_recieved.connect(self.
                                                        recieve_input)

        self.main.add_dockwidget(self)

    def delete_plugin_data(self):
        """Deletes plugin data"""

        for item in self.annotation_list.get_annotation_items():
            item.ann_lines.parent = None
            item.ann_reg.parent = None
            item_idx = self.annotation_list.indexOfTopLevelItem(item)
            self.annotation_list.takeTopLevelItem(item_idx)

        return

    def load_plugin_data(self, data):
        """Function to run when loading session"""

        present_annots = self.annotation_list.get_annotation_items()

        for an_set in data:
            # Check if the set with the given name already exists
            if len([x for x in present_annots
                    if x.label_text == an_set['text']]):
                quest_text = ('"'+an_set['text']+'" annotation set already'
                              ' exists. Do you want to load it anyway?')
                resp = QMessageBox.question(self,
                                            'Annotation set exists',
                                            quest_text)
                if resp == QMessageBox.No:
                    continue

            an_set_obj = self.add_annotation_set(an_set['df'],
                                                 an_set['text'])

            # Set color of the color widget
            t_color = tuple(an_set['color'])
            an_set_obj.item_widget.color_select.set_color(t_color)
            an_set_obj.color = t_color

            an_set_obj.plot_data = an_set['plot_data']
            an_set_obj.item_widget.check_box.setChecked(an_set['plot_data'])

            for an_subset in an_set['subsets']:
                new_subset = AnnotationSubset(an_set_obj)
                an_set_obj.addChild(new_subset)
                new_subset.df_map = an_subset['df_map']
                new_subset.condition_str = an_subset['condition_str']
                new_subset.label_text = an_subset['label_text']
                new_subset.plot_data = an_subset['plot_data']
                an_subset.item_widget.check_box.setChecked()

                # Set color of the color widget
                t_color = tuple(an_subset['color'])
                new_subset.item_widget.color_select.set_color(t_color)
                new_subset.color = t_color

            an_set_obj.plot_set()

        return None

    def save_plugin_data(self):
        """Function to run when saving session"""

        an_sets = []
        for an_set_obj in self.annotation_list.get_annotation_items():
            an_set = {}
            an_set['text'] = an_set_obj.label_text
            an_set['df'] = an_set_obj.df
            an_set['plot_data'] = an_set_obj.plot_data
            an_set['color'] = an_set_obj.color
            an_set['subsets'] = []
            for an_subset_i in range(an_set_obj.childCount()):
                an_subset_obj = an_set_obj.child(an_subset_i)
                an_subset = {}
                an_subset['df_map'] = an_subset_obj.df_map
                an_subset['condition_str'] = an_subset_obj.condition_str
                an_subset['label_text'] = an_subset_obj.label_text
                an_subset['plot_data'] = an_subset_obj.plot_data
                an_subset['color'] = an_subset_obj.color

                an_set['subsets'].append(an_subset)

            an_sets.append(an_set)

        return an_sets

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""

        # TODO: warning if there are unsaved annotations

        return True

    def refresh_plugin(self):
        """Refresh widget"""
        if self._starting_up:
            self._starting_up = False
