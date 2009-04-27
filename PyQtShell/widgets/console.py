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

"""Console widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QWidget, QApplication, QCursor, QVBoxLayout,
                         QFileDialog, QFontDialog, QInputDialog, QLineEdit,
                         QFontMetricsF)
from PyQt4.QtCore import Qt, SIGNAL, QSize

import os, re, sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF, get_font, set_font
from PyQtShell.qthelpers import (get_std_icon, create_action,add_actions,
                                 mimedata2url)
from PyQtShell.environ import EnvDialog
try:
    from PyQtShell.environ import WinUserEnvDialog
except ImportError:
    WinUserEnvDialog = None

# Local package imports
from PyQtShell.widgets.shellbase import ShellBaseWidget
from PyQtShell.widgets.base import WidgetMixin, FindReplace

class Console(QWidget, WidgetMixin):
    """
    Console widget
    """
    ID = 'shell'
    def __init__(self, parent=None, namespace=None, commands=None, message="",
                 debug=False, exitfunc=None):
        # Shell
        self.shell = ShellBaseWidget(parent, namespace, commands,
                                     message, debug, exitfunc)
        
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        
        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.shell)
        self.find_widget.hide()

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.shell)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        # Parameters
        self.shell.set_font( get_font(self.ID) )
        self.shell.set_wrap_mode( CONF.get(self.ID, 'wrap') )
        
        self.connect(self, SIGNAL("executing_command(bool)"),
                     self.change_cursor)
            
        # Accepting drops
        self.setAcceptDrops(True)
        
    def minimumSizeHint(self):
        """Reimplement Qt method to set minimum size"""
        font = get_font(self.ID)
        fm = QFontMetricsF(font)
        return QSize(fm.width(" "*80), fm.height()*10)
        
    def change_cursor(self, state):
        """Change widget cursor"""
        if state:
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        else:
            QApplication.restoreOverrideCursor()

    def get_name(self):
        """Return widget name"""
        return self.tr("Console")
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.shell.interpreter.save_history()
        return True
    
    def quit(self):
        """Quit mainwindow"""
        self.main.close()
    
    def set_actions(self):
        """Setup actions"""
        self.quit_action = create_action(self,
                            self.tr("&Quit"), self.tr("Ctrl+Q"),
                            get_std_icon("DialogCloseButton"), self.tr("Quit"),
                            triggered=self.quit)
        run_action = create_action(self,
                            self.tr("&Run..."), self.tr("Ctrl+R"),
                            'run.png', self.tr("Run a Python script"),
                            triggered=self.run_script)
        environ_action = create_action(self,
                            self.tr("Environment variables..."),
                            icon = 'environ.png',
                            tip = self.tr("Show and edit environment variables"
                                          " (for current session)"),
                            triggered=self.show_env)
        font_action = create_action(self,
                            self.tr("&Font..."), None,
                            'font.png', self.tr("Set shell font style"),
                            triggered=self.change_font)
        history_action = create_action(self,
                            self.tr("History..."), None,
                            'history.png', self.tr("Set history max entries"),
                            triggered=self.change_history_depth)
        exteditor_action = create_action(self,
                            self.tr("External editor path..."), None, None,
                            self.tr("Set external editor executable path"),
                            triggered=self.change_exteditor)
        wrap_action = create_action(self,
                            self.tr("Wrap lines"),
                            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        calltips_action = create_action(self, self.tr("Balloon tips"),
            toggled=self.toggle_calltips)
        calltips_action.setChecked( CONF.get(self.ID, 'calltips') )
        menu_actions = [run_action, environ_action, None,
                             font_action, history_action, wrap_action,
                             calltips_action, exteditor_action,
                             None, self.quit_action]
        toolbar_actions = []
        if WinUserEnvDialog is not None:
            winenv_action = create_action(self,
                self.tr("Windows user environment variables..."),
                icon = 'win_env.png',
                tip = self.tr("Show and edit current user environment variables"
                              " in Windows registry (i.e. for all sessions)"),
                triggered=self.win_env)
            menu_actions.insert(2, winenv_action)
        
        # Add actions to context menu
        add_actions(self.shell.menu, menu_actions)
        
        return menu_actions, toolbar_actions
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.RightDockWidgetArea)
    
    def show_env(self):
        """Show environment variables"""
        dlg = EnvDialog()
        dlg.exec_()
    
    def win_env(self):
        """Show Windows current user environment variables"""
        dlg = WinUserEnvDialog(self)
        dlg.exec_()
        
    def run_script(self, filename=None, silent=False, set_focus=False):
        """Run a Python script"""
        if filename is None:
            self.shell.restore_stds()
            filename = QFileDialog.getOpenFileName(self,
                          self.tr("Run Python script"), os.getcwdu(),
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
                os.chdir( os.path.dirname(filename) )
                filename = os.path.basename(filename)
                self.emit(SIGNAL("refresh()"))
            else:
                return
        command = "execfile(r'%s')" % filename
        if set_focus:
            self.shell.setFocus()
        if silent:
            self.shell.write(command+'\n')
            self.shell.run_command(command)
        else:
            self.shell.write(command)
            
    def get_error_match(self, text):
        """Return error match"""
        return re.match(r'  File "(.*)", line (\d*)', text)
            
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = self.get_error_match(text)
        if match:
            fname, lnb = match.groups()
            self.edit_script(fname, int(lnb))
            
    def edit_script(self, filename=None, goto=None):
        """Edit script"""
        # Called from ShellBaseWidget
        if not hasattr(self, 'main') \
           or not hasattr(self.main, 'editor'):
            self.shell.external_editor(filename, goto)
            return
        if filename is not None:
            self.main.editor.load(os.path.abspath(filename), goto)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                       self, self.tr("Select a new font"))
        if valid:
            self.shell.set_font(font)
            set_font(font, self.ID)

    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInteger(self, self.tr('History'),
                           self.tr('Maximum entries'),
                           CONF.get('history', 'max_entries'), 10, 10000)
        if valid:
            CONF.set('history', 'max_entries', depth)
        
    def change_exteditor(self):
        """Change external editor path"""
        path, valid = QInputDialog.getText(self, self.tr('External editor'),
                          self.tr('External editor executable path:'),
                          QLineEdit.Normal,
                          CONF.get(self.ID, 'external_editor'))
        if valid:
            CONF.set(self.ID, 'external_editor', unicode(path))
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.shell.set_wrap_mode(checked)
        CONF.set(self.ID, 'wrap', checked)
            
    def toggle_calltips(self, checked):
        """Toggle calltips"""
        self.shell.set_calltips(checked)

                
    #----Drag and drop                    
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        if source.hasUrls() or source.hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        if source.hasUrls():
            files = mimedata2url(source)
            if files:
                files = ["r'%s'" % path for path in files]
                if len(files) == 1:
                    text = files[0]
                else:
                    text = "[" + ", ".join(files) + "]"
                self.shell.insert_text(text)
        elif source.hasText():
            lines = unicode(source.text())
            self.shell.move_cursor_to_end()
            self.shell.execute_lines(lines)
        event.acceptProposedAction()
