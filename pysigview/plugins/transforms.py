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
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout,
                             QWidget, QStackedWidget,
                             QListWidget, QTreeWidget, QTreeWidgetItem,
                             QPushButton, QCheckBox, QLabel)

from vispy import scene

# Local imports
from pysigview.plugins.base import BasePluginWidget
# from pysigview.config.main import CONF
from pysigview.cameras.signal_camera import SignalCamera
from pysigview.widgets.transforms.filters import Filters
from pysigview.widgets.transforms.montages import Montages
from pysigview.widgets.transforms.envelopes import Envelopes
from pysigview.plugins.channels import PlotContainerItem, PlotCollectionItem

from pysigview.visuals.simple_line_visual import SimpleLine


class TransformChainItem(QTreeWidgetItem):

    def __init__(self, parent, channel_item):
        super().__init__(parent)

        self.channel_item = channel_item

        # Chekc if the item is a container
        if hasattr(self.channel_item, 'pvc'):
            self.vc = channel_item.pvc
            self.temporary_chain = self.vc.transform_chain[:]


class TransformChainView(QTreeWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.main = self.parent().main

        # Convenience
        self.visible_channels = None

        # Widget behavior
        self.setAcceptDrops(True)

        self.orig_channel_items = []

        self.itemClicked.connect(self.set_preview_pvc)

    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        event.setDropAction(Qt.CopyAction)

        # Dropped from outside of Qt app
        if event.source() == self.visible_channels:
            event.accept()

            self.orig_channel_items = self.visible_channels.drag_items

            for di in self.orig_channel_items:
                if isinstance(di, PlotCollectionItem):
                    coll_trans_item = TransformChainItem(self, di)
                    coll_trans_item.setText(0, di.text(0))
                    for cont_i in range(di.childCount()):
                        container_item = di.child(cont_i)
                        cont_trans_item = TransformChainItem(coll_trans_item,
                                                             container_item)
                        cont_trans_item.setText(0, container_item.pvc.
                                                orig_channel)
                        for i, trans in enumerate(container_item.pvc.
                                                  transform_chain):
                            cont_trans_item.setText(i+1, trans.name)

                    self.addTopLevelItem(coll_trans_item)

                elif isinstance(di, PlotContainerItem):
                    cont_trans_item = TransformChainItem(self, di)
                    cont_trans_item.setText(0, di.pvc.name)
                    for i, trans in enumerate(di.pvc.transform_chain):
                            cont_trans_item.setText(i+1, trans.name)
                    self.addTopLevelItem(cont_trans_item)
                else:
                    pass

            self.create_transform_columns()

        else:
            event.ignore()

    def set_preview_pvc(self, item):
        if hasattr(item.channel_item, 'pvc'):
            pvc = item.channel_item.pvc
            temp_chain = item.temporary_chain
            self.parent().signal_preview.preview_pvc = pvc
            self.parent().signal_preview.preview_transform_chain = temp_chain

            self.parent().signal_preview.set_orig_trans_sig()

    def create_transform_columns(self):

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)

            if hasattr(item.channel_item, 'pvc'):
                n_transforms = len(item.temporary_chain)
                if n_transforms + 1 > self.columnCount():
                    self.setColumnCount(n_transforms + 1)
                for k in range(n_transforms):
                    trans = item.temporary_chain[k]
                    item.setText(k+1, trans.name)
            else:
                for j in range(item.childCount()):
                    child_item = item.child(j)
                    if hasattr(child_item.channel_item, 'pvc'):
                        n_transforms = len(child_item.temporary_chain)
                        if n_transforms + 1 > self.columnCount():
                            self.setColumnCount(n_transforms + 1)
                        for k in range(n_transforms):
                            trans = child_item.temporary_chain[k]
                            child_item.setText(k+1, trans.name)


class TransformButtons(QWidget):
    """
    Holds buttons for operations with transforms
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.main = self.parent().main
        self.plugin = self.parent()

        # Convenience
        self.visible_channels = None

        # Widget layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.add_btn = QPushButton('Add transform')
        self.add_btn.setDisabled(True)

        self.add_to_all_label = QLabel('Add to all:')
        self.add_to_all_cb = QCheckBox()

        self.apply_btn = QPushButton('Apply')
        self.apply_btn.setDisabled(True)

        self.create_copies_label = QLabel('Create copies:')
        self.creat_copies_cb = QCheckBox()

        # Connect signals
        self.add_btn.pressed.connect(self.add_transforms)
        self.apply_btn.pressed.connect(self.apply_transforms)

        # Asemble the layout
        layout.addWidget(self.add_btn)

        layout.addWidget(self.add_to_all_label)
        layout.addWidget(self.add_to_all_cb)

        layout.addWidget(self.apply_btn)

        layout.addWidget(self.create_copies_label)
        layout.addWidget(self.creat_copies_cb)

        self.setLayout(layout)

    def add_transforms(self):
        """
        Adds previewed transform to the transform chain within plugin
        """

        curr_transform = self.plugin.signal_preview.preview_temp_transform
        transform_view = self.plugin.transform_view

        if curr_transform is None:
            return

        if self.add_to_all_cb.isChecked():
            for i in range(transform_view.topLevelItemCount()):
                item = transform_view.topLevelItem(i)

                if hasattr(item.channel_item, 'pvc'):
                    item.temporary_chain.append(curr_transform)
                else:
                    for j in range(item.childCount()):
                        child_item = item.child(j)
                        if hasattr(child_item.channel_item, 'pvc'):
                            child_item.temporary_chain.append(curr_transform)

        # Apply to the previewed signal
        else:
            curr_item = transform_view.currentItem()
            curr_item.temporary_chain.append(curr_transform)

        # Enable apply button
        self.apply_btn.setDisabled(False)

        self.plugin.transform_view.create_transform_columns()

    def apply_transforms(self):
        """
        Pushes the transforms back to the main view.
        """

        transform_view = self.plugin.transform_view

        for i in range(transform_view.topLevelItemCount()):
            item = transform_view.topLevelItem(i)

            if hasattr(item.channel_item, 'pvc'):
                if self.creat_copies_cb.isChecked():
                    dup_ch_item = item.channel_item.create_duplicate()
                    for transform in item.temporary_chain[:]:
                        transform.visual_container = dup_ch_item.pvc
                else:
                    for transform in item.temporary_chain[:]:
                        transform.visual_container = item.channel_item.pvc
            else:
                for j in range(item.childCount()):
                    item = item.child(j)
                    if not hasattr(item.channel_item, 'pvc'):
                        continue

                    if self.creat_copies_cb.isChecked():
                        dup_ch_item = item.channel_item.create_duplicate()
                        for transform in item.temporary_chain[:]:
                            transform.visual_container = dup_ch_item.pvc
                    else:
                        for transform in item.temporary_chain[:]:
                            transform.visual_container = item.channel_item.pvc

        # TODO - cleanup TransformChainView and shown channel
        self.plugin.transform_view.clear()
        self.visible_channels.update_plot_positions()
        self.visible_channels.items_added.emit()

        self.plugin.delete_plugin_data()


class SignalPreview(QWidget):
    """
    Preview of the signal and its transforms.
    """
    #TODO - slove the parent issue (why I cannot use self.parent())
    def __init__(self, parent):
        super().__init__(parent)

        self.main = self.parent().main
        self.transform_buttons = self.parent().transform_buttons

        self.preview_pvc_idx = 0
        self.preview_pvc = None
        self.preview_transform_chain = []
        self.preview_temp_transform = None

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = scene.SceneCanvas(show=True, keys='interactive',
                                        parent=self,
                                        size=(200, 200),
                                        bgcolor='white')

        # Preview camera
        self.preview_camera = SignalCamera()

        # Create view
        cw = self.canvas.central_widget
        self.preview_view = cw.add_view(camera=self.preview_camera)

        # Visuals - 2 signals (orig, transformed)
        self.orig_sig = SimpleLine(color=np.array([0., 0., 0., .3],
                                                  'float32'),
                                   parent=self.preview_view.scene)
        self.trans_sig = SimpleLine(color=np.array([0., 0., 0., 1.],
                                                   'float32'),
                                    parent=self.preview_view.scene)

#        self.orig_sig = Line(parent = self.preview_view.scene)
#        self.trans_sig = Line(parent = self.preview_view.scene)

        # TODO 2 2Ds (orig, transformed)

        layout.addWidget(self.canvas.native)

        self.setLayout(layout)

#    def set_preview_pvc(self, pvc):
#        self.preview_pvc = pvc
#        self.preview_transform_chain = self.pvc.transform_chain

    def update_trans_sig(self):

        if self.preview_temp_transform is None:
            return

        dap = self.preview_pvc.data_array_pos
        data = np.squeeze(np.vstack(self.main.signal_display.data_array[dap]))

        for t in self.preview_transform_chain + [self.preview_temp_transform]:
            data = t.apply_transform(data)

        y = data.astype('float32')
        x = np.arange(len(y), dtype='float32')

        pos = np.c_[x, y]

        self.trans_sig.pos = pos

        # Scale
        s_x = 1 / len(pos)
        s_y = 1 / (np.abs(max(pos[:, 1]) - min(pos[:, 1])))
        s = (s_x, s_y)

        # Translate
        t_x = 0
        t_y = (-np.nanmean(pos[:, 1]) * s_y) + 0.5
        t = (t_x, t_y)

        self.trans_sig.transform = scene.transforms.STTransform(s, t)

    def set_orig_trans_sig(self):

        dap = self.preview_pvc.data_array_pos
        data = self.main.signal_display.data_array[dap]

        if len(self.preview_transform_chain):
            for t in self.preview_transform_chain:
                data = t.apply_transform(data)
        else:
            data = data[0]

        y = data.astype('float32')
        x = np.arange(len(y), dtype='float32')

        pos = np.c_[x, y]

        self.orig_sig.pos = pos
        self.trans_sig.pos = pos

        # Scale
        s_x = 1 / len(pos)
        s_y = 1 / (np.abs(max(pos[:, 1]) - min(pos[:, 1])))
        s = (s_x, s_y)

        # Translate
        t_x = 0
        t_y = (-np.nanmean(pos[:, 1]) * s_y) + 0.5
        t = (t_x, t_y)

        self.orig_sig.transform = scene.transforms.STTransform(s, t)
        self.trans_sig.transform = scene.transforms.STTransform(s, t)

        self.parent().transform_buttons.add_btn.setDisabled(False)


class TransformsListStack(QWidget):

    def __init__(self, parent):
        super(TransformsListStack, self).__init__(parent)

        self.plugin = parent
        self.main = self.plugin.main

        # Widget layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Listwidget
        self.stack_list = QListWidget(self)
        self.stack_list.currentRowChanged.connect(self.switch_stack)

        # Stack widget
        self.stack_widget = QStackedWidget(self)

        # Setup subwidgets
        self.setup_transform_widgets()

        # Asemble the layout
        layout.addWidget(self.stack_list)
        layout.addWidget(self.stack_widget)

        self.setLayout(layout)

    def setup_transform_widgets(self):
        """
        Loads individual transforms and sets them up in the list/stack widget
        """

        self.transform_list = []

        # TODO - load automoatically from folder
        filters = Filters(parent=self)
        self.transform_list.append(filters)
        self.stack_list.addItem(filters.get_transform_title())
        self.stack_widget.addWidget(filters)
        filters.register_transform()

        montages = Montages(parent=self)
        self.transform_list.append(montages)
        self.stack_list.addItem(montages.get_transform_title())
        self.stack_widget.addWidget(montages)
        montages.register_transform()

        envelopes = Envelopes(parent=self)
        self.transform_list.append(envelopes)
        self.stack_list.addItem(envelopes.get_transform_title())
        self.stack_widget.addWidget(envelopes)
        envelopes.register_transform()

    def switch_stack(self, row):
        """
        Switches the widget in the stack
        """
        self.stack_widget.setCurrentWidget(self.transform_list[row])


class Transforms(BasePluginWidget):

    # Attributes
    CONF_SECTION = 'transforms'
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
        self.title = 'Transforms'
        self.main = parent

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Transform chain tree widget
        self.transform_view = TransformChainView(self)

        # Transform buttons widget
        self.transform_buttons = TransformButtons(self)

        # Preview widget
        self.signal_preview = SignalPreview(self)

        # Main stack widget
        self.transforms_stack = TransformsListStack(self)

        # Aseble the layout
        layout.addWidget(self.transform_view)
        layout.addWidget(self.transform_buttons)
        layout.addWidget(self.transforms_stack)
        layout.addWidget(self.signal_preview)

        self.setLayout(layout)

    # TODO
    # def connect_navigation(self):

    # ----- PysigviewPluginWidget API -----------------------------------------
    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        pass

    def get_plugin_title(self):
        """Return widget title"""
        return 'Transforms'

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

        vs = self.main.channels.visible_channels

        self.transform_view.visible_channels = vs
        self.transform_buttons.visible_channels = vs

        self.main.add_dockwidget(self)

    def delete_plugin_data(self):
        """Deletes plugin data"""

        self.transform_view.clear()
        self.signal_preview.orig_sig.pos = None
        self.signal_preview.trans_sig.pos = None

        return None

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
