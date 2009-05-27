# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This file is part of PyQtShell.
#
#    PyQtShell is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    PyQtShell is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PyQtShell; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""External Console widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QVBoxLayout, QFileDialog, QFontDialog, QMessageBox
from PyQt4.QtCore import Qt, SIGNAL, QProcess, QString

import sys, os
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF, get_font, get_icon, set_font
from PyQtShell.qthelpers import create_toolbutton, create_action
from PyQtShell.widgets import Tabs
from PyQtShell.widgets.externalshell import ExternalShell
from PyQtShell.widgets.shellhelpers import get_error_match
from PyQtShell.widgets.findreplace import FindReplace
from PyQtShell.plugins import PluginWidget


class ExternalConsole(PluginWidget):
    """
    Console widget
    """
    ID = 'external_shell'
    location = Qt.RightDockWidgetArea
    def __init__(self, parent, commands=None):
        self.commands = commands
        self.tabwidget = None
        self.menu_actions = None
        self.dockviewer = None
        self.shelldict = {}
        PluginWidget.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh)
        self.connect(self.tabwidget, SIGNAL("close_tab(int)"),
                     self.tabwidget.removeTab)
        self.close_button = create_toolbutton(self.tabwidget,
                                          icon=get_icon("fileclose.png"),
                                          callback=self.close,
                                          tip=self.tr("Close current console"))
        self.tabwidget.setCornerWidget(self.close_button)
        layout.addWidget(self.tabwidget)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        
        self.setLayout(layout)

    def close(self, index=-1):
        if not self.tabwidget.count():
            return
        if index == -1:
            index = self.tabwidget.currentIndex()
        self.tabwidget.widget(index).close()
        self.tabwidget.removeTab(index)
        for key in self.shelldict.keys():
            if self.shelldict[key] == index:
                self.shelldict.pop(key)
        
    def set_docviewer(self, docviewer):
        """Bind docviewer instance to this console"""
        self.docviewer = docviewer
        
    def start(self, fname, wdir, ask_for_arguments, interact, debug):
        """Start new console"""
        # Note: fname is None <=> Python interpreter
        fname = unicode(fname) if isinstance(fname, QString) else fname
        wdir = unicode(wdir) if isinstance(wdir, QString) else wdir
        index = self.shelldict.get(fname)
        if index is not None and CONF.get(self.ID, 'single_tab') \
           and fname is not None:
            old_shell = self.tabwidget.widget(index)
            if old_shell.process.state() == QProcess.Running:
                answer = QMessageBox.question(self, self.get_widget_title(),
                    self.tr("%1 is already running in a separate process.\n"
                            "Do you want to kill the process before starting "
                            "a new one?").arg(osp.basename(fname)),
                    QMessageBox.Yes | QMessageBox.Cancel)
                if answer == QMessageBox.Yes:
                    old_shell.process.kill()
                    old_shell.process.waitForFinished()
                else:
                    return
            self.close(index)

        # Creating a new external shell
        shell = ExternalShell(self, fname, wdir, self.commands, interact, debug)        
        shell.shell.set_font( get_font(self.ID) )
        shell.shell.set_wrap_mode( CONF.get(self.ID, 'wrap') )
        shell.shell.set_docviewer(self.docviewer)
        self.connect(shell.shell, SIGNAL("go_to_error(QString)"),
                     self.go_to_error)
        name = "Python" if fname is None else osp.basename(fname)
        if index is None:
            index = self.tabwidget.addTab(shell, name)
        else:
            self.tabwidget.insertTab(index, shell, name)
        if fname is not None:
            self.shelldict[fname] = index
                
        self.connect(shell, SIGNAL("started()"),
                     lambda i=index: self.tabwidget.setTabIcon(i,
                                                  get_icon('execute.png')))
        self.connect(shell, SIGNAL("finished()"),
                     lambda i=index: self.tabwidget.setTabIcon(i,
                                                  get_icon('terminated.png')))
        self.find_widget.set_editor(shell.shell)
        self.tabwidget.setTabToolTip(index, fname if wdir is None else wdir)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget:
            self.dockwidget.setVisible(True)
        
        # Start process and give focus to console
        shell.start(ask_for_arguments)
        shell.shell.setFocus()
        
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('External console')
        
    def set_actions(self):
        """Setup actions"""
        interpreter_action = create_action(self,
                            self.tr("Open &interpreter"), None,
                            'python.png', self.tr("Open a Python interpreter"),
                            triggered=self.open_interpreter)
        run_action = create_action(self,
                            self.tr("&Run..."), None,
                            'run.png', self.tr("Run a Python script"),
                            triggered=self.run_script)
        font_action = create_action(self,
                            self.tr("&Font..."), None,
                            'font.png', self.tr("Set shell font style"),
                            triggered=self.change_font)
        wrap_action = create_action(self,
                            self.tr("Wrap lines"),
                            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        singletab_action = create_action(self,
                            self.tr("One tab per script"),
                            toggled=self.toggle_singletab)
        singletab_action.setChecked( CONF.get(self.ID, 'single_tab') )
        self.menu_actions = [interpreter_action, run_action,
                             font_action, wrap_action, singletab_action]
        return (self.menu_actions, None)
        
    def open_interpreter(self):
        """Open interpreter"""
        self.start(None, os.getcwdu(), False, True, False)
        
    def run_script(self):
        """Run a Python script"""
        self.main.console.shell.restore_stds()
        filename = QFileDialog.getOpenFileName(self,
                      self.tr("Run Python script"), os.getcwdu(),
                      self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.main.console.shell.redirect_stds()
        if filename:
            self.start(unicode(filename), None, False, False, False)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                       self, self.tr("Select a new font"))
        if valid:
            for index in range(self.tabwidget.count()):
                self.tabwidget.widget(index).shell.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if self.tabwidget is None:
            return
        for index in range(self.tabwidget.count()):
            self.tabwidget.widget(index).shell.set_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
        
    def toggle_singletab(self, checked):
        """Toggle single tab mode"""
        CONF.set(self.ID, 'single_tab', checked)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
    
    def refresh(self):
        """Refresh tabwidget"""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget().shell
        else:
            editor = None
        self.find_widget.set_editor(editor)
    
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(unicode(text))
        if match:
            fname, lnb = match.groups()
            self.emit(SIGNAL("edit_goto(QString,int)"),
                      osp.abspath(fname), int(lnb))
