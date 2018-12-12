
# Standard library imports

# Third party imports
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QListWidget, QStackedWidget, QCheckBox,
                             QWidget, QLineEdit, QGridLayout, QFormLayout,
                             QPushButton, QHBoxLayout, QDialog)
from PyQt5.QtGui import QIntValidator

# Local imports
from pysigview.core import source_manager as sm
from pysigview.core.buffer_handler import MemoryBuffer

from pysigview.utils.qthelpers import hex2rgba, rgba2hex
from pysigview.config.main import CONF
from pysigview.widgets.color_button import ColorButton


# Classes
class Preferences(QDialog):

    # signals
    preferences_updated = pyqtSignal(name='preferences_updated')

    def __init__(self, parent=None):
        super(Preferences, self).__init__(parent)

        self.main = self.parent()

        # basic class atributes
        self.title = 'Preferences'
        self.not_configurable = ['DEFAULTS', 'quick_layouts', 'main']
        self.sections = [section for section in CONF.sections()
                         if section not in self.not_configurable]

        self.preferences_changed = {section: {} for section in self.sections}

        # Master layout
        layout = QGridLayout()
        layout.setSpacing(10)

        # Buttons Widgets
        self.butt_cancel = QPushButton('Cancel')
        self.butt_apply = QPushButton('Apply')
        self.butt_ok = QPushButton('OK')

        # Form Widgets for selection of config section
        self._build_section_list()

        # Stacked option forms for selected config form
        self.options_editor = QStackedWidget(self)
        self._build_option_stack()

        # preferences grid layout setup
        layout.addWidget(self.butt_cancel, 9, 1, 1, 2,
                         alignment=Qt.AlignBottom)
        layout.addWidget(self.butt_apply, 9, 4, 1, 2,
                         alignment=Qt.AlignBottom)
        layout.addWidget(self.butt_ok, 9, 6, 1, 2,
                         alignment=Qt.AlignBottom)
        layout.addWidget(self.sections_selector, 1, 1, 4, 3)
        layout.addWidget(self.options_editor, 1, 4, 4, 3)

        self.setLayout(layout)
        self.show()

        # Connect main layout signals
        self.sections_selector.currentRowChanged.connect(self._select_section)
        self.butt_cancel.clicked.connect(self.close_widget)
        self.butt_apply.clicked.connect(self.apply_preferences)
        self.butt_ok.clicked.connect(self.apply_preferences)
        self.butt_ok.clicked.connect(self.close_widget)
        self.preferences_updated.connect(self.apply_changes)

    def apply_changes(self):

        # ----- Main -----
        source_opened = sm.ODS.recording_info is not None
        if len(self.preferences_changed['data_management']) and source_opened:
            dm_prefs = self.preferences_changed['data_management']

            # TODO: do not address navigation bar directly
            if 'use_memory_buffer' in dm_prefs:
                if dm_prefs['use_memory_buffer'] is True:
                    sm.PDS = MemoryBuffer(self.main)
                    sm.PDS.state_changed.connect(self.main.navigation_bar.
                                                 bar_widget.update_buffer_bar)
                    sm.PDS.apply_settings()
                else:
                    sm.PDS.state_changed.disconnect()
                    sm.PDS.terminate_buffer()
                    sm.PDS.terminate_monitor_thread()
                    sm.PDS.purge_data()
                    self.main.signal_display.data_map_changed. \
                        disconnect(sm.PDS.update)
                    # TODO: create reset data for navigation bar bars
                    self.main.navigation_bar.bar_widget.buffer_bar. \
                        set_data([0, 0])
                    self.main.navigation_bar.bar_widget.buffer_bar.update()
                    sm.PDS = sm.ODS

            elif isinstance(sm.PDS, MemoryBuffer):
                sm.PDS.apply_settings()

        # ----- Signal display -----
        if len(self.preferences_changed['signal_display']):
            self.main.signal_display.apply_settings()

        # ------ Plugins -------
        for plugin in self.main.plugin_list:
            if plugin.CONF_SECTION not in self.preferences_changed.keys():
                continue
            if len(self.preferences_changed[plugin.CONF_SECTION]):
                plugin.refresh_plugin()

        # In the end restart changed preferences
        self.preferences_changed = {section: {} for section in self.sections}

    # ----- create stacked widget functions ------
    def _select_section(self, sec):
        '''
            selects section in preferences
        :param sec:
        :return:
        '''
        self.options_editor.setCurrentIndex(sec)

    def _build_section_list(self):
        '''
            creates preference section list based on actual config
        :return:
        '''
        self.sections_selector = QListWidget()
        for num, section in enumerate(self.sections):
            # Create nice section name
            first_letter = section[0]
            section = section.replace(first_letter, first_letter.upper(), 1)
            section = section.replace('_', ' ')
            self.sections_selector.insertItem(num, section)

    def _build_option_stack(self):
        '''
            create editable options with visible current values,
             editation type is define by the option possible values
        :return:
        '''

        # temporary prototype
        self.stack_layout_dict = {}
        self.options = {}
        # create stack with all editable sections
        self.stack_layout_dict = {section: QFormLayout() for section
                                  in self.sections}

        for section in self.sections:
            options = CONF.options(section=section)
            if 'enable' in options:
                options.remove('enable')

            self.options[section] = options
            for option in options:
                option_val = CONF.get(section, option)

                name_reference = section + '||' + option
                # boolean (true/False) setup
                if isinstance(option_val, bool):
                    tmp_widget = QCheckBox('On/Off')
                    tmp_widget.setObjectName(name_reference)
                    if option_val:
                        tmp_widget.setChecked(True)
                    else:
                        tmp_widget.setChecked(False)
                    tmp_widget.stateChanged.connect(self._boolean_state)

                # one string or color setup
                if isinstance(option_val, str):
                    # TODO take care of hexa strings withou alpha channel
                    if (len(option_val) == 9) & (option_val.startswith('#')):
                        tmp_widget = QHBoxLayout()
                        tmp_val = PreferenceLineedit(option_val,
                                                     name_reference, 9)
                        tmp_col = ColorButton(hex2rgba(option_val))
                        tmp_col.setObjectName(name_reference)
                        tmp_col.color_changed.connect(self._color_change)
                        tmp_val.editingFinished.connect(self._color_change_hex)
                        tmp_widget.addWidget(tmp_val)
                        tmp_widget.addWidget(tmp_col)
                    else:
                        tmp_widget = PreferenceLineedit(option_val,
                                                        name_reference,
                                                        max_len=100)
                        tmp_widget.editingFinished.connect(self._line_edit)

                # configuration of list (multiple selection)
                if (isinstance(option_val, tuple)
                   | isinstance(option_val, list)):
                    tmp_widget = QHBoxLayout()

                    for i, val in enumerate(option_val):
                        name_loc = name_reference + '||{}'.format(i)
                        if isinstance(val, int):
                            validator = QIntValidator()
                        else:
                            validator = None
                        tmp_val = PreferenceLineedit(str(val),
                                                     name_loc,
                                                     validator=validator)
                        tmp_val.editingFinished.connect(self._line_edit_multi)
                        tmp_widget.addWidget(tmp_val)

                    self.preferences_changed[section][option] = \
                        list(option_val)

                # configuration of single number
                if isinstance(option_val, int) & ~isinstance(option_val, bool):
                    tmp_widget = PreferenceLineedit(str(option_val),
                                                    name_reference, max_len=4,
                                                    validator=QIntValidator())
                    tmp_widget.editingFinished.connect(self._line_edit)

                if option.split('/')[0] in self.sections:
                    _, option = option.split('/')

                # Create nice option name
                first_letter = option[0]
                option = option.replace(first_letter,
                                        first_letter.upper(), 1)
                option = option.replace('_', ' ')
                self.stack_layout_dict[section].addRow(str(option),
                                                       tmp_widget)

        # build whole stack
        for section in self.sections:
            tmp = QWidget()
            tmp.setLayout(self.stack_layout_dict[section])
            self.options_editor.addWidget(tmp)

    # ----- functions saving signal function changes ----
    def _color_change(self, color):
        tmp_widget = self.sender()
        parent = tmp_widget.parent()
        name = tmp_widget.objectName()
        child = parent.findChild(QLineEdit, name)
        result = rgba2hex(color.getRgbF())
        child.setText(result)
        pos_change = name.split('||')
        self.preferences_changed[pos_change[0]][pos_change[1]] = result

    def _color_change_hex(self):
        tmp_widget = self.sender()
        parent = tmp_widget.parent()
        name = tmp_widget.objectName()
        child = parent.findChild(QPushButton, name)
        result = tmp_widget.text()
        child.set_color(hex2rgba(result))
        pos_change = name.split('||')
        self.preferences_changed[pos_change[0]][pos_change[1]] = result

    def _boolean_state(self):
        tmp_widget = self.sender()
        pos_change = tmp_widget.objectName().split('||')
        if tmp_widget.isChecked():
            self.preferences_changed[pos_change[0]][pos_change[1]] = True
        else:
            self.preferences_changed[pos_change[0]][pos_change[1]] = False

    def _line_edit_multi(self):
        tmp_widget = self.sender()
        pos_change = tmp_widget.objectName().split('||')

        if isinstance(tmp_widget.validator(), QIntValidator):
            self.preferences_changed[pos_change[0]]
            [pos_change[1]][int(pos_change[2])] = int(tmp_widget.text())
        else:
            self.preferences_changed[pos_change[0]]
            [pos_change[1]][int(pos_change[2])] = tmp_widget.text()

    def _line_edit(self):
        tmp_widget = self.sender()
        pos_change = tmp_widget.objectName().split('||')
        print()
        if isinstance(tmp_widget.validator(), QIntValidator):
            self.preferences_changed[pos_change[0]][pos_change[1]] \
                = int(tmp_widget.text())
        else:
            self.preferences_changed[pos_change[0]][pos_change[1]] \
                = tmp_widget.text()

    # ----- control button signals ------

    def close_widget(self):
        '''
            close button press action
        :return:
        '''
        self.close()

    def apply_preferences(self):
        '''
            save and update preferences
        :return:
        '''
        for section in self.preferences_changed.keys():
            for option in self.preferences_changed[section].keys():
                CONF.set(section, option,
                         self.preferences_changed[section][option])

        self.preferences_updated.emit()


# helper Classes
class PreferenceLineedit(QLineEdit):

    def __init__(self, value=None, name=None, max_len=None, validator=None,
                 parent=None):
        super(PreferenceLineedit, self).__init__(parent=parent)

        if value is not None:
            self.setText(value)
        if name is not None:
            self.setObjectName(name)
        if max_len is not None:
            self.setMaxLength(max_len)
        if validator is not None:
            self.setValidator(validator)
