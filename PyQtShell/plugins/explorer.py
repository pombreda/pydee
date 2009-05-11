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

"""Files and Directories Explorer"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QMenu

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF
from PyQtShell.qthelpers import create_action, add_actions, get_filetype_icon
from PyQtShell.widgets.explorer import ExplorerWidget
from PyQtShell.plugins import PluginMixin


#TODO: middle-click runs selected .py/.pyw file ??
#TODO: add context menu entry to run selected .py/.pyw file
#FIXME: bugs after Python interpreter has been restarted
#       (it will certainly be fixed when restart will be nicely implemented)
class Explorer(ExplorerWidget, PluginMixin):
    """File and Directories Explorer DockWidget"""
    ID = 'explorer'
    def __init__(self, parent=None, path=None):
        PluginMixin.__init__(self, parent)
        valid_types = CONF.get(self.ID, 'valid_filetypes')
        show_hidden = CONF.get(self.ID, 'show_hidden_files')
        show_all = CONF.get(self.ID, 'show_all_files')
        
        ExplorerWidget.__init__(self, parent, path, get_filetype_icon,
                                valid_types, show_hidden, show_all)
        
        self.menu = QMenu(self)

        #---- Setup context menu
        # Wrap
        wrap_action = create_action(self, self.tr("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap = CONF.get(self.ID, 'wrap')
        wrap_action.setChecked(wrap)
        self.toggle_wrap_mode(wrap)
        # Show hidden files
        hidden_action = create_action(self, self.tr("Show hidden files"),
                                      toggled=self.toggle_hidden)
        hidden_action.setChecked(show_hidden)
        # Show all files
        all_action = create_action(self, self.tr("Show all files"),
                                   toggled=self.toggle_all)
        all_action.setChecked(show_all)
        add_actions(self.menu, [wrap_action, hidden_action, all_action])
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("Explorer")
    
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
#remove this if it's safe to let "self.refresh()" in the base class method
#    def visibility_changed(self, enable):
#        """Reimplement PydeeDockWidget method"""
#        PydeeDockWidget.visibility_changed(self, enable)
#        self.refresh()
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        CONF.set(self.ID, 'wrap', checked)
        self.setWrapping(checked)
        
    def toggle_hidden(self, checked):
        """Toggle hidden files mode"""
        CONF.set(self.ID, 'show_hidden', checked)
        self.show_hidden = checked
        self.refresh()
        
    def toggle_all(self, checked):
        """Toggle all files mode"""
        CONF.set(self.ID, 'show_all', checked)
        self.show_all = checked
        self.refresh()
        
    def contextMenuEvent(self, event):
        """Override Qt method"""
        if self.menu:
            self.menu.popup(event.globalPos())
