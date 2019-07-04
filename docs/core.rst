PySigView core
===================
PySigView core has a couple of basic concepts. Based on `VisPy <http://vispy.org/l>`_ library the viewer utilizes GPU acceleration to view signals with high sampling frequencies over a long period of time with the possibility to quickly zoom in and out. The viewer core operates with 1D `NumPy <https://www.numpy.org/>`_ arrays so the signals can have different sampling frequencies. 

Adding data formats
~~~~~~~~~~~~~~~~~~~~~~

The viewer can support any data format as long as there exists a library to read the data into python. To add the data format to the viewer a short wrapper code must be created to provide the data to the viewer through the specified API (LINK).

.. note::
   PySigView has a separate library for the data server (pysigview_cs). To introduce a new format to the server the wrapper file has to be copied into this library as well.

Buffering
~~~~~~~~~~~~~
The viewer contains buffering capabilities. The buffer is circular and its extent is defined in number of windows. The buffer can be turned on/off in the viewer Preferences. For computers with low RAM there is an option to turn on hard drive buffering which is slower but provides enough space for buffering. Buffering utilizes `Bcolz <https://bcolz.readthedocs.io/en/latest/>`_ library for fast compression in memory and/or on disk.