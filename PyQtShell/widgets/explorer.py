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
                         QLabel, QHBoxLayout, QDrag, QApplication, QMessageBox,
                         QInputDialog, QLineEdit)
from PyQt4.QtCore import Qt, SIGNAL, QMimeData

import os, sys
import os.path as osp
from sets import Set

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.qthelpers import get_std_icon, translate


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
    """File and Directories Explorer Widget
    get_filetype_icon(fname): fn which returns a QIcon for file extension"""
    def __init__(self, parent=None, path=None, get_filetype_icon=None,
                 valid_types=('.py', '.pyw'),
                 show_hidden=False, show_all=False):
        QListWidget.__init__(self, parent)
        
        if get_filetype_icon is None:
            def get_filetype_icon(fname):
                return get_std_icon('FileIcon')
        self.get_filetype_icon = get_filetype_icon
        self.valid_types = valid_types
        self.show_hidden = show_hidden
        self.show_all = show_all
        
        self.path = None
        self.itemdict = None
        self.nameset = None
        self.refresh(path)
        
        self.setWrapping(True)
#        self.setFlow(QListWidget.LeftToRight)
#        self.setUniformItemSizes(True)
#        self.setViewMode(QListWidget.IconMode)
        
        # Enable drag events
        self.setDragEnabled(True)
        
    def refresh(self, new_path=None):
        """Refresh widget"""
        if new_path is None:
            new_path = os.getcwd()

        names = listdir(new_path, self.valid_types,
                        self.show_hidden, self.show_all)
        new_nameset = Set(names)
        
        if (new_path != self.path):
            self.path = new_path
            self.nameset = Set([])
            self.itemdict = {}
            self.clear()

        for name in self.nameset - new_nameset:
            self.takeItem(self.row(self.itemdict[name]))
            self.itemdict.pop(name)

        if new_nameset - self.nameset:
            for row, name in enumerate(names):
                if not self.itemdict.has_key(name):
                    # Adding new item
                    item = QListWidgetItem(name)
                    #item.setFlags(item.flags() | Qt.ItemIsEditable)
                    if osp.isdir(osp.join(self.path, name)):
                        item.setIcon(get_std_icon('DirClosedIcon'))
                    else:
                        item.setIcon( self.get_filetype_icon(name) )
                    self.itemdict[name] = item
                    self.insertItem(row, item)
            self.nameset = new_nameset
        
    def resizeEvent(self, event):
        """Reimplement Qt Method"""
        self.reset()
        QApplication.processEvents()
        event.ignore()

    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked()
            event.accept()
        elif event.key() == Qt.Key_F2:
            self.rename()
            event.accept()
        else:
            QListWidget.keyPressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        self.clicked()
        event.accept()

    def get_filename(self):
        """Return selected filename"""
        if self.currentItem() is not None:
            return unicode(self.currentItem().text())
            
    def clicked(self):
        """Selected item was double-clicked or enter/return was pressed"""
        fname = self.get_filename()
        if fname:
            if osp.isdir(osp.join(self.path, fname)):
                self.emit(SIGNAL("open_dir(QString)"), fname)
                self.refresh()
            else:
                self.emit(SIGNAL("open_file(QString)"), fname)
            
    def rename(self):
        """Rename selected item"""
        fname = self.get_filename()
        if fname:
            path, valid = QInputDialog.getText(self,
                                          translate('Explorer', 'Rename item'),
                                          translate('Explorer', 'New name:'),
                                          QLineEdit.Normal, fname)
            if valid and path != fname:
                try:
                    os.rename(fname, path)
                except IOError, error:
                    QMessageBox.critical(self,
                        translate('Explorer', "Rename item"),
                        translate('Explorer',
                                  "<b>Unable to rename selected item</b>"
                                  "<br><br>Error message:<br>%1") \
                        .arg(str(error)))
                finally:
                    selected_row = self.currentRow()
                    self.refresh()
                    self.setCurrentRow(selected_row)
            
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
        self.connect(self.explorer, SIGNAL("open_file(QString)"),
                     self.label1.setText)
        
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)
        label = QLabel("<b>Open dir:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout2.addWidget(label)
        self.label2 = QLabel()
        hlayout2.addWidget(self.label2)
        self.connect(self.explorer, SIGNAL("open_dir(QString)"),
                     self.label2.setText)
        self.connect(self.explorer, SIGNAL("open_dir(QString)"),
                     lambda path: os.chdir(unicode(path)))

if __name__ == "__main__":
    QApplication([])
    test = Test()
    test.exec_()
