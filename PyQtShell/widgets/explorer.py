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

"""Files and Directories Explorer"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QDialog, QListWidget, QListWidgetItem, QVBoxLayout,
                         QLabel, QHBoxLayout, QDrag, QMenu)
from PyQt4.QtCore import Qt, SIGNAL, QMimeData

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF, get_icon
from PyQtShell.qthelpers import get_std_icon, create_action, add_actions
from PyQtShell.widgets.base import WidgetMixin


def listdir(path, valid_types=('.py', '.pyw'),
            show_hidden=False, show_all=False):
    """List files and directories"""
    namelist = []
    dirlist = [osp.pardir]
    for item in os.listdir(path):
        if osp.isdir(osp.join(path, item)):
            dirlist.append(item)
        elif (show_all or (osp.splitext(item)[1] in valid_types)) and \
             (show_hidden or not item.startswith('.')):
            namelist.append(item)
    return sorted(dirlist) + sorted(namelist)


class ExplorerWidget(QListWidget):
    """File and Directories Explorer Widget"""
    def __init__(self, parent=None, path=None,
                 valid_types=('.py', '.pyw'),
                 show_hidden=False, show_all=False):
        QListWidget.__init__(self, parent)
        
        self.valid_types = valid_types
        self.show_hidden = show_hidden
        self.show_all = show_all
        
        self.path = None
        self.set_path(os.getcwd() if path is None else path)
        
        self.setWrapping(True)
#        self.setFlow(QListWidget.LeftToRight)
#        self.setUniformItemSizes(True)
#        self.setViewMode(QListWidget.IconMode)
        
        # Enable drag events
        self.setDragEnabled(True)
        
    def refresh(self):
        """Refresh widget"""
        self.set_path(os.getcwd())
        
    def set_path(self, path):
        """Set Explorer path"""
        self.path = path
        self.clear()
        for name in listdir(path, self.valid_types,
                            self.show_hidden, self.show_all):
            item = QListWidgetItem(name)
            if osp.isdir(osp.join(path, name)):
                item.setIcon(get_std_icon('DirClosedIcon'))
            elif osp.splitext(name)[1] in ('.py', '.pyw'):
                item.setIcon(get_icon('py.png'))
            else:
                item.setIcon(get_std_icon('FileIcon'))
            self.addItem(item)

    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked()
            event.accept()
        else:
            QListWidget.keyPressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        self.clicked()
        event.accept()
            
    def clicked(self):
        """Selected item was double-clicked or enter/return was pressed"""
        if self.currentItem() is not None:
            selection = unicode(self.currentItem().text())
            if osp.isdir(osp.join(self.path, selection)):
                self.emit(SIGNAL("opendir(QString)"), selection)
                self.refresh()
            else:
                self.emit(SIGNAL("openfile(QString)"), selection)
            
    def dragEnterEvent(self, event):
        """Drag and Drop - Enter event"""
        event.setAccepted(event.mimeData().hasFormat("text/plain"))

    def dragMoveEvent(self, event):
        """Drag and Drop - Move event"""
        if (event.mimeData().hasFormat("text/plain")):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()
            
    def startDrag(self, dropActions):
        """Reimplement Qt Method - handle drag event"""
        item = self.currentItem()
        mimeData = QMimeData()
        mimeData.setText('r"'+unicode(item.text())+'"')
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_()


#TODO: middle-click runs selected .py/.pyw file ??
#TODO: add context menu entry to run selected .py/.pyw file
#FIXME: bugs after Python interpreter has been restarted
#       (it will certainly be fixed when restart will be nicely implemented)
class Explorer(ExplorerWidget, WidgetMixin):
    """File and Directories Explorer DockWidget"""
    ID = 'explorer'
    def __init__(self, parent=None, path=None):
        WidgetMixin.__init__(self, parent)
        valid_types = CONF.get(self.ID, 'valid_filetypes')
        show_hidden = CONF.get(self.ID, 'show_hidden_files')
        show_all = CONF.get(self.ID, 'show_all_files')
        ExplorerWidget.__init__(self, parent, path,
                                valid_types, show_hidden, show_all)
        
        self.menu = QMenu(self)

        #---- Setup context menu
        # Wrap
        wrap_action = create_action(self, self.tr("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap = CONF.get(self.ID, 'wrap')
        wrap_action.setChecked(wrap)
        self.toggle_wrap_mode(wrap)
        # Show hidden files
        hidden_action = create_action(self, self.tr("Show hidden files"),
                                      toggled=self.toggle_hidden)
        hidden_action.setChecked(show_hidden)
        # Show all files
        all_action = create_action(self, self.tr("Show all files"),
                                   toggled=self.toggle_all)
        all_action.setChecked(show_all)
        add_actions(self.menu, [wrap_action, hidden_action, all_action])
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("Explorer")
    
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
#remove this if it's safe to let "self.refresh()" in the base class method
#    def visibility_changed(self, enable):
#        """Reimplement PydeeDockWidget method"""
#        PydeeDockWidget.visibility_changed(self, enable)
#        self.refresh()
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        CONF.set(self.ID, 'wrap', checked)
        self.setWrapping(checked)
        
    def toggle_hidden(self, checked):
        """Toggle hidden files mode"""
        CONF.set(self.ID, 'show_hidden', checked)
        self.show_hidden = checked
        self.refresh()
        
    def toggle_all(self, checked):
        """Toggle all files mode"""
        CONF.set(self.ID, 'show_all', checked)
        self.show_all = checked
        self.refresh()
        
    def contextMenuEvent(self, event):
        """Override Qt method"""
        if self.menu:
            self.menu.popup(event.globalPos())

        

class Test(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.explorer = ExplorerWidget(show_all=True)
        vlayout.addWidget(self.explorer)
        
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.connect(self.explorer, SIGNAL("openfile(QString)"),
                     self.label1.setText)
        
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)
        label = QLabel("<b>Open dir:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout2.addWidget(label)
        self.label2 = QLabel()
        hlayout2.addWidget(self.label2)
        self.connect(self.explorer, SIGNAL("opendir(QString)"),
                     self.label2.setText)

if __name__ == "__main__":
    from PyQt4.QtGui import QApplication
    QApplication([])
    test = Test()
    test.exec_()
