# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
Dictionary Editor Widget and Dialog based on PyQt4
"""

#TODO: Multiple selection: open as many editors (array/dict/...) as necessary,
#      at the same time

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import re
from PyQt4.QtCore import (Qt, QVariant, QModelIndex, QAbstractTableModel,
                          SIGNAL, SLOT, QDateTime)
from PyQt4.QtGui import (QMessageBox, QTableView, QItemDelegate, QLineEdit,
                         QVBoxLayout, QWidget, QColor, QDialog, QDateEdit,
                         QDialogButtonBox, QMenu, QInputDialog, QDateTimeEdit,
                         QApplication, QKeySequence)

# Local import
from pydeelib.config import get_icon, get_font
from pydeelib.qthelpers import translate, add_actions, create_action
from pydeelib.widgets.texteditor import TextEditor
from pydeelib.widgets.importwizard import ImportWizard

#----Numpy arrays support
class FakeObject(object):
    """Fake class used in replacement of missing modules"""
    pass
try:
    from numpy import ndarray
    from pydeelib.widgets.arrayeditor import ArrayEditor
except ImportError:
    class ndarray(FakeObject):
        """Fake ndarray"""
        pass

#----Misc.
def address(obj):
    """Return object address as a string: '<classname @ address>'"""
    return "<%s @ %s>" % (obj.__class__.__name__,
                          hex(id(obj)).upper().replace('X','x'))

#----date and datetime objects support
import datetime
try:
    from dateutil.parser import parse as dateparse
except ImportError:
    from string import atoi
    def dateparse(datestr):
        """Just for 'year, month, day' strings"""
        return datetime.datetime( *map(atoi, datestr.split(',')) )
def datestr_to_datetime(value):
    rp = value.rfind('(')+1
    return dateparse(value[rp:-1])

#----Background colors for supported types 
COLORS = {
          bool: Qt.magenta,
          (int, float, long): Qt.blue,
          list: Qt.yellow,
          dict: Qt.cyan,
          tuple: Qt.lightGray,
          (str, unicode): Qt.darkRed,
          ndarray: Qt.green,
          datetime.date: Qt.darkYellow,
          }

def get_color(value, alpha=.2):
    """Return color depending on value type"""
    color = QColor()
    for typ in COLORS:
        if isinstance(value, typ):
            color = QColor(COLORS[typ])
    color.setAlphaF(alpha)
    return color

#----Sorting
def sort_against(lista, listb, reverse=False):
    """Arrange lista items in the same order as sorted(listb)"""
    return [item for _, item in sorted(zip(listb, lista), reverse=reverse)]

def unsorted_unique(lista):
    """Removes duplicates from lista neglecting its initial ordering"""
    set = {}
    map(set.__setitem__,lista,[])
    return set.keys()

#----Display <--> Value
def value_to_display(value, truncate=False,
                     trunc_len=80, minmax=False, collvalue=True):
    """Convert value for display purpose"""
    if minmax and isinstance(value, ndarray):
        if value.size == 0:
            return repr(value)
        try:
            return 'Min: %r\nMax: %r' % (value.min(), value.max())
        except TypeError:
            pass
    if not isinstance(value, (str, unicode)):
        if isinstance(value, (list, tuple, dict, set)) and not collvalue:            
            value = address(value)
        else:
            value = repr(value)
    if truncate and len(value) > trunc_len:
        value = value[:trunc_len].rstrip() + ' ...'
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
        elif isinstance(default_value, datetime.datetime):
            value = datestr_to_datetime(value)
        elif isinstance(default_value, datetime.date):
            value = datestr_to_datetime(value).date()
        else:
            value = try_to_eval(value)
    except (ValueError, SyntaxError):
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
    found = re.findall(r"<type '([\S]*)'>", str(type(item)))
    text = unicode(translate('DictEditor', 'unknown')) \
           if not found else found[0]
    if isinstance(item, ndarray):
        text = item.dtype.name
    return text[text.find('.')+1:]


class ReadOnlyDictModel(QAbstractTableModel):
    """DictEditor Read-Only Table Model"""
    def __init__(self, parent, data, title="", names=False,
                 truncate=True, minmax=False, collvalue=True, remote=False):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self.names = names
        self.truncate = truncate
        self.minmax = minmax
        self.collvalue = collvalue
        self.remote = remote
        self.header0 = None
        self._data = None
        self.showndata = None
        self.keys = None
        self.title = unicode(title) # in case title is not a string
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
        if dictfilter is not None and not self.remote:
            data = dictfilter(data)
        self.showndata = data
        self.header0 = translate("DictEditor", "Index")
        if self.names:
            self.header0 = translate("DictEditor", "Name")
        if isinstance(data, tuple):
            self.keys = range(len(data))
            self.title += translate("DictEditor", "Tuple")
        elif isinstance(data, list):
            self.keys = range(len(data))
            self.title += translate("DictEditor", "List")
        elif isinstance(data, dict):
            self.keys = data.keys()
            self.title += translate("DictEditor", "Dictionary")
            if not self.names:
                self.header0 = translate("DictEditor", "Key")
        else:
            raise RuntimeError("Invalid data type")
        self.title += ' ('+str(len(self.keys))+' '+ \
                      translate("DictEditor", "elements")+')'
        if self.remote:
            self.sizes = [ data[self.keys[index]]['size']
                           for index in range(len(self.keys)) ]
            self.types = [ data[self.keys[index]]['type']
                           for index in range(len(self.keys)) ]
        else:
            self.sizes = [ get_size(data[self.keys[index]])
                           for index in range(len(self.keys)) ]
            self.types = [ get_type(data[self.keys[index]])
                           for index in range(len(self.keys)) ]
        self.reset()

    def sort(self, column, order=Qt.AscendingOrder):
        """Overriding sort method"""
        reverse = (order==Qt.DescendingOrder)
        if column == 0:
            self.sizes = sort_against(self.sizes, self.keys, reverse)
            self.types = sort_against(self.types, self.keys, reverse)
            self.keys.sort(reverse=reverse)
        elif column == 1:
            self.keys = sort_against(self.keys, self.types, reverse)
            self.sizes = sort_against(self.sizes, self.types, reverse)
            self.types.sort(reverse=reverse)
        elif column == 2:
            self.keys = sort_against(self.keys, self.sizes, reverse)
            self.types = sort_against(self.types, self.sizes, reverse)
            self.sizes.sort(reverse=reverse)
        elif column == 3:
            self.keys = sort_against(self.keys, self.sizes, reverse)
            self.types = sort_against(self.types, self.sizes, reverse)
            self.sizes.sort(reverse=reverse)
        elif column == 4:
            values = [self._data[key] for key in self.keys]
            self.keys = sort_against(self.keys, values, reverse)
            self.sizes = sort_against(self.sizes, values, reverse)
            self.types = sort_against(self.types, values, reverse)
        self.reset()

    def columnCount(self, qindex=QModelIndex()):
        """Array column number"""
        return 4

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return len(self.keys)
    
    def get_key(self, index):
        """Return current key"""
        return self.keys[index.row()]
    
    def get_value(self, index):
        """Return current value"""
        if index.column() == 0:
            return self.keys[ index.row() ]
        elif index.column() == 1:
            return self.types[ index.row() ]
        elif index.column() == 2:
            return self.sizes[ index.row() ]
        else:
            return self._data[ self.keys[index.row()] ]

    def get_bgcolor(self, index):
        """Background color depending on value"""
        if index.column() == 0:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.05)
        elif index.column() < 3:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.2)
        else:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.3)
        return color

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return QVariant()
        value = self.get_value(index)
        if index.column() == 3 and self.remote:
            value = value['view']
        display = value_to_display(value,
                               truncate=index.column() == 3 and self.truncate,
                               minmax=self.minmax,
                               collvalue=self.collvalue or index.column() != 3)
        if role == Qt.DisplayRole:
            return QVariant(display)
        elif role == Qt.EditRole:
            return QVariant(value_to_display(value))
        elif role == Qt.TextAlignmentRole:
            if index.column() == 3:
                if len(display.splitlines()) < 3:
                    return QVariant(int(Qt.AlignLeft|Qt.AlignVCenter))
                else:
                    return QVariant(int(Qt.AlignLeft|Qt.AlignTop))
            else:
                return QVariant(int(Qt.AlignLeft|Qt.AlignVCenter))
        elif role == Qt.BackgroundColorRole:
            return QVariant( self.get_bgcolor(index) )
        elif role == Qt.FontRole:
            if index.column() < 3:
                return QVariant(get_font('dicteditor_header'))
            else:
                return QVariant(get_font('dicteditor'))
        return QVariant()
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overriding method headerData"""
        if role != Qt.DisplayRole:
            if role == Qt.FontRole:
                return QVariant(get_font('dicteditor_header'))
            else:
                return QVariant()
        i_column = int(section)
        if orientation == Qt.Horizontal:
            headers = (self.header0,
                       translate("DictEditor", "Type"),
                       translate("DictEditor", "Size"),
                       translate("DictEditor", "Value"))
            return QVariant( headers[i_column] )
        else:
            return QVariant()

    def flags(self, index):
        """Overriding method flags"""
        # This method was implemented in DictModel only, but to enable tuple
        # exploration (even without editing), this method was moved here
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                            Qt.ItemIsEditable)

class DictModel(ReadOnlyDictModel):
    """DictEditor Table Model"""
    
    def set_value(self, index, value):
        """Set value"""
        self._data[ self.keys[index.row()] ] = value
        self.showndata[ self.keys[index.row()] ] = value
        self.sizes[index.row()] = get_size(value)
        self.types[index.row()] = get_type(value)

    def get_bgcolor(self, index):
        """Background color depending on value"""
        value = self.get_value(index)
        if index.column()<3:
            color = ReadOnlyDictModel.get_bgcolor(self, index)
        else:
            if self.remote:
                color = value['color']
            else:
                color = get_color(value)
        return color

    def setData(self, index, value, role=Qt.EditRole):
        """Cell content change"""
        if not index.isValid():
            return False
        if index.column()<3:
            return False
        value = display_to_value( value, self.get_value(index) )
        self.set_value(index, value)
        self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                  index, index)
        return True


class DictDelegate(QItemDelegate):
    """DictEditor Item Delegate"""
    def __init__(self, parent=None, inplace=False):
        QItemDelegate.__init__(self, parent)
        self.inplace = inplace
        
    def get_value(self, index):
        return index.model().get_value(index)
    
    def set_value(self, index, value):
        index.model().set_value(index, value)

    def createEditor(self, parent, option, index):
        """Overriding method createEditor"""
        if index.column()<3:
            return None
        value = self.get_value(index)
        key = index.model().get_key(index)
        readonly = isinstance(value, tuple) or self.parent().readonly
        #---editor = DictEditor
        if isinstance(value, (list, tuple, dict)) and not self.inplace:
            editor = DictEditor(value, key, icon=self.parent().windowIcon(),
                                readonly=readonly)
            if editor.exec_() and not readonly:
                self.set_value(index, editor.get_copy())
            return None
        #---editor = ArrayEditor
        elif isinstance(value, ndarray) and ndarray is not FakeObject \
                                        and not self.inplace:
            if value.size == 0:
                return None
            editor = ArrayEditor(value, title=key, readonly=readonly)
            if editor.exec_():
                # Only necessary for child class RemoteDictDelegate:
                # (ArrayEditor does not make a copy of value)
                self.set_value(index, value)
            return None
        #---editor = QDateTimeEdit
        elif isinstance(value, datetime.datetime) and not self.inplace:
            editor = QDateTimeEdit(value, parent)
            editor.setCalendarPopup(True)
            editor.setFont(get_font('dicteditor'))
            self.connect(editor, SIGNAL("returnPressed()"),
                         self.commitAndCloseEditor)
            return editor
        #---editor = QDateEdit
        elif isinstance(value, datetime.date) and not self.inplace:
            editor = QDateEdit(value, parent)
            editor.setCalendarPopup(True)
            editor.setFont(get_font('dicteditor'))
            self.connect(editor, SIGNAL("returnPressed()"),
                         self.commitAndCloseEditor)
            return editor
        #---editor = QTextEdit
        elif isinstance(value, (str, unicode)) and len(value)>40:
            editor = TextEditor(value, key)
            if editor.exec_() and not readonly:
                conv = str if isinstance(value, str) else unicode
                self.set_value(index, conv(editor.get_copy()))
            return None
        #---editor = QLineEdit
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
        """Overriding method setEditorData
        Model --> Editor"""
        value = self.get_value(index)
        if isinstance(editor, QLineEdit):
            if not isinstance(value, basestring):
                value = unicode(value)
            editor.setText(value)
        elif isinstance(editor, QDateEdit):
            editor.setDate(value)
        elif isinstance(editor, QDateTimeEdit):
            editor.setDateTime(QDateTime(value.date(), value.time()))

    def setModelData(self, editor, model, index):
        """Overriding method setModelData
        Editor --> Model"""
        if not hasattr(model, "set_value"):
            # Read-only mode
            return
        
        if isinstance(editor, QLineEdit):
            value = editor.text()
        elif isinstance(editor, QDateEdit):
            qdate = editor.date()
            value = datetime.date( qdate.year(), qdate.month(), qdate.day() )
        elif isinstance(editor, QDateTimeEdit):
            qdatetime = editor.dateTime()
            qdate = qdatetime.date()
            qtime = qdatetime.time()
            value = datetime.datetime( qdate.year(), qdate.month(),
                                       qdate.day(), qtime.hour(),
                                       qtime.minute(), qtime.second() )
        else:
            # Should not happen...
            raise RuntimeError("Unsupported editor widget")
        
        value = display_to_value( QVariant(value), self.get_value(index) )        
        self.set_value(index, value)


class BaseTableView(QTableView):
    def __init__(self, parent):
        QTableView.__init__(self, parent)
        
    def setup_table(self):
        """Setup table"""
        self.horizontalHeader().setStretchLastSection(True)
        self.adjust_columns()
        # Sorting columns
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
    
    def setup_menu(self, truncate, minmax, inplace, collvalue):
        """Setup context menu"""
        self.edit_action = create_action(self, 
                                      translate("DictEditor", "Edit"),
                                      icon=get_icon('edit.png'),
                                      triggered=self.edit_item)
        self.plot_action = create_action(self, 
                                      translate("DictEditor", "Plot"),
                                      icon=get_icon('plot.png'),
                                      triggered=self.plot_item)
        self.plot_action.setVisible(False)
        self.imshow_action = create_action(self, 
                                      translate("DictEditor", "Show image"),
                                      icon=get_icon('imshow.png'),
                                      triggered=self.imshow_item)
        self.imshow_action.setVisible(False)
        self.insert_action = create_action(self, 
                                      translate("DictEditor", "Insert"),
                                      icon=get_icon('insert.png'),
                                      triggered=self.insert_item)
        self.remove_action = create_action(self, 
                                      translate("DictEditor", "Remove"),
                                      icon=get_icon('editdelete.png'),
                                      triggered=self.remove_item)
        self.truncate_action = create_action(self,
                                    translate("DictEditor", "Truncate values"),
                                    toggled=self.toggle_truncate)
        self.truncate_action.setChecked(truncate)
        self.toggle_truncate(truncate)
        self.minmax_action = create_action(self,
                                translate("DictEditor", "Show arrays min/max"),
                                toggled=self.toggle_minmax)
        self.minmax_action.setChecked(minmax)
        self.toggle_minmax(minmax)
        self.collvalue_action = create_action(self,
                            translate("DictEditor", "Show collection contents"),
                            toggled=self.toggle_collvalue)
        self.collvalue_action.setChecked(collvalue)
        self.toggle_collvalue(collvalue)
        self.inplace_action = create_action(self,
                                       translate("DictEditor",
                                                 "Always edit in-place"),
                                       toggled=self.toggle_inplace)
        self.inplace_action.setChecked(inplace)
        if self.delegate is None:
            self.inplace_action.setEnabled(False)
        else:
            self.toggle_inplace(inplace)
        self.rename_action = create_action(self,
                                    translate("DictEditor", "Rename"),
                                    icon=get_icon('rename.png'),
                                    triggered=self.rename_item)
        self.duplicate_action = create_action(self,
                                    translate("DictEditor", "Duplicate"),
                                    icon=get_icon('edit_add.png'),
                                    triggered=self.duplicate_item)
        menu = QMenu(self)
        menu_actions = [self.edit_action, self.plot_action, self.imshow_action,
                        self.insert_action,
                        self.remove_action, None,
                        self.rename_action,self.duplicate_action, None,
                        self.truncate_action, self.inplace_action,
                        self.collvalue_action]
        if ndarray is not FakeObject:
            menu_actions.append(self.minmax_action)
        add_actions(menu, menu_actions)
        return menu
    
    def refresh_menu(self):
        """Refresh context menu"""
        index = self.currentIndex()
        condition = index.isValid()
        self.edit_action.setEnabled( condition )
        self.remove_action.setEnabled( condition )
        self.refresh_plot_entries(index)
        
    def refresh_plot_entries(self, index):
        if index.isValid():
            value = self.delegate.get_value(index)
            condition_plot = isinstance(value, ndarray) and len(value) != 0 \
                             and len(value.shape) <= 2
            condition_imshow = condition_plot and min(value.shape) > 2
        else:
            condition_plot = condition_imshow = False
        self.plot_action.setVisible(condition_plot)
        self.imshow_action.setVisible(condition_imshow)
        
    def adjust_columns(self):
        """Resize two first columns to contents"""
        for col in range(3):
            self.resizeColumnToContents(col)
        
    def set_data(self, data):
        """Set table data"""
        if data is not None:
            self.model.set_data(data, self.dictfilter)
            self.sortByColumn(0, Qt.AscendingOrder)

    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() != Qt.LeftButton:
            QTableView.mousePressEvent(self, event)
            return
        index_clicked = self.indexAt(event.pos())
        if index_clicked.isValid():
            if index_clicked == self.currentIndex() \
               and index_clicked in self.selectedIndexes():
                self.clearSelection()
            else:
                QTableView.mousePressEvent(self, event)
        else:
            self.clearSelection()
            event.accept()
    
    def keyPressEvent(self, event):
        """Reimplement Qt methods"""
        if event.key() == Qt.Key_Delete:
            self.remove_item()
            event.accept()
        elif event.key() == Qt.Key_F2:
            self.rename_item()
            event.accept()
        elif event == QKeySequence.Paste:
            self.paste()
            event.accept()
        else:
            QTableView.keyPressEvent(self, event)
        
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        if self.model.showndata:
            self.refresh_menu()
            self.menu.popup(event.globalPos())
            event.accept()

    def toggle_inplace(self, state):
        """Toggle in-place editor option"""
        self.emit(SIGNAL('option_changed'), 'inplace', state)
        self.delegate.inplace = state
        
    def toggle_truncate(self, state):
        """Toggle display truncating option"""
        self.emit(SIGNAL('option_changed'), 'truncate', state)
        self.model.truncate = state
        
    def toggle_minmax(self, state):
        """Toggle min/max display for numpy arrays"""
        self.emit(SIGNAL('option_changed'), 'minmax', state)
        self.model.minmax = state
        
    def toggle_collvalue(self, state):
        """Toggle value display for collections"""
        self.emit(SIGNAL('option_changed'), 'collvalue', state)
        self.model.collvalue = state
            
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
            idx_rows = unsorted_unique(map(lambda idx: idx.row(), indexes))
            keys = [ self.model.keys[idx_row] for idx_row in idx_rows ]
            self.remove_values(keys)

    def copy_item(self, erase_original=False):
        """Copy item"""
        indexes = self.selectedIndexes()
        if not indexes:
            return
        idx_rows = unsorted_unique(map(lambda idx: idx.row(), indexes))
        if len(idx_rows) > 1 or not indexes[0].isValid():
            return
        orig_key = self.model.keys[idx_rows[0]]
        new_key, valid = QInputDialog.getText(self,
                          translate("DictEditor", 'Rename'),
                          translate("DictEditor", 'Key:'),
                          QLineEdit.Normal,orig_key)
        if valid and not new_key.isEmpty():
            new_key = try_to_eval(unicode(new_key))
            if new_key == orig_key:
                return
            self.copy_value(orig_key, new_key)
            if erase_original:
                self.remove_values([orig_key])
    
    def duplicate_item(self):
        """Duplicate item"""
        self.copy_item()

    def rename_item(self):
        """Rename item"""
        self.copy_item(True)
    
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
            self.new_value(key, try_to_eval(unicode(value)))
            
    def __prepare_plot(self):
        try:
            from matplotlib import rcParams
            rcParams['backend'] = 'Qt4agg'
            return True
        except ImportError:
            QMessageBox.warning(self, translate("DictEditor", "Import error"),
                    translate("DictEditor",
                              "Please install <b>matplotlib</b>."))

            
    def plot_item(self):
        """Plot item"""
        index = self.currentIndex()
        if self.__prepare_plot():
            from pylab import plot, show
            data = self.delegate.get_value(index)
            plot(data)
            show()
            
    def imshow_item(self):
        """Imshow item"""
        index = self.currentIndex()
        if self.__prepare_plot():
            from pylab import imshow, show
            data = self.delegate.get_value(index)
            imshow(data)
            show()
        

class DictEditorTableView(BaseTableView):
    """DictEditor table view"""
    def __init__(self, parent, data, readonly=False, title="",
                 names=False, truncate=True, minmax=False,
                 inplace=False, collvalue=True):
        BaseTableView.__init__(self, parent)
        self.dictfilter = None
        self.readonly = readonly or isinstance(data, tuple)
        self.model = None
        self.delegate = None
        DictModelClass = ReadOnlyDictModel if self.readonly else DictModel
        self.model = DictModelClass(self, data, title, names=names,
                                    truncate=truncate, minmax=minmax,
                                    collvalue=collvalue)
        self.setModel(self.model)
        self.delegate = DictDelegate(self, inplace=inplace)
        self.setItemDelegate(self.delegate)

        self.setup_table()
        self.menu = self.setup_menu(truncate, minmax, inplace, collvalue)
        self.copy_action = create_action(self,
                                      translate("DictEditor", "Copy"),
                                      icon=get_icon('editcopy.png'),
                                      triggered=self.copy)                                      
        self.paste_action = create_action(self,
                                      translate("DictEditor", "Paste"),
                                      icon=get_icon('editpaste.png'),
                                      triggered=self.paste)
        self.menu.insertAction(self.remove_action, self.copy_action)
        self.menu.insertAction(self.remove_action, self.paste_action)
    
    def remove_values(self, keys):
        """
        Remove values from data
        (implemented differently for remote table view)
        """
        data = self.model.get_data()
        for key in keys:
            data.pop(key)
        self.set_data(data)

    def copy_value(self, orig_key, new_key):
        """
        Copy value
        (implemented differently for remote table view)
        """
        data = self.model.get_data()
        data[new_key] = data[orig_key]
        self.set_data(data)
    
    def new_value(self, key, value):
        """
        Create new value in data
        (implemented differently for remote table view)
        """
        data = self.model.get_data()
        data[key] = value
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
        self.refresh_plot_entries(index)
        
    def set_filter(self, dictfilter=None):
        """Set table dict filter"""
        self.dictfilter = dictfilter

    def copy(self):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        data = self.model.get_data()
        clipl = []
        for idx in self.selectedIndexes():
            if not idx.isValid:
                continue
            _txt = u''
            if isinstance(data,dict):
                _txt = unicode(data.get(self.model.keys[idx.row()]))
            else:
                _txt = unicode(data[idx.row()])
            clipl.append(_txt)
        clipboard.setText(u'\n'.join(clipl))
    
    def paste(self):
        """Import text/data/code from clipboard"""
        clipboard = QApplication.clipboard()
        cliptext = u""
        if clipboard.mimeData().hasText():
            cliptext = unicode(clipboard.text())
        if cliptext.strip():
            data = self.model.get_data()
            varname_base = translate("DictEditor", "new")
            get_varname = lambda index: varname_base + ("%03d" % index)
            index = 0
            while data.has_key(get_varname(index)):
                index += 1
            editor = ImportWizard(self, cliptext,
                                  title=translate("DictEditor",
                                                  "Import from clipboard"),
                                  contents_title=translate("DictEditor",
                                                           "Clipboard contents"),
                                  varname=get_varname(index))
            if editor.exec_():
                var_name, clip_data = editor.get_data()
                data[var_name] = clip_data
                self.set_data(data)
        else:
            QMessageBox.warning(self,
                                translate("DictEditor", "Empty clipboard"),
                                translate("DictEditor", "Nothing to be imported"
                                          " from clipboard."))


class DictEditorWidget(QWidget):
    """Dictionary Editor Dialog"""
    def __init__(self, parent, data, readonly=False, title="", remote=False):
        QWidget.__init__(self, parent)
        if remote:
            self.editor = RemoteDictEditorTableView(self, data, readonly)
        else:
            self.editor = DictEditorTableView(self, data, readonly, title)
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        self.setLayout(layout)
        
    def set_data(self, data):
        """Set DictEditor data"""
        self.editor.set_data(data)
        
    def get_title(self):
        """Get model title"""
        return self.editor.model.title


class DictEditor(QDialog):
    """Dictionary/List Editor Dialog"""
    def __init__(self, data, title="", width=500,
                 readonly=False, icon='dictedit.png', remote=False):
        QDialog.__init__(self)
        import copy
        self.data_copy = copy.deepcopy(data)
        self.widget = DictEditorWidget(self, self.data_copy, title=title,
                                       readonly=readonly, remote=remote)
        
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)
        
        # Buttons configuration
        buttons = QDialogButtonBox.Ok
        if not readonly:
            buttons = buttons | QDialogButtonBox.Cancel
        bbox = QDialogButtonBox(buttons)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        if not readonly:
            self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        layout.addWidget(bbox)

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
        return self.data_copy
    
    
def dedit(seq):
    """
    Edit the sequence 'seq' in a GUI-based editor and return the edited copy
    (if Cancel is pressed, return None)

    The object 'seq' is a container (dict, list or tuple)

    (instantiate a new QApplication if necessary,
    so it can be called directly from the interpreter)
    """
    if QApplication.startingUp():
        QApplication([])
    dialog = DictEditor(seq)
    if dialog.exec_():
        return dialog.get_copy()


#----Remote versions of DictDelegate and DictEditorTableView
class RemoteDictDelegate(DictDelegate):
    """DictEditor Item Delegate"""
    def __init__(self, parent=None, inplace=False,
                 get_value_func=None, set_value_func=None):
        DictDelegate.__init__(self, parent, inplace=inplace)
        self.get_value_func = get_value_func
        self.set_value_func = set_value_func
        
    def get_value(self, index):
        name = index.model().keys[index.row()]
        return self.get_value_func(name)
    
    def set_value(self, index, value):
        name = index.model().keys[index.row()]
        self.set_value_func(name, value)
        
class RemoteDictEditorTableView(BaseTableView):
    """DictEditor table view"""
    def __init__(self, parent, data,
                 truncate=True, minmax=False, inplace=False, collvalue=True,
                 get_value_func=None, set_value_func=None,
                 new_value_func=None, remove_values_func=None,
                 copy_value_func=None):
        BaseTableView.__init__(self, parent)
        
        self.remove_values = remove_values_func
        self.copy_value = copy_value_func
        self.new_value = new_value_func
        
        self.dictfilter = None
        self.model = None
        self.delegate = None
        self.readonly = False
        self.model = DictModel(self, data, names=True,
                               truncate=truncate, minmax=minmax,
                               collvalue=collvalue, remote=True)
        self.setModel(self.model)
        self.delegate = RemoteDictDelegate(self, inplace,
                                           get_value_func, set_value_func)
        self.setItemDelegate(self.delegate)
        
        self.setup_table()
        self.menu = self.setup_menu(truncate, minmax, inplace, collvalue)


#----Globals filter: filter namespace dictionaries (to be edited in DictEditor)
def is_supported(value, iter=0, itermax=-1, filters=None):
    """Return True if the value is supported, False otherwise"""
    assert filters is not None
    if iter == itermax:
        return True
    elif not isinstance(value, filters):
        return False
    elif isinstance(value, (list, tuple, set)):
        for val in value:
            if not is_supported(val, iter+1, filters=filters):
                return False
    elif isinstance(value, dict):
        for key, val in value.iteritems():
            if not is_supported(key, iter+1, filters=filters) \
               or not is_supported(val, iter+1, filters=filters):
                return False
    return True

def globalsfilter(input_dict, itermax=-1, filters=None,
                  exclude_private=None, exclude_upper=None,
                  exclude_unsupported=None, excluded_names=None):
    """Keep only objects that can be pickled"""
    output_dict = input_dict.copy() # Shallow copy
    for key in input_dict:
        if (exclude_private and key.startswith('_')) or \
           (exclude_upper and key[0].isupper()) or \
           (key in excluded_names) or \
           (exclude_unsupported and not is_supported(input_dict[key],
                                                     itermax=itermax,
                                                     filters=filters)):
            output_dict.pop(key)
    return output_dict


if __name__ == "__main__":
    import numpy as N
    testdict = {'d': 1, 'a': N.random.rand(10, 10), 'b': [1, 2]}
    testdate = datetime.date(1945, 5, 8)
    example = {'str': 'kjkj kj k j j kj k jkj',
               'unicode': u'éù',
               'list': [1, 3, [4, 5, 6], 'kjkj', None],
               'tuple': ([1, testdate, testdict], 'kjkj', None),
               'dict': testdict,
               'float': 1.2233,
               'array': N.random.rand(10, 10),
               'empty_array': N.array([]),
               'date': testdate,
               'datetime': datetime.datetime(1945, 5, 8),
               }
    
#    # Remote dict test:
#    from pydeelib.widgets.monitor import make_remote_view
#    remote = make_remote_view(example)
#    from pprint import pprint
#    pprint(remote)
#    if QApplication.startingUp():
#        QApplication([])
#    dialog = DictEditor(remote, remote=True)
#    if dialog.exec_():
#        print dialog.get_copy()
    
    out = dedit(example)
    print "out:", out
    