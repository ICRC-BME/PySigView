#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 20 08:48:52 2017

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

PySigView configurations

This module provides the main constans used by pysigview
"""

# Std library imports
import os
import sys

# Third party imports

# Local imports
from pysigview.config.utils import SUBFOLDER
from pysigview.config.user import UserConfig

# =============================================================================
# Main constants
# =============================================================================

# OS Specific
WIN = os.name == 'nt'
MAC = sys.platform == 'darwin'
LINUX = sys.platform.startswith('linux')
CTRL = "Meta" if MAC else "Ctrl"

# =============================================================================
# Default "factory" config settings
# =============================================================================

DEFAULTS = {'DEFAULTS': {'enable': True
                         },
            'main': {'window/size': (800, 600),
                     'window/position': (10, 10),
                     'window/is_maximized': False,
                     'window/is_fullscreen': False,
                     'window/prefs_dialog_size': (745, 411)
                     },
            'data_management': {'use_memory_buffer': False,
                                'use_disk_buffer': False,
                                'n_chunks_before': 1,
                                'n_chunks_after': 1,
                                'chunk_size': 10
                                },
            'signal_display': {'n_cols': 1,
                               'plot_method': 'gl',  # gl or agg
                               'bgcolor': '#606060ff',
                               'grid_color': '#ffffffff',
                               'side_flash_color': '#ff0000ff',
                               'color_palette': 'spring',
                               'init_line_width': 1,
                               'init_line_color': '#ffff00ff',
                               'init_time_scale': 10,  # in seconds
                               'label_font_size': 12,
                               'antialiasing': 'min_max',
                               'init_crosshair_color': '#ffffffff',
                               'init_marker_color': '#ffffffff'
                               },
            'channels': {
                         },
            'navigation_bar': {'enable': True,
                               'discontinuity_limit': 29,
                               'bgcolor': '#606060',
                               'view_bar_color': '#ff0000cc',
                               'buffer_bar_color': '#0000ffcc',
                               'discontinuity_color': '#ffff0044'
                               },
            'annotations': {'enable': True,
                            'database/database': '',
                            'database/table': '',
                            'database/start_column': '',
                            'database/end_column': '',
                            'database/channel_column': '',
                            'database/where_clause': ''},
            'database': {'enable': True,
                         'host': '',
                         'port': '',
                         'username': ''
                         },
            'transforms': {'enable': True,
                           },
            'measurement': {'enable': True,
                            'bgcolor': '#606060ff',
                            'axis_color': '#ffffffff'},
            'shortcuts': {
                          },
            }

CONF_VERSION = '0.6.0'

# Main configuration instance
try:
    CONF = UserConfig('pysigview', defaults=DEFAULTS, load=True,
                      version=CONF_VERSION, subfolder=SUBFOLDER, backup=True,
                      raw_mode=True)
except Exception:
    CONF = UserConfig('pysigview', defaults=DEFAULTS, load=False,
                      version=CONF_VERSION, subfolder=SUBFOLDER, backup=True,
                      raw_mode=True)
