#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
formlayout
==========

Module creating PyQt4 form dialogs/layouts to edit various type of parameters

Copyright © 2009 Pierre Raybaut
This software is licensed under the terms of the GNU General Public
License version 2 as published by the Free Software Foundation.
"""

__version__ = '1.0.1'

DEBUG = False

import sys
STDERR = sys.stderr

try:
    from PyQt4.QtGui import QFormLayoutx
except ImportError:
    raise ImportError, "Warning: PyQt4 version is outdated (formlayout requires >v4.3)"

from PyQt4.QtGui import (QWidget, QLineEdit, QComboBox, QLabel, QSpinBox,
                         QIcon, QDialogButtonBox, QHBoxLayout, QVBoxLayout,
                         QDialog, QColor, QPushButton, QCheckBox, QColorDialog,
                         QPixmap, QTabWidget, QApplication, QStackedWidget)
from PyQt4.QtCore import (Qt, SIGNAL, SLOT, QSize, QString,
                          pyqtSignature, pyqtProperty)


# Create a QApplication instance if the module is used directly from interpreter
if QApplication.startingUp():
    QApplication([])


class ColorButton(QPushButton):
    """
    Derived from ColorButton(QToolButton):
    Copyright (C) 2007 David Boddie <david@boddie.org.uk>
    Licensed under GNU GPL v2
    """
    __pyqtSignals__ = ("colorChanged(QColor)",)
    
    def __init__(self, parent=None):
        QPushButton.__init__(self, parent)
        self.setFixedSize(20, 20)
        self.setIconSize(QSize(12, 12))
        self.connect(self, SIGNAL("clicked()"), self.chooseColor)
        self._color = QColor()
    
    def chooseColor(self):
        rgba, valid = QColorDialog.getRgba(self._color.rgba(),
                                           self.parentWidget())
        if valid:
            color = QColor.fromRgba(rgba)
            self.setColor(color)
    
    def color(self):
        return self._color
    
    @pyqtSignature("QColor")
    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.emit(SIGNAL("colorChanged(QColor)"), self._color)
            pixmap = QPixmap(self.iconSize())
            pixmap.fill(color)
            self.setIcon(QIcon(pixmap))
    
    color = pyqtProperty("QColor", color, setColor)


def text_to_qcolor(text):
    """Create a QColor from specified string
    Avoid a warning from Qt when an invalid QColor is instantiated"""
    color = QColor()
    if isinstance(text, QString):
        text = str(text)
    if not isinstance(text, (unicode, str)):
        return color
    if text.startswith('#') and len(text)==7:
        correct = '#0123456789abcdef'
        for char in text:
            if char.lower() not in correct:
                return color
    elif text not in list(QColor.colorNames()):
        return color
    color.setNamedColor(text)
    return color

class ColorLayout(QHBoxLayout):
    """Color-specialized QLineEdit layout"""
    def __init__(self, color, parent=None):
        QHBoxLayout.__init__(self)
        assert isinstance(color, QColor)
        self.lineedit = QLineEdit(color.name(), parent)
        self.connect(self.lineedit, SIGNAL("textChanged(QString)"),
                     self.update_color)
        self.addWidget(self.lineedit)
        self.colorbtn = ColorButton(parent)
        self.colorbtn.color = color
        self.connect(self.colorbtn, SIGNAL("colorChanged(QColor)"),
                     self.update_text)
        self.addWidget(self.colorbtn)

    def update_color(self, text):
        color = text_to_qcolor(text)
        if color.isValid():
            self.colorbtn.color = color

    def update_text(self, color):
        self.lineedit.setText(color.name())
        
    def text(self):
        return self.lineedit.text()


class FormWidget(QWidget):
    def __init__(self, data, comment="", parent=None):
        super(FormWidget, self).__init__(parent)
        from copy import deepcopy
        self.data = deepcopy(data)
        self.widgets = []
        self.formlayout = QFormLayout(self)
        if comment:
            self.formlayout.addRow(QLabel(comment))
            self.formlayout.addRow(QLabel(" "))
        if DEBUG:
            print "\n"+("*"*80)
            print "DATA:", self.data
            print "*"*80
            print "COMMENT:", comment
            print "*"*80
        self.setup()

    def setup(self):
        for label, value in self.data:
            if DEBUG:
                print "value:", value
            if label is None and value is None:
                # Separator: (None, None)
                self.formlayout.addRow(QLabel(" "), QLabel(" "))
                self.widgets.append(None)
                continue
            elif label is None:
                # Comment
                self.formlayout.addRow(QLabel(value))
                self.widgets.append(None)
                continue
            elif text_to_qcolor(value).isValid():
                field = ColorLayout(QColor(value), self)
            elif isinstance(value, (str, unicode)):
                field = QLineEdit(value, self)
            elif isinstance(value, (list, tuple)):
                selindex = value.pop(0)
                field = QComboBox(self)
                if isinstance(value[0], (list, tuple)):
                    keys = [ key for key, _val in value ]
                    value = [ val for _key, val in value ]
                else:
                    keys = value
                field.addItems(value)
                if selindex in value:
                    selindex = value.index(selindex)
                elif selindex in keys:
                    selindex = keys.index(selindex)
                elif not isinstance(selindex, int):
                    print >> STDERR, "Warning: '%s' index is invalid (label: %s, value: %s)" % (selindex, label, value)
                    selindex = 0
                field.setCurrentIndex(selindex)
            elif isinstance(value, bool):
                field = QCheckBox(self)
                field.setCheckState(Qt.Checked if value else Qt.Unchecked)
            elif isinstance(value, float):
                field = QLineEdit(repr(value), self)
            elif isinstance(value, int):
                field = QSpinBox(self)
                field.setValue(value)
                field.setMaximum(1e9)
            else:
                field = QLineEdit(repr(value), self)
            self.formlayout.addRow(label, field)
            self.widgets.append(field)
            
    def get(self):
        valuelist = []
        for index, (label, value) in enumerate(self.data):
            field = self.widgets[index]
            if label is None:
                # Separator / Comment
                continue
            elif isinstance(value, (str, unicode)):
                value = unicode(field.text())
            elif isinstance(value, (list, tuple)):
                index = int(field.currentIndex())
                if isinstance(value[0], (list, tuple)):
                    value = value[index][0]
                else:
                    value = value[index]
            elif isinstance(value, bool):
                value = field.checkState() == Qt.Checked
            elif isinstance(value, float):
                value = float(field.text())
            elif isinstance(value, int):
                value = int(field.value())
            else:
                value = eval(str(field.text()))
            valuelist.append(value)
        return valuelist


class FormComboWidget(QWidget):
    def __init__(self, datalist, comment="", parent=None):
        super(FormComboWidget, self).__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.combobox = QComboBox()
        layout.addWidget(self.combobox)
        
        self.stackwidget = QStackedWidget(self)
        layout.addWidget(self.stackwidget)
        self.connect(self.combobox, SIGNAL("currentIndexChanged(int)"),
                     self.stackwidget, SLOT("setCurrentIndex(int)"))
        
        self.widgetlist = []
        for data, title, comment in datalist:
            self.combobox.addItem(title)
            widget = FormWidget(data, comment=comment, parent=self)
            self.stackwidget.addWidget(widget)
            self.widgetlist.append(widget)

    def get(self):
        return [ widget.get() for widget in self.widgetlist]
        


class FormTabWidget(QWidget):
    def __init__(self, datalist, comment="", parent=None):
        super(FormTabWidget, self).__init__(parent)
        layout = QVBoxLayout()
        self.tabwidget = QTabWidget()
        layout.addWidget(self.tabwidget)
        self.setLayout(layout)
        self.widgetlist = []
        for data, title, comment in datalist:
            if len(data[0])==3:
                widget = FormComboWidget(data, comment=comment, parent=self)
            else:
                widget = FormWidget(data, comment=comment, parent=self)
            index = self.tabwidget.addTab(widget, title)
            self.tabwidget.setTabToolTip(index, comment)
            self.widgetlist.append(widget)
            
    def get(self):
        return [ widget.get() for widget in self.widgetlist]


class FormDialog(QDialog):
    """Form Dialog"""
    def __init__(self, data, title="", comment="",
                 icon=None, parent=None):
        super(FormDialog, self).__init__(parent, Qt.Window)
        
        # Form
        if isinstance(data[0][0], (list, tuple)):
            self.formwidget = FormTabWidget(data, comment=comment, parent=self)
        elif len(data[0])==3:
            self.formwidget = FormComboWidget(data, comment=comment, parent=self)
        else:
            self.formwidget = FormWidget(data, comment=comment, parent=self)
        layout = QVBoxLayout()
        layout.addWidget(self.formwidget)
        
        # Button box
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        layout.addWidget(bbox)

        self.setLayout(layout)
        
        self.setWindowTitle(title)
        if isinstance(icon, QIcon):
            self.setWindowIcon(icon)
        
    def accept(self):
        self.data = self.formwidget.get()
        QDialog.accept(self)
        
    def reject(self):
        self.data = None
        QDialog.reject(self)
        
    def get(self):
        """Return form result"""
        return self.data


def fedit(data, title="", comment="", icon=None, parent=None):
    """
    Create form dialog and return result
    (if Cancel button is pressed, return None)
    
    data: datalist, datagroup
    
    datalist: list/tuple of (field_name, field_value)
    datagroup: list/tuple of (datalist *or* datagroup, title, comment)
    
    -> one field for each member of a datalist
    -> one tab for each member of a top-level datagroup
    -> one page (of a multipage widget, each page can be selected with a combo
       box) for each member of a datagroup inside a datagroup
       
    Supported types for field_value:
      - int, float, str, unicode, bool
      - colors: in Qt-compatible text form, i.e. in hex format or name (red,...)
                (automatically detected from a string)
      - list/tuple:
          * the first element will be the selected index (or value)
          * the other elements can be couples (key, value) or only values
    """
    dialog = FormDialog(data, title, comment, icon, parent)
    if dialog.exec_():
        return dialog.get()



if __name__ == "__main__":
    
    def create_datalist_example():
        return [('str', 'this is a string'),
                ('list', [0, '1', '3', '4']),
                ('list2', ['--', ('none', 'None'), ('--', 'Dashed'),
                           ('-.', 'DashDot'), ('-', 'Solid'),
                           ('steps', 'Steps'), (':', 'Dotted')]),
                ('float', 1.2),
                (None, 'Other:'),
                ('int', 12),
                ('color', '#123409'),
                ('bool', True),
                ]
        
    def create_datagroup_example():
        datalist = create_datalist_example()
        return ((datalist, "Category 1", "Category 1 comment"),
                (datalist, "Category 2", "Category 2 comment"),
                (datalist, "Category 3", "Category 3 comment"))
    
    #--------- datalist example
    datalist = create_datalist_example()
    print "result:", fedit(datalist, title="Example",
                           comment="This is just an <b>example</b>.")
    
    #--------- datagroup example
    datagroup = create_datagroup_example()
    print "result:", fedit(datagroup, "Global title")
        
    #--------- datagroup inside a datagroup example
    datalist = create_datalist_example()
    datagroup = create_datagroup_example()
    print "result:", fedit(((datagroup, "Title 1", "Tab 1 comment"),
                            (datalist, "Title 2", "Tab 2 comment"),
                            (datalist, "Title 3", "Tab 3 comment")),
                            "Global title")
