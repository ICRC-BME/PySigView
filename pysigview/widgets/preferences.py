
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
        # Master layout
        layout = QGridLayout()
        layout.setSpacing(10)

        # Buttons Widgets
        self.butt_load = QPushButton('Load Preferences')
        self.butt_save = QPushButton('Save&Update Preferences')
        self.butt_cancel = QPushButton('Cancel')

        # Labels
        self.sections_label = QLabel('Preferences Sections:')
        self.options_label = QLabel('Options')

        # Form Widgets
        self.sections = QListWidget()
        self.sections.insertItem(0, 'section0')
        self.sections.insertItem(1, 'section1')
        self.sections.insertItem(2, 'section2')

        self.options = QStackedWidget(self)

        self.stack1 = QWidget()
        self.stack2 = QWidget()
        self.stack3 = QWidget()

        layout = QFormLayout()
        layout.addRow("Name", QLineEdit())
        layout.addRow("Address", QLineEdit())

        self.stack1.setLayout(layout)

        layout = QFormLayout()
        sex = QHBoxLayout()
        sex.addWidget(QRadioButton("Male"))
        sex.addWidget(QRadioButton("Female"))
        layout.addRow(QLabel("Sex"), sex)
        layout.addRow("Date of Birth", QLineEdit())
        self.stack2.setLayout(layout)
        self.stack3.setLayout(layout)

        self.options.addWidget(self.stack1)
        self.options.addWidget(self.stack2)
        self.options.addWidget(self.stack3)

        layout.addWidget(self.butt_load, 9, 1, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.butt_save, 9, 4, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.butt_cancel, 9, 6, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.sections_label, 0, 2, 1, 1)
        layout.addWidget(self.options_label, 0, 5, 1, 1)
        layout.addWidget(self.sections_selector, 1, 1, 4, 3)
        layout.addWidget(self.options_editor, 1, 4, 4, 3)

        self.setLayout(layout)


        # Connect signals
        self.sections.currentRowChanged.connect(self._select_section)

    # ----- create stacked widget functions ------
    def _select_section(self, sec):
        self.options.setCurrentIndex(sec)

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
            load different ini file
        :return:
        '''
        pass