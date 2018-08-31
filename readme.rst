PySigView: Python signal viewer
====================================================

PySigView is a python package for vizualisation of electrophysiological
signals. The developement is aimed mainly at EEG but technically, any signal
can be vizualized.

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

