# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Console widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QApplication, QCursor, QVBoxLayout, QFileDialog,
                         QFontDialog, QInputDialog, QLineEdit)
from PyQt4.QtCore import Qt, SIGNAL

import os, sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.config import CONF, get_font, set_font
from pydeelib.qthelpers import create_action,add_actions, mimedata2url
from pydeelib.environ import EnvDialog
from pydeelib.widgets.interactiveshell import InteractiveShell
from pydeelib.widgets.shellhelpers import get_error_match
from pydeelib.widgets.findreplace import FindReplace
from pydeelib.widgets.dicteditor import DictEditor
from pydeelib.plugins import PluginWidget

    
def show_syspath():
    """Show sys.path"""
    dlg = DictEditor(sys.path, title="sys.path",
                     width=600, icon='syspath.png', readonly=True)
    dlg.exec_()

class Console(PluginWidget):
    """
    Console widget
    """
    ID = 'shell'
    location = Qt.RightDockWidgetArea
    def __init__(self, parent=None, namespace=None, commands=None, message="",
                 debug=False, exitfunc=None, profile=False):
        # Shell
        self.shell = InteractiveShell(parent, namespace, commands,
                                     message, debug, exitfunc, profile)
        self.connect(self.shell, SIGNAL("go_to_error(QString)"),
                     self.go_to_error)
        self.connect(self.shell, SIGNAL("focus_changed()"),
                     lambda: self.emit(SIGNAL("focus_changed()")))
        
        PluginWidget.__init__(self, parent)
        
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
        
    def set_docviewer(self, docviewer):
        """Bind docviewer instance to this console"""
        self.shell.docviewer = docviewer
        
    def change_cursor(self, state):
        """Change widget cursor"""
        if state:
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        else:
            QApplication.restoreOverrideCursor()
            
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Interactive console')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.shell
    
    def get_shortcut(self):
        """Return widget shortcut key sequence (string)"""
        return "Ctrl+Maj+I"
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.shell.save_history()
        return True
    
    def quit(self):
        """Quit mainwindow"""
        self.main.close()
        
    def refresh(self):
        pass
    
    def set_actions(self):
        """Setup actions"""
        self.quit_action = create_action(self,
                            self.tr("&Quit"), self.tr("Ctrl+Q"),
                            'exit.png', self.tr("Quit"),
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
        syspath_action = create_action(self,
                            self.tr("Show sys.path contents..."),
                            icon = 'syspath.png',
                            tip = self.tr("Show (read-only) sys.path"),
                            triggered=show_syspath)
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
        menu_actions = [run_action, environ_action, syspath_action, None,
                        font_action, history_action, wrap_action,
                        calltips_action, exteditor_action, None,
                        self.quit_action]
        toolbar_actions = []
        
        # Add actions to context menu
        add_actions(self.shell.menu, menu_actions)
        
        return menu_actions, toolbar_actions
    
    def show_env(self):
        """Show environment variables"""
        dlg = EnvDialog()
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
        if self.dockwidget:
            self.dockwidget.setVisible(True)
            self.dockwidget.raise_()
        if silent:
            self.shell.write(command+'\n')
            self.shell.run_command(command)
        else:
            self.shell.write(command)
            
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(unicode(text))
        if match:
            fname, lnb = match.groups()
            self.edit_script(fname, int(lnb))
            
    def edit_script(self, filename=None, goto=-1):
        """Edit script"""
        # Called from InteractiveShell
        if not hasattr(self, 'main') \
           or not hasattr(self.main, 'editor'):
            self.shell.external_editor(filename, goto)
            return
        if filename is not None:
            self.emit(SIGNAL("edit_goto(QString,int)"),
                      osp.abspath(filename), goto)
        
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
                           CONF.get('historylog', 'max_entries'), 10, 10000)
        if valid:
            CONF.set('historylog', 'max_entries', depth)
            self.shell.max_history_entries = depth
        
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
