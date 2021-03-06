[![Build Status](https://travis-ci.com/ICRC-BME/PySigView.svg?branch=master)](https://travis-ci.com/ICRC-BME/PySigView)
[![DOI](https://zenodo.org/badge/146943108.svg)](https://zenodo.org/badge/latestdoi/146943108)
[![Documentation Status](https://readthedocs.org/projects/pysigview/badge/?version=latest)](https://pysigview.readthedocs.io/en/latest/?badge=latest)

PySigView: Python signal viewer
====================================================

PySigView is a python package for vizualisation of electrophysiological
signals. The developement is aimed mainly at EEG but technically, any signal
can be vizualized.

Installation
------------

To install please use:
```bash
pip install pysigview
```

To install from source:
```bash
python setup.py install
```


Supported formats
-----------------

- **.mef** - multiscale electrophysiology format
- **.d**   - format used by FNUSA-ICRC

Other formats can be added by modifying ./file_types.py

Plugins
-------
- **navigation_bar** - bar for navigation through the recording
- **database** - plugin for creating connection to a database
- **annotations**    - plugin for loading and creating data annotations
- **transforms** - plugin for signal transformations (filtering, montages, etc.)
- **console** - ipython console for interaction with the app

