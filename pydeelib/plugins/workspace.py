# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Workspace widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QFileDialog, QMessageBox
from PyQt4.QtCore import SIGNAL

import os, sys, cPickle
import os.path as osp

try:
    import numpy as N
    def save_array(data, basename, index):
        """Save numpy array"""
        fname = basename + '_%04d.npy' % index
        N.save(fname, data)
        return fname
except ImportError:
    N = None

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.config import CONF, get_conf_path, str2type, get_icon
from pydeelib.qthelpers import create_action

# Package local imports
from pydeelib.widgets.dicteditor import DictEditorTableView
from pydeelib.plugins import PluginMixin

FILTERS = tuple(str2type(CONF.get('workspace', 'filters')))
# Max number of filter iterations for worskpace display:
# (for workspace saving, itermax == -1, see Workspace.save)
ITERMAX = -1 #XXX: To be adjusted if it takes too much to compute... 2, 3?

def is_supported(value, iter=0, itermax=-1):
    """Return True if the value is supported, False otherwise"""
    if iter == itermax:
        return True
    elif not isinstance(value, FILTERS):
        return False
    elif isinstance(value, (list, tuple, set)):
        for val in value:
            if not is_supported(val, iter+1):
                return False
    elif isinstance(value, dict):
        for key, val in value.iteritems():
            if not is_supported(key, iter+1) or not is_supported(val, iter+1):
                return False
    return True

def wsfilter(input_dict, itermax=ITERMAX):
    """Keep only objects that can be saved"""
    exclude_private = CONF.get('workspace', 'exclude_private')
    exclude_upper = CONF.get('workspace', 'exclude_upper')
    exclude_unsupported = CONF.get('workspace', 'exclude_unsupported_datatypes')
    excluded_names = CONF.get('workspace', 'excluded')
    output_dict = input_dict.copy() # Shallow copy
    for key in input_dict:
        if (exclude_private and key.startswith('_')) or \
           (exclude_upper and key[0].isupper()) or \
           (key in excluded_names) or \
           (exclude_unsupported and not is_supported(input_dict[key],
                                                     itermax=itermax)):
            output_dict.pop(key)
    return output_dict


class Workspace(DictEditorTableView, PluginMixin):
    """
    Workspace widget (namespace explorer)
    """
    ID = 'workspace'
    file_path = get_conf_path('.temp.ws')
    def __init__(self, parent):
        self.interpreter = None
        self.namespace = None
        self.filename = None
        truncate = CONF.get(self.ID, 'truncate')
        inplace = CONF.get(self.ID, 'inplace')
        minmax = CONF.get(self.ID, 'minmax')
        collvalue = CONF.get(self.ID, 'collvalue')
        DictEditorTableView.__init__(self, parent, None, names=True,
                                     truncate=truncate, inplace=inplace,
                                     minmax=minmax, collvalue=collvalue)
        PluginMixin.__init__(self, parent)
        self.load_temp_namespace()
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Workspace')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self
        
    def set_interpreter(self, interpreter):
        """Bind to interpreter"""
        self.interpreter = interpreter
        self.refresh()
        
    def get_namespace(self, itermax=ITERMAX):
        """Return filtered namespace"""
        return wsfilter(self.namespace, itermax=itermax)
    
    def _clear_namespace(self):
        """Clear namespace"""
        keys = self.get_namespace().keys()
        for key in keys:
            self.namespace.pop(key)
        self.refresh()
    
    def _update_dock_title(self):
        """Set the dockwidget title"""
        if hasattr(self, "dockwidget") and self.dockwidget:
            title = self.get_widget_title() + \
                                 ' - ' + osp.basename(self.filename)
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
        close_action = create_action(self, self.tr("Close..."), None,
            'fileclose.png', self.tr("Close the workspace"),
            triggered=self.close)
        open_action = create_action(self, self.tr("Open..."), None,
            'ws_open.png', self.tr("Open a workspace"), triggered = self.load)
        save_action = create_action(self, self.tr("Save"), None, 'ws_save.png',
            self.tr("Save current workspace"), triggered = self.save)
        save_as_action = create_action(self, self.tr("Save as..."), None,
            'ws_save_as.png',  self.tr("Save current workspace as..."),
            triggered = self.save_as)
        exclude_private_action = create_action(self,
            self.tr("Exclude private references"),
            tip=self.tr("Exclude references which name starts"
                        " with an underscore"),
            toggled=self.toggle_exclude_private)
        exclude_private_action.setChecked(CONF.get(self.ID, 'exclude_private'))
        exclude_upper_action = create_action(self,
            self.tr("Exclude capitalized references"),
            tip=self.tr("Exclude references which name starts with an "
                        "upper-case character"),
            toggled=self.toggle_exclude_upper)
        exclude_upper_action.setChecked( CONF.get(self.ID, 'exclude_upper') )
        exclude_unsupported_action = create_action(self,
            self.tr("Exclude unsupported data types"),
            tip=self.tr("Exclude references to unsupported data types"
                        " (i.e. which won't be handled/saved correctly)"),
            toggled=self.toggle_exclude_unsupported)
        exclude_unsupported_action.setChecked(CONF.get(self.ID,
                                              'exclude_unsupported_datatypes'))

        refresh_action = create_action(self, self.tr("Refresh"), None,
            'ws_refresh.png', self.tr("Refresh workspace"),
            triggered = self.refresh_editor)
        
        autorefresh_action = create_action(self, self.tr("Auto refresh"),
                                           toggled=self.toggle_autorefresh)
        autorefresh_action.setChecked( CONF.get(self.ID, 'autorefresh') )
        
        autosave_action = create_action(self, self.tr("Auto save"),
            toggled=self.toggle_autosave,
            tip=self.tr("Automatically save workspace in a temporary file"
                        " when quitting"))
        autosave_action.setChecked( CONF.get(self.ID, 'autosave') )
        
        clear_action = create_action(self, self.tr("Clear workspace"),
                                 icon=get_icon('clear.png'),
                                 tip=self.tr("Clear all data from workspace"),
                                 triggered=self.clear)
        
        menu_actions = (refresh_action, autorefresh_action, None,
                        self.truncate_action, self.inplace_action, None,
                        exclude_private_action, exclude_upper_action,
                        exclude_unsupported_action, None,
                        new_action, open_action,
                        save_action, save_as_action, close_action,
                        autosave_action, None, clear_action)
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
            workspace = self.get_namespace(itermax=-1)
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
                answer = QMessageBox.question(self, self.get_widget_title(),
                   self.tr("Workspace is currently keeping reference "
                           "to %1 object%2.\n\nDo you want to save %3?") \
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
        self.filename = unicode(self.file_path)
        if osp.isfile(self.filename):
            self.load(self.filename)
        else:
            self.namespace = None
            self.refresh()

    def load(self, filename=None):
        """Attempt to load namespace"""
        title = self.tr("Open workspace")
        if filename is None:
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            basedir = osp.dirname(self.filename)
            filename = QFileDialog.getOpenFileName(self,
                          title, basedir,
                          self.tr("Workspaces")+" (*.ws)")
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            if filename:
                filename = unicode(filename)
            else:
                return
        self.filename = unicode(filename)
        try:
            if self.main:
                self.main.set_splash(self.tr("Loading workspace..."))
            namespace = cPickle.load(file(self.filename))
            if N is not None:
                # Loading numpy arrays saved with N.save
                saved_arrays = namespace.get('__saved_arrays__')
                if saved_arrays:
                    for nametuple, fname in saved_arrays.iteritems():
                        name, index = nametuple
                        if osp.isfile(fname):
                            data = N.load(fname)
                            if index is None:
                                namespace[name] = data
                            elif isinstance(namespace[name], dict):
                                namespace[name][index] = data
                            else:
                                namespace[name].insert(index, data)
            if self.namespace is None:
                self.namespace = namespace
            else:
                self._clear_namespace()
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

    def close(self):
        """Close workspace"""
        answer = QMessageBox.question(self, self.tr("Save workspace"),
            self.tr("Do you want to save current workspace "
                    "before closing it?"),
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if answer == QMessageBox.Cancel:
            return False
        elif answer == QMessageBox.Yes:
            self.save()
        self._clear_namespace()
        self.main.console.shell.restore_stds()
        self.load_temp_namespace()
        return True
    
    def new(self):
        """Attempt to close the current workspace and create a new one"""
        if not self.close():
            return
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getSaveFileName(self,
                        self.tr("New workspace"), self.filename,
                        self.tr("Workspaces")+" (*.ws)")
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            self.filename = unicode(filename)
        self.save()
    
    def save_as(self):
        """Save current workspace as"""
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getSaveFileName(self,
                      self.tr("Save workspace"), self.filename,
                      self.tr("Workspaces")+" (*.ws)")
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
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
            namespace = self.get_namespace(itermax=-1).copy()
            if N is not None:
                # Saving numpy arrays with N.save
                saved_arrays = {}
                basename = self.filename[:-3]
                for name in namespace.keys():
                    if isinstance(namespace[name], N.ndarray):
                        # Saving arrays at namespace root
                        fname = save_array(namespace[name], basename,
                                           len(saved_arrays))
                        saved_arrays[(name, None)] = fname
                        namespace.pop(name)
                    elif isinstance(namespace[name], (list, dict)):
                        # Saving arrays nested in lists or dictionaries
                        if isinstance(namespace[name], list):
                            iterator = enumerate(namespace[name])
                        else:
                            iterator = namespace[name].iteritems()
                        to_remove = []
                        for index, value in iterator:
                            if isinstance(value, N.ndarray):
                                fname = save_array(value, basename,
                                                   len(saved_arrays))
                                saved_arrays[(name, index)] = fname
                                to_remove.append(index)
                        for index in sorted(to_remove, reverse=True):
                            namespace[name].pop(index)
                if saved_arrays:
                    namespace['__saved_arrays__'] = saved_arrays
            cPickle.dump(namespace, file(self.filename, 'w'))
        except RuntimeError, error:
            if self.main:
                self.main.splash.hide()
            QMessageBox.critical(self, self.tr("Save workspace"),
                self.tr("<b>Unable to save current workspace</b>"
                        "<br><br>Error message:<br>%1") \
                .arg(str(error)))
        except (cPickle.PicklingError, TypeError), error:
            if self.main:
                self.main.splash.hide()
            QMessageBox.critical(self, self.tr("Save workspace"),
                self.tr("<b>Unable to save current workspace</b>"
                        "<br><br>Error message:<br>%1") \
                .arg(error.message))
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

    def toggle_exclude_unsupported(self, checked):
        """Toggle exclude unsupported datatypes"""
        CONF.set(self.ID, 'exclude_unsupported_datatypes', checked)
        self.refresh()

    #----Focus
    def focusInEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        DictEditorTableView.focusInEvent(self, event)
        
    def focusOutEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        DictEditorTableView.focusOutEvent(self, event)
