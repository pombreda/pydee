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

from PyQt4.QtGui import (QDockWidget, QWidget, QFontDialog, QShortcut,
                         QKeySequence)
from PyQt4.QtCore import SIGNAL, Qt, QObject

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.qthelpers import (toggle_actions, create_action, add_actions,
                                translate)
from pydeelib.config import CONF, get_font, set_font
from pydeelib.widgets.qscieditor import QsciEditor
from pydeelib.widgets.findreplace import FindReplace


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
        short = self.get_shortcut()
        if short is not None:
            QShortcut(QKeySequence(short), self.main,
                      lambda: self.visibility_changed(True))
        return (dock, self.location)
    
    def get_shortcut(self):
        """Return widget shortcut key sequence (string)"""
        pass

    def visibility_changed(self, enable):
        """DockWidget visibility has changed
        enable: this parameter is not used because we want to detect if
        DockWiget is visible or not, with 'not toplevel = visible'"""
        if enable:
            self.dockwidget.raise_()
            widget = self.get_focus_widget()
            if widget is not None:
                widget.setFocus()
        visible = self.dockwidget.isVisible()
        toggle_actions(self.menu_actions, visible)
        toggle_actions(self.toolbar_actions, visible)
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
        """
        Return widget title
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute
        """
        raise NotImplementedError
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        pass
        
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


class ReadOnlyEditor(PluginWidget):
    """
    Read-only editor plugin widget
    (see examples of children classes in history.py and docviewer.py)
    """
    def __init__(self, parent):
        PluginWidget.__init__(self, parent)

        # Read-only editor
        self.editor = QsciEditor(self, linenumbers=False, language='py',
                                 code_folding=True)
        self.connect(self.editor, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        self.editor.setReadOnly(True)
        self.editor.set_font( get_font(self.ID) )
        self.editor.set_wrap_mode( CONF.get(self.ID, 'wrap') )
        
        # Add entries to read-only editor context-menu
        font_action = create_action(self, translate("Editor", "&Font..."), None,
                                    'font.png',
                                    translate("Editor", "Set font style"),
                                    triggered=self.change_font)
        wrap_action = create_action(self, translate("Editor", "Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        self.editor.readonly_menu.addSeparator()
        add_actions(self.editor.readonly_menu, (font_action, wrap_action))
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()
        
        # <!> Layout will have to be implemented in child class!
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.editor
            
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                      translate("Editor", "Select a new font"))
        if valid:
            self.editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.editor.set_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
