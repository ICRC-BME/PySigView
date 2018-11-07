
# Standard library imports

# Third party imports
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout,QListWidget, QStackedWidget, QCheckBox,
                             QWidget, QLineEdit, QGridLayout, QFormLayout,QRadioButton,
                             QComboBox, QLabel, QMessageBox, QPushButton,QHBoxLayout,
                             )
from PyQt5.QtGui import QIntValidator

# Local imports
from pysigview.utils.qthelpers import hex2rgba, rgba2hex
from pysigview.config.main import CONF
from pysigview.widgets.color_button import ColorButton

# Classes
class Preferences(QWidget):

    #signals
    preferences_updated = pyqtSignal(name='preferences_updated')

    def __init__(self, parent=None):
        super(Preferences, self).__init__(parent)

        self.title = 'Preferences'
        self.not_configurable = ['DEFAULTS', 'quick_layouts']
        self.sections = [section for section in CONF.sections()
                         if section not in self.not_configurable]
        self.preferences_changed = {section: {} for section in self.sections}

        # Master layout
        layout = QGridLayout()
        layout.setSpacing(10)

        # Buttons Widgets
        self.butt_load = QPushButton('Load Preferences')
        self.butt_save = QPushButton('Save&Update Preferences')
        self.butt_cancel = QPushButton('Cancel')

        # Labels
        self.sections_label = QLabel('Preferences sections:')
        self.options_label = QLabel('options_editor')

        # Form Widgets
        self._build_section_list()

        self.options_editor = QStackedWidget(self)
        self._build_option_stack()

        layout.addWidget(self.butt_load, 9, 1, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.butt_save, 9, 4, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.butt_cancel, 9, 6, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.sections_label, 0, 2, 1, 1)
        layout.addWidget(self.options_label, 0, 5, 1, 1)
        layout.addWidget(self.sections_selector, 1, 1, 4, 3)
        layout.addWidget(self.options_editor, 1, 4, 4, 3)

        self.setLayout(layout)
        self.show()

        # Connect signals
        self.sections_selector.currentRowChanged.connect(self._select_section)
        self.butt_cancel.clicked.connect(self.close)
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
            self.sections_selector.insertItem(num, section)

    def _build_option_stack(self):
        '''
            create editable options with visible current values,
             editation type is define by the option possible values
        :return:
        '''

        # temporary prototype
        self.stack_layout_dict = {}
        for section in self.sections:
            tmp = QWidget()
            tmp_layout = QFormLayout()
            options = CONF.options(section=section)
            for option in options:
                option_val = CONF.get(section, option)

                if isinstance(option_val, bool):
                    tmp_widget = QCheckBox('On/Off')
                    tmp_widget.setChecked(True) if option_val else tmp_widget.setChecked(False)
                    tmp_widget.stateChanged.connect(self._write_change(self._boolean_state, section, option))

                if isinstance(option_val, str):
                    # TODO take care of hexa strings withou alpha channel
                    if (len(option_val) == 9) & (option_val.startswith('#')):
                        tmp_widget = QHBoxLayout()
                        tmp_val = QLineEdit()
                        tmp_val.setText(option_val)
                        tmp_val.setMaxLength(9)

                        tmp_col = ColorButton(hex2rgba(option_val))
                        tmp_widget.addWidget(tmp_val)
                        tmp_widget.addWidget(tmp_col)

                    else:
                        tmp_widget = QLineEdit()
                        tmp_widget.setMaxLength(100)
                        tmp_widget.setText(option_val)
                        #tmp_widget.editingFinished.connect(lambda:self._line_edit(tmp_widget))

                if isinstance(option_val, tuple) | isinstance(option_val, tuple):
                    tmp_widget = QHBoxLayout()
                    for val in option_val:
                        tmp_val = QLineEdit()
                        tmp_val.setText(str(val))
                        tmp_widget.addWidget(tmp_val)

                if isinstance(option_val, int) & ~isinstance(option_val, bool):
                    tmp_widget = QLineEdit()
                    tmp_widget.setMaxLength(100)
                    tmp_widget.setValidator(QIntValidator())
                    tmp_widget.setMaxLength(4)
                    tmp_widget.setText(str(option_val))

                tmp_layout.addRow(str(option), tmp_widget)

            tmp.setLayout(tmp_layout)
            self.stack_layout_dict[section] = tmp
            self.options_editor.addWidget(tmp)

    # ----- modifying functions for dynamic signals ----
    def _boolean_state(self):
        tmp_widget = self.sender()
        if tmp_widget.isChecked():
            return True
        else:
            return False

    def _write_change(self, func, arg1, arg2):
        def inner():
            result = func()
            self.preferences_changed[arg1][arg2] = result
        return inner

    def _line_edit(self, s):
        print(s.text())
    # ----- control button signals ------

    def close_widget(self):
        '''
            close button press action
        :return:
        '''
        pass

    def save_preferences(self):
        '''
            save and update preferences
        :return:
        '''
        pass

    def load_preferences(self):
        '''
            load different preferences ini file
        :return:
        '''
        pass