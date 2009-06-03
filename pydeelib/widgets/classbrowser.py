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

from PyQt4.QtGui import QTreeWidget, QTreeWidgetItem, QMenu
from PyQt4.QtCore import SIGNAL, Qt

# Local imports
from pydeelib.config import get_icon
from pydeelib.qthelpers import add_actions, translate, create_action

#TODO: Add "Collapse all" and "Expand all" buttons
class ClassBrowser(QTreeWidget):
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)
        self.fname = None
        self.classes = None
        self.lines = None
        self.setItemsExpandable(True)
        self.setColumnCount(1)
        self.setHeaderLabels([translate("ClassBrowser", "Class and function browser")])
        self.connect(self, SIGNAL('itemActivated(QTreeWidgetItem*,int)'),
                     self.activated)
        # Setup context menu
        self.menu = QMenu(self)
        self.common_actions = self.setup_common_actions()
                     
    def setup_common_actions(self):
        """Setup context menu common actions"""
        collapse_act = create_action(self,
                    text=self.tr('Collapse all'),
                    icon=get_icon('collapse.png'),
                    triggered=self.collapseAll)
        expand_act = create_action(self,
                    text=self.tr('Expand all'),
                    icon=get_icon('expand.png'),
                    triggered=self.expandAll)
        return [collapse_act, expand_act]
                     
    def update_menu(self):
        self.menu.clear()
        actions = []
        # Right here: add other actions if necessary (in the future)
        if actions:
            actions.append(None)
        actions += self.common_actions
        add_actions(self.menu, actions)
                     
    def contextMenuEvent(self, event):
        """Override Qt method"""
        self.update_menu()
        self.menu.popup(event.globalPos())
        
    def setup(self, fname):
        """Setup class browser"""
        assert osp.isfile(fname)
        self.fname = osp.abspath(fname)
        self.refresh()

    def get_data(self):
        return (self.fname, self.classes, self.lines, self.class_names)

    def set_data(self, data):
        self.fname, self.classes, self.lines, self.class_names = data
        self.clear()
        self.populate_classes(self.class_names)
        self.expandAll()

    def refresh(self):
        self.clear()
        self.class_names = self.list_classes()
        self.populate_classes(self.class_names)
        self.resizeColumnToContents(0)
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