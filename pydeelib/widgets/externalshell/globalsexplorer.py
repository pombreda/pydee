# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Globals explorer widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, pickle

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt4.QtCore import SIGNAL, Qt

# Local imports
from pydeelib.widgets.externalshell.monitor import (communicate,
                                    monitor_set_global, monitor_get_global,
                                    monitor_del_global, monitor_copy_global)
from pydeelib.widgets.dicteditor import RemoteDictEditorTableView
from pydeelib.qthelpers import create_toolbutton
from pydeelib.config import get_icon, CONF


#TODO: Add a context-menu to customize wsfilter, ...
#      --> store these settings elsewhere?
#          (Workspace's settings are currently used)
class GlobalsExplorer(QWidget):
    ID = 'external_shell'
    
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        
        self.shell = parent
        
        hlayout = QHBoxLayout()
        hlayout.setAlignment(Qt.AlignLeft)
        
        # Setup toolbar
        self.toolbar_widgets = []
        explorer_label = QLabel(self.tr("<span style=\'color: #444444\'>"
                                        "<b>Global variables explorer</b>"
                                        "</span>"))

        self.toolbar_widgets.append(explorer_label)
        hide_button = create_toolbutton(self,
                                           text=self.tr("Hide"),
                                           icon=get_icon('hide.png'),
                                           triggered=self.collapse)
        self.toolbar_widgets.append(hide_button)
        refresh_button = create_toolbutton(self,
                                           text=self.tr("Refresh"),
                                           icon=get_icon('reload.png'),
                                           triggered=self.refresh_table)
        self.toolbar_widgets.append(refresh_button)
        
        for widget in self.toolbar_widgets:
            hlayout.addWidget(widget)
        hlayout.insertStretch(1, 1)
        
        # Dict editor:
        truncate = CONF.get(self.ID, 'truncate')
        inplace = CONF.get(self.ID, 'inplace')
        minmax = CONF.get(self.ID, 'minmax')
        collvalue = CONF.get(self.ID, 'collvalue')
        self.editor = RemoteDictEditorTableView(parent, None,
                                        truncate=truncate, inplace=inplace,
                                        minmax=minmax, collvalue=collvalue,
                                        get_value_func=self.get_value,
                                        set_value_func=self.set_value,
                                        new_value_func=self.set_value,
                                        remove_values_func=self.remove_values,
                                        copy_value_func=self.copy_value)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.editor)
        self.setLayout(vlayout)
        
    def refresh_table(self):
        sock = self.shell.monitor_socket
        if sock is None:
            return
        data = communicate(sock, "__make_remote_view__(globals())")
        obj = pickle.loads(data)
        self.set_data(obj)
        
    def get_value(self, name):
        return monitor_get_global(self.shell.monitor_socket, name)
        
    def set_value(self, name, value):
        sock = self.shell.monitor_socket
        monitor_set_global(sock, name, value)
        self.refresh_table()
        
    def remove_values(self, names):
        sock = self.shell.monitor_socket
        for name in names:
            monitor_del_global(sock, name)
        self.refresh_table()
        
    def copy_value(self, orig_name, new_name):
        sock = self.shell.monitor_socket
        monitor_copy_global(sock, orig_name, new_name)
        self.refresh_table()
        
    def set_data(self, data):
        self.editor.set_data(data)
        self.editor.adjust_columns()
        
    def collapse(self):
        self.emit(SIGNAL('collapse()'))
        
