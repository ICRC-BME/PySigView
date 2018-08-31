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

# Local imports


class BasePlotTransform():

    def __init__(self, parent):
        super().__init__()

        self.name = ''
        self._vc = None
        self.parent = parent

    def apply_transform(self, data):
        raise NotImplementedError

    def modify_visual_container(self):
        return

    @property
    def visual_container(self):
        return self._vc

    @visual_container.setter
    def visual_container(self, vc):
        self._vc = vc
        self._vc.transoform_chain_add(self)

    @visual_container.deleter
    def visual_container(self):
        self._vc.transoform_chain_remove(self)
        self._vc = None

# TODO demodify the visual container
# (watch out not to interfere with other transforms)
# not sure what I meant by this
