# -*- coding: utf-8 -*-

#TODO: multiple line QTextEdit/QScintilla editor
#TODO: globals explorer widget

import os
from PyQt4.QtGui import QWidget, QHBoxLayout, QFileDialog, QStyle
from PyQt4.QtGui import QLabel, QLineEdit, QPushButton, QAction
from PyQt4.QtGui import QFontDialog, QInputDialog
from PyQt4.QtCore import SIGNAL

# Local import
import config
from config import CONFIG


def create_action(parent, text, slot=None, shortcut=None, icon=None,
                  tip=None, checkable=False, signal="triggered()"):
    action = QAction(text, parent)
    if icon is not None:
        action.setIcon(config.icon(icon))
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if slot is not None:
        parent.connect(action, SIGNAL(signal), slot)
    if checkable:
        action.setCheckable(True)
    return action

def add_actions(target, actions):
    for action in actions:
        if action is None:
            target.addSeparator()
        else:
            target.addAction(action)


# QShell widget
try:
    from qsciwidgets import QsciShell as QShellBase
    # from qsciwidgets import QsciEditor as QEditor
except ImportError:
    from qtwidgets import QSimpleShell as QShellBase
    # from qtwidgets import QSimpleEditor as QEditor


## Typical widget interface
#class BaseWidget(QWidget):
#    def set_toolbar(self, parent):
#        pass
#    def set_menu(self, parent):
#        pass
#    def refresh(self):
#        pass
class QShell(QShellBase):
    def get_actions(self, toolbar=False):
        run_action = create_action(self, self.tr("&Run..."),
                self.run_script, self.tr("Ctrl+R"), 'run.png',
                self.tr("Run a Python script"))
        font_action = create_action(self, self.tr("&Font..."),
                self.change_font, None, None,
                self.tr("Set shell font style"))
        history_action = create_action(self, self.tr("History..."),
                self.change_history_depth, None, None,
                self.tr("Set history max entries"))
        if toolbar:
            return (run_action,)
        else:
            return (run_action, None, font_action, history_action)
    
    def set_menu(self, parent):
        menu = parent.menuBar().addMenu(self.tr("&Console"))
        add_actions(menu, self.get_actions())
        
    def run_script(self):
        self.restore_stds()
        fname = QFileDialog.getOpenFileName(self,
                    self.tr("Run Python script"), os.getcwd(),
                    self.tr("Python scripts")+" (*.py ; *.pyw)")
        if fname:
            fname = unicode(fname)
            os.chdir( os.path.dirname(fname) )
            self.emit(SIGNAL("refresh()"))
            command = "execfile('%s')" % os.path.basename(fname)
            self.write(command)
            self.setFocus()
        self.redirect_stds()
        
    def change_font(self):
        font, ok = QFontDialog.getFont(config.get_font(),
                       self, self.tr("Select a new font"))
        if ok:
            self.set_font(font)
            CONFIG.set('Font', 'family/%s' % os.name,
                       str(font.family()))
            CONFIG.set('Font', 'pointSize',
                       float(font.pointSize()))
            CONFIG.set('Font', 'weight',
                       int(font.weight()))

    def change_history_depth(self):
        depth, ok = QInputDialog.getInteger(self, self.tr('History'),
                    self.tr('Maximum entries'),
                    CONFIG.get('History', 'max_entries'),
                    10, 10000)
        if ok:
            CONFIG.set('History', 'max_entries', depth)


class CurrentDirChanger(QWidget):
    """
    Current directory changer widget
    """
    def __init__(self, parent):
        super(CurrentDirChanger, self).__init__()
        self.parent = parent
        layout = QHBoxLayout()
        layout.addWidget( QLabel(self.tr('Current directory')+':') )
        self.pathedit = QLineEdit()
        self.pathedit.setEnabled(False)
        layout.addWidget(self.pathedit)
        icon = self.style().standardIcon(QStyle.SP_DirOpenIcon)
        self.button = QPushButton(icon, self.tr('Browse'))
        self.connect(self.button, SIGNAL('clicked()'), self.select_directory)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.refresh()
        
    def refresh(self):
        """Refresh widget"""
        self.pathedit.setText( os.getcwd() )
        
    def select_directory(self):
        """Select directory and set it as working directory"""
        self.parent.shell.restore_stds()
        directory = QFileDialog.getExistingDirectory(self.parent,
                    self.tr("Select directory"), os.getcwd())
        if not directory.isEmpty():
            self.change_directory(directory)
        self.parent.shell.redirect_stds()
        
    def change_directory(self, directory):
        os.chdir( unicode(directory) )
        self.pathedit.setText(directory)


def tests():
    """
    Testing all widgets
    """
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    # Current directory changer test:
    dialog = CurrentDirChanger(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    tests()
        