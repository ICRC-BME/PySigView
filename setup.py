# -*- coding: utf-8 -*-
"""
Created on Thu Dec 17 00:29:55 2015

Setup file for the PySigView.

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

# Std library imports
import os
import os.path as osp
from setuptools import setup
import shutil
import sys
import subprocess
from distutils.command.install_data import install_data

# Third party imports

# Local imports


# =============================================================================
# Constants
# =============================================================================
NAME = 'pysigview'
LIBNAME = 'pysigview'

# =============================================================================
# Auxiliary functions
# =============================================================================


def get_package_data(name, extlist):
    """Return data files for package *name* with extensions in *extlist*"""
    flist = []
    # Workaround to replace os.path.relpath (not available until Python 2.6):
    offset = len(name)+len(os.pathsep)
    for dirpath, _dirnames, filenames in os.walk(name):
        for fname in filenames:
            if not fname.startswith('.') and osp.splitext(fname)[1] in extlist:
                flist.append(osp.join(dirpath, fname)[offset:])
    return flist


def get_subpackages(name):
    """Return subpackages of package *name*"""
    splist = []
    for dirpath, _dirnames, _filenames in os.walk(name):
        if osp.isfile(osp.join(dirpath, '__init__.py')):
            splist.append(".".join(dirpath.split(os.sep)))
    return splist


def get_data_files():
    """Return data_files in a platform dependent manner"""
    if sys.platform.startswith('linux'):
        data_files = [('/usr/share/icons/hicolor/scalable/apps',
                       ['icons/pysigview.svg']),
                      ('/usr/share/applications',
                       ['scripts/pysigview.desktop'])]
    elif os.name == 'nt':
        data_files = [('scripts', ['img_src/spyder.ico',
                                   'img_src/spyder_reset.ico'])]
    else:
        data_files = []
    return data_files


def get_packages():
    """Return package list"""
    packages = (
        get_subpackages(LIBNAME)
        )
    return packages

# =============================================================================
# Make Linux detect PySigView desktop file
# =============================================================================


class MyInstallData(install_data):
    def run(self):
        install_data.run(self)
        if sys.platform.startswith('linux'):
            try:
                if shutil.which('update-desktop-database') is not None:
                    subprocess.call(['update-desktop-database'])
            except RuntimeError:
                print("ERROR: unable to update desktop database",
                      file=sys.stderr)


CMDCLASS = {'install_data': MyInstallData}

# =============================================================================
# Depndencies check
# =============================================================================


# =============================================================================
# Main scripts
# =============================================================================
# NOTE: the '[...]_win_post_install.py' script is installed even on non-Windows
# platforms due to a bug in pip installation process (see Issue 1158)
SCRIPTS = ['%s_win_post_install.py' % NAME]
SCRIPTS.append('pysigview')


# =============================================================================
# Files added to the package
# =============================================================================
EXTLIST = ['.svg', '.png']
if os.name == 'nt':
    SCRIPTS += ['spyder.bat']
    EXTLIST += ['.ico']

# =============================================================================
# Setup arguments
# =============================================================================

setup_args = dict(name='pysigview',
                  version='0.0.0b4',
                  description='Package for viewing signals using VisPy',
                  url='https://github.com/ICRC-BME/PySigView',
                  author='Jan Cimbalnik',
                  author_email=('jan.cimbalnik@fnusa.cz,'
                                'jan.cimbalnik@mayo.edu'),
                  license='Apache 2.0',
                  packages=get_packages(),
                  package_data={LIBNAME: get_package_data(LIBNAME, EXTLIST)},
                  platforms=['Linux', 'MacOS', 'Windows'],
                  keywords='PyQt5 vispy signal',
                  install_requires=['pyqt5==5.15.1', 'numpy', 'vispy',
                                    'pyopengl', 'pandas', 'scipy',
                                    'sqlalchemy', 'pymysql', 'pysigview_cs',
                                    'pillow', 'jupyter',
                                    'pymef', 'pydread', 'h5py'],
                  zip_safe=False,
                  classifiers=['License :: OSI Approved :: MIT License',
                               'Operating System :: MacOS',
                               'Operating System :: POSIX :: Linux',
                               'Operating System :: Microsoft :: Windows',
                               'Programming Language :: Python :: 3',
                               'Development Status :: 4 - Beta',
                               'Topic :: Scientific/Engineering'],
                  data_files=get_data_files(),
                  entry_points={'gui_scripts': [
                                'pysigview = pysigview.app.start:main']},
                  cmdclass=CMDCLASS)

# =============================================================================
# Run setup
# =============================================================================
setup(**setup_args)
