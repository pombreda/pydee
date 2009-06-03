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


#TODO: Add "Find in files" feature
#      -> two more buttons on the toolbar (editable combo boxes):
#           1. one to enter the search pattern
#           2. one to choose the file pattern (--> look at the module 'glob')
#      -> show results in an another tab (allowing multiple results):
#           hyperlinks in a QTextBrowser?

#TODO: Add an option to force Pydee to open file in Editor
#      even if it's not a supported file type

class Explorer(ExplorerWidget, PluginMixin):
    """File and Directories Explorer DockWidget"""
    ID = 'explorer'
    def __init__(self, parent=None, path=None):
        valid_types = CONF.get(self.ID, 'valid_filetypes') + \
                      CONF.get('editor', 'valid_filetypes')
        show_hidden = CONF.get(self.ID, 'show_hidden')
        show_all = CONF.get(self.ID, 'show_all')
        wrap = CONF.get(self.ID, 'wrap')
        show_toolbar = CONF.get(self.ID, 'show_toolbar')
        
        ExplorerWidget.__init__(self, parent, path, valid_types, show_hidden,
                                show_all, wrap, show_toolbar)
        PluginMixin.__init__(self, parent)
        
        self.connect(self, SIGNAL("open_file(QString)"), self.open_file)
        
    def refresh(self, new_path=None):
        """Refresh explorer widget"""
        self.listwidget.refresh(new_path)
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("File explorer")
    
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

