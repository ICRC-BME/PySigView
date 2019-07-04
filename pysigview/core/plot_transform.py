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

    def __init__(self):

        self.name = ''

    def apply_transform(self, data):
        raise NotImplementedError

    def modify_visual_container(self, vc):
        return

    @property
    def transform_variables(self):
        return NotImplementedError
    
    @transform_variables.setter
    def transforms_variables(self, vars):
        return NotImplementedError
