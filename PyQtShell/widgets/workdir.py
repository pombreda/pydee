# -*- coding: utf-8 -*-
"""Working Directory widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QWidget, QHBoxLayout, QPushButton, QLabel, QSizePolicy,
                         QFileDialog)
from PyQt4.QtCore import Qt, SIGNAL

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell import encoding
from PyQtShell.config import CONF, get_conf_path
from PyQtShell.qthelpers import get_std_icon

# Package local imports
from PyQtShell.widgets.base import WidgetMixin, PathComboBox


class WorkingDirectory(QWidget, WidgetMixin):
    """
    Working directory changer widget
    """
    log_path = get_conf_path('.workingdir')
    def __init__(self, parent, workdir=None):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        
        layout = QHBoxLayout()
        if self.mainwindow is None:
            # Not a dock widget
            layout.addWidget( QLabel(self.get_name()+':') )
        
        # Path combo box
        self.pathedit = PathComboBox(self)
        self.pathedit.setMaxCount(CONF.get('shell', 'working_dir_history'))
        wdhistory = self.load_wdhistory( workdir )
        if workdir is None:
            if wdhistory:
                workdir = wdhistory[0]
            else:
                workdir = "."
        self.chdir( workdir )
        self.pathedit.addItems( wdhistory )
        self.refresh()
        layout.addWidget(self.pathedit)
        
        # Browse button
        self.browse_btn = QPushButton(get_std_icon('DirOpenIcon'), '')
        self.browse_btn.setFixedWidth(30)
        self.browse_btn.setToolTip(self.tr('Browse a working directory'))
        self.connect(self.browse_btn, SIGNAL('clicked()'),
                     self.select_directory)
        layout.addWidget(self.browse_btn)
        
        # Parent dir button
        self.parent_btn = QPushButton(get_std_icon('FileDialogToParent'), '')
        self.parent_btn.setFixedWidth(30)
        self.parent_btn.setToolTip(self.tr('Change to parent directory'))
        self.connect(self.parent_btn, SIGNAL('clicked()'),
                     self.parent_directory)
        layout.addWidget(self.parent_btn)
        
        self.setLayout(layout)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
    def get_name(self, raw=True):
        """Return widget name"""
        return self.tr('Working directory')
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def load_wdhistory(self, workdir=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.log_path):
            wdhistory, _ = encoding.readlines(self.log_path)
            wdhistory = [name for name in wdhistory if os.path.isdir(name)]
        else:
            if workdir is None:
                workdir = os.getcwd()
            wdhistory = [ workdir ]
        return wdhistory
    
    def save_wdhistory(self):
        """Save history to a text file in user home directory"""
        text = [ unicode( self.pathedit.itemText(index) ) \
                 for index in range(self.pathedit.count()) ]
        encoding.writelines(text, self.log_path)
        
    def refresh(self):
        """Refresh widget"""
        curdir = os.getcwd()
        index = self.pathedit.findText(curdir)
        while index!=-1:
            self.pathedit.removeItem(index)
            index = self.pathedit.findText(curdir)
        self.pathedit.insertItem(0, curdir)
        self.pathedit.setCurrentIndex(0)
        self.save_wdhistory()
        
    def select_directory(self):
        """Select directory"""
        self.mainwindow.shell.restore_stds()
        directory = QFileDialog.getExistingDirectory(self.mainwindow,
                    self.tr("Select directory"), os.getcwd())
        if not directory.isEmpty():
            self.chdir(directory)
        self.mainwindow.shell.redirect_stds()
        
    def parent_directory(self):
        """Change working directory to parent directory"""
        os.chdir(os.path.join(os.getcwd(), os.path.pardir))
        self.refresh()
        
    def chdir(self, directory):
        """Set directory as working directory"""
        os.chdir( unicode(directory) )
        sys.path.append(os.getcwd())
        self.refresh()


def tests():
    """
    Testing Working Directory Widget
    """
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    # Working directory changer test:
    dialog = WorkingDirectory(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    tests()
        