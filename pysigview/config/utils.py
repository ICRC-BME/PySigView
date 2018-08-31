#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 20 09:14:11 2017

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

import os.path as osp
import os
import shutil
import sys
from pathlib import Path

# Third party imports

# Local imports

# =============================================================================
# Configuration paths
# =============================================================================
# PySigView settings dir

if sys.platform.startswith('linux'):
    SUBFOLDER = 'pysigview'
else:
    SUBFOLDER = '.pysigview'


def get_home_dir():
    """
    Return user home directory
    """

    return str(Path.home())


def get_conf_path(filename=None):
    """
    Return absolute path for configuration file with specified filename
    Create the directory is not present
    """

    if sys.platform.startswith('linux'):
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME', '')
        if not xdg_config_home:
            xdg_config_home = osp.join(get_home_dir(), '.config')
            os.makedirs(xdg_config_home, exist_ok=True)
        conf_dir = osp.join(xdg_config_home, SUBFOLDER)
    else:
        conf_dir = osp.join(get_home_dir(), SUBFOLDER)
    if not osp.isdir(conf_dir):
        os.makedirs(conf_dir, exist_ok=True)
    if filename is None:
        return conf_dir
    else:
        return osp.join(conf_dir, filename)


def get_module_path(modname):
    """Return module *modname* base path"""
    return osp.abspath(osp.dirname(sys.modules[modname].__file__))


def get_module_data_path(modname, relpath=None, attr_name='DATAPATH'):
    """Return module *modname* data path
    Note: relpath is ignored if module has an attribute named *attr_name*

    Handles py2exe/cx_Freeze distributions"""
    datapath = getattr(sys.modules[modname], attr_name, '')
    if datapath:
        return datapath
    else:
        datapath = get_module_path(modname)
        parentdir = osp.join(datapath, osp.pardir)
        if osp.isfile(parentdir):
            # Parent directory is not a directory but the 'library.zip' file:
            # this is either a py2exe or a cx_Freeze distribution
            datapath = osp.abspath(osp.join(osp.join(parentdir, osp.pardir),
                                            modname))
        if relpath is not None:
            datapath = osp.abspath(osp.join(datapath, relpath))
        return datapath


def get_module_source_path(modname, basename=None):
    """Return module *modname* source path
    If *basename* is specified, return *modname.basename* path where
    *modname* is a package containing the module *basename*

    *basename* is a filename (not a module name), so it must include the
    file extension: .py or .pyw

    Handles py2exe/cx_Freeze distributions"""
    srcpath = get_module_path(modname)
    parentdir = osp.join(srcpath, osp.pardir)
    if osp.isfile(parentdir):
        # Parent directory is not a directory but the 'library.zip' file:
        # this is either a py2exe or a cx_Freeze distribution
        srcpath = osp.abspath(osp.join(osp.join(parentdir, osp.pardir),
                                       modname))
    if basename is not None:
        srcpath = osp.abspath(osp.join(srcpath, basename))
    return srcpath


# def is_py2exe_or_cx_Freeze():
#    """Return True if this is a py2exe/cx_Freeze distribution of Spyder"""
#    return osp.isfile(osp.join(get_module_path('spyder'), osp.pardir))


# =============================================================================
# Image path list
# =============================================================================
IMG_PATH = []


def add_image_path(path):
    if not osp.isdir(path):
        return
    global IMG_PATH
    IMG_PATH.append(path)
    for dirpath, dirnames, _filenames in os.walk(path):
        for dirname in dirnames:
            IMG_PATH.append(osp.join(dirpath, dirname))


add_image_path(get_module_data_path('pysigview', relpath='images'))


def get_image_path(name, default="not_found.png"):
    """Return image absolute path"""
    for img_path in IMG_PATH:
        full_path = osp.join(img_path, name)
        if osp.isfile(full_path):
            return osp.abspath(full_path)
    if default is not None:
        img_path = osp.join(get_module_path('pysigview'), 'images')
        return osp.abspath(osp.join(img_path, default))


# =============================================================================
# Mac application utilities
# =============================================================================
MAC_APP_NAME = 'PySigView.app'


def running_in_mac_app():
    if sys.platform == "darwin" and MAC_APP_NAME in __file__:
        return True
    else:
        return False


# =============================================================================
# Reset config files
# =============================================================================
SAVED_CONFIG_FILES = ('pysigview.ini')


def reset_config_files():
    """Remove all config files"""
    print("*** Reset PySigView settings to defaults ***")
    for fname in SAVED_CONFIG_FILES:
        cfg_fname = get_conf_path(fname)
        if osp.isfile(cfg_fname) or osp.islink(cfg_fname):
            os.remove(cfg_fname)
        elif osp.isdir(cfg_fname):
            shutil.rmtree(cfg_fname)
        else:
            continue
        print("removing:", cfg_fname)
