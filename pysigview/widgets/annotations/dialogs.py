#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 18 16:37:00 2017

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
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QDialog, QGridLayout, QLineEdit, QComboBox,
                             QLabel, QPushButton, QFrame, QHBoxLayout,
                             QVBoxLayout, QListWidget)
from PyQt5.QtGui import QIntValidator, QDoubleValidator

import numpy as np

# Local imports


class ConditionDialog(QDialog):

    condition_created = pyqtSignal(str, name='condition_created')

    def __init__(self, columns, condition):
        super().__init__()

        self.columns = columns

        # Strip df part
        condition = condition.replace('self.parent().df', '')

        # Strip brackets and quotes
        condition = condition.replace('["', '')
        condition = condition.replace('"]', '')
        condition = condition.replace('[\'', '')
        condition = condition.replace('\'[', '')

        self.layout = QGridLayout(self)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        self.condition_le = QLineEdit(condition)

        self.layout.addWidget(QLabel('Pandas-like condition string'), 0, 0)
        self.layout.addWidget(self.condition_le, 0, 1, 1, 3)
        self.layout.addWidget(line, 1, 0, 1, 4)

        # ----- Labels -----
        self.layout.addWidget(QLabel('Column:'), 2, 0)
        self.layout.addWidget(QLabel('Math operation (optional):'), 2, 1)
        self.layout.addWidget(QLabel('Operator:'), 2, 2)
        self.layout.addWidget(QLabel('Condition value:'), 2, 3)

        # Rolldown column selector
        column_box = QComboBox(self)
        for col in self.columns:
            column_box.addItem(col)
        self.layout.addWidget(column_box, 3, 0)

        # Optional mathematical operation on column
        self.layout.addWidget(QLineEdit(), 3, 1)

        # Rolldown comparison oeprators
        operator_box = QComboBox(self)
        operator_box.addItem('<')
        operator_box.addItem('>')
        operator_box.addItem('==')
        operator_box.addItem('!=')
        self.layout.addWidget(operator_box, 3, 2)

        # Editline value input
        self.layout.addWidget(QLineEdit(), 3, 3)

        # OK / cancel button
        self.button_layout = QHBoxLayout()
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.construct_condition_string)
        ok_btn.clicked.connect(self.accept)

        clc_btn = QPushButton('Cancel')
        clc_btn.clicked.connect(self.reject)

        self.button_layout.addWidget(ok_btn)
        self.button_layout.addWidget(clc_btn)

        self.layout.addLayout(self.button_layout, 4, 0, 1, 4)

        self.setLayout(self.layout)

    def construct_condition_string(self):
        if self.condition_le.text():
            cond_string = self.condition_le.text()

            for col in self.columns:

                col_i = 0
                cl_pos = cond_string.find(col)
                while cl_pos >= 0:
                    corr_pos = col_i + cl_pos
                    cond_string = (cond_string[:corr_pos+len(col)]
                                   + '"]'
                                   + cond_string[corr_pos+len(col):])
                    cond_string = (cond_string[:corr_pos]
                                   + 'self.parent().df["'
                                   + cond_string[corr_pos:])
                    col_i += corr_pos + len('self.parent().df["'+col+'"]') + 1
                    cl_pos = cond_string[col_i:].find(col)

        else:
            cond_string = ''

        print(cond_string)

        self.condition_created.emit(cond_string)

        return


class HistogramDialog(QDialog):

    histogram_strs_created = pyqtSignal(list, name='histogram_strs_created')

    def __init__(self, df):
        super().__init__()

        self.df = df
        columns = list(self.df.columns)
        self.edge_list = []

        self.layout = QGridLayout(self)

        # ----- Labels -----
        self.layout.addWidget(QLabel('Column:'), 0, 0)
        self.layout.addWidget(QLabel('Number of bins'), 0, 1)

        # Rolldown column selector
        self.column_box = QComboBox(self)
        for col in columns:
            self.column_box.addItem(col)
        self.column_box.currentIndexChanged.connect(self.set_bins)
        self.layout.addWidget(self.column_box, 1, 0)

        # Number of bins

        self.N_bins_le = QLineEdit(str(1))
        onlyInt = QIntValidator()
        self.N_bins_le.setValidator(onlyInt)
        self.N_bins_le.textEdited.connect(self.set_bins)
        self.layout.addWidget(self.N_bins_le, 1, 1)

        # Edge editor layout
        self.edge_edit_layout = QVBoxLayout()
#        self.edge_edit_layout.addWidget(QLineEdit())
        self.layout.addLayout(self.edge_edit_layout, 2, 0, 1, 2)

        # OK / cancel button
        self.button_layout = QHBoxLayout()
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.construct_histogram_strings)
        ok_btn.clicked.connect(self.accept)

        clc_btn = QPushButton('Cancel')
        clc_btn.clicked.connect(self.reject)

        self.button_layout.addWidget(ok_btn)
        self.button_layout.addWidget(clc_btn)

        self.layout.addLayout(self.button_layout, 3, 0, 1, 2)

        self.setLayout(self.layout)
        self.set_bins()

    def set_bins(self):

        if not self.N_bins_le.text():
            return

        # Remove from layout
        for bin_le in self.edge_list:
            self.edge_edit_layout.removeWidget(bin_le)
            bin_le.setParent(None)

        # Get the data from the column
        series = self.df[self.column_box.currentText()]
        bins = np.histogram(series[~series.isnull()],
                            int(self.N_bins_le.text()))[1]
        self.edge_list = []
        self.layout.setRowStretch(2, len(bins))
        for bin_i in bins:
            le = QLineEdit(str(bin_i))
            onlyDouble = QDoubleValidator()
            le.setValidator(onlyDouble)
            self.edge_edit_layout.addWidget(le)
            self.edge_list.append(le)

    def construct_histogram_strings(self):

        col = self.column_box.currentText()

        # Get edges
        edge_arr = np.empty(len(self.edge_list))
        for i, edge in enumerate(self.edge_list[:-1]):
            edge_arr[i] = np.float(edge.text())

        eval_strs = self.construct_eval_strs(edge_arr, col)

        self.histogram_strs_created.emit(eval_strs)

        return

    def construct_eval_strs(self, edge_arr, col):

        # Sort
        edge_arr = np.sort(edge_arr)
        eval_strs = []
        for i in range(len(edge_arr)-1):
            bin_start = edge_arr[i]
            bin_stop = edge_arr[i+1]

            df_str = 'self.parent().df["'+col+'"]'
            left_edge = '('+df_str+' >= '+str(bin_start)+')'
            le_name = '['+str(bin_start)
            if i+1 < len(edge_arr):
                right_edge = '('+df_str + ' < '+str(bin_stop)+')'
                re_name = str(bin_stop) + ')'
            else:
                right_edge = '('+df_str + ' <= '+str(bin_stop)+')'
                re_name = str(bin_stop) + ']'

            eval_strs.append([left_edge + ' & ' + right_edge,
                              col+le_name+re_name])

        return eval_strs


class CathegoricalDialog(QDialog):

    categories_strs_created = pyqtSignal(list, name='categories_strs_created')

    def __init__(self, df):
        super().__init__()

        self.df = df
        columns = list(self.df.columns)
        self.edge_list = []

        self.layout = QGridLayout(self)

        # ----- Labels -----
        self.layout.addWidget(QLabel('Column:'), 0, 0)
        self.layout.addWidget(QLabel('Number of cathegories'), 1, 0)

        # Rolldown column selector
        self.column_box = QComboBox(self)
        for col in columns:
            self.column_box.addItem(col)
        self.column_box.currentIndexChanged.connect(self.set_cathegories)
        self.layout.addWidget(self.column_box, 0, 1)

        # Number of cathegories
        self.n_c_label = QLabel('')
        self.layout.addWidget(self.n_c_label, 1, 1)

        # List of cathegoreis
        self.cath_list = QListWidget(self)
        self.layout.addWidget(self.cath_list, 2, 0, 1, 2)

        # OK / cancel button
        self.button_layout = QHBoxLayout()
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.construct_cathecoric_strings)
        ok_btn.clicked.connect(self.accept)

        clc_btn = QPushButton('Cancel')
        clc_btn.clicked.connect(self.reject)

        self.button_layout.addWidget(ok_btn)
        self.button_layout.addWidget(clc_btn)

        self.layout.addLayout(self.button_layout, 3, 0, 1, 2)

        self.setLayout(self.layout)
        self.set_cathegories()

    def set_cathegories(self):

        col = self.column_box.currentText()
        caths = self.df[col].unique()

        # Number of cathegories
        self.n_c_label.setText(str(len(caths)))

        # List of cathegories
        self.cath_list.clear()

        if len(caths) > 100:
            self.cath_list.addItem(str('N > 100, likely not cathegory'))
            return

        for i, cath in enumerate(caths):
            self.cath_list.addItem(str(cath))

    def construct_cathecoric_strings(self):

        col = self.column_box.currentText()

        if self.cath_list.count() < 2:
            return

        eval_strs = []
        for row_i in range(self.cath_list.count()):
            c_item = self.cath_list.item(row_i)
            cath = c_item.text()
            df_str = 'self.parent().df["'+col+'"]'

            try:
                float(cath)
                eval_strs.append([df_str + ' == ' + cath, cath])
            except ValueError:
                eval_strs.append([df_str + ' == "' + cath + '"', cath])

        self.categories_strs_created.emit(eval_strs)
