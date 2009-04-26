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

"""Workspace widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QFileDialog, QShortcut, QKeySequence, QMessageBox
from PyQt4.QtCore import Qt

import os, sys, cPickle
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF, get_conf_path, str2type
from PyQtShell.qthelpers import create_action, get_std_icon

# Package local imports
from PyQtShell.widgets.base import WidgetMixin
from PyQtShell.widgets.dicteditor import DictEditorTableView


class NoValue(object):
    """Dummy class used by wsfilter"""
    pass

def wsfilter(obj_in, rec=0):
    """Keep only objects that can be saved"""
    filters = tuple(str2type(CONF.get('workspace', 'filters')))
    exclude_private = CONF.get('workspace', 'exclude_private')
    exclude_upper = CONF.get('workspace', 'exclude_upper')
    if rec == 2:
        return NoValue
    obj_out = obj_in
    if isinstance(obj_in, dict):
        obj_out = {}
        for key in obj_in:
            value = obj_in[key]
            if rec == 0:
                # Excluded references for namespace to be saved without error
                if key in CONF.get('workspace', 'excluded'):
                    continue
                if exclude_private and key.startswith('_'):
                    continue
                if exclude_upper and key[0].isupper():
                    continue
                if isinstance(value, filters):
                    value = wsfilter(value, rec+1)
                    if value is not NoValue:
                        obj_out[key] = value
            elif isinstance(value, filters) and isinstance(key, filters):
                # Just for rec == 1
                obj_out[key] = value
            else:
                return NoValue
#    elif isinstance(obj_in, (list, tuple)):
#        obj_out = []
#        for value in obj_in:
#            if isinstance(value, filters):
#                value = wsfilter(value, rec+1)
#                if value is not NoValue:
#                    obj_out.append(value)
#        if isinstance(obj_in, tuple):
#            obj_out = tuple(obj_out)
    return obj_out            


class Workspace(DictEditorTableView, WidgetMixin):
    """
    Workspace widget (namespace explorer)
    """
    ID = 'workspace'
    file_path = get_conf_path('.temp.ws')
    def __init__(self, parent):
        self.interpreter = None
        self.namespace = None
        self.filename = None
        DictEditorTableView.__init__(self, parent, None)
        WidgetMixin.__init__(self, parent)
        self.load_temp_namespace()
        QShortcut(QKeySequence("Ctrl+E"), self, self.remove_item)
        
    def get_name(self):
        """Return widget name"""
        return self.tr('Workspace')
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.LeftDockWidgetArea)
        
    def set_interpreter(self, interpreter):
        """Bind to interpreter"""
        self.interpreter = interpreter
        self.refresh()
        
    def get_namespace(self):
        """Return filtered namespace"""
        return wsfilter(self.namespace)
    
    def _clear_namespace(self):
        """Clear namespace"""
        keys = self.get_namespace().keys()
        for key in keys:
            self.namespace.pop(key)
        self.refresh()
    
    def _update_dock_title(self):
        """Set the dockwidget title"""
        if hasattr(self, "dockwidget") and self.dockwidget:
            title = self.get_name() + ' - ' + osp.basename(self.filename)
            self.dockwidget.setWindowTitle(title)
    
    def clear(self):
        """Ask to clear workspace"""
        answer = QMessageBox.question(self, self.tr("Clear workspace"),
                    self.tr("Do you want to clear all data from workspace?"),
                    QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self._clear_namespace()

    def refresh(self):
        """Refresh widget"""
        if CONF.get(self.ID, 'autorefresh'):
            self.refresh_editor()
        self._update_dock_title()
        
    def refresh_editor(self):
        """Refresh DictEditor"""
        if self.interpreter is not None:
            self.namespace = self.interpreter.namespace
        self.set_filter( wsfilter )
        self.set_data( self.namespace )
        self.adjust_columns()
        
    def set_actions(self):
        """Setup actions"""
        new_action = create_action(self, self.tr("New..."), None,
            'ws_new.png', self.tr("Create a new workspace"),
            triggered = self.new)        
        open_action = create_action(self, self.tr("Open..."), None,
            'ws_open.png', self.tr("Open a workspace"), triggered = self.load)
        save_action = create_action(self, self.tr("Save"), None, 'ws_save.png',
            self.tr("Save current workspace"), triggered = self.save)
        save_as_action = create_action(self, self.tr("Save as..."), None,
            'ws_save_as.png',  self.tr("Save current workspace as..."),
            triggered = self.save_as)
        exclude_private_action = create_action(self,
            self.tr("Exclude private references"),
            tip=self.tr("Exclude references which name starts with an underscore"),
            toggled=self.toggle_exclude_private)
        exclude_private_action.setChecked( CONF.get(self.ID, 'exclude_private') )
        exclude_upper_action = create_action(self,
            self.tr("Exclude capitalized references"),
            tip=self.tr("Exclude references which name starts with an upper-case character"),
            toggled=self.toggle_exclude_upper)
        exclude_upper_action.setChecked( CONF.get(self.ID, 'exclude_upper') )

        refresh_action = create_action(self, self.tr("Refresh"), None,
            'ws_refresh.png', self.tr("Refresh workspace"),
            triggered = self.refresh_editor)
        
        autorefresh_action = create_action(self, self.tr("Auto refresh"),
                                           toggled=self.toggle_autorefresh)
        autorefresh_action.setChecked( CONF.get(self.ID, 'autorefresh') )
        
        autosave_action = create_action(self, self.tr("Auto save"),
            toggled=self.toggle_autosave,
            tip=self.tr("Automatically save workspace in a temporary file when quitting"))
        autosave_action.setChecked( CONF.get(self.ID, 'autosave') )
        
        clear_action = create_action(self, self.tr("Clear workspace"),
                                 icon=get_std_icon("TrashIcon"),
                                 tip=self.tr("Clear all data from workspace"),
                                 triggered=self.clear)
        
        menu_actions = (refresh_action, autorefresh_action, None,
                        self.fulldisplay_action,
                        self.sort_action, self.inplace_action, None,
                        exclude_private_action, exclude_upper_action, None,
                        new_action, open_action,
                        save_action, save_as_action, autosave_action,
                        None, clear_action)
        toolbar_actions = (refresh_action, open_action, save_action)
        return (menu_actions, toolbar_actions)
    
    def toggle_autorefresh(self, checked):
        """Toggle autorefresh mode"""
        CONF.set(self.ID, 'autorefresh', checked)
        self.refresh()
        
    def toggle_autosave(self, checked):
        """Toggle autosave mode"""
        CONF.set(self.ID, 'autosave', checked)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        if CONF.get(self.ID, 'autosave'):
            # Saving workspace
            self.save()
        else:
            workspace = self.get_namespace()
            if workspace is None:
                return True
            refnb = len(workspace)
            if refnb > 1:
                srefnb = str(refnb)
                s_or_not = 's'
                it_or_them = self.tr('them')
            else:
                srefnb = self.tr('one')
                s_or_not = ''
                it_or_them = self.tr('it')
            if refnb > 0:
                buttons = QMessageBox.Yes | QMessageBox.No
                if cancelable:
                    buttons = buttons | QMessageBox.Cancel
                answer = QMessageBox.question(self, self.get_name(),
                   self.tr("Workspace is currently keeping reference to %1 object%2.\n\nDo you want to save %3?") \
                   .arg(srefnb).arg(s_or_not).arg(it_or_them), buttons)
                if answer == QMessageBox.Yes:
                    # Saving workspace
                    self.save()
                elif answer == QMessageBox.Cancel:
                    return False
                elif osp.isfile(self.file_path):
                    # Removing last saved workspace
                    os.remove(self.file_path)
        return True
    
    def load_temp_namespace(self):
        """Attempt to load last session namespace"""
        self.filename = self.file_path
        if osp.isfile(self.filename):
            self.load(self.filename)
        else:
            self.namespace = None

    def load(self, filename=None):
        """Attempt to load namespace"""
        title = self.tr("Open workspace")
        if filename is None:
            self.main.console.shell.restore_stds()
            basedir = osp.dirname(self.filename)
            filename = QFileDialog.getOpenFileName(self,
                          title, basedir,
                          self.tr("Workspaces")+" (*.ws)")
            self.main.console.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
            else:
                return
        self.filename = filename
        try:
            if self.main:
                self.main.set_splash(self.tr("Loading workspace..."))
            namespace = cPickle.load(file(self.filename))
            if self.namespace is None:
                self.namespace = namespace
            else:
                for key in namespace:
                    self.interpreter.namespace[key] = namespace[key]
        except (EOFError, ValueError):
            os.remove(self.filename)
            QMessageBox.critical(self, title,
                self.tr("Unable to load the following workspace:") + '\n' + \
                self.filename)
        self.refresh()
        if self.main:
            self.main.splash.hide()

    def new(self):
        """Attempt to close the current workspace and create a new one"""
        answer = QMessageBox.question(self, self.tr("Save workspace"),
            self.tr("Do you want to save current workspace "
                    "before creating a new one?"),
            QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.save()
        self._clear_namespace()
        self.main.console.shell.restore_stds()
        filename = QFileDialog.getSaveFileName(self,
                        self.tr("New workspace"), self.filename,
                        self.tr("Workspaces")+" (*.ws)")
        self.main.console.shell.redirect_stds()
        if filename:
            self.filename = unicode(filename)
        else:
            self.load_temp_namespace()
        self.save()
    
    def save_as(self):
        """Save current workspace as"""
        self.main.console.shell.restore_stds()
        filename = QFileDialog.getSaveFileName(self,
                      self.tr("Save workspace"), self.filename,
                      self.tr("Workspaces")+" (*.ws)")
        self.main.console.shell.redirect_stds()
        if filename:
            self.filename = unicode(filename)
        else:
            return False
        self.save()
    
    def save(self):
        """Save current workspace"""
        if self.filename is None:
            return self.save_as()
        if self.main:
            self.main.set_splash(self.tr("Saving workspace..."))
        try:
            cPickle.dump(self.get_namespace(), file(self.filename, 'w'))
        except RuntimeError, error:
            if self.main:
                self.main.splash.hide()
            QMessageBox.critical(self, self.tr("Save workspace"),
                self.tr("Unable to save current workspace"))
            raise RuntimeError(self.tr("Unable to save current workspace:") + \
                               '\n\r' + error)
        if self.main:
            self.main.splash.hide()
        self.refresh()
        return True
        
    def toggle_exclude_private(self, checked):
        """Toggle exclude private references"""
        CONF.set(self.ID, 'exclude_private', checked)
        self.refresh()
        
    def toggle_exclude_upper(self, checked):
        """Toggle exclude upper-case references"""
        CONF.set(self.ID, 'exclude_upper', checked)
        self.refresh()

