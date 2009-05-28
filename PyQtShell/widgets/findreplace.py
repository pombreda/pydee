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

"""Customized combobox widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QHBoxLayout, QGridLayout, QCheckBox, QKeySequence,
                         QLabel, QWidget, QLineEdit, QShortcut)
from PyQt4.QtCore import SIGNAL, Qt

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.qthelpers import get_std_icon, create_toolbutton


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
        
        self.close_button = create_toolbutton(self, callback=self.hide,
                                      icon=get_std_icon("DialogCloseButton"))
        self.layout().addWidget(self.close_button, 0, 0)
        
        # Find layout
        self.edit = QLineEdit()
        self.connect(self.edit, SIGNAL("textChanged(QString)"),
                     self.text_has_changed)
        
        self.previous_button = create_toolbutton(self,
                                             callback=self.find_previous,
                                             icon=get_std_icon("ArrowBack"))
        self.next_button = create_toolbutton(self,
                                             callback=self.find_next,
                                             icon=get_std_icon("ArrowForward"))

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
        
        self.replace_button = create_toolbutton(self,
                                     callback=self.replace_find,
                                     icon=get_std_icon("DialogApplyButton"))
        
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
                
        self.refresh()
        
    def show(self):
        """Overrides Qt Method"""
        QWidget.show(self)
        if self.editor is not None:
            text = self.editor.selectedText()
            if len(text)>0:
                self.edit.setText(text)
                self.edit.selectAll()
                self.refresh()
            else:
                self.edit.selectAll()
        
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
        if self.isHidden():
            return
        state = self.editor is not None
        for widget in self.widgets:
            widget.setEnabled(state)
        if state:
            self.find()
            
    def set_editor(self, editor, refresh=True):
        """Set parent editor"""
        self.editor = editor
        if refresh:
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
                self.editor.replace(self.replace_edit.text())
                self.refresh()
                if not self.all_check.isChecked():
                    break
            self.all_check.setCheckState(Qt.Unchecked)