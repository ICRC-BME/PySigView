#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 10:03:54 2018

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

# Std imports

# Third pary imports
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QDialog,
                             QPushButton, QGridLayout)

# Local imports


class DirTreeWidget(QTreeWidget):

    def __init__(self):
        super().__init__()

        self.current_path = None

        self.itemClicked.connect(self.set_current_path)
        self.itemDoubleClicked.connect(self.set_current_path)

    def add_elemtens(self, dir_tree_dict_item, parent=None):

        itm = QTreeWidgetItem()
        itm.setText(0, dir_tree_dict_item['name'])

        if parent:
            parent.addChild(itm)
        else:
            self.addTopLevelItem(itm)

        # TODO - switch to different icons
        if dir_tree_dict_item['type'] == 'directory':
            itm.setIcon(0, QIcon('assets/folder.ico'))
        elif dir_tree_dict_item['type'] == 'file':
            itm.setIcon(0, QIcon('assets/file.ico'))

        if 'children' in dir_tree_dict_item.keys():
            for child in dir_tree_dict_item['children']:
                self.add_elemtens(child, itm)

    def set_current_path(self, item):

        path = []
        while item is not None:
            path.append(str(item.text(0)))
            item = item.parent()
        self.current_path = '/'.join(reversed(path))


class DirTreeDialog(QDialog):

    def __init__(self):
        super().__init__()

        self.dir_tree_widget = DirTreeWidget()
        self.dir_tree_widget.itemDoubleClicked.connect(self.accept)

        self.setModal(True)
        self.accepted.connect(self.return_tree_widget_path)

        layout = QGridLayout(self)

        layout.addWidget(self.dir_tree_widget, 0, 0, 1, 2)

        clc_btn = QPushButton("Cancel")
        clc_btn.clicked.connect(self.reject)
        layout.addWidget(clc_btn, 1, 0)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, 1, 1)

    def cancel_clicked(self):

        self.done(1)

    def return_tree_widget_path(self):

        return self.dir_tree_widget.current_path
