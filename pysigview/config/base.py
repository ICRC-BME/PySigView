#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 09:23:17 2017

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
import sys

# Third party imports

# Local imports


# =============================================================================
# Mac application utilities
# =============================================================================

MAC_APP_NAME = 'pysigview.app'


def running_in_mac_app():
    if sys.platform == "darwin" and MAC_APP_NAME in __file__:
        return True
    else:
        return False
