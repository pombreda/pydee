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

import sys

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt4.QtCore import SIGNAL, Qt

# Local imports
from pydeelib.widgets.externalshell.monitor import (monitor_set_value,
                                                    monitor_get_value)
from pydeelib.widgets.dicteditor import RemoteDictEditorTableView
from pydeelib.qthelpers import create_toolbutton
from pydeelib.config import get_icon, CONF, get_font


#TODO: Add a context-menu to customize wsfilter, ...
#      --> store these settings elsewhere?
#          (Workspace's settings are currently used)
class GlobalsExplorer(QWidget):
    ID = 'workspace'
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
                                           triggered=self.refresh)
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
                                            set_value_func=self.set_value)
        self.editor.setFont(get_font(self.ID))
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.editor)
        self.setLayout(vlayout)
        
    def get_value(self, name):
        return monitor_get_value(self.shell.monitor_socket, name)
        
    def set_value(self, name, value):
        monitor_set_value(self.shell.monitor_socket, name, value)
        self.emit(SIGNAL('refresh()'))
        
    def set_data(self, data):
        self.editor.set_data(data)
        self.editor.adjust_columns()
        
    def collapse(self):
        self.emit(SIGNAL('collapse()'))
        
    def refresh(self):
        self.emit(SIGNAL('refresh()'))
        
