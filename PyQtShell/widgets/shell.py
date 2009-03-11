# -*- coding: utf-8 -*-
"""Shell widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QMessageBox, QShortcut, QKeySequence, QMenu
from PyQt4.QtGui import QFileDialog, QFontDialog, QInputDialog, QLineEdit
from PyQt4.QtGui import QApplication, QCursor
from PyQt4.QtCore import Qt, SIGNAL

import os, re, sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell.config import CONF, get_font, get_icon, set_font
from PyQtShell.qthelpers import get_std_icon, create_action,add_actions
from PyQtShell.qthelpers import translate
from PyQtShell.shell import ShellBaseWidget
from PyQtShell.environ import EnvDialog
try:
    from PyQtShell.environ import WinUserEnvDialog
except ImportError:
    WinUserEnvDialog = None

# Local package imports
from PyQtShell.widgets.base import WidgetMixin

class Shell(ShellBaseWidget, WidgetMixin):
    """
    Shell widget
    """
    ID = 'shell'
    def __init__(self, parent=None, namespace=None, commands=None, message="",
                 debug=False, exitfunc=None):
        self.menu = None
        ShellBaseWidget.__init__(self, parent, namespace, commands, message,
                                 debug, exitfunc)
        WidgetMixin.__init__(self, parent)
        
        # Parameters
        self.set_font( get_font(self.ID) )
        self.set_wrap_mode( CONF.get(self.ID, 'wrap') )
        
        # Escape shortcut
        QShortcut(QKeySequence("Escape"), self, self.clear_line)
        
        self.connect(self, SIGNAL("executing_command(bool)"),
                     self.change_cursor)
        
    def change_cursor(self, state):
        """Change widget cursor"""
        if state:
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        else:
            QApplication.restoreOverrideCursor()
        
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        self.menu.popup(event.globalPos())
        event.accept()

    def help(self):
        """Help on PyQtShell console"""
        QMessageBox.about(self,
            translate("ShellBaseWidget", "Help"),
            self.tr("""<b>%1</b>
            <p><i>%2</i><br>    edit foobar.py
            <p><i>%3</i><br>    xedit foobar.py
            <p><i>%4</i><br>    run foobar.py
            <p><i>%5</i><br>    clear x, y
            <p><i>%6</i><br>    !ls
            <p><i>%7</i><br>    object?
            """) \
            .arg(translate("ShellBaseWidget", 'Shell special commands:')) \
            .arg(translate("ShellBaseWidget", 'Internal editor:')) \
            .arg(translate("ShellBaseWidget", 'External editor:')) \
            .arg(translate("ShellBaseWidget", 'Run script:')) \
            .arg(translate("ShellBaseWidget", 'Remove references:')) \
            .arg(translate("ShellBaseWidget", 'System commands:')) \
            .arg(translate("ShellBaseWidget", 'Python help:')))

    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr("&Console")
        if raw:
            return name
        else:
            return name.replace("&", "")
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.interpreter.save_history()
        return True
    
    def quit(self):
        """Quit mainwindow"""
        self.mainwindow.close()
    
    def set_actions(self):
        """Setup actions"""
        quit_action = create_action(self, self.tr("&Quit"), self.tr("Ctrl+Q"),
            get_std_icon("DialogCloseButton"), self.tr("Quit"),
            triggered=self.quit)
        run_action = create_action(self, self.tr("&Run..."), self.tr("Ctrl+R"),
            'run.png', self.tr("Run a Python script"),
            triggered=self.run_script)
        environ_action = create_action(self,self.tr("Environment variables..."),
            icon = 'environ.png',
            tip = self.tr("Show and edit environment variables (for current session)"),
            triggered=self.show_env)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set shell font style"),
            triggered=self.change_font)
        history_action = create_action(self, self.tr("History..."), None,
            'history.png', self.tr("Set history max entries"),
            triggered=self.change_history_depth)
        exteditor_action = create_action(self,
            self.tr("External editor path..."), None,
            None, self.tr("Set external editor executable path"),
            triggered=self.change_exteditor)
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        calltips_action = create_action(self, self.tr("Balloon tips"),
            toggled=self.toggle_calltips)
        calltips_action.setChecked( CONF.get(self.ID, 'calltips') )
        menu_actions = [run_action, environ_action, None,
                        font_action, history_action, wrap_action,
                        calltips_action, exteditor_action,
                        None, quit_action]
        toolbar_actions = (run_action,)
        if WinUserEnvDialog is not None:
            winenv_action = create_action(self,self.tr("Windows user environment variables..."),
                icon = 'win_env.png',
                tip = self.tr("Show and edit current user environment variables in Windows registry (i.e. for all sessions)"),
                triggered=self.win_env)
            menu_actions.insert(2, winenv_action)
        
        # Create a little context menu
        def keybinding(attr):
            ks = getattr(QKeySequence, attr)
            return QKeySequence.keyBindings(ks)[0].toString()
        
        self.menu = QMenu(self)
        cut_action   = create_action(self, translate("ShellBaseWidget", "Cut"),
                           shortcut=keybinding('Cut'),
                           icon=get_icon('cut.png'), triggered=self.cut)
        copy_action  = create_action(self, translate("ShellBaseWidget", "Copy"),
                           shortcut=keybinding('Copy'),
                           icon=get_icon('copy.png'), triggered=self.copy)
        paste_action = create_action(self,
                           translate("ShellBaseWidget", "Paste"),
                           shortcut=keybinding('Paste'),
                           icon=get_icon('paste.png'), triggered=self.paste)
        clear_action = create_action(self,
                           translate("ShellBaseWidget", "Clear shell"),
                           icon=get_std_icon("TrashIcon"),
                           tip=translate("ShellBaseWidget",
                                   "Clear shell contents ('cls' command)"),
                           triggered=self.clear_terminal)
        self.help_action = create_action(self,
                           translate("ShellBaseWidget", "Help..."),
                           shortcut="F1",
                           icon=get_std_icon('DialogHelpButton'),
                           triggered=self.help)
        add_actions(self.menu, (cut_action, copy_action, paste_action,
                                None, clear_action, None, self.help_action) )

        add_actions(self.menu, (None,))
        add_actions(self.menu, menu_actions)
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
            self.restore_stds()
            filename = QFileDialog.getOpenFileName(self,
                          self.tr("Run Python script"), os.getcwd(),
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.redirect_stds()
            if filename:
                filename = unicode(filename)
                os.chdir( os.path.dirname(filename) )
                filename = os.path.basename(filename)
                self.emit(SIGNAL("refresh()"))
            else:
                return
        command = "execfile(r'%s')" % filename
        if set_focus:
            self.setFocus()
        if silent:
            self.write(command+'\n')
            self.run_command(command)
        else:
            self.write(command)
            
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = re.match(r'  File "(.*)", line (\d*)', text)
        if match:
            fname, lnb = match.groups()
            self.edit_script(fname, int(lnb))
            
    def edit_script(self, filename=None, goto=None):
        """Edit script"""
        # Called from ShellBaseWidget
        if not hasattr(self, 'mainwindow') \
           or not hasattr(self.mainwindow, 'editor'):
            self.external_editor(filename, goto)
            return
        if filename is not None:
            self.mainwindow.editor.load(os.path.abspath(filename), goto)
        
    def change_font(self):
        """Change console font"""
        font, valid = QFontDialog.getFont(get_font(self.ID),
                       self, self.tr("Select a new font"))
        if valid:
            self.set_font(font)
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
        self.set_wrap_mode(checked)
            
    def toggle_calltips(self, checked):
        """Toggle calltips"""
        self.set_calltips(checked)

