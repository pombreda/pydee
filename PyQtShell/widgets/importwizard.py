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
Text data Importing Wizard based on PyQt4
"""

from PyQt4.QtCore import (Qt, QVariant, QModelIndex, QAbstractTableModel,
                          SIGNAL, SLOT, QString, pyqtSignature)
from PyQt4.QtGui import (QTableView, QVBoxLayout, QHBoxLayout, QWidget,
                         QDialog, QTextEdit, QTabWidget, QPushButton, QLabel,
                         QSpacerItem, QSizePolicy, QCheckBox, QRadioButton,
                         QLineEdit, QFrame)

from functools import partial as ft_partial

# Local import
from PyQtShell.config import get_icon
from PyQtShell.qthelpers import translate


def has_special_char(value):
    """Check if value is a string and contains special chars"""
    spec_chars = (u'/', u'%')
    if filter(lambda c: c in value, spec_chars):
        return True
    return False
    
def try_to_eval(value):
    """Return True if value is correct or if it contains special chars"""
    if has_special_char(value):
        return value
    try:
        return eval(value)
    except (NameError, SyntaxError, ImportError):
        return value


class ContentsWidget(QWidget):
    """Import wizard contents widget"""
    def __init__(self, parent, cliptext):
        QWidget.__init__(self, parent)
        
        self.text_editor = QTextEdit(self)
        self.text_editor.setText(cliptext)
        self.text_editor.setReadOnly(True)
        
        # Type frame
        type_layout = QHBoxLayout()
        type_label = QLabel(translate("ImportWizard", "Import as"))
        type_layout.addWidget(type_label)
        data_btn = QRadioButton(translate("ImportWizard", "data"))
        data_btn.setChecked(True)
        self._as_data = True
        type_layout.addWidget(data_btn)
        txt_btn = QRadioButton(translate("ImportWizard", "text"))
        type_layout.addWidget(txt_btn)
        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        type_layout.addItem(h_spacer)        
        type_frame = QFrame()
        type_frame.setLayout(type_layout)
        
        # Opts frame
        opts_layout = QHBoxLayout()
        trnsp_box = QCheckBox(translate("ImportWizard", "Transpose"))
        trnsp_box.setEnabled(False)
        opts_layout.addWidget(trnsp_box)
        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        opts_layout.addItem(h_spacer)
        col_label = QLabel(translate("ImportWizard", "Column separator:"))
        opts_layout.addWidget(col_label)
        self.tab_btn = QRadioButton(translate("ImportWizard", "Tab"))
        self.tab_btn.setChecked(True)
        opts_layout.addWidget(self.tab_btn)
        other_btn = QRadioButton(translate("ImportWizard", "other"))
        opts_layout.addWidget(other_btn)
        self.line_edt = QLineEdit(";")
        self.line_edt.setMaximumWidth(30)
        self.line_edt.setEnabled(False)
        self.connect(other_btn, SIGNAL("toggled(bool)"),
                     self.line_edt, SLOT("setEnabled(bool)"))
        opts_layout.addWidget(self.line_edt)
        
        opts_frame = QFrame()
        opts_frame.setLayout(opts_layout)
        
        self.connect(data_btn, SIGNAL("toggled(bool)"),
                     opts_frame, SLOT("setEnabled(bool)"))
        self.connect(data_btn, SIGNAL("toggled(bool)"),
                     self, SLOT("set_as_data(bool)"))
#        self.connect(txt_btn, SIGNAL("toggled(bool)"),
#                     self, SLOT("is_text(bool)"))

        # Final layout
        layout = QVBoxLayout()
        layout.addWidget(type_frame)
        layout.addWidget(self.text_editor)
        layout.addWidget(opts_frame)
        self.setLayout(layout)

    def _get_as_data(self):
        return self._as_data
    as_data = property(_get_as_data)
    
    def _get_col_sep(self):
        if self.tab_btn.isChecked():
            return u"\t"
        return unicode(self.line_edt.text())
    col_sep = property(_get_col_sep)

    @pyqtSignature("bool")
    def set_as_data(self, as_data):
        self._as_data = as_data
        self.emit(SIGNAL("asDataChanged(bool)"), as_data)


class PreviewTableModel(QAbstractTableModel):
    """Import wizard preview table model"""
    def __init__(self, data=[], parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self._data[0])

    def _display_data(self, index):
        return QVariant(self._data[index.row()][index.column()])
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        if role == Qt.DisplayRole:
            return self._display_data(index)
        elif role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignRight|Qt.AlignVCenter))
        return QVariant()
    
    def setData(self, index, value, role=Qt.EditRole):
        return False

    def get_data(self):
        return self._data[:][:]


class PreviewWidget(QTableView):
    """Import wizard preview widget"""
    def __init__(self, parent):
        QTableView.__init__(self, parent)
        self._model = None

    def _shape_text(self, text, colsep=u"\t", rowsep=u"\n"):
        """Decode the shape of the given text"""
        assert colsep != rowsep
        out = []
        textRows = map(None, text.split(rowsep))
        for row in textRows:
            if row.isEmpty():
                continue
            line = QString(row).split(colsep)
            line = map(lambda x: try_to_eval(unicode(x)), line)
            out.append(line)
        return out
    
    def get_data(self):
        """xxx"""
        if self._model is None:
            return None
        return self._model.get_data()

    def process_data(self, cliptext, colsep=u"\t", rowsep=u"\n"):
        """xxx"""
        data = self._shape_text(cliptext, colsep, rowsep)
        self._model = PreviewTableModel(data)
        self.setModel(self._model)


class ImportWizard(QDialog):
    """Text data import wizard"""
    def __init__(self, parent, cliptext,
                 title=None, icon=None, contents_title=None, varname=None):
        QDialog.__init__(self, parent)
        
        if title is None:
            title = translate("ImportWizard", "Import wizard")
        self.setWindowTitle(title)
        if icon is None:
            self.setWindowIcon(get_icon("fileimport.png"))
        if contents_title is None:
            contents_title = translate("ImportWizard", "Raw text")
        
        if varname is None:
            varname = translate("ImportWizard", "variable_name")
        
        self.var_name, self.clip_data = None, None
        
        # Setting GUI
        self.tab_widget = QTabWidget(self)
        self.text_widget = ContentsWidget(self, cliptext)
        self.table_widget = PreviewWidget(self)
        
        self.tab_widget.addTab(self.text_widget, translate("ImportWizard",
                                                           "text"))
        self.tab_widget.setTabText(0, contents_title)
        self.tab_widget.addTab(self.table_widget, translate("ImportWizard",
                                                            "table"))
        self.tab_widget.setTabText(1, translate("ImportWizard", "Preview"))
        self.tab_widget.setTabEnabled(1, False)
        
        name_layout = QHBoxLayout()
        name_h_spacer = QSpacerItem(40, 20, 
                                    QSizePolicy.Expanding, QSizePolicy.Minimum)
        name_layout.addItem(name_h_spacer)
        
        name_label = QLabel(translate("ImportWizard", "Name"))
        name_layout.addWidget(name_label)
        self.name_edt = QLineEdit()
        self.name_edt.setMaximumWidth(100)
        self.name_edt.setText(varname)
        name_layout.addWidget(self.name_edt)
        
        btns_layout = QHBoxLayout()
        cancel_btn = QPushButton(translate("ImportWizard", "Cancel"))
        btns_layout.addWidget(cancel_btn)
        self.connect(cancel_btn, SIGNAL("clicked()"), self, SLOT("reject()"))
        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        btns_layout.addItem(h_spacer)
        self.back_btn = QPushButton(translate("ImportWizard", "Previous"))
        self.back_btn.setEnabled(False)
        btns_layout.addWidget(self.back_btn)
        self.connect(self.back_btn, SIGNAL("clicked()"),
                     ft_partial(self._set_step, step=-1))
        self.fwd_btn = QPushButton(translate("ImportWizard", "Next"))
        btns_layout.addWidget(self.fwd_btn)
        self.connect(self.fwd_btn, SIGNAL("clicked()"),
                     ft_partial(self._set_step, step=1))
        self.done_btn = QPushButton(translate("ImportWizard", "Done"))
        btns_layout.addWidget(self.done_btn)
        self.connect(self.done_btn, SIGNAL("clicked()"),
                     self, SLOT("process()"))
        
        self.connect(self.text_widget, SIGNAL("asDataChanged(bool)"),
                     self.fwd_btn, SLOT("setEnabled(bool)"))
        
        layout = QVBoxLayout()
        layout.addLayout(name_layout)
        layout.addWidget(self.tab_widget)
        layout.addLayout(btns_layout)
        self.setLayout(layout)

    def _focus_tab(self, tab_idx):
        """xxx"""
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, False)
        self.tab_widget.setTabEnabled(tab_idx, True)
        self.tab_widget.setCurrentIndex(tab_idx)
        
    def _set_step(self, step):
        """xxx"""
        new_tab = self.tab_widget.currentIndex() + step
        assert new_tab < self.tab_widget.count() and new_tab >= 0
        self._focus_tab(new_tab)
        self.fwd_btn.setEnabled(True)
        self.back_btn.setEnabled(True)
        if new_tab == self.tab_widget.count()-1:
            colsep = self.text_widget.col_sep
            self.table_widget.process_data(self._get_plain_text(), colsep)
            self.fwd_btn.setEnabled(False)
        elif new_tab == 0:
            self.back_btn.setEnabled(False)
    
    def get_data(self):
        """Return processed data"""
        return self.var_name, self.clip_data

    def _simplify_shape(self, alist, rec=0):
        """Reduce the alist dimension if needed"""
        if rec != 0:
            if len(alist) == 1:
                return alist[-1]
            return alist
        if len(alist) == 1:
            return self._simplify_shape(alist[-1], 1)
        return map(lambda al: self._simplify_shape(al, 1), alist)

    def _get_table_data(self):
        """xxx"""
        data = self.table_widget.get_data()
        return self._simplify_shape(data)

    def _get_plain_text(self):
        """xxx"""
        return self.text_widget.text_editor.toPlainText()

    @pyqtSignature("")
    def process(self):
        """Process the data from clipboard"""
        self.var_name = unicode(self.name_edt.text())
        if self.text_widget.as_data:
            self.clip_data = self._get_table_data()
        else:
            self.clip_data = unicode(self._get_plain_text())
        self.accept()


def test(text):
    """Test"""
    from PyQt4.QtGui import QApplication
    if QApplication.startingUp():
        QApplication([])
    dialog = ImportWizard(None, text)
    if dialog.exec_():
        return dialog.get_data()


if __name__ == "__main__":
    print test(QString(u"17/11/1976\t1.34\n14/05/09\t3.14"))
