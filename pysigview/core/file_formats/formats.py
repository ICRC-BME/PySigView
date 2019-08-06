#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 22 19:51:42 2017

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

# Std library imports

# Third party imports

# Local imports
from .mefd import mefdHandler
from .d import dHandler
from .h5 import h5Handler

def extension_evaluator(path):
    """
    Returns file handler class.
    """
    if '.' not in path:
        return None

    # Remove trailing slash if present
    if path[-1] == '/':
        path = path[:-1]

    extension = path[path.rindex('.'):]

    formats = get_available_file_formats()
    file_handler = [x for x in formats if x.extension == extension][0]

    if file_handler == []:
        return None
    else:
        file_handler.path = path

    return file_handler, extension


def get_available_file_formats():
    """
    Reads available extensions
    """

    # TODO do this automatically in the future
    supported_file_formats = [mefdHandler(), dHandler(), h5Handler()]

    return supported_file_formats
