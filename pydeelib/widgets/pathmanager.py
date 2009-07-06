# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Pydee path manager"""

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
class PathManager(QDialog):
    def __init__(self, parent=None, pathlist=None):
        QDialog.__init__(self, parent)
        
        assert isinstance(pathlist, list)
        self.pathlist = pathlist
        
        self.last_path = os.getcwdu()
        
        self.setWindowTitle(self.tr("Path manager"))
        self.resize(500, 300)
        
        self.selection_widgets = []
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)
        self.toolbar_widgets1 = self.setup_top_toolbar(top_layout)

        self.listwidget = QListWidget(self)
        self.connect(self.listwidget, SIGNAL("currentRowChanged(int)"),
                     self.refresh)
        layout.addWidget(self.listwidget)

        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)
        self.toolbar_widgets2 = self.setup_bottom_toolbar(bottom_layout)        
        
        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Close)
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        bottom_layout.addWidget(bbox)
        
        self.update_list()
        self.refresh()
        
    def _add_widgets_to_layout(self, layout, widgets):
        layout.setAlignment(Qt.AlignLeft)
        for widget in widgets:
            layout.addWidget(widget)
        
    def setup_top_toolbar(self, layout):
        toolbar = []
        movetop_button = create_toolbutton(self,
                                    text=self.tr("Move to top"),
                                    icon=get_icon('2uparrow.png'),
                                    triggered=lambda: self.move_to(absolute=0))
        toolbar.append(movetop_button)
        moveup_button = create_toolbutton(self,
                                    text=self.tr("Move up"),
                                    icon=get_icon('1uparrow.png'),
                                    triggered=lambda: self.move_to(relative=-1))
        toolbar.append(moveup_button)
        movedown_button = create_toolbutton(self,
                                    text=self.tr("Move down"),
                                    icon=get_icon('1downarrow.png'),
                                    triggered=lambda: self.move_to(relative=1))
        toolbar.append(movedown_button)
        movebottom_button = create_toolbutton(self,
                                    text=self.tr("Move to bottom"),
                                    icon=get_icon('2downarrow.png'),
                                    triggered=lambda: self.move_to(absolute=1))
        toolbar.append(movebottom_button)
        self.selection_widgets.extend(toolbar)
        self._add_widgets_to_layout(layout, toolbar)
        return toolbar
    
    def setup_bottom_toolbar(self, layout):
        toolbar = []
        add_button = create_toolbutton(self, text=self.tr("Add path"),
                                       icon=get_icon('edit_add.png'),
                                       triggered=self.add_path)
        toolbar.append(add_button)
        remove_button = create_toolbutton(self, text=self.tr("Remove path"),
                                          icon=get_icon('edit_remove.png'),
                                          triggered=self.remove_path)
        toolbar.append(remove_button)
        self.selection_widgets.append(remove_button)
        self._add_widgets_to_layout(layout, toolbar)
        layout.addStretch(1)
        if os.name == 'nt':
            self.sync_button = create_toolbutton(self,
                  text=self.tr("Synchronize..."),
                  icon=get_icon('synchronize.png'), triggered=self.synchronize,
                  tip=self.tr("Synchronize Pydee's path list with PYTHONPATH "
                              "environment variable"))
            layout.addWidget(self.sync_button)
        return toolbar
    
    def synchronize(self):
        """
        Synchronize Pydee's path list with PYTHONPATH environment variable
        Only apply to: current user, on Windows platforms
        """
        answer = QMessageBox.question(self, self.tr("Synchronize"),
            self.tr("This will synchronize Pydee's path list with "
                    "<b>PYTHONPATH</b> environment variable for current user, "
                    "allowing you to run your Python modules outside Pydee "
                    "without having to configure sys.path. "
                    "<br>Do you want to clear contents of PYTHONPATH before "
                    "adding Pydee's path list?"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if answer == QMessageBox.Cancel:
            return
        elif answer == QMessageBox.Yes:
            remove = True
        else:
            remove = False
        from pydeelib.environ import (get_user_env, set_user_env,
                                      listdict2envdict)
        env = get_user_env()
        if remove:
            ppath = self.pathlist
        else:
            ppath = env.get('PYTHONPATH', [])
            if not isinstance(ppath, list):
                ppath = [ppath]
            ppath = [path for path in ppath if path not in self.pathlist]
            ppath.extend(self.pathlist)
        env['PYTHONPATH'] = ppath
        set_user_env( listdict2envdict(env) )
        
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
        not_empty = self.listwidget.count() > 0
        if os.name == 'nt':
            self.sync_button.setEnabled(not_empty)
    
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
