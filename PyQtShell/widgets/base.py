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
#    Foobar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""PyQtShell base widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QDockWidget, QComboBox, QFont, QToolTip
from PyQt4.QtCore import SIGNAL, Qt

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.qthelpers import toggle_actions


class WidgetMixin(object):
    """Useful methods to bind widgets to the main window"""
    def __init__(self, mainwindow):
        """Bind widget to a QMainWindow instance"""
        super(WidgetMixin, self).__init__()
        self.mainwindow = mainwindow
        self.menu_actions, self.toolbar_actions = self.set_actions()
        self.dockwidget = None
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        # Must return True or False (if cancelable)
        raise NotImplementedError
        
    def get_name(self, raw=True):
        """Return widget name"""
        raise NotImplementedError
    
    def set_actions(self):
        """Setup actions"""
        # Return menu and toolbar actions
        raise NotImplementedError
        
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        raise NotImplementedError
    
    def get_dockwidget_features(self):
        """Return QDockWidget features"""
        return QDockWidget.DockWidgetClosable | \
               QDockWidget.DockWidgetFloatable | \
               QDockWidget.DockWidgetMovable
        
    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        allowed_areas, location = self.get_dockwidget_properties()
        dock = QDockWidget(self.get_name(raw=False), self.mainwindow)
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(allowed_areas)
        dock.setFeatures( self.get_dockwidget_features() )
        dock.setWidget(self)
        self.connect(dock, SIGNAL('visibilityChanged(bool)'),
                     self.visibility_changed)
        self.dockwidget = dock
        return (dock, location)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        toggle_actions(self.menu_actions, enable)
        toggle_actions(self.toolbar_actions, enable)
    
    def chdir(self, dirname):
        """Change working directory"""
        self.mainwindow.workdir.chdir(dirname)


class EditableComboBox(QComboBox):
    """
    Editable QComboBox
    """
    def __init__(self, parent):
        super(EditableComboBox, self).__init__(parent)
        self.font = QFont()
        self.setEditable(True)
        self.connect(self, SIGNAL("editTextChanged(QString)"), self.validate)
        self.set_default_style()
        self.tips = {True: self.tr("Press enter to validate this entry"),
                     False: self.tr('This entry is incorrect')}
        
    def show_tip(self, tip=""):
        """Show tip"""
        QToolTip.showText(self.mapToGlobal(self.pos()), tip, self)
        
    def set_default_style(self):
        """Set widget style to default"""
        self.font.setBold(False)
        self.setFont(self.font)
        self.setStyleSheet("")
        self.show_tip()
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        raise NotImplementedError
        
    def validate(self, qstr):
        """Validate entered path"""
        if self.hasFocus():
            self.font.setBold(True)
            self.setFont(self.font)
            valid = self.is_valid(qstr)
            if valid:
                self.setStyleSheet("color:rgb(50, 155, 50);")
            else:
                self.setStyleSheet("color:rgb(200, 50, 50);")
            self.show_tip(self.tips[valid])
        else:
            self.set_default_style()


class PathComboBox(EditableComboBox):
    """
    QComboBox handling path locations
    """
    def __init__(self, parent):
        super(PathComboBox, self).__init__(parent)
        self.tips = {True: self.tr("Press enter to validate this path"),
                     False: self.tr('This path is incorrect.\nEnter a correct directory path.\nThen press enter to validate')}
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        return osp.isdir( unicode(qstr) )

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            directory = unicode(self.currentText())
            if osp.isdir( directory ):
                self.parent().chdir(directory)
                self.set_default_style()
                if hasattr(self.parent(), 'mainwindow'):
                    if self.parent().mainwindow is not None:
                        self.parent().mainwindow.shell.setFocus()
        else:
            QComboBox.keyPressEvent(self, event)
    
