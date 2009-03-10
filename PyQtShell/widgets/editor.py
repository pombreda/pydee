# -*- coding: utf-8 -*-
"""Editor widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel
from PyQt4.QtGui import QFileDialog, QPushButton, QLineEdit, QTabWidget, QMenu
from PyQt4.QtGui import QShortcut, QKeySequence, QCheckBox, QMessageBox
from PyQt4.QtGui import QFontDialog, QComboBox, QSizePolicy
from PyQt4.QtCore import Qt, SIGNAL

import os, sys, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from PyQtShell import encoding
from PyQtShell.config import CONF, get_conf_path, get_icon, get_font, set_font
from PyQtShell.qthelpers import get_std_icon, create_action, add_actions
from PyQtShell.dochelpers import getdoc, getsource
try:
    from PyQtShell.widgets.qscibase import QsciEditor as EditorBaseWidget
except ImportError:
    from PyQtShell.widgets.qtbase import QtEditor as EditorBaseWidget

# Package local imports
from PyQtShell.widgets.base import WidgetMixin, EditableComboBox


class FindReplace(QWidget):
    """
    Find widget
    """
    STYLE = {False: "background-color:rgb(255, 175, 90);",
             True: ""}
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.editor = None
        self.setLayout(QGridLayout())
        
        self.close_button = QPushButton(get_std_icon("DialogCloseButton"), "")
        self.connect(self.close_button, SIGNAL('clicked()'), self.hide)
        self.layout().addWidget(self.close_button, 0, 0)
        
        # Find layout
        self.edit = QLineEdit()
        self.connect(self.edit, SIGNAL("textChanged(QString)"),
                     self.text_has_changed)
        
        self.previous_button = QPushButton(get_std_icon("ArrowBack"), "")
        self.connect(self.previous_button, SIGNAL('clicked()'),
                     self.find_previous)
        self.next_button = QPushButton(get_std_icon("ArrowForward"), "")
        self.connect(self.next_button, SIGNAL('clicked()'),
                     self.find_next)

        self.case_check = QCheckBox(self.tr("Case Sensitive"))
        self.connect(self.case_check, SIGNAL("stateChanged(int)"), self.find)
        self.words_check = QCheckBox(self.tr("Whole words"))
        self.connect(self.words_check, SIGNAL("stateChanged(int)"), self.find)

        layout = QHBoxLayout()
        self.widgets = [self.close_button, self.edit, self.previous_button,
                        self.next_button, self.case_check, self.words_check]
        for widget in self.widgets[1:]:
            layout.addWidget(widget)
        self.layout().addLayout(layout, 0, 1)

        # Replace layout
        replace_with = QLabel(self.tr("Replace with:"))
        self.replace_edit = QLineEdit()
        
        self.replace_button = QPushButton(get_std_icon("DialogApplyButton"), "")
        self.connect(self.replace_button, SIGNAL('clicked()'),
                     self.replace_find)
        
        self.all_check = QCheckBox(self.tr("Replace all"))
        
        self.replace_layout = QHBoxLayout()
        widgets = [replace_with, self.replace_edit,
                   self.replace_button, self.all_check]
        for widget in widgets:
            self.replace_layout.addWidget(widget)
        self.layout().addLayout(self.replace_layout, 1, 1)
        self.widgets.extend(widgets)
        self.replace_widgets = widgets
        self.hide_replace()
        
        self.edit.setTabOrder(self.edit, self.replace_edit)
        
        # Escape shortcut
        QShortcut(QKeySequence("Escape"), self, self.hide)
                
        self.tweak_buttons()
        self.refresh()
        
    def tweak_buttons(self):
        """Change buttons appearance"""
        for widget in self.widgets:
            if isinstance(widget, QPushButton):
                widget.setFlat(True)
                widget.setFixedWidth(20)
        
    def show(self):
        """Overrides Qt Method"""
        QWidget.show(self)
        text = self.editor.selectedText()
        if len(text)>0:
            self.edit.setText(text)
            self.refresh()
        
    def hide(self):
        """Overrides Qt Method"""
        for widget in self.replace_widgets:
            widget.hide()
        QWidget.hide(self)
        if self.editor is not None:
            self.editor.setFocus()
        
    def show_replace(self):
        """Show replace widgets"""
        for widget in self.replace_widgets:
            widget.show()
            
    def hide_replace(self):
        """Hide replace widgets"""
        for widget in self.replace_widgets:
            widget.hide()
        
    def refresh(self):
        """Refresh widget"""
        state = self.editor is not None
        for widget in self.widgets:
            widget.setEnabled(state)
        if state:
            self.find()
            
    def set_editor(self, editor):
        """Set parent editor"""
        self.editor = editor
        self.refresh()
        
    def find_next(self):
        """Find next occurence"""
        self.find(changed=False, forward=True)
        
    def find_previous(self):
        """Find previous occurence"""
        self.find(changed=False, forward=False)
        
    def text_has_changed(self, text):
        """Find text has changed"""
        self.find(changed=True, forward=True)
        
    def find(self, changed=True, forward=True):
        """Call the find function"""
        text = self.edit.text()
        if len(text)==0:
            self.edit.setStyleSheet("")
            return None
        else:
            found = self.editor.find_text(text, changed, forward,
                                          case=self.case_check.isChecked(),
                                          words=self.words_check.isChecked())
            self.edit.setStyleSheet(self.STYLE[found])
            return found
            
    def replace_find(self):
        """Replace and find"""
        if (self.editor is not None):
            while self.find(changed=True, forward=True):
                if not self.all_check.isChecked():
                    break
                self.editor.replace(self.replace_edit.text())
                self.refresh()
            self.all_check.setCheckState(Qt.Unchecked)


class SimpleEditor(EditorBaseWidget):
    """
    Simple Editor Widget
    QsciEditor/QtEditor -> *SimpleEditor* -> used in Editor's tabwidget
    """
    def __init__(self, parent, text):
        super(SimpleEditor, self).__init__(parent)
        self.setup_editor(text)
        
    def setup_editor(self, text):
        """Setup Editor"""
        self.set_font( get_font('editor') )
        self.set_wrap_mode( CONF.get('editor', 'wrap') )
        self.setup_api()
        self.set_text(text)
        self.setModified(False)
        self.connect( self, SIGNAL('modificationChanged(bool)'),
                      self.parent().change )
        
    def highlight_line(self, linenb):
        """Highlight line number linenb"""
        line = unicode(self.get_text()).splitlines()[linenb-1]
        self.find_text(line)

    def check_syntax(self, filename):
        """Check module syntax"""
        f = open(filename, 'r')
        source = f.read()
        f.close()
        if '\r' in source:
            source = re.sub(r"\r\n", "\n", source)
            source = re.sub(r"\r", "\n", source)
        if source and source[-1] != '\n':
            source = source + '\n'
        try:
            # If successful, return the compiled code
            if compile(source, filename, "exec"):
                return None
        except (SyntaxError, OverflowError), err:
            try:
                msg, (_errorfilename, lineno, _offset, _line) = err
                self.highlight_line(lineno)
            except:
                msg = "*** " + str(err)
            return self.tr("There's an error in your program:") + "\n" + msg


class Tabs(QTabWidget):
    """TabWidget with a context-menu"""
    def __init__(self, parent, actions):
        QTabWidget.__init__(self, parent)
        self.menu = QMenu(self)
        add_actions(self.menu, actions)
        
    def contextMenuEvent(self, event):
        """Override Qt method"""
        if self.menu:
            self.menu.popup(event.globalPos())

class Editor(QWidget, WidgetMixin):
    """
    Editor widget
    """
    file_path = get_conf_path('.temp.py')
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        
        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.tab_actions)
        self.connect(self.tabwidget, SIGNAL('currentChanged(int)'),
                     self.refresh)
        layout.addWidget(self.tabwidget)
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)
        self.setLayout(layout)
        
        self.file_dependent_actions = []
        self.filenames = []
        self.encodings = []
        self.editors = []
        
        filenames = CONF.get('editor', 'filenames', [])
        if filenames:
            self.load(filenames)
        else:
            self.load_temp_file()
        
    def refresh(self, index):
        """Refresh tabwidget"""
        # Doesn't work... references must be lost somewhere...
        enable = index != -1
        for action in self.file_dependent_actions:
            action.setEnabled(enable)
        # The following works
        if self.tabwidget.count():
            editor = self.editors[self.tabwidget.currentIndex()]
        else:
            editor = None
        self.find_widget.set_editor(editor)

    def change(self, state=None):
        """Change tab title depending on modified state"""
        index = self.tabwidget.currentIndex()
        if state is None:
            state = self.editors[index].isModified()
        title = self.get_title(self.filenames[index])
        if state:
            title += "*"
        elif title.endswith('*'):
            title = title[:-1]
        self.tabwidget.setTabText(index, title)
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&Editor')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.BottomDockWidgetArea)

    def set_actions(self):
        """Setup actions"""
        new_action = create_action(self, self.tr("New..."), "Ctrl+N",
            'new.png', self.tr("Create a new Python script"),
            triggered = self.new)
        open_action = create_action(self, self.tr("Open..."), "Ctrl+O",
            'open.png', self.tr("Open a Python script"),
            triggered = self.load)
        save_action = create_action(self, self.tr("Save"), "Ctrl+S",
            'save.png', self.tr("Save current script"),
            triggered = self.save)
        save_as_action = create_action(self, self.tr("Save as..."), None,
            'saveas.png', self.tr("Save current script as..."),
            triggered = self.save_as)
        find_action = create_action(self, self.tr("Find text"), "Ctrl+F",
            'find.png', self.tr("Find text in current script"),
            triggered = self.find)
        replace_action = create_action(self, self.tr("Replace text"), "Ctrl+H",
            tip = self.tr("Replace text in current script"),
            triggered = self.replace)
        close_action = create_action(self, self.tr("Close"), "Ctrl+W",
            'close.png', self.tr("Close current script"),
            triggered = self.close)
        close_all_action = create_action(self, self.tr("Close all"),
            "Ctrl+Maj+W", 'close_all.png', self.tr("Close all opened scripts"),
            triggered = self.close_all)
        check_action = create_action(self, self.tr("&Check syntax"), "F5",
            'check.png', self.tr("Check current script for syntax errors"),
            triggered=self.check_script)
        exec_action = create_action(self, self.tr("&Execute"), "F9",
            'execute.png', self.tr("Execute current script"),
            triggered=self.exec_script)
        exec_interact_action = create_action(self,
            self.tr("Execute and &interact"), "Shift+F9",
            'execute_interact.png',
            self.tr("Execute current script and set focus to shell"),
            triggered=self.exec_script_and_interact)
        exec_selected_action = create_action(self,
            self.tr("Execute selection"), "Ctrl+F9", 'execute_selection.png',
            self.tr("Execute selected text in current script and set focus to shell"),
            triggered=self.exec_selected_text)
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set editor font style"),
            triggered=self.change_font)
        wrap_action = create_action(self, self.tr("Wrap lines"),
            toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get('editor', 'wrap') )
        workdir_action = create_action(self, self.tr("Set working directory"),
            tip=self.tr("Change working directory to current script directory"),
            triggered=self.set_workdir)
        menu_actions = (new_action, open_action, save_action, save_as_action,
                        None, check_action, exec_action, exec_interact_action,
                        exec_selected_action,
                        None, find_action, replace_action,
                        None, close_action, close_all_action,
                        None, font_action, wrap_action)
        toolbar_actions = (new_action, open_action, save_action, exec_action,
                           exec_selected_action, find_action, None)
        self.file_dependent_actions = (save_action, save_as_action,
                                       check_action, exec_action,
                                       exec_interact_action,
                                       exec_selected_action,
                                       close_action, close_all_action,
                                       find_action, replace_action)
        self.tab_actions = (save_action, save_as_action,
                            check_action,exec_action,
                            workdir_action,
                            None, close_action)
        return (menu_actions, toolbar_actions)                
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        CONF.set('editor', 'filenames', self.filenames)
        return self.save_if_changed(cancelable)
        
    def find(self):
        """Show Find Widget"""
        self.find_widget.show()
        self.find_widget.edit.setFocus()
        
    def replace(self):
        """Show Replace Widget"""
        self.find()
        self.find_widget.show_replace()
        
    def set_workdir(self):
        """Set working directory as current script directory"""
        index = self.tabwidget.currentIndex()
        self.chdir( os.path.dirname(os.path.abspath(self.filenames[index])) )
        self.emit(SIGNAL("refresh()"))
        
    def load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if not osp.isfile(self.file_path):
            # Creating temporary file
            default = ['# -*- coding: utf-8 -*-',
                       '"""',
                       self.tr("PyQtShell Editor"),
                       '',
                       self.tr("This temporary script file is located here:"),
                       self.file_path,
                       '"""',
                       '',
                       '',
                       ]
            text = "\r\n".join([unicode(qstr) for qstr in default])
            encoding.write(unicode(text), self.file_path, 'utf-8')
        self.load(self.file_path)
    
    def new(self):
        """Create a new Python script"""
        gen_name = lambda nb: self.tr("untitled") + ("%d.py" % nb)
        nb = 0
        while osp.isfile(gen_name(nb)):
            nb += 1
        fname = gen_name(nb)
        self.mainwindow.shell.restore_stds()
        fname = QFileDialog.getSaveFileName(self, self.tr("New Python script"),
                    fname, self.tr("Python scripts")+" (*.py ; *.pyw)")
        self.mainwindow.shell.redirect_stds()
        if not fname.isEmpty():
            fname = unicode(fname)
            default = ['# -*- coding: utf-8 -*-',
                       '"""',
                       osp.basename(fname),
                       '"""',
                       '',
                       '',
                       ]
            text = "\r\n".join([unicode(qstr) for qstr in default])
            encoding.write(unicode(text), fname, 'utf-8')
            self.load(fname)
    
    def check_script(self):
        """Check current script for syntax errors"""
        if self.save():
            index = self.tabwidget.currentIndex()
            errors = self.editors[index].check_syntax(self.filenames[index])
            title = self.tr("Check syntax")
            if errors:
                QMessageBox.critical(self, title, errors)
            else:
                QMessageBox.information(self, title,
                                        self.tr("There is no error in your program.")) 
    
    def exec_script(self, set_focus=False):
        """Execute current script"""
        if self.save():
            index = self.tabwidget.currentIndex()
            self.mainwindow.shell.run_script(self.filenames[index],
                                             silent=True, set_focus=set_focus)
    
    def exec_script_and_interact(self):
        """Execute current script and set focus to shell"""
        self.exec_script(set_focus=True)
        
    def exec_selected_text(self):
        """Execute selected text in current script and set focus to shell"""
        index = self.tabwidget.currentIndex()
        lines = unicode( self.editors[index].selectedText() )
        self.mainwindow.shell.execute_lines(lines)
        self.mainwindow.shell.setFocus()

    def save_if_changed(self, cancelable=False):
        """Ask user to save file if modified"""
        buttons = QMessageBox.Yes | QMessageBox.No
        if cancelable:
            buttons = buttons | QMessageBox.Cancel
        for index in range(0, self.tabwidget.count()):
            self.tabwidget.setCurrentIndex(index)
            filename = self.filenames[index]
            if filename == self.file_path:
                self.save()
            if self.editors[index].isModified():
                answer = QMessageBox.question(self, self.get_name(raw=False),
                    osp.basename(filename)+' '+ \
                    self.tr(" has been modified.\nDo you want to save changes?"),
                    buttons)
                if answer == QMessageBox.Yes:
                    self.save()
                elif answer == QMessageBox.Cancel:
                    return False
        return True
    
    def close(self):
        """Close current Python script file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            is_ok = self.save_if_changed(cancelable=True)
            if is_ok:
                self.tabwidget.removeTab(index)
                self.filenames.pop(index)
                self.encodings.pop(index)
                self.editors.pop(index)
            return is_ok
        else:
            self.find_widget.set_editor(None)
            
    def close_all(self):
        """Close all opened scripts"""
        while self.close():
            pass
        
    def get_title(self, filename):
        """Return tab title"""
        if filename != self.file_path:
            return osp.basename(filename)
        else:
            return unicode(self.tr("Temporary file"))
        
    def load(self, filenames=None, goto=None):
        """Load a Python script file"""
        if filenames is None:
            self.mainwindow.shell.restore_stds()
            basedir = os.getcwd()
            if self.filenames:
                index = self.tabwidget.currentIndex()
                if self.filenames[index] != self.file_path:
                    basedir = osp.dirname(self.filenames[index])
            filenames = QFileDialog.getOpenFileNames(self,
                          self.tr("Open Python script"), basedir,
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.mainwindow.shell.redirect_stds()
            filenames = list(filenames)
            if len(filenames):
#                self.chdir( os.path.dirname(unicode(filenames[-1])) )
                filenames = [osp.normpath(unicode(fname)) for fname in filenames]
            else:
                return
            
        if not isinstance(filenames, list):
            filenames = [filenames]
            
        for filename in filenames:
            # -- Do not open an already opened file
            if filename in self.filenames:
                index = self.filenames.index(filename)
                self.tabwidget.setCurrentIndex(index)
                editor = self.editors[index]
                editor.setFocus()
            # --
            elif osp.isfile(filename):
                self.filenames.append(filename)
                txt, enc = encoding.read(filename)
                self.encodings.append(enc)
                
                # Editor widget creation
                editor = SimpleEditor(self, txt)
                self.connect(editor, SIGNAL("drop_files(PyQt_PyObject)"),
                             self.load)
                self.editors.append(editor)
                
                title = self.get_title(filename)
                index = self.tabwidget.addTab(editor, title)
                self.tabwidget.setTabToolTip(index, filename)
                self.tabwidget.setTabIcon(index, get_icon('python.png'))
                
                self.find_widget.set_editor(editor)
               
                self.change()
                self.tabwidget.setCurrentIndex(index)
                editor.setFocus()
            
            if goto is not None:
                editor.highlight_line(goto)

    def save_as(self):
        """Save the currently edited Python script file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            self.mainwindow.shell.restore_stds()
            filename = QFileDialog.getSaveFileName(self,
                          self.tr("Save Python script"), self.filenames[index],
                          self.tr("Python scripts")+" (*.py ; *.pyw)")
            self.mainwindow.shell.redirect_stds()
            if filename:
                filename = unicode(filename)
                self.filenames[index] = filename
#                self.chdir( os.path.dirname(filename) )
            else:
                return False
            self.save()
    
    def save(self):
        """Save the currently edited Python script file"""
        if self.tabwidget.count():
            index = self.tabwidget.currentIndex()
            txt = unicode(self.editors[index].get_text())
            self.encodings[index] = encoding.write(txt,
                                                   self.filenames[index],
                                                   self.encodings[index])
            self.editors[index].setModified(False)
            self.change()
            return True
        
    def change_font(self):
        """Change editor font"""
        font, valid = QFontDialog.getFont(get_font('editor'),
                          self, self.tr("Select a new font"))
        if valid:
            for index in range(0, self.tabwidget.count()):
                self.editors[index].set_font(font)
            set_font(font, 'editor')
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if hasattr(self, 'tabwidget'):
            for index in range(0, self.tabwidget.count()):
                self.editors[index].set_wrap_mode(checked)


class HistoryLog(EditorBaseWidget, WidgetMixin):
    """
    History log widget
    """
    def __init__(self, parent):
        EditorBaseWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)
        self.setReadOnly(True)
        self.set_font( get_font('history') )
        self.set_wrap_mode( CONF.get('history', 'wrap') )
        self.history = self.mainwindow.shell.interpreter.rawhistory
        self.refresh()
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&History log')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def refresh(self):
        """Refresh widget"""
        self.set_text("\n".join(self.history))
        self.set_cursor_to("End")
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True


class DocComboBox(EditableComboBox):
    """
    QComboBox handling doc viewer history
    """
    def __init__(self, parent):
        super(DocComboBox, self).__init__(parent)
        self.tips = {True: self.tr("Press enter to validate this object name"),
                     False: self.tr('This object name is incorrect')}
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        try:
            eval(unicode(qstr),
                 self.parent().mainwindow.shell.interpreter.locals)
            return True
        except:
            return False

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            text = self.currentText()
            if self.is_valid(text):
                self.parent().refresh(text)
                self.set_default_style()
        else:
            QComboBox.keyPressEvent(self, event)
    
class DocViewer(QWidget, WidgetMixin):
    """
    Docstrings viewer widget
    """
    log_path = get_conf_path('.docviewer')
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, parent)

        # Read-only editor
        self.editor = EditorBaseWidget(self, margin=False)
        self.editor.setReadOnly(True)
        self.editor.set_font( get_font('docviewer') )
        self.editor.set_wrap_mode( CONF.get('docviewer', 'wrap') )
        
        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.addWidget(QLabel(self.tr("Object")))
        self.combo = DocComboBox(self)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout_edit.addWidget(self.combo)
        self.combo.setMaxCount(CONF.get('docviewer', 'max_history_entries'))
        dvhistory = self.load_dvhistory()
        self.combo.addItems( dvhistory )
        
        self.help_or_doc = QCheckBox(self.tr("Show source"))
        self.connect(self.help_or_doc, SIGNAL("stateChanged(int)"),
                     self.toggle_help)
        layout_edit.addWidget(self.help_or_doc)
        self.docstring = None
        self.autosource = False
        self.toggle_help(Qt.Unchecked)

        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(layout_edit)
        layout.addWidget(self.editor)
        self.setLayout(layout)
        
    def get_name(self, raw=True):
        """Return widget name"""
        name = self.tr('&Doc')
        if raw:
            return name
        else:
            return name.replace("&", "")
    
    def get_dockwidget_properties(self):
        """Return QDockWidget properties"""
        return (Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea |
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea,
                Qt.TopDockWidgetArea)
        
    def load_dvhistory(self, obj=None):
        """Load history from a text file in user home directory"""
        if osp.isfile(self.log_path):
            dvhistory = [line.replace('\n','')
                         for line in file(self.log_path, 'r').readlines()]
        else:
            dvhistory = [ ]
        return dvhistory
    
    def save_dvhistory(self):
        """Save history to a text file in user home directory"""
        file(self.log_path, 'w').write("\n".join( \
            [ unicode( self.combo.itemText(index) )
                for index in range(self.combo.count()) ] ))
        
    def toggle_help(self, state):
        """Toggle between docstring and help()"""
        self.docstring = (state == Qt.Unchecked)
        self.refresh()
        
    def refresh(self, text=None):
        """Refresh widget"""
        if text is None:
            text = self.combo.currentText()
        else:
            index = self.combo.findText(text)
            while index!=-1:
                self.combo.removeItem(index)
                index = self.combo.findText(text)
            self.combo.insertItem(0, text)
            self.combo.setCurrentIndex(0)
        self.set_help(text)
        self.save_dvhistory()
        
    def set_help(self, obj_text):
        """Show help"""
        obj_text = unicode(obj_text)
        hlp_text = None
        try:
            obj = eval(obj_text, self.mainwindow.shell.interpreter.locals)
            if self.docstring:
                hlp_text = getdoc(obj)
                if hlp_text is None:
                    self.help_or_doc.setChecked(True)
                    return
            else:
                hlp_text = getsource(obj)
        except:
            pass
        if hlp_text is None:
            hlp_text = self.tr("No documentation available.")
        self.editor.set_text(hlp_text)
        self.editor.set_cursor_to("Start")
        
    def set_actions(self):
        """Setup actions"""
        return (None, None)
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

