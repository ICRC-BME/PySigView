Interface
===================
The basic interface consists of the main window with top bar and widgets. The main widget is the area where signals are displayed while the rest are dockable widgets (plugins) that can be moved and anchored around the main widget.

Top bar
------------------
Top bar includes basic functions of the viewer such as opening files, modifying preferences and bug reporting.

File menu
~~~~~~~~~~~~~
The file menu contains actions to either open file or MEF session and close PySigView.

Another action is to connect to a PySigView server which can subsequently serve data to the viewer from a remote (or even local) server as if it were a local file.

.. note::
  This functionality requires the package pysigview_cs to be installed. The package is installed by default with PySigView.

Apart from this basic functionality it allows for saving and loading PySigView session. The PySigView session stores the current state of the viewer including any plugin data. This can be useful when saving unfinished work such as signal annotation or when sharing your work with a colleague.
	
Tools menu
~~~~~~~~~~~~~
Tools menu contains preferences action to modify the preferences for the application and plugins.

Help menu
~~~~~~~~~~~~~
Help penu contains action to report a bug on GitHub.

Main widget and channels
------------------------------------
The main widget and channels widget are tightly bound together and are the only widgets that are required for the PySigView to work. Upon opening a file the available channels are displayed in the lower hidden channels field (NUMBER). To display signals drag&drop the marked channels to either higher visible channels field (NUMBER) or to the main widget (NUMBER).

.. tip::
  To select multiple channels either hold down the SHIFT key or CTRL key

Signal display widget
~~~~~~~~~~~~~~~~~~~~~~~~~
The signal display widget is in the middle of the window and acts as a center point for all dockable widgets. The signals are displayed here and it provides basic operations.

Basic keyboard shortcuts:

- Up arrow - increase the amplitude of displayed signals
- Down arrow - decrease the amplitude of displayed signals
- Right arrow - move one window forward
- Left arrow - move one window backward
- Q - increase time span
- A - decrease time span
- Shift + Right arrow - move half window forward
- Shift + Left arrow - move half window backward

Basic mouse operations:

- Right mouse button - activate zoom. Moving the mouse right/left zooms in and zooms out along the x-axis respectively. Moving the mouse up/down zooms in and zooms out along the y-axis respectively.
- Left mouse button - activate pan. Moving the mouse in the desired direction while zoomed in moves the field of view.
- Wheel - activates vertical zoom - only a portion of the displayed signals is zoomed in. This is useful for finding small events.
- Shift + mouse - signal highlighting mode.
- Ctrl + mouse - signal measurement mode. A click in the mode creates a fixed point from which the amplitude and time is measured.

Top bar tools:

- Camera (NUMBER) - Take a snapshot of the signal display widget.
- Grid (NUMBER) - Enable / disable grid in the signal display widget.
- Up/down arrows (NUMBER) - Enable / disable signal autoscale.
- Diskette (NUMBER) - Save the currently displayed data to disk.
- Circle arrow (NUMBER) - Reload recording metadata (useful when the recording is being written).
- Play button (NUMBER) - Automated window shift. Useful when looking through the signal.
- Research / browse dropdown (NUMBER) - Research mode displays all data but is slower. Browse mode downsamples the data proportionally to the number of pixels but is faster.
- Color mode dropdown (NUMBER) - Apply color map to either individual channels or channel groups. 

Channels
~~~~~~~~~~
This plugin is the only one that must be installed with PySigView. It serves for basic operations with signals. The bottom part (NUMBER) shows hidden channels while the top part (NUMBER) shows visible channels.

The visible channels pane consists of so called "collections" which are space holders for individual signal "containers". Collections can be drag&dropped within the visible channels pane to change their locations. Individual containers can be drag&dropped to different collections to draw over each other. This is useful for comparison of two signals.

Signal containers are used for providing information about signals and for simple operations with them. Removing the tick serves for hiding the signal. The color dot shows the current signal color and for changing it.

When the signal container is unfolded it provides basic information about the viewed signal with some modifiable fields. Time span and autoscale can be modified for individual signals.

Annotations plugin widget
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This plugin adds the ability to create / modify / load / save annotations. There are four types of annotations depending on whether they are a one time event or a start/stop event and whether they belong to one channel or the whole recording. The annotation plugin adds functionality to the main signal display widget:

- Shift + 1x Left mouse button (NUMBER) - Add one time annotation to the highlighted channel.
- Shift + 2x Left mouse button (NUMBER) - Add start/stop annotation to the highlighted channel.
- Shift + 1x Right mouse button (NUMBER) - Add one time annotation to the whole recording.
- Shift + 2x Right mouse button (NUMBER) - Add start/stop annotation to the whole recording. 

The annotations can be modified in the annotation list pane. Annotations are divided into annotation sets which can be enabled/disabled and their color can be changed. The icon to the right of the set name displays a dialog with the list of individual annotations. Here the annotation info can be modified. The dialog also allows browsing through annotations by either activating the browse mode or by clicking on the index of the annotation (leftmost number in the row). When Delete is pressed the currently selected annotation is removed from the set.

Top bar tools:

- Folded page icon (NUMBER) - Load annotations form a python pickle.
- Diskette icon (NUMBER) - Save annotations into a python pickle.
- Database arrow down icon (NUMBER) - Download annotations from a database. A database connection has to be active (see DATABASE PLUGIN).
- Database arrow up icon (NUMBER) - Upload annotations from a database. A database connection has to be active (see DATABASE PLUGIN).
- Plus icon (NUMBER) - Add a new annotation set.

.. note::
  The underling data structure of annotations is a `pandas.Dataframe <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html>`_. Hence the python pickles used for saving and loading annotations contain pandas dataframes that can be modified outside the viewer.

Navigation bar plugin widget
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This plugin serves for basic navigation through the recording. It displays the current displayed time point (uUTC / date) and the current time span. Both of these fields can be modified to either jump to a specific time or to manually change the time span.

The bottom bar shows the current position in the recording, the extent of data loaded in the buffer(see BUFFER) (if activated) and recording discontinuities if the data format supports them. Left clinking on a point in the lower pane moves the displayed channels to the selected time point.

Database plugin
~~~~~~~~~~~~~~~~~~~~
This plugin allows to create database connections especially for downloading and uploading annotations or for getting information about channels.

Measurements plugin
~~~~~~~~~~~~~~~~~~~~~~
The plugin 

IPython console plugin
~~~~~~~~~~~~~~~~~~~~~~~~~
The plugin allows for direct interaction with the application. 

TODO

.. tip::
  The console cane be utilized for applying custom scripts. For processing a displayed signal and visualizing the results in a separate window for example using matplotlib library. The signal emitted when the signal is changed can be connected to dynamically change the result window.

Transforms plugin
~~~~~~~~~~~~~~~~~~~~~~
The plugin introduces signal processing into PySigView. Individual signal transformations can be chained to create final result.

To create a transformed signal drag&drop signal collections or containers to the transforms widget area (NUMBER) and select one of the containers. The signal will be previewed in the preview area (NUMBER). Select one of the transform from the list (NUMBER) and enter the parameters. Upon clicking on Set button (NUMBER) the transform signal will be visualized in the preview window. To attach the transform to the transform chain click the Apply button (NUMBER). You can either apply the transform to a single channel or all of the channels by ticking the option (NUMBER). Another transform can now be introduced into the transform chain. Once the transform chain is completed the transformed signals will be created by clicking Apply button (NUMBER). The signals can be either transformed or transformed copies can be created.

Measurement plugin
~~~~~~~~~~~~~~~~~~~~~~~~
The measurement plugin provides detailed information about signal frequencies.

To introduce a signal into the plugin simply measure it in the signal display widget (using Ctrl + mouse). The signal will be previewed in the preview pane (NUMBER) and its corresponding spectrum in the lower pane.

The plugin supports two options - either a spectrum is produced or a spectrogram image. The parameters can be adjusted using parameter widgets (NUMBER)
