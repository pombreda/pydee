# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
Class browser widget
"""

import os.path as osp
import pyclbr, sys

from PyQt4.QtGui import QTreeWidget, QTreeWidgetItem
from PyQt4.QtCore import SIGNAL

# Local imports
from pydeelib.config import get_icon


class ClassBrowser(QTreeWidget):
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)
        self.fname = None
        self.classes = None
        self.lines = None
        self.setItemsExpandable(True)
        self.setColumnCount(1)
        self.setHeaderLabels([self.tr("Class browser")])
        self.connect(self, SIGNAL('itemActivated(QTreeWidgetItem*,int)'),
                     self.activated)
        
    def setup(self, fname):
        """Setup class browser"""
        assert osp.isfile(fname)
        self.fname = osp.abspath(fname)
        self.refresh()

    def refresh(self):
        self.clear()
        self.class_names = self.list_classes()
        self.populate_classes(self.class_names)
        self.resizeColumnToContents(0)
        self.expandAll()

    def get_data(self):
        return (self.fname, self.classes, self.lines, self.class_names)

    def set_data(self, data):
        self.fname, self.classes, self.lines, self.class_names = data
        self.clear()
        self.populate_classes(self.class_names)
        self.expandAll()

    def activated(self, item):
        """Double-click or click event"""
        self.emit(SIGNAL('go_to_line(int)'), self.lines[item])
        
    def list_classes(self):
        """Analyze file and return classes and methods"""
        pyclbr._modules.clear()
        path, relpath = osp.split(self.fname)
        basename, _ext = osp.splitext(relpath)
        try:
            contents = pyclbr.readmodule_ex(basename, [path] + sys.path)
        except ImportError:
            return []
        items = []
        self.classes = {}
        for name, klass in contents.items():
            if klass.module == basename:
                if hasattr(klass, 'super') and klass.super:
                    supers = []
                    for sup in klass.super:
                        if type(sup) is type(''):
                            sname = sup
                        else:
                            sname = sup.name
                            if sup.module != klass.module:
                                sname = "%s.%s" % (sup.module, sname)
                        supers.append(sname)
                    name = name + "(%s)" % ", ".join(supers)
                items.append((klass.lineno, name))
                self.classes[name] = klass
        items.sort()
        return items
        
    def populate_classes(self, class_names):
        """Populate classes"""
        self.lines = {}
        for lineno, c_name in class_names:
            item = QTreeWidgetItem(self, [c_name])
            self.lines[item] = lineno
            if isinstance(self.classes[c_name], pyclbr.Function):
                item.setIcon(0, get_icon('function.png'))
            else:
                item.setIcon(0, get_icon('class.png'))
            if self.methods_exist(c_name):
                self.populate_methods(item, c_name)
            
    def methods_exist(self, c_name):
        """Is there any method?"""
        return hasattr(self.classes[c_name], 'methods')
                
    def list_methods(self, c_name):
        """List class c_name methods"""
        items = []
        for name, lineno in self.classes[c_name].methods.items():
            items.append((lineno, name))
        items.sort()
        return items
                
    def populate_methods(self, parent, c_name):
        """Populate methods"""
        for lineno, m_name in self.list_methods(c_name):
            item = QTreeWidgetItem(parent, [m_name])
            self.lines[item] = lineno
            if m_name.startswith('__'):
                item.setIcon(0, get_icon('private2.png'))
            elif m_name.startswith('_'):
                item.setIcon(0, get_icon('private1.png'))
            else:
                item.setIcon(0, get_icon('method.png'))
            

if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    widget = ClassBrowser(None)
    widget.setup("dicteditor.py")
    widget.show()
    
    sys.exit(app.exec_())