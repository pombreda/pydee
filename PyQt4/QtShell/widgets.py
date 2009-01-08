# -*- coding: utf-8 -*-

#TODO: satellite widgets which refresh when shell widget
# emits a signal (e.g. when it executes a command)

#TODO: multiple line QTextEdit/QScintilla editor
#TODO: globals explorer widget

import os
from PyQt4.QtGui import QWidget, QHBoxLayout, QFileDialog, QStyle
from PyQt4.QtGui import QLabel, QLineEdit, QPushButton
from PyQt4.QtCore import SIGNAL

# Local import
# import config

try:
    from qsciwidgets import QsciShell as QShell
    # from qsciwidgets import QsciEditor as QEditor
except ImportError:
    from qtwidgets import QSimpleShell as QShell
    # from qtwidgets import QSimpleEditor as QEditor


class CurrentDirChanger(QWidget):
    """
    Current directory changer widget
    """
    def __init__(self, shell):
        super(CurrentDirChanger, self).__init__()
        self.shell = shell
        layout = QHBoxLayout()
        layout.addWidget( QLabel('Current directory:') )
        self.pathedit = QLineEdit()
        self.pathedit.setEnabled(False)
        layout.addWidget(self.pathedit)
        icon = self.style().standardIcon(QStyle.SP_DirOpenIcon)
        self.button = QPushButton(icon, 'Browse')
        self.connect(self.button, SIGNAL('clicked()'), self.change_directory)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.refresh()
        
    def refresh(self):
        """Refresh widget"""
        self.pathedit.setText( os.getcwd() )
        
    def change_directory(self):
        """Select directory and set it as working directory"""
        import sys
        self.shell.restore_stds()
        directory = QFileDialog.getExistingDirectory(None, "Select directory", os.getcwd())
        if not directory.isEmpty():
            os.chdir(directory)
            self.pathedit.setText(directory)
        self.shell.save_stds()
        


def tests():
    """
    Testing all widgets
    """
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    # Current directory changer test:
    dialog = CurrentDirChanger(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    tests()
        