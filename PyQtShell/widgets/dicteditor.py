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

"""
Dictionary Editor Widget and Dialog based on PyQt4
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtCore import (Qt, QVariant, QModelIndex, QAbstractTableModel,
                          SIGNAL, SLOT)
from PyQt4.QtGui import (QMessageBox, QTableView, QItemDelegate, QLineEdit,
                         QVBoxLayout, QWidget, QColor, QDialog,
                         QDialogButtonBox, QMenu, QInputDialog)

# Local import
from PyQtShell.config import get_icon, get_font
from PyQtShell.qthelpers import translate, add_actions, create_action

class FakeObject(object):
    """Fake class used in replacement of missing modules"""
    pass
try:
    from numpy import ndarray, array
    from PyQtShell.widgets.arrayeditor import ArrayEditor
except ImportError:
    class ndarray(FakeObject):
        """Fake ndarray"""
        pass

COLORS = {
          bool: Qt.magenta,
          (int, float, long): Qt.blue,
          list: Qt.yellow,
          dict: Qt.cyan,
          tuple: Qt.lightGray,
          (str, unicode): Qt.darkRed,
          ndarray: Qt.green,
          }

def sort_against(lista, listb, reverse=False):
    """Arrange lista items in the same order as sorted(listb)"""
    return [item for _, item in sorted(zip(listb, lista), reverse=reverse)]

def value_to_display(value):
    """Convert value for display purpose"""
    if not isinstance(value, (str, unicode)):
        value = repr(value)
    return value
    
def try_to_eval(value):
    """Try to eval value"""
    try:
        return eval(value)
    except (NameError, SyntaxError, ImportError):
        return value
    
def display_to_value(value, default_value):
    """Convert back to value"""
    value = unicode(value.toString())
    try:
        if isinstance(default_value, str):
            value = str(value)
        elif isinstance(default_value, (bool, list, dict, tuple)):
            value = eval(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        else:
            value = try_to_eval(value)
    except ValueError:
        value = try_to_eval(value)
    return value

def get_size(item):
    """Return size of an item of arbitrary type"""
    if isinstance(item, (list, tuple, dict)):
        return len(item)
    elif isinstance(item, ndarray):
        return item.shape
    else:
        return 1

def get_type(item):
    """Return type of an item"""
    text = str(type(item)).replace("<type '", "").replace("'>", "")
    if text.endswith('ndarray'):
        text += '\n('+str(item.dtype)+')'
    return text[text.find('.')+1:]

class DictModelRO(QAbstractTableModel):
    """DictEditor Read-Only Table Model"""
    def __init__(self, parent, data, sortkeys=True, title=""):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self.sortkeys = sortkeys
        self._data = None
        self.showndata = None
        self.keys = None
        self.title = title
        if self.title:
            self.title = self.title + ' - '
        self.sizes = None
        self.types = None
        self.set_data(data)
        
    def get_data(self):
        """Return model data"""
        return self._data
            
    def set_data(self, data, dictfilter=None):
        """Set model data"""
        self._data = data
        if dictfilter is not None:
            data = dictfilter(data)
        self.showndata = data
        if isinstance(data, tuple):
            self.keys = range(len(data))
            self.title += translate("DictEditor", "Tuple")
        elif isinstance(data, list):
            self.keys = range(len(data))
            self.title += translate("DictEditor", "List")
        elif isinstance(data, dict):
            self.keys = data.keys()
            self.title += translate("DictEditor", "Dictionary")
        else:
            raise RuntimeError("Invalid data type")
        self.title += ' ('+str(len(self.keys))+' '+ \
                      translate("DictEditor", "elements")+')'
        self.sizes = [ get_size(data[self.keys[index]])
                       for index in range(len(self.keys)) ]
        self.types = [ get_type(data[self.keys[index]])
                       for index in range(len(self.keys)) ]
        if self.sortkeys:
            self.sort(-1)

    def sort(self, column, order=Qt.AscendingOrder):
        """Overriding sort method"""
        reverse = (order==Qt.DescendingOrder)
        if column == 0:
            self.keys = sort_against(self.keys, self.types, reverse)
            self.sizes = sort_against(self.sizes, self.types, reverse)
            self.types.sort(reverse=reverse)
        elif column == 1:
            self.keys = sort_against(self.keys, self.sizes, reverse)
            self.types = sort_against(self.types, self.sizes, reverse)
            self.sizes.sort(reverse=reverse)
        elif column == 2:
            self.keys = sort_against(self.keys, self.sizes, reverse)
            self.types = sort_against(self.types, self.sizes, reverse)
            self.sizes.sort(reverse=reverse)
        elif column == 3:
            values = [self._data[key] for key in self.keys]
            self.keys = sort_against(self.keys, values, reverse)
            self.sizes = sort_against(self.sizes, values, reverse)
            self.types = sort_against(self.types, values, reverse)
        elif column == -1:
            self.sizes = sort_against(self.sizes, self.keys, reverse)
            self.types = sort_against(self.types, self.keys, reverse)
            self.keys.sort(reverse=reverse)
        self.reset()

    def columnCount(self, qindex=QModelIndex()):
        """Array column number"""
        return 3

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return len(self.keys)
    
    def get_key(self, index):
        """Return current key"""
        return self.keys[index.row()]
    
    def get_value(self, index):
        """Return current value"""
        if index.column()==0:
            return self.types[ index.row() ]
        elif index.column()==1:
            return self.sizes[ index.row() ]
        else:
            return self._data[ self.keys[index.row()] ]

    def get_bgcolor(self, index):
        """Background color depending on value"""
        color = QColor(Qt.lightGray)
        color.setAlphaF(.3)
        return color

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return QVariant()
        value = self.get_value(index)
        if role == Qt.DisplayRole:
            return QVariant( value_to_display(value) )
        elif role == Qt.TextAlignmentRole:
            if index.column()==2:
                if isinstance(value, ndarray):
                    return QVariant(int(Qt.AlignLeft))
                if len(repr(value).splitlines())<3:
                    return QVariant(int(Qt.AlignLeft|Qt.AlignVCenter))
                else:
                    return QVariant(int(Qt.AlignLeft|Qt.AlignTop))
            else:
                return QVariant(int(Qt.AlignLeft|Qt.AlignVCenter))
        elif role == Qt.BackgroundColorRole:
            return QVariant( self.get_bgcolor(index) )
        elif role == Qt.FontRole:
            return QVariant(get_font('dicteditor'))
        return QVariant()
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overriding method headerData"""
        if role != Qt.DisplayRole:
            return QVariant()
        i_column = int(section)
        if orientation == Qt.Horizontal:
            headers = (translate("DictEditor", "Type"),
                       translate("DictEditor", "Size"),
                       translate("DictEditor", "Value"))
            return QVariant( headers[i_column] )
        else:
            return QVariant( self.keys[i_column] )

class DictModel(DictModelRO):
    """DictEditor Table Model"""
    
    def set_value(self, index, value):
        """Set value"""
        self._data[ self.keys[index.row()] ] = value
        self.showndata[ self.keys[index.row()] ] = value
        self.sizes[index.row()] = get_size(value)
        self.types[index.row()] = get_type(value)
        if self.sortkeys:
            self.sort(-1)

    def get_bgcolor(self, index):
        """Background color depending on value"""
        value = self.get_value(index)
        if index.column()<2:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.2)
        else:
            color = QColor()
            for typ in COLORS:
                if isinstance(value, typ):
                    color = QColor(COLORS[typ])
            color.setAlphaF(.2)
        return color

    def setData(self, index, value, role=Qt.EditRole):
        """Cell content change"""
        if not index.isValid():
            return False
        if index.column()<2:
            return False
        value = display_to_value( value, self.get_value(index) )
        self.set_value(index, value)
        self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                  index, index)
        return True

    def flags(self, index):
        """Overriding method flags"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                            Qt.ItemIsEditable)


class DictDelegate(QItemDelegate):
    """DictEditor Item Delegate"""
    def __init__(self, parent=None):
        QItemDelegate.__init__(self, parent)
        self.inplace = False

    def createEditor(self, parent, option, index):
        """Overriding method createEditor"""
        if index.column()<2:
            return None
        value = index.model().get_value(index)
        key = index.model().get_key(index)
        if isinstance(value, (list, tuple, dict)) and not self.inplace:
            editor = DictEditorDialog(value, key,
                                      icon=self.parent().windowIcon())
            if editor.exec_():
                index.model().set_value(index, editor.get_copy())
            return None
        elif isinstance(value, ndarray) and ndarray is not FakeObject \
                                        and not self.inplace:
            editor = ArrayEditor(value, key)
            if editor.exec_():
                index.model().set_value(index, editor.get_copy())
            return None
        else:
            editor = QLineEdit(parent)
            editor.setFont(get_font('dicteditor'))
            editor.setAlignment(Qt.AlignLeft)
            self.connect(editor, SIGNAL("returnPressed()"),
                         self.commitAndCloseEditor)
            return editor

    def commitAndCloseEditor(self):
        """Overriding method commitAndCloseEditor"""
        editor = self.sender()
        self.emit(SIGNAL("commitData(QWidget*)"), editor)
        self.emit(SIGNAL("closeEditor(QWidget*)"), editor)

    def setEditorData(self, editor, index):
        """Overriding method setEditorData"""
        if isinstance(editor, QLineEdit):
            text = index.model().data(index, Qt.DisplayRole).toString()
            editor.setText(text)

    def setModelData(self, editor, model, index):
        """Overriding method setModelData"""
        if isinstance(editor, QLineEdit):
            model.setData(index, QVariant(editor.text()))


class DictEditor(QTableView):
    """DictEditor table view"""
    def __init__(self, parent, data, readonly=False, sort_by=None, title=""):
        QTableView.__init__(self, parent)
        self.dictfilter = None
        self.readonly = readonly or isinstance(data, tuple)
        self.sort_by = sort_by
        self.model = None
        self.delegate = None
        if self.readonly:
            self.model = DictModelRO(self, data, title=title)
        else:
            self.model = DictModel(self, data, title=title)
        self.setModel(self.model)
        self.delegate = DictDelegate(self)
        self.setItemDelegate(self.delegate)
        self.horizontalHeader().setStretchLastSection(True)
        self.adjust_columns()
        self.menu = self.setup_menu()
        
    def setup_menu(self):
        """Setup context menu"""
        self.edit_action = create_action(self, 
                                      translate("DictEditor", "Edit"),
                                      triggered=self.edit_item)
        self.insert_action = create_action(self, 
                                      translate("DictEditor", "Insert"),
                                      triggered=self.insert_item)
        self.remove_action = create_action(self, 
                                      translate("DictEditor", "Remove"),
                                      icon=get_icon('close.png'),
                                      triggered=self.remove_item)
        self.sort_action = create_action(self,
                                    translate("DictEditor", "Sort columns"),
                                    toggled=self.setSortingEnabled)
        self.inplace_action = create_action(self,
                                       translate("DictEditor",
                                                 "Always edit in-place"),
                                       toggled=self.set_inplace_editor)
        menu = QMenu(self)
        add_actions( menu, (self.edit_action, self.insert_action,
                            self.remove_action,
                            None, self.sort_action, self.inplace_action) )
        return menu
    
    def edit_item(self):
        """Edit item"""
        index = self.currentIndex()
        if not index.isValid():
            return
        self.edit(index)
    
    def remove_item(self):
        """Remove item"""
        indexes = self.selectedIndexes()
        if not indexes:
            return
        for index in indexes:
            if not index.isValid():
                return
        answer = QMessageBox.question(self,
            translate("DictEditor", "Remove"),
            translate("DictEditor", "Do you want to remove selected item%1?") \
            .arg('s' if len(indexes)>1 else ''),
            QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            data = self.model.get_data()
            for index in indexes:
                data.pop( self.model.keys[ index.row() ] )
            self.set_data(data)
            
    def insert_item(self):
        """Insert item"""
        index = self.currentIndex()
        if not index.isValid():
            row = self.model.rowCount()
        else:
            row = index.row()
        data = self.model.get_data()
        if isinstance(data, list):
            key = row
            data.insert(row, '')
        elif isinstance(data, dict):
            key, valid = QInputDialog.getText(self,
                              translate("DictEditor", 'Insert'),
                              translate("DictEditor", 'Key:'),
                              QLineEdit.Normal)
            if valid and not key.isEmpty():
                key = try_to_eval(unicode(key))
            else:
                return
        else:
            return
        value, valid = QInputDialog.getText(self,
                  translate("DictEditor", 'Insert'),
                  translate("DictEditor", 'Value:'),
                  QLineEdit.Normal)
        if valid and not value.isEmpty():
            data[key] = try_to_eval(unicode(value))
            self.set_data(data)
            
    def refresh_menu(self):
        """Refresh context menu"""
        data = self.model.get_data()
        index = self.currentIndex()
        condition = (not isinstance(data, tuple)) and index.isValid() \
                    and not self.readonly
        self.edit_action.setEnabled( condition )
        self.remove_action.setEnabled( condition )
        self.insert_action.setEnabled( not self.readonly )
        
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        self.refresh_menu()
        self.menu.popup(event.globalPos())
        event.accept()
        
    def adjust_columns(self):
        """Resize two first columns to contents"""
        for col in range(2):
            self.resizeColumnToContents(col)
        
    def set_inplace_editor(self, state):
        """Set option in-place editor"""
        if state:
            self.delegate.inplace = True
        else:
            self.delegate.inplace = False
        
    def set_filter(self, dictfilter=None):
        """Set table dict filter"""
        self.dictfilter = dictfilter
        
    def set_data(self, data):
        """Set table data"""
        if data is not None:
            self.model.set_data(data, self.dictfilter)

class DictEditorWidget(QWidget):
    """Dictionary Editor Dialog"""
    def __init__(self, parent, data, readonly=False, sort_by=None, title=""):
        QWidget.__init__(self, parent)
        self.editor = DictEditor(self, data, readonly, sort_by, title)
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        self.setLayout(layout)
        
    def set_data(self, data):
        """Set DictEditor data"""
        self.editor.set_data(data)
        
    def get_title(self):
        """Get model title"""
        return self.editor.model.title


class DictEditorDialog(QDialog):
    """Dictionary/List Editor Dialog"""
    def __init__(self, data, title="", width=500,
                 readonly=False, icon='dictedit.png'):
        QDialog.__init__(self)
        import copy
        self.copy = copy.deepcopy(data)
        self.widget = DictEditorWidget(self, self.copy, sort_by='type',
                                       title=title, readonly=readonly)
        
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        
        # Buttons configuration
        buttons = QDialogButtonBox.Ok
        if not readonly:
            buttons = buttons | QDialogButtonBox.Cancel
        bbox = QDialogButtonBox(buttons)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        if not readonly:
            self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        layout.addWidget(bbox)

        self.setLayout(layout)
        constant = 121
        row_height = 30
        error_margin = 20
        height = constant + row_height*min([20, len(data)]) + error_margin
        self.resize(width, height)
        
        self.setWindowTitle(self.widget.get_title())
        if isinstance(icon, (str, unicode)):
            icon = get_icon(icon)
        self.setWindowIcon(icon)
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        
    def get_copy(self):
        """Return modified copy of dictionary or list"""
        return self.copy
    
    
def main():
    """Dict editor demo"""
    from PyQt4.QtGui import QApplication
    QApplication([])
    import numpy
    dico = {'str': 'kjkj kj k j j kj k jkj',
            'list': [1, 3, 4, 'kjkj', None],
            'dict': {'d': 1, 'a': None, 'b': [1, 2]},
            'float': 1.2233,
            'array': numpy.random.rand(10, 10),
            }
    dialog = DictEditorDialog(dico, title="Bad title")
    if dialog.exec_():
        print "Accepted:", dialog.get_copy()
    else:
        print "Canceled"

if __name__ == "__main__":
    main()