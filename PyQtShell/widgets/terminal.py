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

"""Terminal widget based on QScintilla"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys
from time import time

from PyQt4.QtGui import QMenu, QKeySequence
from PyQt4.QtCore import Qt, QString, QEventLoop, QCoreApplication
from PyQt4.Qsci import QsciScintilla, QsciLexerPython

# For debugging purpose:
STDOUT = sys.stdout
STDERR = sys.stderr

# Local import
from PyQtShell.config import CONF, get_icon
from PyQtShell.qthelpers import (translate, keybinding, create_action,
                                 add_actions)
from PyQtShell.widgets.qscibase import QsciBase

#TODO: Outside QsciTerminal: replace most of 'insert_text' occurences by 'write'

#TODO: Prepare code for IPython integration:
#    - implement the self.input_buffer property (see qt_console_widget.py)
#    - remove all references to prompt (there is no need to keep prompt
#      string in self.prompt) and use prompt position instead (like it's
#      done in qt_console_widget.py: self.current_prompt_pos -- do not
#      implement self.current_prompt_line which is dead code from the
#      porting from wx's console_widget.py)
#    - implement the 'new_prompt' method like in qt_console_widget.py
#    - implement the 'pop_completion' method like in qt_console_widget.py
#      (easy... just rename a few methods here and there)
#    - implement the 'new_prompt' method like in qt_console_widget.py
#    - implement '_configure_scintilla', '_apply_style', ...
#    - implement 'write' method -> this change will eventually require
#      to merge with shellbase.py where there's already a 'write' method

class IOHandler(object):
    """Handle stream output"""
    def __init__(self, write):
        self._write = write
    def write(self, cmd):
        self._write(cmd)
    def flush(self):
        pass


class QsciTerminal(QsciBase):
    """
    Terminal based on QScintilla
    """
    def __init__(self, parent=None, debug=False, profile=False):
        """
        parent : specifies the parent widget
        """
        QsciBase.__init__(self, parent)

        # Debug mode
        self.debug = debug

        # Simple profiling test
        self.profile = profile
        
        # write/flush
        self.__buffer = []
        self.__timestamp = 0.0
        
        # Allow raw_input support:
        self.input_loop = None
        self.input_mode = False
        
        # capture all interactive input/output 
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        self.stdout = self
        self.stderr = IOHandler(self.write_error)
        self.stdin = self
        self.redirect_stds()
        
        # Mouse selection copy feature
        self.always_copy_selection = False

        # Give focus to widget
        self.setFocus()
        
    def setup_scintilla(self):
        """Reimplement QsciBase method"""
        QsciBase.setup_scintilla(self)
        
        # Wrapping
        if CONF.get('shell', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
        # Suppressing Scintilla margins
        self.remove_margins()
        
        # Lexer
        self.lex = QsciLexerPython(self)
        self.error_style = self.lex.Decorator
        self.traceback_link_style = self.lex.CommentBlock
        self.lex.setColor(Qt.black, self.lex.Default)
        self.lex.setColor(Qt.red, self.error_style)
        self.lex.setColor(Qt.blue, self.traceback_link_style)

    def setUndoRedoEnabled(self, state):
        """Fake Qt method (QTextEdit)"""
        pass

    def set_font(self, font):
        """Set shell font"""
        self.lex.setFont(font)
        font.setUnderline(True)
        self.lex.setFont(font, self.traceback_link_style)
        self.setLexer(self.lex)

    #------ Context menu
    def setup_context_menu(self):
        """Setup shell context menu"""
        self.menu = QMenu(self)
        self.cut_action = create_action(self,
                           translate("ShellBaseWidget", "Cut"),
                           shortcut=keybinding('Cut'),
                           icon=get_icon('editcut.png'), triggered=self.cut)
        self.copy_action = create_action(self,
                           translate("ShellBaseWidget", "Copy"),
                           shortcut=keybinding('Copy'),
                           icon=get_icon('editcopy.png'), triggered=self.copy)
        paste_action = create_action(self,
                           translate("ShellBaseWidget", "Paste"),
                           shortcut=keybinding('Paste'),
                           icon=get_icon('editpaste.png'), triggered=self.paste)
        clear_line_action = create_action(self,
                           self.tr("Clear line"),
                           QKeySequence("Escape"),
                           icon=get_icon('eraser.png'),
                           tip=translate("ShellBaseWidget", "Clear line"),
                           triggered=self.clear_line)
        clear_action = create_action(self,
                           translate("ShellBaseWidget", "Clear shell"),
                           icon=get_icon('clear.png'),
                           tip=translate("ShellBaseWidget",
                                   "Clear shell contents ('cls' command)"),
                           triggered=self.clear_terminal)
        add_actions(self.menu, (self.cut_action, self.copy_action, paste_action,
                                clear_line_action, None, clear_action, None) )
          
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        state = self.hasSelectedText()
        self.copy_action.setEnabled(state)
        self.cut_action.setEnabled(state)
        self.menu.popup(event.globalPos())
        event.accept()        
    
    #------ Standard input/output
    def redirect_stds(self):
        """Redirects stds"""
        if not self.debug:
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            sys.stdin  = self.stdin
        
    def restore_stds(self):
        """Restore stds"""
        if not self.debug:
            sys.stdout = self.initial_stdout
            sys.stderr = self.initial_stderr
            sys.stdin = self.initial_stdin
    
    def readline(self):
        """For help() support (to be implemented...)"""
        #TODO: help() support -> won't implement it (because IPython is coming)
        inp = self.wait_input()
        return inp
        
    def wait_input(self):
        """Wait for input (raw_input)"""
        self.input_data = None # If shell is closed, None will be returned
        self.input_mode = True
        self.input_loop = QEventLoop()
        self.input_loop.exec_()
        self.input_loop = None
        return self.input_data
    
    def end_input(self, cmd):
        """End of wait_input mode"""
        self.input_data = cmd
        self.input_mode = False
        self.input_loop.exit()

    def write_error(self, text):
        """Simulate stderr"""
#        self.flush()
        self.write(text, flush=True, error=True)
        STDERR.write(text)

    def write(self, text, flush=False, error=False):
        """Simulate stdout and stderr"""
        if isinstance(text, QString):
            # This test is useful to discriminate QStrings from decoded str
            text = unicode(text)
        self.__buffer.append(text)
        ts = time()
        if flush or ts-self.__timestamp > 0.05:
            self.flush(error=error)
            self.__timestamp = ts

    def flush(self, error=False):
        """Flush buffer, write text to console"""
        text = "".join(self.__buffer)
        self.__buffer = []
        self.insert_text(text, at_end=True, error=error)
        QCoreApplication.processEvents()
        self.repaint()

        
    #------ Utilities
    def getpointy(self, cursor=True, end=False, prompt=False):
        """Return point y of cursor, end or prompt"""
        line, index = self.getCursorPosition()
        if end:
            line, index = self.get_end_pos()
        elif prompt:
            index = 0
        pos = self.position_from_lineindex(line, index)
        return self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION,
                                  0, pos)


    #------ Text Insertion
    def insert_text(self, text, at_end=False, error=False):
        """
        Insert text at the current cursor position
        or at the end of the command line
        """
        if error and text.startswith('  File "<'):
            return
        if at_end:
            # Insert text at the end of the command line
            line, col = self.get_end_pos()
            self.setCursorPosition(line, col)
            self.SendScintilla(QsciScintilla.SCI_STARTSTYLING,
                               self.text().length(), 0xFF)
            self.insert(text)
            if error:
                if text.startswith('  File'):
                    self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                       len(text), self.traceback_link_style)
                else:
                    self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                       len(text), self.error_style)
            else:
                self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                   len(text), self.lex.Default)
            self.prline, self.prcol = self.get_end_pos()
            self.setCursorPosition(self.prline, self.prcol)
            self.ensureCursorVisible()
            self.ensureLineVisible(self.prline)
        else:
            # Insert text at current cursor position
            line, col = self.getCursorPosition()
            self.insertAt(text, line, col)
            self.setCursorPosition(line, col + len(unicode(text)))

            
    #------ Re-implemented Qt Methods
    def focusNextPrevChild(self, next):
        """
        Reimplemented to stop Tab moving to the next window
        While the user is entering a multi-line command, the movement to
        the next window by the Tab key being pressed is suppressed.
        next: next window
        @return flag indicating the movement
        """
        if next and self.more:
            return False
        return QsciScintilla.focusNextPrevChild(self, next)
    
    def mouseReleaseEvent(self, event):
        """Reimplemented"""
        if self.hasSelectedText() and self.always_copy_selection:
            self.copy()
        QsciScintilla.mouseReleaseEvent(self, event)

    
    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Drag and Drop - Enter event"""
        event.setAccepted(event.mimeData().hasFormat("text/plain"))

    def dragMoveEvent(self, event):
        """Drag and Drop - Move event"""
        if (event.mimeData().hasFormat("text/plain")):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Drag and Drop - Drop event"""
        if(event.mimeData().hasFormat("text/plain")):
            text = event.mimeData().text()
            self.insert_text(text, at_end=True)
            self.setFocus()
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()


    #------ Clear line, terminal
    def clear_line(self):
        """Clear current line"""
        cline, _cindex = self.getCursorPosition()
        self.setSelection(cline, len(self.prompt),
                          cline, self.lineLength(cline))
        self.removeSelectedText()
            
    def clear_terminal(self):
        """Clear terminal window and write prompt"""
        self.clear()
        self.write(self.prompt, flush=True)
