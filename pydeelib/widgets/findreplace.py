# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Find/Replace widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QHBoxLayout, QGridLayout, QCheckBox, QLabel, QWidget,
                         QLineEdit, QSizePolicy)
from PyQt4.QtCore import SIGNAL, SLOT, Qt

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.qthelpers import get_std_icon, create_toolbutton


class FindReplace(QWidget):
    """
    Find widget
    """
    STYLE = {False: "background-color:rgb(255, 175, 90);",
             True: ""}
    def __init__(self, parent, enable_replace=False):
        QWidget.__init__(self, parent)
        self.enable_replace = enable_replace
        self.editor = None
        
        glayout = QGridLayout()
        glayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(glayout)
        
        self.close_button = create_toolbutton(self, triggered=self.hide,
                                      icon=get_std_icon("DialogCloseButton"))
        glayout.addWidget(self.close_button, 0, 0)
        
        # Find layout
        self.edit = QLineEdit()
        self.connect(self.edit, SIGNAL("textChanged(QString)"),
                     self.text_has_changed)
        
        self.previous_button = create_toolbutton(self,
                                             text=self.tr("Previous"),
                                             triggered=self.find_previous,
                                             icon=get_std_icon("ArrowBack"))
        self.next_button = create_toolbutton(self,
                                             text=self.tr("Next"),
                                             triggered=self.find_next,
                                             icon=get_std_icon("ArrowForward"))

        self.case_check = QCheckBox(self.tr("Case Sensitive"))
        self.connect(self.case_check, SIGNAL("stateChanged(int)"), self.find)
        self.words_check = QCheckBox(self.tr("Whole words"))
        self.connect(self.words_check, SIGNAL("stateChanged(int)"), self.find)

        hlayout = QHBoxLayout()
        self.widgets = [self.close_button, self.edit, self.previous_button,
                        self.next_button, self.case_check, self.words_check]
        for widget in self.widgets[1:]:
            hlayout.addWidget(widget)
        hlayout.addStretch(1)
        glayout.addLayout(hlayout, 0, 1)

        # Replace layout
        replace_with1 = QLabel(self.tr("Replace"))
        replace_with2 = QLabel()
        font = replace_with2.font()
        font.setBold(True)
        replace_with2.setFont(font)
        replace_with3 = QLabel(self.tr("with:"))
        self.replace_edit = QLineEdit()
        
        self.replace_button = create_toolbutton(self,
                                     triggered=self.replace_find,
                                     icon=get_std_icon("DialogApplyButton"))
        
        self.all_check = QCheckBox(self.tr("Replace all"))
        
        self.replace_layout = QHBoxLayout()
        widgets = [replace_with1, replace_with2, replace_with3,
                   self.replace_edit, self.replace_button, self.all_check]
        for widget in widgets:
            self.replace_layout.addWidget(widget)
        self.connect(self.edit, SIGNAL("textChanged(QString)"),
                     replace_with2, SLOT("setText(QString)"))
        self.replace_layout.addStretch(1)
        glayout.addLayout(self.replace_layout, 1, 1)
        self.widgets.extend(widgets)
        self.replace_widgets = widgets
        self.hide_replace()
        
        self.edit.setTabOrder(self.edit, self.replace_edit)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
    def keyPressEvent(self, event):
        """Reimplemented to handle key events"""
        ctrl = event.modifiers() & Qt.ControlModifier
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
            return
        elif event.key() == Qt.Key_F and ctrl:
            # Toggle find widgets
            if self.isVisible():
                self.hide()
            else:
                self.show()
        elif event.key() == Qt.Key_H and ctrl and self.enable_replace:
            # Toggle replace widgets
            if self.replace_widgets[0].isVisible():
                self.hide_replace()
                self.edit.setFocus()
            else:
                self.show_replace()
                self.replace_edit.setFocus()
        else:
            event.ignore()
        
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
            replace_text = self.replace_edit.text()
            first = True
            while True:
                if first:
                    # First found
                    if self.editor.hasSelectedText() \
                       and self.editor.selectedText() == self.edit.text():
                        # Text was already found, do nothing
                        pass
                    else:
                        self.find(changed=False, forward=True)
                    first = False
                    wrapped = False
                    line, index = self.editor.getCursorPosition()
                    line0, index0 = line, index
                else:
                    line1, index1 = self.editor.getCursorPosition()
                    if line1 == line0 and index1 == index0:
                        # Avoid infinite loop: single found occurence
                        break
                    if line1-line0 < 0 or (line1 == line0 and index1-index0 < 0):
                        wrapped = True
                    if wrapped:
                        if line0 > line or (line0 == line and index0 > index):
                            # Avoid infinite loop: replace string includes
                            # part of the search string
                            break
                    line0, index0 = line1, index1
                
                self.editor.replace(replace_text)
                self.refresh()
                if not self.all_check.isChecked():
                    break
            self.all_check.setCheckState(Qt.Unchecked)
            