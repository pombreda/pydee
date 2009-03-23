# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This file is part of PyQtShell.
#
#    PyQtShell is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    PyQtShell is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PyQtShell; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Working Directory widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QToolBar, QLabel, QSizePolicy, QFileDialog
from PyQt4.QtCore import Qt

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell import encoding
from PyQtShell.config import CONF, get_conf_path
from PyQtShell.qthelpers import get_std_icon, create_action

# Package local imports
from PyQtShell.widgets.base import WidgetMixin, PathComboBox


class WorkingDirectory(QToolBar, WidgetMixin):
    """
    Working directory changer widget
    """
    log_path = get_conf_path('.workingdir')
    def __init__(self, parent, workdir=None):
        QToolBar.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        
        self.setWindowTitle(self.get_name()) # Toolbar title
        self.setObjectName(self.get_name()) # Used to save Window state
        
        self.addWidget( QLabel(self.tr("Working directory:")+" ") )
        
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
        self.addWidget(self.pathedit)
        
        # Browse action
        browse_action = create_action(self, "browse", None,
                                      get_std_icon('DirOpenIcon'),
                                      self.tr('Browse a working directory'),
                                      triggered=self.select_directory)
        self.addAction(browse_action)
        
        # Parent dir action
        parent_action = create_action(self, "parent", None,
                                      get_std_icon('FileDialogToParent', 16),
                                      self.tr('Change to parent directory'),
                                      triggered=self.parent_directory)
        self.addAction(parent_action)
        
    def get_name(self):
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

