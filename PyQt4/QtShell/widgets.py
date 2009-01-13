# -*- coding: utf-8 -*-

#TODO: multiple line QTextEdit/QScintilla editor
#TODO: globals explorer widget

import os
import os.path as osp
from PyQt4.QtGui import QWidget, QHBoxLayout, QFileDialog, QStyle
from PyQt4.QtGui import QLabel, QComboBox, QPushButton, QAction
from PyQt4.QtGui import QFontDialog, QInputDialog, QDockWidget
from PyQt4.QtCore import Qt, SIGNAL

# Local import
import config
from config import CONF


def create_action(parent, text, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None):
    """Create a QAction"""
    action = QAction(text, parent)
    if triggered is not None:
        parent.connect(action, SIGNAL("triggered()"), triggered)
    if toggled is not None:
        parent.connect(action, SIGNAL("toggled(bool)"), toggled)
        action.setCheckable(True)
    if icon is not None:
        if isinstance(icon, (str, unicode)):
            icon = config.icon(icon)
        action.setIcon( icon )
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    return action

def add_actions(target, actions):
    """Add actions to a menu"""
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
        dock = QDockWidget(self.get_name(), self.mainwindow)
        dock.setObjectName(self.__class__.__name__+"_dw")
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(self)
        return (dock, location)


class QShell(QShellBase, BaseWidget):
    def __init__(self, interpreter=None, initcommands=None,
                 message="", log='', parent=None):
        super(QShell, self).__init__(interpreter, initcommands,
                                     message, log, parent)
        self.bind(parent)
        
    def get_name(self):
        """Return widget name"""
        return self.tr("&Console")
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_history()
    
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
        
    def run_script(self):
        """Run a Python script"""
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
        """Change console font"""
        font, ok = QFontDialog.getFont(config.get_font(),
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
    

class WorkingDirChanger(QWidget, BaseWidget):
    """
    Working directory changer widget
    """
    log_path = osp.join(osp.expanduser('~'), '.workingdir')
    def __init__(self, parent):
        super(WorkingDirChanger, self).__init__(parent)
        self.bind(parent)
        
        layout = QHBoxLayout()
        if self.mainwindow is None:
            # Not a dock widget
            layout.addWidget( QLabel(self.get_name()+':') )
        
        # Path combo box
        self.max_history_entries = CONF.get('shell', 'working_dir_history')
        self.pathedit = PathComboBox(self)
        self.pathedit.addItems( self.load_history() )
        layout.addWidget(self.pathedit)
        icon = self.style().standardIcon(QStyle.SP_DirOpenIcon)
        
        # Browse button
        self.browse_btn = QPushButton(icon, '')
        self.browse_btn.setFixedWidth(30)
        self.connect(self.browse_btn, SIGNAL('clicked()'),
                     self.select_directory)
        layout.addWidget(self.browse_btn)
        
        # Parent dir button
        self.parent_btn = QPushButton(config.icon('parent.png'), '')
        self.parent_btn.setFixedWidth(30)
        self.connect(self.parent_btn, SIGNAL('clicked()'),
                     self.parent_directory)
        layout.addWidget(self.parent_btn)
        
        self.setLayout(layout)
        self.refresh()
        
    def get_name(self):
        """Return widget name"""
        return self.tr('Working directory')
    
    def get_dockwidget_properties(self):
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea,
                Qt.BottomDockWidgetArea)
        
    def closing(self):
        """Perform actions before parent main window is closed"""
        self.save_history()
        
    def load_history(self):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.log_path):
            fileobj = open(self.log_path, 'r')
            history = [line.replace('\n','') for line in fileobj.readlines()]
            fileobj.close()
        else:
            history = [ os.getcwd() ]
        return history
    
    def save_history(self, qobj=None):
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


def tests():
    """
    Testing all widgets
    """
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    # Working directory changer test:
    dialog = WorkingDirChanger(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    tests()
        