#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 15:00:21 2017

Adopted from

https://github.com/SanPen/GridCal/blob/master/UnderDevelopment/GridCal/
gui/GuiFunctions.py

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
from PyQt5.QtCore import QAbstractTableModel, Qt, pyqtSignal
from PyQt5.QtWidgets import QTableView

import numpy as np

# Local imports


class DataFrameView(QTableView):

    row_selected = pyqtSignal(int, name='row_selected')
    data_changed = pyqtSignal(name='data_changed')

    def __init__(self, df, parent=None):
        super().__init__()

        self.model = DataFrameModel(df, self)

        self.setModel(self.model)

        self.n_cols = len(df.columns)
        self.n_rows = len(df.index)

        # enable sorting
        self.setSortingEnabled(True)

        # signals
        self.selectionModel().selectionChanged.connect(self.evaluate_selection)

    def set_selection_mode(self, value):
        if value:
            self.setSelectionBehavior(self.SelectRows)
        else:
            self.setSelectionBehavior(self.SelectItems)

    def evaluate_selection(self):
        indexes = self.selectionModel().selectedIndexes()

        # Whole row selected
        if (len(indexes) == self.n_cols
                and not (sum(np.diff([i.row() for i in indexes])))):
            self.row_selected.emit(self.model.df.index[indexes[0].row()])

    def pass_data_changed_signal(self, i, j):
        self.data_changed.emit()


class DataFrameModel(QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """
    def __init__(self, df, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.df = df.copy()

    def rowCount(self, parent=None):
        return self.df.shape[0]

    def columnCount(self, parent=None):
        return self.df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return False
        if role == Qt.DisplayRole:
            return str(self.df.iloc[index.row(), index.column()])
        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if role == Qt.EditRole:
            ri = index.row()
            ci = index.column()
            r = int(self.headerData(ri, Qt.Vertical, Qt.DisplayRole))
            c = self.headerData(ci, Qt.Horizontal, Qt.DisplayRole)
            self.df.loc[r, c] = value
            self.dataChanged.emit(index, index)
            return True

    def headerData(self, n, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.df.columns[n]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(self.df.index[n])
        return None

    def sort(self, col_n, order):
        self.layoutAboutToBeChanged.emit()
        col = self.df.columns[col_n]
        if order == Qt.DescendingOrder:
            self.df.sort_values(by=col, ascending=False, inplace=True)
        else:
            self.df.sort_values(by=col, ascending=True, inplace=True)
        self.layoutChanged.emit()

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
