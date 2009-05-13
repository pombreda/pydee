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
from PyQt4.QtCore import SIGNAL

import sys, os
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF
from PyQtShell.qthelpers import (create_action, add_actions, get_filetype_icon,
                                 get_std_icon)
from PyQtShell.widgets.explorer import ExplorerWidget
from PyQtShell.plugins import PluginMixin


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
        self.common_actions = [wrap_action, hidden_action, all_action]
        
        self.connect(self, SIGNAL("open_file(QString)"), self.open)
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("Explorer")
    
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
            
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
        menu = QMenu(self)
        actions = []
        if self.currentItem() is not None:
            fname = self.get_filename()
            is_dir = osp.isdir(fname)
            ext = osp.splitext(fname)[1]
            #TODO: Action to create a new directory
            #TODO: Action to rename dir/file
            run_action = create_action(self, self.tr("Run"),
                                       icon="run.png",
                                       triggered=self.run)
            edit_action = create_action(self, self.tr("Edit"),
                                        icon="edit.png",
                                        triggered=self.clicked)
            browse_action = create_action(self, self.tr("Browse"),
                                          icon=get_std_icon("CommandLink"),
                                          triggered=self.clicked)
            open_action = create_action(self, self.tr("Open"),
                                        triggered=self.startfile)
            if ext in ('.py', '.pyw'):
                actions.append(run_action)
            if ext in CONF.get('editor', 'valid_filetypes') \
               or os.name != 'nt':
                actions.append(browse_action if is_dir else edit_action)
            else:
                actions.append(open_action)
            if is_dir and os.name == 'nt':
                # Actions specific to Windows directories
                #TODO: Action to start cmd.exe here
                actions.append( create_action(self,
                                           self.tr("Open in Windows Explorer"),
                                           icon="magnifier.png",
                                           triggered=self.startfile) )
            if actions:
                actions.append(None)
        actions += self.common_actions
        add_actions(menu, actions)
        menu.popup(event.globalPos())
        
    def open(self, fname):
        """Open filename with the appropriate application
        Redirect to the right widget (txt -> editor, ws -> workspace, ...)"""
        fname = unicode(fname)
        ext = osp.splitext(fname)[1]
        if ext in CONF.get('editor', 'valid_filetypes'):
            self.emit(SIGNAL("edit(QString)"), fname)
        elif ext == '.ws':
            self.emit(SIGNAL("open_workspace(QString)"), fname)
        else:
            self.startfile(fname)
        
    def startfile(self, fname=None):
        """Windows only: open file in the associated application"""
        if fname is None:
            fname = self.get_filename()
        emit = False
        if os.name == 'nt':
            try:
                os.startfile(fname)
            except WindowsError:
                emit = True
        else:
            emit = True
        if emit:
            self.emit(SIGNAL("edit(QString)"), fname)
        
    def run(self):
        """Run Python script"""
        self.emit(SIGNAL("run(QString)"), self.get_filename())
                
