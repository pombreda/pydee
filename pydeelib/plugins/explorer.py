# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Files and Directories Explorer"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtCore import SIGNAL

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.config import CONF
from pydeelib.widgets.explorer import ExplorerWidget
from pydeelib.plugins import PluginMixin


class Explorer(ExplorerWidget, PluginMixin):
    """File and Directories Explorer DockWidget"""
    ID = 'explorer'
    def __init__(self, parent=None, path=None):
        valid_types = CONF.get(self.ID, 'valid_filetypes') + \
                      CONF.get('editor', 'valid_filetypes')
        include = CONF.get(self.ID, 'include')
        exclude = CONF.get(self.ID, 'exclude')
        show_all = CONF.get(self.ID, 'show_all')
        wrap = CONF.get(self.ID, 'wrap')
        show_toolbar = CONF.get(self.ID, 'show_toolbar')
        show_icontext = CONF.get(self.ID, 'show_icontext')
        
        ExplorerWidget.__init__(self, parent, path, include, exclude,
                                valid_types, show_all, wrap,
                                show_toolbar, show_icontext)
        PluginMixin.__init__(self, parent)
        
        self.connect(self, SIGNAL("open_file(QString)"), self.open_file)
        
    def refresh(self, new_path=None):
        """Refresh explorer widget"""
        self.listwidget.refresh(new_path)
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("File explorer")
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.listwidget
    
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def open_file(self, fname):
        """Open filename with the appropriate application
        Redirect to the right widget (txt -> editor, ws -> workspace, ...)"""
        fname = unicode(fname)
        ext = osp.splitext(fname)[1]
        if ext in CONF.get('editor', 'valid_filetypes'):
            self.emit(SIGNAL("edit(QString)"), fname)
        elif ext == '.ws':
            self.emit(SIGNAL("open_workspace(QString)"), fname)
        else:
            self.listwidget.startfile(fname)

