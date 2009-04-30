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

"""
NumPy Array Editor Dialog based on PyQt4
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtCore import Qt, QVariant, QModelIndex, QAbstractTableModel
from PyQt4.QtCore import SIGNAL, SLOT
from PyQt4.QtGui import (QHBoxLayout, QColor, QTableView, QItemDelegate,
                         QLineEdit, QCheckBox, QGridLayout, QDoubleValidator,
                         QDialog, QDialogButtonBox, QMessageBox, QPushButton,
                         QInputDialog)
import numpy as N

# Local import
from PyQtShell.config import get_icon, get_font


def is_float(dtype):
    """Return True if datatype dtype is a float kind"""
    return ('float' in dtype.name) or dtype.name in ['single', 'double']

def is_number(dtype):
    """Return True is datatype dtype is a number kind"""
    return is_float(dtype) or ('int' in dtype.name) or ('long' in dtype.name) \
           or ('short' in dtype.name)


class ArrayModel(QAbstractTableModel):
    """Array Editor Table Model"""
    def __init__(self, data, format="%.3f", xy_mode=False, parent=None):
        super(ArrayModel, self).__init__()

        self.dialog = parent

        # Backgroundcolor settings
        huerange = [.66, .99] # Hue
        self.sat = .7 # Saturation
        self.val = 1. # Value
        self.alp = .6 # Alpha-channel

        self._data = data
        self._format = format
        self._xy = xy_mode
        
        self.vmin = data.min()
        self.vmax = data.max()
        if self.vmax == self.vmin:
            self.vmin -= 1
        self.hue0 = huerange[0]
        self.dhue = huerange[1] - huerange[0]
        
        self.bgcolor_enabled = True
        
    def get_format(self):
        """Return current format"""
        # Avoid accessing the private attribute _format from outside
        return self._format
        
    def set_format(self, format):
        """Change display format"""
        self._format = format
        self.reset()

    def columnCount(self, qindex=QModelIndex()):
        """Array column number"""
        return self._data.shape[1]

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return self._data.shape[0]

    def bgcolor(self, state):
        """Toggle backgroundcolor"""
        self.bgcolor_enabled = state > 0
        self.reset()

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return QVariant()
        i = index.row()
        j = index.column()
        value = self._data[i, j]
        if role == Qt.DisplayRole:
            return QVariant( self._format % value )
        elif role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignCenter|Qt.AlignVCenter))
        elif role == Qt.BackgroundColorRole and self.bgcolor_enabled:
            hue = self.hue0+self.dhue*(self.vmax-value)/(self.vmax-self.vmin)
            color = QColor.fromHsvF(hue, self.sat, self.val, self.alp)
            return QVariant(color)
        elif role == Qt.FontRole:
            return QVariant(get_font('arrayeditor'))
        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        """Cell content change"""
        if not index.isValid():
            return False
        i = index.row()
        j = index.column()
        value = str(value.toString())
        if self._data.dtype.name == "bool":
            try:
                val = bool(float(value))
            except ValueError:
                val = value.lower() == "true"
        else:
            try:
                val = float(value)
            except ValueError, e:
                QMessageBox.critical(self.dialog, "Error",
                                     "Value error: %s" % e.message)
        try:
            self._data[i, j] = val
            self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                      index, index)
            if val > self.vmax:
                self.vmax = val
            if val < self.vmin:
                self.vmin = val
            return True
        except OverflowError, e:
            print type(e.message)
            QMessageBox.critical(self.dialog, "Error",
                                 "Overflow error: %s" % e.message)
        return False
    
    def flags(self, index):
        """Set editable flag"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                            Qt.ItemIsEditable)
                
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header data"""
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return QVariant(int(section))
        else:
            if self._xy:
                if section == 0:
                    return QVariant('x')
                elif self.rowCount() == 2:
                    return QVariant('y')
                else:
                    return QVariant('y ('+str(section-1)+')')
            else:
                return QVariant(int(section))


class ArrayDelegate(QItemDelegate):
    """Array Editor Item Delegate"""
    def __init__(self, dtype, parent=None):
        super(ArrayDelegate, self).__init__(parent)
        self.dtype = dtype

    def createEditor(self, parent, option, index):
        """Create editor widget"""
        editor = QLineEdit(parent)
        editor.setFont(get_font('arrayeditor'))
        editor.setAlignment(Qt.AlignCenter)
        if is_number(self.dtype):
            editor.setValidator( QDoubleValidator(editor) )
        self.connect(editor, SIGNAL("returnPressed()"),
                     self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):
        """Commit and close editor"""
        editor = self.sender()
        self.emit(SIGNAL("commitData(QWidget*)"), editor)
        self.emit(SIGNAL("closeEditor(QWidget*)"), editor)

    def setEditorData(self, editor, index):
        """Set editor widget's data"""
        text = index.model().data(index, Qt.DisplayRole).toString()
        editor.setText( text )


class ArrayEditor(QDialog):
    """Array Editor Dialog"""
    FORMATS = {
               'single': '%.3f',
               'double': '%.3f',
               'float_': '%.3f',
               'float32': '%.3f',
               'float64': '%.3f',
               'float96': '%.3f',
               'int_': '%d',
               'int8': '%d',
               'int16': '%d',
               'int32': '%d',
               'int64': '%d',
               'uint': '%d',
               'uint8': '%d',
               'uint16': '%d',
               'uint32': '%d',
               'uint64': '%d',
               'bool': '%r'
               }
    
    def __init__(self, data, title='', xy=False):
        super(ArrayEditor, self).__init__()
        format = self.get_format(data)
        
        self.copy = data.copy()
        self.data = self.copy.view()
        if len(self.data.shape)==1:
            self.data.shape = (self.data.shape[0], 1)

        if len(self.data.shape)!=2:
            raise RuntimeError( "ArrayEditor doesn't support arrays"
                                " with more than 2 dimensions" )
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.setWindowIcon(get_icon('arredit.png'))
        self.setWindowTitle(self.tr("Array editor") + \
                            "%s" % (" - "+str(title) if str(title) else ""))
        self.resize(600, 500)

        # Table configuration
        self.view = QTableView()
        self.model = ArrayModel(self.data, format=format,
                                xy_mode=xy, parent=self)
        self.view.setModel(self.model)
        self.view.setItemDelegate(ArrayDelegate(data.dtype, self))
        total_width = 0
        for k in xrange(self.data.shape[1]):
            total_width += self.view.columnWidth(k)
        total_width = min(total_width, 1024)
        view_size = self.view.size()
        self.view.viewport().resize( total_width, view_size.height() )
        self.layout.addWidget(self.view, 0, 0)

        layout = QHBoxLayout()
        btn = QPushButton(self.tr("Format"))
        # disable format button for int type
        btn.setEnabled( is_float(data.dtype) )
        layout.addWidget( btn )
        self.connect(btn, SIGNAL("clicked()"), self.change_format )
        btn = QPushButton(self.tr("Resize"))
        layout.addWidget( btn )
        self.connect(btn, SIGNAL("clicked()"), self.resize_to_contents )
        bgcolor = QCheckBox(self.tr('Background color'))
        bgcolor.setChecked(True)
        self.connect(bgcolor, SIGNAL("stateChanged(int)"), self.model.bgcolor)
        layout.addWidget( bgcolor )
        
        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        layout.addWidget(bbox)
        self.layout.addLayout(layout, 2, 0)
        
        self.setMinimumSize(400, 300)
        
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)

    def get_format(self, data):
        """Return (type, format) depending on array dtype"""
        name = data.dtype.name
        try:
            return self.FORMATS[name]
        except KeyError:
            QMessageBox.warning(self, self.tr("Array editor"),
                self.tr("Warning: %1 arrays are currently not supported") \
                .arg(name))
            return '%.3f'

    def resize_to_contents(self):
        """Resize cells to contents"""
        self.view.resizeColumnsToContents()
        self.view.resizeRowsToContents()
        
    def change_format(self):
        """Change display format"""
        format, valid = QInputDialog.getText(self, self.tr('Format'),
                          self.tr("Float formatting"), QLineEdit.Normal,
                          self.model.get_format())
        if valid:
            format = str(format)
            try:
                format % 1.1
            except:
                QMessageBox.critical(self, self.tr("Error"),
                      self.tr("Format (%1) is incorrect").arg(format))
                return
            self.model.set_format(format)

    def get_copy(self):
        """Return modified copy of ndarray"""
        return self.copy
    
    
def aedit(data, title=""):
    """
    Edit the array 'data' with the ArrayEditor and return the edited copy
    (if Cancel is pressed, return None)
    (instantiate a new QApplication if necessary,
    so it can be called directly from the interpreter)
    """
    from PyQt4.QtGui import QApplication
    if QApplication.startingUp():
        QApplication([])
    dialog = ArrayEditor(data, title)
    if dialog.exec_():
        return dialog.get_copy()

if __name__ == "__main__":
    arr = N.array([True, False, True])
    print "result:", aedit(arr, "bool array")
    arr = N.array([1, 2, 3], dtype="int8")
    print "result:", aedit(arr, "int array")
    arr = N.random.rand(20, 20)
    print "result:", aedit(arr, "float array")
