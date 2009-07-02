# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Pydee path manager"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from __future__ import with_statement

from PyQt4.QtGui import (QDialog, QListWidget, QListWidgetItem, QVBoxLayout,
                         QHBoxLayout, QDialogButtonBox, QApplication,
                         QMessageBox, QFileDialog)
from PyQt4.QtCore import Qt, SIGNAL, SLOT

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.qthelpers import get_std_icon, create_toolbutton
from pydeelib.config import get_icon


#TODO: Add an export button to configure environment variables outside Pydee
#TODO: Add an option to automatically configure PYTHONPATH env var on Windows
#TODO: Add multiple selection support
class PathManager(QDialog):
    def __init__(self, parent=None, pathlist=None):
        QDialog.__init__(self, parent)
        
        assert isinstance(pathlist, list)
        self.pathlist = pathlist
        
        self.last_path = os.getcwdu()
        
        self.setWindowTitle(self.tr("Path manager"))
        self.resize(500, 300)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        hlayout1 = QHBoxLayout()
        layout.addLayout(hlayout1)
        hlayout1.setAlignment(Qt.AlignLeft)
        
        self.selection_widgets = []
        
        self.toolbar_widgets1 = []
        self.movetop_button = create_toolbutton(self,
                                    text=self.tr("Move to top"),
                                    icon=get_icon('2uparrow.png'),
                                    triggered=lambda: self.move_to(absolute=0))
        self.toolbar_widgets1.append(self.movetop_button)
        self.moveup_button = create_toolbutton(self,
                                    text=self.tr("Move up"),
                                    icon=get_icon('1uparrow.png'),
                                    triggered=lambda: self.move_to(relative=-1))
        self.toolbar_widgets1.append(self.moveup_button)
        self.movedown_button = create_toolbutton(self,
                                    text=self.tr("Move down"),
                                    icon=get_icon('1downarrow.png'),
                                    triggered=lambda: self.move_to(relative=1))
        self.toolbar_widgets1.append(self.movedown_button)
        self.movebottom_button = create_toolbutton(self,
                                    text=self.tr("Move to bottom"),
                                    icon=get_icon('2downarrow.png'),
                                    triggered=lambda: self.move_to(absolute=1))
        self.toolbar_widgets1.append(self.movebottom_button)
        
        for widget in self.toolbar_widgets1:
            hlayout1.addWidget(widget)
            self.selection_widgets.append(widget)

        self.listwidget = QListWidget(self)
#        self.listwidget.setSelectionMode(QListWidget.ContiguousSelection)
        self.connect(self.listwidget, SIGNAL("currentRowChanged(int)"),
                     self.refresh)
        layout.addWidget(self.listwidget)

        hlayout2 = QHBoxLayout()
        layout.addLayout(hlayout2)
        hlayout2.setAlignment(Qt.AlignLeft)
        
        self.toolbar_widgets2 = []
        self.add_button = create_toolbutton(self,
                                                text=self.tr("Add path"),
                                                icon=get_icon('edit_add.png'),
                                                triggered=self.add_path)
        self.toolbar_widgets2.append(self.add_button)
        self.remove_button = create_toolbutton(self,
                                                text=self.tr("Remove path"),
                                                icon=get_icon('edit_remove.png'),
                                                triggered=self.remove_path)
        self.toolbar_widgets2.append(self.remove_button)
        self.selection_widgets.append(self.remove_button)
        
        for widget in self.toolbar_widgets2:
            hlayout2.addWidget(widget)
        
        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Close)
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        hlayout2.addWidget(bbox)
        
        self.update_list()
        self.refresh()
        
    def get_path_list(self):
        """Return path list"""
        return self.pathlist
        
    def update_list(self):
        """Update path list"""
        self.listwidget.clear()
        for name in self.pathlist:
            item = QListWidgetItem(name)
            item.setIcon(get_std_icon('DirClosedIcon'))
            self.listwidget.addItem(item)
        self.refresh()
        
    def refresh(self, row=None):
        """Refresh widget"""
        for widget in self.selection_widgets:
            widget.setEnabled(self.listwidget.currentItem() is not None)
    
    def move_to(self, absolute=None, relative=None):
        index = self.listwidget.currentRow()
        if absolute is not None:
            if absolute:
                new_index = len(self.pathlist)-1
            else:
                new_index = 0
        else:
            new_index = index + relative        
        new_index = max(0, min(len(self.pathlist)-1, new_index))
        path = self.pathlist.pop(index)
        self.pathlist.insert(new_index, path)
        self.update_list()
        self.listwidget.setCurrentRow(new_index)
        
    def remove_path(self):
        answer = QMessageBox.warning(self, self.tr("Remove path"),
            self.tr("Do you really want to remove selected path?"),
            QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.pathlist.pop(self.listwidget.currentRow())
            self.update_list()
    
    def add_path(self):
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        directory = QFileDialog.getExistingDirectory(self,
                                 self.tr("Select directory"), self.last_path)
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if not directory.isEmpty():
            directory = osp.abspath(directory)
            self.last_path = directory
            if directory in self.pathlist:
                answer = QMessageBox.question(self, self.tr("Add path"),
                    self.tr("This directory is already included in Pydee path "
                            "list.<br>Do you want to move it to the top of "
                            "the list?"),
                    QMessageBox.Yes | QMessageBox.No)
                if answer == QMessageBox.Yes:
                    self.pathlist.remove(directory)
                else:
                    return
            self.pathlist.insert(0, directory)
            self.update_list()


if __name__ == "__main__":
    QApplication([])
    test = PathManager(None, sys.path)
    if test.exec_():
        print test.get_path_list()
