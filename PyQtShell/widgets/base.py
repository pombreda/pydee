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

"""PyQtShell base widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QDockWidget, QComboBox, QFont, QToolTip, QPushButton,
                         QHBoxLayout, QGridLayout, QLabel, QWidget, QLineEdit,
                         QShortcut, QKeySequence, QCheckBox, QSizePolicy)
from PyQt4.QtCore import SIGNAL, Qt

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.qthelpers import toggle_actions, get_std_icon
from PyQtShell.config import CONF


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
        
    def get_name(self):
        """Return widget name"""
        raise NotImplementedError
        
    def refresh(self):
        """Refresh widget"""
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
        dock = QDockWidget(self.get_name(), self.mainwindow)
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(allowed_areas)
        dock.setFeatures( self.get_dockwidget_features() )
        dock.setWidget(self)
        self.connect(dock, SIGNAL('visibilityChanged(bool)'),
                     self.visibility_changed)
        self.dockwidget = dock
        self.refresh()
        return (dock, location)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed
        enable: this parameter is not used because we want to detect if
        DockWiget is visible or not, with 'not toplevel = visible'"""
        enable = self.dockwidget.isVisible()
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
        if CONF.get('shell', 'working_dir_adjusttocontents', False):
            self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr("Press enter to validate this path"),
                     False: self.tr('This path is incorrect.\n'
                                    'Enter a correct directory path.\n'
                                    'Then press enter to validate')}
        
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
                        self.parent().mainwindow.shell.shell.setFocus()
        else:
            QComboBox.keyPressEvent(self, event)


class FindReplace(QWidget):
    """
    Find widget
    """
    STYLE = {False: "background-color:rgb(255, 175, 90);",
             True: ""}
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.editor = None
        self.setLayout(QGridLayout())
        
        self.close_button = QPushButton(get_std_icon("DialogCloseButton"), "")
        self.connect(self.close_button, SIGNAL('clicked()'), self.hide)
        self.layout().addWidget(self.close_button, 0, 0)
        
        # Find layout
        self.edit = QLineEdit()
        self.connect(self.edit, SIGNAL("textChanged(QString)"),
                     self.text_has_changed)
        
        self.previous_button = QPushButton(get_std_icon("ArrowBack"), "")
        self.connect(self.previous_button, SIGNAL('clicked()'),
                     self.find_previous)
        self.next_button = QPushButton(get_std_icon("ArrowForward"), "")
        self.connect(self.next_button, SIGNAL('clicked()'),
                     self.find_next)

        self.case_check = QCheckBox(self.tr("Case Sensitive"))
        self.connect(self.case_check, SIGNAL("stateChanged(int)"), self.find)
        self.words_check = QCheckBox(self.tr("Whole words"))
        self.connect(self.words_check, SIGNAL("stateChanged(int)"), self.find)

        layout = QHBoxLayout()
        self.widgets = [self.close_button, self.edit, self.previous_button,
                        self.next_button, self.case_check, self.words_check]
        for widget in self.widgets[1:]:
            layout.addWidget(widget)
        self.layout().addLayout(layout, 0, 1)

        # Replace layout
        replace_with = QLabel(self.tr("Replace with:"))
        self.replace_edit = QLineEdit()
        
        self.replace_button = QPushButton(get_std_icon("DialogApplyButton"), "")
        self.connect(self.replace_button, SIGNAL('clicked()'),
                     self.replace_find)
        
        self.all_check = QCheckBox(self.tr("Replace all"))
        
        self.replace_layout = QHBoxLayout()
        widgets = [replace_with, self.replace_edit,
                   self.replace_button, self.all_check]
        for widget in widgets:
            self.replace_layout.addWidget(widget)
        self.layout().addLayout(self.replace_layout, 1, 1)
        self.widgets.extend(widgets)
        self.replace_widgets = widgets
        self.hide_replace()
        
        self.edit.setTabOrder(self.edit, self.replace_edit)
        
        # Escape shortcut
        QShortcut(QKeySequence("Escape"), self, self.hide)
                
        self.tweak_buttons()
        self.refresh()
        
    def tweak_buttons(self):
        """Change buttons appearance"""
        for widget in self.widgets:
            if isinstance(widget, QPushButton):
                widget.setFlat(True)
                widget.setFixedWidth(20)
        
    def show(self):
        """Overrides Qt Method"""
        QWidget.show(self)
        if self.editor is not None:
            text = self.editor.selectedText()
            if len(text)>0:
                self.edit.setText(text)
                self.refresh()
        
    def hide(self):
        """Overrides Qt Method"""
        for widget in self.replace_widgets:
            widget.hide()
        QWidget.hide(self)
        if self.editor is not None:
            self.editor.setFocus()
        
    def show_replace(self):
        """Show replace widgets"""
        for widget in self.replace_widgets:
            widget.show()
            
    def hide_replace(self):
        """Hide replace widgets"""
        for widget in self.replace_widgets:
            widget.hide()
        
    def refresh(self):
        """Refresh widget"""
        state = self.editor is not None
        for widget in self.widgets:
            widget.setEnabled(state)
        if state:
            self.find()
            
    def set_editor(self, editor):
        """Set parent editor"""
        self.editor = editor
        self.refresh()
        
    def find_next(self):
        """Find next occurence"""
        self.find(changed=False, forward=True)
        
    def find_previous(self):
        """Find previous occurence"""
        self.find(changed=False, forward=False)
        
    def text_has_changed(self, text):
        """Find text has changed"""
        self.find(changed=True, forward=True)
        
    def find(self, changed=True, forward=True):
        """Call the find function"""
        text = self.edit.text()
        if len(text)==0:
            self.edit.setStyleSheet("")
            return None
        else:
            found = self.editor.find_text(text, changed, forward,
                                          case=self.case_check.isChecked(),
                                          words=self.words_check.isChecked())
            self.edit.setStyleSheet(self.STYLE[found])
            return found
            
    def replace_find(self):
        """Replace and find"""
        if (self.editor is not None):
            while self.find(changed=True, forward=True):
                if not self.all_check.isChecked():
                    break
                self.editor.replace(self.replace_edit.text())
                self.refresh()
            self.all_check.setCheckState(Qt.Unchecked)