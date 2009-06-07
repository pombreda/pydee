# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Find in files Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys

# For debugging purpose:
STDOUT = sys.stdout

from PyQt4.QtCore import SIGNAL

# Local imports
from pydeelib.config import CONF
from pydeelib.widgets.findinfiles import FindInFilesWidget
from pydeelib.plugins import PluginMixin


class FindInFiles(FindInFilesWidget, PluginMixin):
    """Find in files DockWidget"""
    ID = 'find_in_files'
    def __init__(self, parent=None):
        supported_encodings = CONF.get(self.ID, 'supported_encodings')        
        include = CONF.get(self.ID, 'include')
        include_regexp = CONF.get(self.ID, 'include_regexp')
        exclude = CONF.get(self.ID, 'exclude')
        exclude_regexp = CONF.get(self.ID, 'exclude_regexp')
        FindInFilesWidget.__init__(self, parent, include, include_regexp,
                                   exclude, exclude_regexp, supported_encodings)
        PluginMixin.__init__(self, parent)
        
        self.connect(self, SIGNAL('toggle_visibility(bool)'), self.toggle)
        
    def toggle(self, state):
        """Toggle widget visibility"""
        if self.dockwidget:
            self.dockwidget.setVisible(state)
        
    def refresh(self):
        """Refresh widget"""
        pass
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("Find in files")
    
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        options = self.find_options.get_options()
        if options is not None:
            _, _, include, exclude, _, _ = options
            CONF.set(self.ID, 'include', include)
            CONF.set(self.ID, 'include_regexp', True)
            CONF.set(self.ID, 'exclude', exclude)
            CONF.set(self.ID, 'exclude_regexp', True)
        return True

