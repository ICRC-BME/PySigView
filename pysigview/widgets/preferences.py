
# Standard library imports

# Third party imports
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout,QListWidget, QStackedWidget, QCheckBox,
                             QWidget, QLineEdit, QGridLayout, QFormLayout,QRadioButton,
                             QComboBox, QLabel, QMessageBox, QPushButton,QHBoxLayout,
                             )
from PyQt5.QtGui import QIntValidator

# Local imports

from pysigview.config.main import CONF

class Preferences(QWidget):

    #signals
    preferences_updated = pyqtSignal(name='preferences_updated')

    def __init__(self, parent=None):
        super(Preferences, self).__init__(parent)

        self.title = 'Preferences'
        self.not_configurable = ['DEFAULTS', 'quick_layouts']
        self.sections = [section for section in CONF.sections()
                         if section not in self.not_configurable]

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

                if isinstance(option_val, str):

                    tmp_widget = QLineEdit()
                    tmp_widget.setMaxLength(100)
                    tmp_widget.setText(option_val)

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