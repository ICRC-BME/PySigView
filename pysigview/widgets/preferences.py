
# Standard library imports

# Third party imports
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QVBoxLayout,QListWidget, QStackedWidget,
                             QWidget, QLineEdit, QGridLayout, QFormLayout,QRadioButton,
                             QComboBox, QLabel, QMessageBox, QPushButton,QHBoxLayout,
                             )

from scipy.signal import butter, filtfilt

# Local imports

from pysigview.config.main import CONF

class Preferences(QWidget):

    #signals
    preferences_updated = pyqtSignal(name='preferences_updated')

    def __init__(self, parent=None):
        super(Preferences, self).__init__(parent)

        self.title = 'Preferences'
        self.sections = CONF.sections()

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
        # self.sections_selector = QListWidget()
        # self.sections_selector.insertItem(0, 'section0')
        # self.sections_selector.insertItem(1, 'section1')
        # self.sections_selector.insertItem(2, 'section2')

        self.options_editor = QStackedWidget(self)
        self._build_option_stack()

        # self.stack1 = QWidget()
        # self.stack2 = QWidget()
        # self.stack3 = QWidget()
        #
        # tmp_layout = QFormLayout()
        # tmp_layout.addRow("Name", QLineEdit())
        # tmp_layout.addRow("Address", QLineEdit())
        #
        # self.stack1.setLayout(tmp_layout)
        #
        # tmp_layout = QFormLayout()
        # sex = QHBoxLayout()
        # sex.addWidget(QRadioButton("Male"))
        # sex.addWidget(QRadioButton("Female"))
        # tmp_layout.addRow(QLabel("Sex"), sex)
        # tmp_layout.addRow("Date of Birth", QLineEdit())
        # self.stack2.setLayout(tmp_layout)
        # self.stack3.setLayout(tmp_layout)

        # self.options_editor.addWidget(self.stack1)
        # self.options_editor.addWidget(self.stack2)
        # self.options_editor.addWidget(self.stack3)

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
        self.stack_list = []
        for section in self.sections:
            tmp = QWidget()
            tmp_layout = QFormLayout()
            options = CONF.options(section=section)
            for option in options:
                tmp_layout.addRow(str(option) , QLineEdit())
                # tmp_layout.addRow("Address", QLineEdit())
            tmp.setLayout(tmp_layout)
            self.stack_list.append(tmp)
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