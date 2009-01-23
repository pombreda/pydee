# -*- coding: utf-8 -*-
"""
Dictionary Editor Widget and Dialog based on PyQt4
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtCore import Qt, QVariant, QModelIndex, QAbstractTableModel
from PyQt4.QtCore import SIGNAL, SLOT
from PyQt4.QtGui import QHBoxLayout, QTableView, QItemDelegate
from PyQt4.QtGui import QLineEdit, QVBoxLayout, QWidget, QColor, QCheckBox
from PyQt4.QtGui import QDialog, QDialogButtonBox

# Local import
from config import get_icon, get_font
from qthelpers import translate

class FakeObject(object):
    """Fake class used in replacement of missing modules"""
    pass
try:
    from numpy import ndarray
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
    return text[text.find('.')+1:]

class DictModelRO(QAbstractTableModel):
    """DictEditor Read-Only Table Model"""
    def __init__(self, parent, data, dictfilter=None, sortkeys=True):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self.sortkeys = sortkeys
        self._data = None
        self.showndata = None
        self.keys = None
        self.title = None
        self.sizes = None
        self.types = None
        self.set_data(data, dictfilter)
            
    def set_data(self, data, dictfilter):
        """Set model data"""
        self._data = data
        if dictfilter is not None:
            data = dictfilter(data)
        self.showndata = data
        if isinstance(data, tuple):
            self.keys = range(len(data))
            self.title = translate("DictEditor", "Tuple")
        elif isinstance(data, list):
            self.keys = range(len(data))
            self.title = translate("DictEditor", "List")
        elif isinstance(data, dict):
            self.keys = data.keys()
            self.title = translate("DictEditor", "Dictionary")
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
                if isinstance(value, (str, unicode)):
                    if '\n' in value:
                        return QVariant(int(Qt.AlignLeft))
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
        if isinstance(value, (list, tuple, dict)) and not self.inplace:
            editor = DictEditorDialog(self.parent(), value)
            if editor.exec_():
                index.model().set_value(index, editor.get_copy())
            return None
        elif isinstance(value, ndarray) and ndarray is not FakeObject \
                                        and not self.inplace:
            from arrayeditor import ArrayEditor
            editor = ArrayEditor(index.model().get_key(index), value)
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
    def __init__(self, parent, data, readonly=False, sort_by=None):
        QTableView.__init__(self, parent)
        self.readonly = readonly
        self.sort_by = sort_by
        self.model = None
        self.delegate = None
        if self.readonly:
            self.model = DictModelRO(self, data)
        else:
            self.model = DictModel(self, data)
        self.setModel(self.model)
        self.delegate = DictDelegate(self)
        self.setItemDelegate(self.delegate)
        self.horizontalHeader().setStretchLastSection(True)
        
    def set_inplace_editor(self, state):
        """Set option in-place editor"""
        if state:
            self.delegate.inplace = True
        else:
            self.delegate.inplace = False
        
    def set_data(self, data, dictfilter=None):
        """Set table data"""
        if data is not None:
            self.model.set_data(data, dictfilter)
            for col in range(2):
                self.resizeColumnToContents(col)

class DictEditorWidget(QWidget):
    """Dictionary Editor Dialog"""
    def __init__(self, parent, data, readonly=False, sort_by=None):
        QWidget.__init__(self, parent)

        # Options
        layout_opts = QHBoxLayout()
        self.cb_sort = QCheckBox(translate("DictEditor", "Sort columns"))
        layout_opts.addWidget(self.cb_sort)
        self.cb_inline = QCheckBox(translate("DictEditor",
                                             "Always edit in-place"))
        layout_opts.addWidget(self.cb_inline)

        layout = QVBoxLayout()
        layout.addLayout(layout_opts)
        self.editor = DictEditor(self, data, readonly, sort_by)
        self.connect(self.cb_sort, SIGNAL("stateChanged(int)"),
                     self.editor.setSortingEnabled)
        self.connect(self.cb_inline, SIGNAL("stateChanged(int)"),
                     self.editor.set_inplace_editor)
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
    def __init__(self, title, data):
        QDialog.__init__(self)
        import copy
        self.copy = copy.deepcopy(data)
        self.widget = DictEditorWidget(self, self.copy, sort_by='type')
        
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        
        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        layout.addWidget(bbox)

        self.setLayout(layout)
#        self.setMinimumSize(350, 150)
        
        self.setWindowTitle(self.widget.get_title())
        self.setWindowIcon(get_icon('dictedit.png'))
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
    dialog = DictEditorDialog('', dico)
    if dialog.exec_():
        print "Accepted:", dialog.get_copy()
    else:
        print "Canceled"

if __name__ == "__main__":
    main()