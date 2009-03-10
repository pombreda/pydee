# -*- coding: utf-8 -*-
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
from PyQtShell.config import CONF, get_conf_path
from PyQtShell.config import str2type
from PyQtShell.qthelpers import create_action

# Package local imports
from PyQtShell.widgets.base import WidgetMixin
from PyQtShell.widgets.dicteditor import DictEditor


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
            elif not isinstance(value, filters) or not isinstance(key, filters):
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


class Workspace(DictEditor, WidgetMixin):
    """
    Workspace widget (namespace explorer)
    """
    file_path = get_conf_path('.temp.ws')
    def __init__(self, parent):
        self.shell = None
        self.namespace = None
        self.filename = None
        DictEditor.__init__(self, parent, None)
        WidgetMixin.__init__(self, parent)
        self.load_temp_namespace()
        QShortcut(QKeySequence("Del"), self, self.remove_item)
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&Workspace')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def set_shell(self, shell):
        """Bind to shell widget"""
        self.shell = shell
        self.refresh()

    def refresh(self):
        """Refresh widget"""
        if CONF.get('workspace', 'autorefresh'):
            self.refresh_editor()
        
    def refresh_editor(self):
        """Refresh DictEditor"""
        if self.shell is not None:
            self.namespace = self.shell.interpreter.namespace
        self.set_filter( wsfilter )
        self.set_data( self.namespace )
        self.adjust_columns()
        
    def set_actions(self):
        """Setup actions"""
        open_action = create_action(self, self.tr("Open..."), None,
            'ws_open.png', self.tr("Open a workspace"), triggered = self.load)
        save_action = create_action(self, self.tr("Save"), None, 'ws_save.png',
            self.tr("Save current workspace"), triggered = self.save)
        save_as_action = create_action(self, self.tr("Save as..."), None,
            'ws_save_as.png',  self.tr("Save current workspace as..."),
            triggered = self.save_as)        
        exclude_private_action = create_action(self,
            self.tr("Exclude private references"),
            toggled=self.toggle_exclude_private)
        exclude_private_action.setChecked( CONF.get('workspace', 'exclude_private') )

        refresh_action = create_action(self, self.tr("Refresh"), None,
            'ws_refresh.png', self.tr("Refresh workspace"),
            triggered = self.refresh_editor)
        
        autorefresh_action = create_action(self, self.tr("Auto refresh"),
                                           toggled=self.toggle_autorefresh)
        autorefresh_action.setChecked( CONF.get('workspace', 'autorefresh') )
        
        autosave_action = create_action(self, self.tr("Auto save"),
            toggled=self.toggle_autosave,
            tip=self.tr("Automatically save workspace in a temporary file when quitting"))
        autosave_action.setChecked( CONF.get('workspace', 'autosave') )
        
        menu_actions = (refresh_action, autorefresh_action, None,
                        self.sort_action, self.inplace_action, None,
                        exclude_private_action, None, open_action, save_action,
                        save_as_action, autosave_action)
        toolbar_actions = (refresh_action, open_action, save_action)
        return (menu_actions, toolbar_actions)
    
    def toggle_autorefresh(self, checked):
        """Toggle autorefresh mode"""
        CONF.set('workspace', 'autorefresh', checked)
        self.refresh()
        
    def toggle_autosave(self, checked):
        """Toggle autosave mode"""
        CONF.set('workspace', 'autosave', checked)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        if CONF.get('workspace', 'autosave'):
            # Saving workspace
            self.save()
        else:
            workspace = wsfilter(self.namespace)
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
                answer = QMessageBox.question(self, self.get_name(raw=False),
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
            self.mainwindow.shell.restore_stds()
            basedir = osp.dirname(self.filename)
            filename = QFileDialog.getOpenFileName(self,
                          title, basedir,
                          self.tr("Workspaces")+" (*.ws)")
            self.mainwindow.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
            else:
                return
        self.filename = filename
        try:
            if self.mainwindow:
                self.mainwindow.set_splash(self.tr("Loading workspace..."))
            namespace = cPickle.load(file(self.filename))
            if self.namespace is None:
                self.namespace = namespace
            else:
                for key in namespace:
                    self.shell.namespace[key] = namespace[key]
        except (EOFError, ValueError):
            os.remove(self.filename)
            QMessageBox.critical(self, title,
                self.tr("Unable to load the following workspace:") + '\n' + \
                self.filename)
        self.refresh()        
        if self.mainwindow:
            self.mainwindow.splash.hide()

    def save_as(self):
        """Save current workspace as"""
        self.mainwindow.shell.restore_stds()
        filename = QFileDialog.getSaveFileName(self,
                      self.tr("Save workspace"), self.filename,
                      self.tr("Workspaces")+" (*.ws)")
        self.mainwindow.shell.redirect_stds()
        if filename:
            self.filename = unicode(filename)
        else:
            return False
        self.save()
    
    def save(self):
        """Save current workspace"""
        if self.filename is None:
            return self.save_as()
        if self.mainwindow:
            self.mainwindow.set_splash(self.tr("Saving workspace..."))
        try:
            cPickle.dump(wsfilter(self.namespace), file(self.filename, 'w'))
        except RuntimeError, error:
            if self.mainwindow:
                self.mainwindow.splash.hide()
            QMessageBox.critical(self, self.tr("Save workspace"),
                self.tr("Unable to save current workspace"))
            raise RuntimeError(self.tr("Unable to save current workspace:") + \
                               '\n\r' + error)
        if self.mainwindow:
            self.mainwindow.splash.hide()
        return True
        
    def toggle_exclude_private(self, checked):
        """Toggle exclude private references"""
        CONF.set('workspace', 'exclude_private', checked)
        self.refresh()

