#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 15:49:15 2018

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

# Local imports
from .pysigview import pysigviewHandler


def client_type_evaluator(client_type):

    """
    Returns client handler class.
    """

    formats = get_available_client_types()

    client_handler = [x for x in formats if x.type == client_type][0]

    if client_handler == []:
        return None

    return client_handler


def get_available_client_types():
    """
    Reads available extensions
    """

    # TODO do this automatically in the future
    supported_client_types = [pysigviewHandler()]

    return supported_client_types
