# -*- coding: utf-8 -*-

#TODO: Workspace
#TODO: Before Workspace: DictEditor (dictionnary editor)
#      (Workspace will be derived from DictEditor, as well as a ListEditor and
#      a TupleShow)
#TODO: history editor widget derived from Editor (reloaded at each 'refresh()'
#      signal! -->read-only?<-- treeview?)

import os
import os.path as osp
from PyQt4.QtGui import QWidget, QHBoxLayout, QFileDialog, QStyle, QIcon
from PyQt4.QtGui import QLabel, QComboBox, QPushButton, QFont, QFontMetricsF
from PyQt4.QtGui import QFontDialog, QInputDialog, QDockWidget, QSizePolicy
from PyQt4.QtCore import Qt, SIGNAL

# Local import
from qthelpers import create_action, get_std_icon
from config import get_icon, get_font
from config import CONF


class BaseWidget(object):
    """Typical widget interface"""
    def bind(self, mainwindow):
        """Bind widget to a QMainWindow instance"""
        self.mainwindow = mainwindow
        if mainwindow is not None:
            mainwindow.connect(mainwindow, SIGNAL("closing()"), self.closing)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        raise NotImplementedError
        
    def get_name(self):
        """Return widget name"""
        raise NotImplementedError
    
    def get_actions(self, toolbar=False):
        """Return widget actions"""
        raise NotImplementedError
        
    def get_dockwidget_properties(self):
        raise NotImplementedError
        
    def get_dockwidget(self):
        """Add to parent QMainWindow as a dock widget"""
        allowed_areas, location = self.get_dockwidget_properties()
        dock = QDockWidget(self.get_name().replace('&',''),
                           self.mainwindow)
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(allowed_areas)
#        dock.setTitleBarWidget(QWidget())
        dock.setWidget(self)
        return (dock, location)


try:
    from qsciwidgets import QsciShell as ShellBaseWidget
    from qsciwidgets import QsciEditor as EditorBaseWidget
except ImportError:
    from qtwidgets import QtShell as ShellBaseWidget
    from qtwidgets import QtEditor as EditorBaseWidget


class Shell(ShellBaseWidget, BaseWidget):
    """
    Shell widget
    """
    def __init__(self, interpreter=None, initcommands=None,
                 message="", log='', parent=None):
        super(Shell, self).__init__(interpreter, initcommands,
                                     message, log, parent)
        self.bind(parent)
        
    def get_name(self):
        """Return widget name"""
        return self.tr("&Console")
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_history()
    
    def get_dockwidget_properties(self):
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
    
    def get_actions(self, toolbar=False):
        """Get widget actions"""
        run_action = create_action(self, self.tr("&Run..."), self.tr("Ctrl+R"),
            'run.png', self.tr("Run a Python script"),
            triggered=self.run_script)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set shell font style"),
            triggered=self.change_font)
        history_action = create_action(self, self.tr("History..."), None,
            'history.png', self.tr("Set history max entries"),
            triggered=self.change_history_depth)
        if toolbar:
            return (run_action,)
        else:
            return (run_action, None, font_action, history_action)
        
    def run_script(self, filename=None, silent=False):
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
        command = "execfile('%s')" % filename
        self.setFocus()
        if silent:
            self.write(command+'\n')
            self.interpreter.runsource(command)
            self.write(self.prompt)
        else:
            self.write(command)
        
    def change_font(self):
        """Change console font"""
        font, ok = QFontDialog.getFont(get_font('shell'),
                       self, self.tr("Select a new font"))
        if ok:
            self.set_font(font)
            CONF.set('shell', 'font/family/%s' % os.name, str(font.family()))
            CONF.set('shell', 'font/size', float(font.pointSize()))
            CONF.set('shell', 'font/weight', int(font.weight()))

    def change_history_depth(self):
        "Change history max entries"""
        depth, ok = QInputDialog.getInteger(self, self.tr('History'),
                    self.tr('Maximum entries'),
                    CONF.get('shell', 'history/max_entries'), 10, 10000)
        if ok:
            CONF.set('shell', 'history/max_entries', depth)


class PathComboBox(QComboBox):
    """
    QComboBox handling path locations
    """
    def __init__(self, parent):
        super(PathComboBox, self).__init__(parent)
        self.setEditable(True)
        self.connect(self, SIGNAL("editTextChanged(QString)"), self.validate)
        
    def validate(self, qstr):
        """Validate entered path"""
        if self.hasFocus():
            if osp.isdir( unicode(qstr) ):
                self.setStyleSheet( "color:rgb(50, 155, 50);" )
            else:
                self.setStyleSheet( "color:rgb(200, 50, 50);" )
        else:
            self.setStyleSheet( "" )

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            dir = unicode(self.currentText())
            if osp.isdir( dir ):
#                self.setEditable(False)
                self.parent().change_directory(dir)
                self.setStyleSheet( "" )
                if self.parent().mainwindow is not None:
                    self.parent().mainwindow.shell.setFocus()
        else:
            QComboBox.keyPressEvent(self, event)
    

#FIXME: Widget Sizehint/Dockwidget properties
class WorkingDirectory(QWidget, BaseWidget):
    """
    Working directory changer widget
    """
    log_path = osp.join(osp.expanduser('~'), '.workingdir')
    def __init__(self, parent):
        super(WorkingDirectory, self).__init__(parent)
        self.bind(parent)
        
        layout = QHBoxLayout()
        if self.mainwindow is None:
            # Not a dock widget
            layout.addWidget( QLabel(self.get_name()+':') )
        
        # Path combo box
        self.max_wdhistory_entries = CONF.get('shell', 'working_dir_history')
        self.pathedit = PathComboBox(self)
        self.pathedit.addItems( self.load_wdhistory() )
        layout.addWidget(self.pathedit)
        
        # Browse button
        self.browse_btn = QPushButton(get_std_icon('DirOpenIcon'), '')
        self.browse_btn.setFixedWidth(30)
        self.connect(self.browse_btn, SIGNAL('clicked()'),
                     self.select_directory)
        layout.addWidget(self.browse_btn)
        
        # Parent dir button
        self.parent_btn = QPushButton(get_std_icon('FileDialogToParent'), '')
        self.parent_btn.setFixedWidth(30)
        self.connect(self.parent_btn, SIGNAL('clicked()'),
                     self.parent_directory)
        layout.addWidget(self.parent_btn)
        
        self.setLayout(layout)
        self.refresh()
        
#        font = QFont(self.font())
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
#        self.setMaximumHeight(QFontMetricsF(font).height()*2)
        
    def get_name(self):
        """Return widget name"""
        return self.tr('Working directory')
    
    def get_dockwidget_properties(self):
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea,
                Qt.BottomDockWidgetArea)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_wdhistory()
        
    def load_wdhistory(self):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.log_path):
            fileobj = open(self.log_path, 'r')
            wdhistory = [line.replace('\n','') for line in fileobj.readlines()]
            fileobj.close()
        else:
            wdhistory = [ os.getcwd() ]
        return wdhistory
    
    def save_wdhistory(self, qobj=None):
        """Save history to a text file in user home directory"""
        fileobj = open(self.log_path, 'w')
        fileobj.write("\n".join( [ unicode( self.pathedit.itemText(index) )
                                  for index in range(self.pathedit.count()) ] ))
        fileobj.close()
        
    def refresh(self):
        """Refresh widget"""
        curdir = os.getcwd()
        index = self.pathedit.findText(curdir)
        if index != -1:
            self.pathedit.removeItem(index)
        self.pathedit.insertItem(0, curdir)
        self.pathedit.setCurrentIndex(0)
        
    def select_directory(self):
        """Select directory"""
        self.mainwindow.shell.restore_stds()
        directory = QFileDialog.getExistingDirectory(self.mainwindow,
                    self.tr("Select directory"), os.getcwd())
        if not directory.isEmpty():
            self.change_directory(directory)
        self.mainwindow.shell.redirect_stds()
        
    def parent_directory(self):
        """Change working directory to parent directory"""
        os.chdir(os.path.join(os.getcwd(), os.path.pardir))
        self.refresh()
        
    def change_directory(self, directory):
        """Set directory as working directory"""
        os.chdir( unicode(directory) )
        self.refresh()


#TODO: add the filename somewhere in the widget (custom DockWidget title bar?)
#TODO: TabWidget to open more than one script at a time
#TODO: Link: edit with external editor
class Editor(EditorBaseWidget, BaseWidget):
    """
    Editor widget
    """
    file_path = osp.join(osp.expanduser('~'), '.QtShell_tempfile')
    def __init__(self, parent):
        super(Editor, self).__init__(parent)
        self.bind(parent)
        self.filename = self.file_path
        self.load_temp_file()
        
    def get_name(self):
        """Return widget name"""
        return self.tr('&Editor')
    
    def get_dockwidget_properties(self):
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
    
    def get_actions(self, toolbar=False):
        """Get widget actions"""
        open_action = create_action(self, self.tr("Open..."), None,
            get_std_icon('DialogOpenButton', 16),
            self.tr("Open a Python script"),
            triggered = self.open)
        save_action = create_action(self, self.tr("Save as..."), None,
            get_std_icon('DialogSaveButton', 16),
            self.tr("Save current script"),
            triggered = self.save)
        exec_action = create_action(self, self.tr("&Execute"), self.tr("F2"),
            'execute.png', self.tr("Execute current script"),
            triggered=self.exec_script)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set editor font style"),
            triggered=self.change_font)
        if toolbar:
            return (open_action, save_action, exec_action,)
        else:
            return (open_action, save_action, exec_action, None, font_action)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_temp_file()
        
    def load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if osp.isfile(self.filename):
            self.open(self.filename)
    
    def save_temp_file(self):
        """Save temporary file to a text file in user home directory"""
        self.save(prompt=False)
        
    def exec_script(self):
        """Execute current script"""
        self.save_temp_file()
        self.mainwindow.shell.run_script(self.file_path, silent=True)
        
    def open(self, filename=None):
        if filename is None:
            self.mainwindow.shell.restore_stds()
            basedir = os.getcwd()
            if self.filename != self.file_path:
                basedir = osp.dirname(self.filename)
            filename = QFileDialog.getOpenFileName(self,
                          self.tr("Open Python script"), basedir,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.mainwindow.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
                os.chdir( os.path.dirname(filename) )
                filename = os.path.basename(filename)
                self.mainwindow.shell.emit(SIGNAL("refresh()"))
            else:
                return
        self.setFocus()
        fileobj = open(filename, 'r')
        lines = fileobj.read()
        fileobj.close()
        self.set_text(lines)
        self.filename = filename
    
    def save(self, prompt=False):
        if prompt:
            self.mainwindow.shell.restore_stds()
            filename = QFileDialog.getSaveFileName(self,
                          self.tr("Save Python script"), self.filename,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.mainwindow.shell.redirect_stds()
            if filename:
                self.filename = unicode(filename)
                os.chdir( os.path.dirname(self.filename) )
                self.mainwindow.shell.emit(SIGNAL("refresh()"))
            else:
                return
        fileobj = open(self.filename, 'w')
        fileobj.writelines(self.get_text())
        fileobj.close()
        
    def change_font(self):
        """Change editor font"""
        font, ok = QFontDialog.getFont(get_font('editor'),
                       self, self.tr("Select a new font"))
        if ok:
            self.set_font(font)
            CONF.set('editor', 'font/family/%s' % os.name, str(font.family()))
            CONF.set('editor', 'font/size', float(font.pointSize()))
            CONF.set('editor', 'font/weight', int(font.weight()))


def tests():
    """
    Testing all widgets
    """
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    # Working directory changer test:
    dialog = WorkingDirectory(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    tests()
        