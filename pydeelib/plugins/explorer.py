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

from PyQt4.QtGui import QFontDialog
from PyQt4.QtCore import SIGNAL

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.config import CONF, get_font, set_font
from pydeelib.qthelpers import create_action, translate
from pydeelib.widgets.explorer import ExplorerWidget
from pydeelib.plugins import PluginMixin


class Explorer(ExplorerWidget, PluginMixin):
    """File and Directories Explorer DockWidget"""
    ID = 'explorer'
    def __init__(self, parent=None, path=None):
        ExplorerWidget.__init__(self, parent=parent, path=path,
                            include=CONF.get(self.ID, 'include'),
                            exclude=CONF.get(self.ID, 'exclude'),
                            valid_types=CONF.get(self.ID, 'valid_filetypes'),
                            show_all=CONF.get(self.ID, 'show_all'),
                            wrap=CONF.get(self.ID, 'wrap'),
                            show_toolbar=CONF.get(self.ID, 'show_toolbar'),
                            show_icontext=CONF.get(self.ID, 'show_icontext'))
        PluginMixin.__init__(self, parent)

        self.set_font(get_font(self.ID))
        
        self.connect(self, SIGNAL("open_file(QString)"), self.open_file)
        
    def set_editor_valid_types(self, valid_types):
        self.editor_valid_types = valid_types
        self.listwidget.valid_types += valid_types
        
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
        # Font
        font_action = create_action(self, translate('Explorer', "&Font..."),
                                    None, 'font.png',
                                    translate("Explorer", "Set font style"),
                                    triggered=self.change_font)
        self.listwidget.common_actions.append(font_action)
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def open_file(self, fname):
        """Open filename with the appropriate application
        Redirect to the right widget (txt -> editor, ws -> workspace, ...)"""
        fname = unicode(fname)
        ext = osp.splitext(fname)[1]
        if ext in self.editor_valid_types:
            self.emit(SIGNAL("edit(QString)"), fname)
        elif ext == '.ws':
            self.emit(SIGNAL("open_workspace(QString)"), fname)
        else:
            self.listwidget.startfile(fname)
        
    def change_font(self):
        """Change font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                  translate("Explorer", "Select a new font"))
        if valid:
            self.set_font(font)
            set_font(font, self.ID)
            
    def set_font(self, font):
        """Set explorer widget font"""
        self.setFont(font)
        self.listwidget.setFont(font)

