#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Matplotlib patch
"""

from PyQt4.QtGui import QWidget, QVBoxLayout
from PyQt4.QtCore import Qt

# Local imports
from PyQtShell.widgets.base import WidgetMixin

class MatplotlibFigure(QWidget, WidgetMixin):
    """
    Matplotlib Figure Dockwidget
    """
    def __init__(self, parent, canvas, num):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        self.num = num
        self.canvas = canvas

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)        

        self.refresh()
        
    def addToolBar(self, toolbar):
        """Reimplement Qt method"""
        self.layout.addWidget(toolbar)
        
    def get_name(self, raw=True):
        """Return widget name"""
        return self.tr("Figure %d" % self.num)
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def refresh(self):
        """Refresh widget"""
        pass
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True


