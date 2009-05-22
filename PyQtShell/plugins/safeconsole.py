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

"""Console widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtCore import Qt, SIGNAL

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF, get_font, get_icon
from PyQtShell.qthelpers import create_toolbutton
from PyQtShell.widgets import Tabs
from PyQtShell.widgets.safeshell import SafeShell
from PyQtShell.widgets.shellhelpers import get_error_match
from PyQtShell.widgets.findreplace import FindReplace
from PyQtShell.plugins import PluginWidget


class SafeConsole(PluginWidget):
    """
    Console widget
    """
    ID = 'external_shell'
    location = Qt.RightDockWidgetArea
    def __init__(self, parent):
        PluginWidget.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, [])
        self.connect(self.tabwidget, SIGNAL("close_tab(int)"),
                     self.tabwidget.removeTab)
        self.close_button = create_toolbutton(self.tabwidget,
                                          icon=get_icon("fileclose.png"),
                                          callback=self.close,
                                          tip=self.tr("Close current console"))
        self.tabwidget.setCornerWidget(self.close_button)
        layout.addWidget(self.tabwidget)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)

    def close(self, index=-1):
        if not self.tabwidget.count():
            return
        if index == -1:
            index = self.tabwidget.currentIndex()
        self.tabwidget.widget(index).close()
        self.tabwidget.removeTab(index)
        
    def start(self, fname, ask_for_arguments, interact, debug):
        """Start new console"""
        shell = SafeShell(self, fname, ask_for_arguments, interact, debug)
        shell.shell.set_font( get_font(self.ID) )
        shell.shell.set_wrap_mode( CONF.get(self.ID, 'wrap') )
        self.connect(shell.shell, SIGNAL("go_to_error(QString)"),
                     lambda qstr: self.go_to_error(unicode(qstr)))
        self.find_widget.set_editor(shell.shell)
        index = self.tabwidget.addTab(shell, osp.basename(fname))
        self.connect(shell, SIGNAL("finished()"),
                     lambda i=index: self.tabwidget.setTabIcon(i,
                                                  get_icon('terminated.png')))
        self.tabwidget.setToolTip(fname)
        self.tabwidget.setTabIcon(index, get_icon('execute.png'))
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget:
            self.dockwidget.setVisible(True)
        
        # Give focus to console
        shell.shell.setFocus()
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('External console')
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
    def refresh(self):
        pass
    
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(text)
        if match:
            fname, lnb = match.groups()
            self.emit(SIGNAL("edit_goto(QString,int)"),
                      osp.abspath(fname), int(lnb))
