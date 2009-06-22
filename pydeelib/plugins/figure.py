# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
Matplotlib figure integration
"""

import sys

# For debugging purpose:
STDOUT = sys.stdout

from PyQt4.QtGui import QHBoxLayout, QVBoxLayout, QLabel, QDockWidget
from PyQt4.QtCore import Qt

# Local imports
from pydeelib.plugins import PluginWidget
from pydeelib.config import get_font, get_icon
from pydeelib.qthelpers import create_toolbutton

class MatplotlibFigure(PluginWidget):
    """
    Matplotlib Figure Dockwidget
    """
    ID = 'figure'
    features = QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable
    location = Qt.LeftDockWidgetArea
    def __init__(self, parent, canvas, num):        
        self.canvas = canvas
        self.num = num
        PluginWidget.__init__(self, parent)

        # Close button
        self.close_button = create_toolbutton(self, callback=self.close,
                                      icon=get_icon("fileclose.png"),
                                      tip=self.tr("Close figure %1").arg(num))
        
        # Top horizontal layout
        self.h_layout = QHBoxLayout()
        self.statusbar = self.set_statusbar()        
        self.h_layout.addWidget(self.statusbar)
        self.h_layout.addWidget(self.close_button)
        
        # Main vertical layout
        self.v_layout = QVBoxLayout()
        self.v_layout.addLayout(self.h_layout)
        self.v_layout.addWidget(self.canvas)
        self.setLayout(self.v_layout)
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr("Figure %d" % self.num)
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.canvas
        
    def set_statusbar(self):
        """Set status bar"""
        statusbar = QLabel('')
        statusbar.setFont(get_font(self.ID, 'statusbar'))
        return statusbar
        
    def statusBar(self):
        """Fake Qt method --> for matplotlib"""
        return self
    
    def showMessage(self, message):
        """Fake Qt method --> for matplotlib"""
        self.statusbar.setText("    " + message)
        
    def addToolBar(self, toolbar):
        """Fake Qt method --> for matplotlib"""
        self.h_layout.insertWidget(0, toolbar)
        
    def refresh(self):
        """Refresh widget"""
        pass
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def closeEvent(self, event):
        """closeEvent reimplementation"""
        self.main.widgetlist.pop(self.main.widgetlist.index(self))
        self.dockwidget.close()
        event.accept()

