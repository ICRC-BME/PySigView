#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 12:25:24 2017

Core plugin for channel operations

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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QAbstractItemView, QListWidget, QListWidgetItem,
                             QVBoxLayout, QTreeWidget, QTreeWidgetItem)

# Local imports
from pysigview.plugins.base import BasePluginWidget
from pysigview.core import source_manager as sm
from pysigview.widgets.channels.container_item_widget import (
        ContainerItemWidget)
from pysigview.widgets.channels.attribute_item_widget import (
        AttributeItemWidget)
from pysigview.utils.qthelpers import hex2rgba
from pysigview.core.visual_container import SignalContainer


class PlotAttributeItem(QTreeWidgetItem):
    """
    Class for exposing info about plot attributes and allowing modifications
    """

    def __init__(self, attrb, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.main = parent.main

        # Widget settings
        self.item_widget = AttributeItemWidget(attrb[0], attrb[1], attrb[2])
        self.treeWidget().setItemWidget(self, 0, self.item_widget)

        # Is not read only
        if not attrb[2]:
            self.item_widget.value_le.returnPressed.connect(self.update_ea)

    def update_ea(self):
        self.parent().pvc.set_eas(self.item_widget.label.text(),
                                  self.item_widget.value_le.text())
        self.main.signal_display.update_data_map_channels()
        self.main.signal_display.set_plot_data()


class PlotContainerItem(QTreeWidgetItem):
    """
    Class that contains one plot
    """
    def __init__(self, pvc, parent=None, **kwargs):
        super().__init__(parent, 1001, **kwargs)

        self.main = parent.main
        self.sd = self.main.signal_display

        self.pvc = pvc

        # Expose seleted variables
        self.pas = []
        for ea in self.pvc.exposed_attributes:
            pa = PlotAttributeItem(ea, self)
            self.pas.append(pa)

        # Widget settings
        if self.pvc.line_color is not None:
            self.item_widget = ContainerItemWidget(self.pvc.name,
                                                   self.pvc.line_color)
        else:
            self.item_widget = ContainerItemWidget(self.pvc.name)
        self.treeWidget().setItemWidget(self, 0, self.item_widget)

        # Connect signals
        self.item_widget.color_select.color_changed.connect(self.change_color)
        self.item_widget.check_box.stateChanged.connect(self.evaluate_check)
        self.sd.plots_changed.connect(self.pvc.update_eas)
        self.sd.plots_changed.connect(self.update_pas)

    def update_label(self):
        self.item_widget.set_edit_label(self.pvc.name)
        self.parent().update_label()

    def change_color(self, color):
        self.pvc.line_color = hex2rgba(color.name()+'ff')
        # TODO - move this to a signal
        self.sd.update_signals()

    def evaluate_check(self):
        if self.item_widget.check_box.checkState():
            self.pvc.visible = True
        else:
            self.pvc.visible = False

        self.sd.update_signals()

    def update_pas(self):
        for ea, pa in zip(self.pvc.exposed_attributes, self.pas):
            pa.item_widget.label.setText(ea[0])
            pa.item_widget.value_le.setText(str(ea[1]))

    def create_duplicate(self):

        # Create pvc
        pvc = self.sd.add_signal_container(self.pvc.orig_channel)
        pvc.uutc_ss = self.pvc.uutc_ss[:]
        pvc.transform_chain = self.pvc.transform_chain[:]

        # TODO plot specific variables (signal vs 2D)

        new_container_item = PlotContainerItem(pvc,
                                               self.parent())
        new_container_item.pvc.container = new_container_item

        return new_container_item


class PlotCollectionItem(QTreeWidgetItem):
    """
    Class that contains collection of containers
    """
    def __init__(self, parent=None, **kwargs):
        super(PlotCollectionItem, self).__init__(parent, 1002, **kwargs)

        self.main = parent.main
        self.sd = self.main.signal_display

        self.setChildIndicatorPolicy(2)

    def update_label(self):
        cont_labels = []
        for cont_i in range(self.childCount()):
            container = self.child(cont_i)
            cont_labels.append(container.item_widget.label.text())

        new_label = '|'.join(cont_labels)
        if new_label == '':
            new_label = 'NA'
        self.setText(0, new_label)


# TODO: change the style of class naming to confomr to the rest of pysigview
class visible_channels(QTreeWidget):

    # Signals
    items_reordered = pyqtSignal(name='items_reordered')
    items_added = pyqtSignal(name='items_added')
    items_removed = pyqtSignal(name='items_removed')

    def __init__(self, parent=None, **kwargs):
        super(visible_channels, self).__init__(parent, **kwargs)

        self.main = parent.main
        self.sd = self.main.signal_display

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.drag_items = []
        self.drag_rows = []
        self.drop_row = None

        self.plot_collections = []

        self.hidden_channels = None

        # Hide the header for now
        self.header().close()

    def enterEvent(self, event):
        self.setFocus()

    # Reimplementation of drag event
    def startDrag(self, supportedActions):
        self.drag_items = self.selectedItems()
        self.drag_rows = [self.indexOfTopLevelItem(x) for x in self.drag_items]
        super(visible_channels, self).startDrag(supportedActions)

    # Reimplementation of drop event
    def insert_items(self, channels):
        insert_collections = []
        for ch in channels:
            collection = PlotCollectionItem(self)
            collection.setText(0, ch)
            insert_collections.append(collection)

        # Reorder the collections
        # ??? Maybe we can use Vispy camera's "flip property to avoid flipping"
        for insert_collection in insert_collections[::-1]:
            coll_i = self.indexOfTopLevelItem(insert_collection)
            move_item = self.takeTopLevelItem(coll_i)
            self.insertTopLevelItem(0, move_item)
            pvc = self.sd.add_signal_container(move_item.text(0))
            new_container_item = PlotContainerItem(pvc,
                                                   move_item)
            new_container_item.pvc.container = new_container_item

        self.update_plot_positions()
        self.items_added.emit()

    def dropEvent(self, event):
        source = event.source()

        # Add channels and signal plots
        # ??? - we can automatically create filtered channels etc. here
        if source == self.parent().hidden_channels:
            event.accept()
            self.insert_items([x.text() for x in source.drag_items])

        elif source == self.parent().visible_channels:

            # Check all items are of same kind
            collections = all([isinstance(x, PlotCollectionItem)
                               for x in self.drag_items])
            containers = all([isinstance(x, PlotContainerItem)
                              for x in self.drag_items])
            if not (collections or containers):
                event.ignore()
                return

            event.accept()

            self.drop_row = self.indexAt(event.pos()).row()
            self.drop_col = self.indexAt(event.pos()).column()
            # 0 - onitem, 1 - above iten, 2 - below item
            drop_position = self.dropIndicatorPosition()
            drop_on_item = self.itemAt(event.pos())

            # Put container contents into drop on containter, or change places?
            if drop_position == 0:

                # Collection on collection
                if collections and isinstance(drop_on_item,
                                              PlotCollectionItem):
                    pass

                # Container on collection
                elif containers and isinstance(drop_on_item,
                                               PlotCollectionItem):
                    for container in self.drag_items:
                        new_conainer_item = PlotContainerItem(container.pvc,
                                                              drop_on_item)
                        new_conainer_item.pvc.container = new_conainer_item
                        self.sd.plots_changed.disconnect(container.update_pas)
                        container.parent().removeChild(container)
                        drop_on_item.addChild(new_conainer_item)

                    self.update_plot_positions()
                    self.items_reordered.emit()

                else:
                    pass

            # Reorder
            else:
                if drop_position == 1 and self.drop_row != 0:
                    # If above item insert above it
                    self.drop_row -= 1

                if collections:
                    for drag_item in self.drag_items:
                        coll_i = self.indexOfTopLevelItem(drag_item)
                        move_item = self.takeTopLevelItem(coll_i)
                        containers = move_item.takeChildren()
                        move_idx = self.indexOfTopLevelItem(drop_on_item)
                        self.insertTopLevelItem(move_idx, move_item)
                        for container in containers:
                            self.sd.plots_changed.disconnect(container.
                                                             update_pas)
                            new_conainer_item = PlotContainerItem(container.
                                                                  pvc,
                                                                  move_item)
                            new_conainer_item.pvc.container = new_conainer_item
                            move_item.addChild(new_conainer_item)

                # TODO
                # elif containers:

                # Update plot positions
                self.update_plot_positions()
                self.items_reordered.emit()

            self.update_plot_collection_labels()
        else:
            event.ignore()

    def update_plot_positions(self):
        for coll_i in range(self.topLevelItemCount()):
            coll = self.topLevelItem(coll_i)
            col = 0  # TODO
            for cont_i in range(coll.childCount()):
                x = col
                y = self.topLevelItemCount() - (coll_i+1)
                z = cont_i

                cont = coll.child(cont_i)

                cont.pvc.plot_position = [x, y, z]
                cont.update_pas()

    def create_plot_container_item(self, sc, parent):
        container = PlotContainerItem(sc, parent)
        parent.addChild(container)

    def remove_drag_items(self):
        for item in self.drag_items:
            if isinstance(item, PlotCollectionItem):
                coll_i = self.indexOfTopLevelItem(item)
                containers = item.takeChildren()
                for container in containers:
                    cont_i = item.indexOfChild(container)
                    self.sd.plots_changed.disconnect(container.update_pas)
                    item.takeChild(cont_i)
                self.takeTopLevelItem(coll_i)

            elif isinstance(item, PlotContainerItem):
                self.sd.plots_changed.disconnect(item.update_pas)
                item.parent().removeChild(item)

        self.update_plot_collection_labels()
        self.update_plot_positions()
        self.items_reordered.emit()

    def update_plot_collection_labels(self):
        for coll_i in range(self.topLevelItemCount()):
            collection = self.topLevelItem(coll_i)
            collection.update_label()

    def get_collection_items(self):
        collections = []
        for coll_i in range(self.topLevelItemCount()):
            collections.append(self.topLevelItem(coll_i))
        return collections

    def get_container_items(self):
        containers = []
        for collection in self.get_collection_items():
            for cont_i in range(collection.childCount()):
                containers.append(collection.child(cont_i))

        return containers

    def get_row_count(self):
        return self.topLevelItemCount() / self.columnCount()

    def get_col_count(self):
        return self.columnCount()

#        super(visible_channels, self).dropEvent(event)


class hidden_channels(QListWidget):
    """
    Pane with hidden channels - normal QListWidget from which we drag to
    QTree Widget where the real bussines is done
    """

    # Signals

    def __init__(self, parent=None, **kwargs):
        super(hidden_channels, self).__init__(parent, **kwargs)

        self.main = parent.main

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.drag_items = []

        self.visible_channels = None

    def dropEvent(self, event):

        source = event.source()
        if source == self.parent().visible_channels:
            self.add_drag_items()
            self.visible_channels.remove_drag_items()
            self.visible_channels.items_removed.emit()

    def startDrag(self, supportedActions):
        self.drag_items = self.selectedItems()
        super(hidden_channels, self).startDrag(supportedActions)

    def add_drag_items(self):
        # TODO - move back from under the line
        # for item in self.parent().visible_channels.drag_items:
        # self.addItem(item.text(0))

        return

    def move_drag_items(self):
        # TODO - move behind some line
        # for item in self.drag_items:
        #    row = self.row(item)
        #    self.takeItem(row)
        return

    def reset_list(self):
        # Clean up
        self.clear()


class Channels(BasePluginWidget):

    CONF_SECTION = 'channels'
    CONFIGWIDGET_CLASS = None
    IMG_PATH = 'images'
    DISABLE_ACTIONS_WHEN_HIDDEN = True
    shortcut = None

    def __init__(self, parent):
        BasePluginWidget.__init__(self, parent)

        # Widget configiration
        self.ALLOWED_AREAS = Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        self.LOCATION = Qt.LeftDockWidgetArea

        # Presets for the main window
        self.title = 'Channels'
        self.main = parent
        self.sd = self.main.signal_display

        # Widget layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.visible_channels = visible_channels(self)
        layout.addWidget(self.visible_channels)

        self.hidden_channels = hidden_channels(self)
        layout.addWidget(self.hidden_channels)

        self.visible_channels.hidden_channels = self.hidden_channels
        self.hidden_channels.visible_channels = self.visible_channels

        self.setLayout(layout)

    # Do this after you open the file
    def refresh_channel_list(self):

        self.hidden_channels.reset_list()

        # Clean up everything and add separation line

        # Get filename using QFileDialog
#        self.file_name = QFileDialog.getOpenFileName(self, 'Open File',
#            '/media/jan_cimbalnik/DATADRIVE1/data-d_fnusa_oragnizace/seeg/',
#            'All files (*.*);;'+file_types.file_dialog_str)

        # We have the file name - get the extension and process the file


#        self.main_signal_display.plot_stop = max(self.header_info['fsamp'])

        # Construct the list
        for channel in sm.ODS.data_map['channels']:
            item = QListWidgetItem(channel)
            # item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            # item.setCheckState(QtCore.Qt.Unchecked)
            self.hidden_channels.addItem(item)

    # XXX: tool bar with a little lock to lock channels properties

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
        # TODO - focus on channel list
#        self.combo.lineEdit().selectAll()
#        return self.combo
        return None

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def register_plugin(self):
        """Register plugin in Pysigview's main window"""
#        self.focus_changed.connect(self.main.plugin_focus_changed)

        self.create_toggle_view_action()

        # Get the needed signals
        self.main.sig_file_opened.connect(self.refresh_channel_list)

        self.visible_channels.items_added.connect(self.
                                                  main.
                                                  signal_display.
                                                  update_data_map_channels)
        self.visible_channels.items_removed.connect(self.
                                                    main.
                                                    signal_display.
                                                    update_data_map_channels)
        self.visible_channels.items_reordered.connect(self.
                                                      main.
                                                      signal_display.
                                                      update_signals)

        # Slide in variables to signal view
        self.main.signal_display.hidden_channels = self.hidden_channels
        self.main.signal_display.visible_channels = self.visible_channels

        self.main.add_dockwidget(self)

    def load_plugin_data(self, data):
        """Function to run when loading session"""
        # Create the item tree and visuals
        for coll in data:
            collection = PlotCollectionItem(self.visible_channels)
            collection.setText(0, coll['text'])
            for cont in coll['containers']:
                pvc = self.sd.add_signal_container(cont['pvc']['orig_channel'])
                new_container_item = PlotContainerItem(pvc,
                                                       collection)
                new_container_item.pvc.container = new_container_item

                # TODO change text

                # Set color of the color widget
                t_color = tuple(cont['pvc']['line_color'])
                new_container_item.item_widget.color_select.set_color(t_color)

                # Set pvc variables
                pvc.uutc_ss = cont['pvc']['uutc_ss']

                # Set pvc variables - signal
                pvc.line_color = t_color
                pvc.line_alpha = cont['pvc']['line_alpha']
                pvc.autoscale = cont['pvc']['autoscale']
                pvc.scale_factor = cont['pvc']['scale_factor']
                pvc.visible = cont['pvc']['visible']

                # TODO - transforms

        # Move the items and visuals around

        self.visible_channels.update_plot_positions()
        self.visible_channels.items_added.emit()

        return

    def delete_plugin_data(self):
        """Deletes plugin data"""

        for item in self.visible_channels.get_collection_items():
            coll_i = self.visible_channels.indexOfTopLevelItem(item)
            containers = item.takeChildren()
            for container in containers:
                cont_i = item.indexOfChild(container)
                self.sd.plots_changed.disconnect(container.update_pas)
                item.takeChild(cont_i)
            self.visible_channels.takeTopLevelItem(coll_i)

        return

    def save_plugin_data(self):
        """Function to run when saving session"""

        # Suck out data from collections, containers, attributes
        coll_items = self.visible_channels.get_collection_items()
        collections = []
        for coll_i in coll_items:
            collection = {}
            collection['text'] = coll_i.text(0)
            containers = []
            for cont_idx in range(coll_i.childCount()):
                cont_i = coll_i.child(cont_idx)
                iw = cont_i.item_widget
                container = {}
                container['text'] = iw.label.text()

                # Data of the visual
                pvc = {}
                pvc['name'] = cont_i.pvc.name
                pvc['orig_channel'] = cont_i.pvc.orig_channel
                pvc['uutc_ss'] = cont_i.pvc.uutc_ss

                if type(cont_i.pvc) == SignalContainer:
                    pvc['line_color'] = cont_i.pvc.line_color
                    pvc['line_alpha'] = cont_i.pvc.line_alpha
                    pvc['scale_factor'] = cont_i.pvc.scale_factor
                    pvc['autoscale'] = cont_i.pvc.autoscale
                    pvc['visible'] = cont_i.pvc.visible

                container['pvc'] = pvc

                containers.append(container)

            collection['containers'] = containers
            collections.append(collection)

        return collections

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def refresh_plugin(self):
        """Refresh widget"""
        if self._starting_up:
            self._starting_up = False
