# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
pydeelib.plugins
=================

Here, 'plugins' are widgets designed specifically for Pydee
These plugins inherit the following classes (PluginMixin & PluginWidget)
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QDockWidget, QWidget
from PyQt4.QtCore import SIGNAL, Qt, QObject

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.qthelpers import toggle_actions
from pydeelib.config import CONF


class PluginMixin(object):
    """Useful methods to bind widgets to the main window
    See PydeeWidget class for required widget interface"""
    flags = Qt.Window
    allowed_areas = Qt.AllDockWidgetAreas
    location = Qt.LeftDockWidgetArea
    features = QDockWidget.DockWidgetClosable | \
               QDockWidget.DockWidgetFloatable | \
               QDockWidget.DockWidgetMovable
    def __init__(self, main):
        """Bind widget to a QMainWindow instance"""
        super(PluginMixin, self).__init__()
        self.main = main
        self.menu_actions, self.toolbar_actions = self.set_actions()
        self.dockwidget = None
        QObject.connect(self, SIGNAL('option_changed'), self.option_changed)
        
    def create_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        dock = QDockWidget(self.get_widget_title(), self.main)#, self.flags) -> bug in Qt 4.4
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(self.allowed_areas)
        dock.setFeatures(self.features)
        dock.setWidget(self)
        self.connect(dock, SIGNAL('visibilityChanged(bool)'),
                     self.visibility_changed)
        self.dockwidget = dock
        self.refresh()
        return (dock, self.location)

    def visibility_changed(self, enable):
        """DockWidget visibility has changed
        enable: this parameter is not used because we want to detect if
        DockWiget is visible or not, with 'not toplevel = visible'"""
        enable = self.dockwidget.isVisible()
        toggle_actions(self.menu_actions, enable)
        toggle_actions(self.toolbar_actions, enable)
        self.refresh() #XXX Is it a good idea?

    def option_changed(self, option, value):
        """
        Change a plugin option in configuration file
        Use a SIGNAL to call it, e.g.:
        self.emit(SIGNAL('option_changed'), 'show_all', checked)
        """
        CONF.set(self.ID, option, value)


class PluginWidget(QWidget, PluginMixin):
    """Pydee base widget class
    Pydee's widgets either inherit this class or reimplement its interface"""
    ID = None
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        PluginMixin.__init__(self, parent)
        assert self.ID is not None
        self.setWindowTitle(self.get_widget_title())
        
    def get_widget_title(self):
        """Return widget title
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute"""
        raise NotImplementedError
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        # Must return True or False (if cancelable)
        raise NotImplementedError
        
    def refresh(self):
        """Refresh widget"""
        raise NotImplementedError
    
    def set_actions(self):
        """Setup actions"""
        # Return menu and toolbar actions
        raise NotImplementedError

