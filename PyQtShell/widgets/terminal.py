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

import sys, os, time
import os.path as osp

from PyQt4.QtGui import QMenu, QApplication, QCursor
from PyQt4.QtCore import Qt, QString, QCoreApplication, SIGNAL, pyqtProperty
from PyQt4.Qsci import QsciScintilla, QsciLexerPython

# For debugging purpose:
STDOUT = sys.stdout
STDERR = sys.stderr

# Local import
from PyQtShell import __version__, encoding
from PyQtShell.config import CONF, get_icon
from PyQtShell.qthelpers import (translate, keybinding, create_action,
                                 add_actions)
from PyQtShell.widgets.qscibase import QsciBase
from PyQtShell.widgets.shellhelpers import get_error_match


class QsciTerminal(QsciBase):
    """
    Terminal based on QScintilla
    """
    inithistory = [
                   '# -*- coding: utf-8 -*-',
                   '# *** PyQtShell v%s -- History log ***' % __version__,
                   '',
                   ]
    separator = '%s# ---(%s)---' % (os.linesep, time.ctime())
    
    def __init__(self, parent, history_filename, max_history_entries=100,
                 debug=False, profile=False):
        """
        parent : specifies the parent widget
        """
        QsciBase.__init__(self, parent)
        
        # Prompt position: tuple (line, index)
        self.current_prompt_pos = None
        self.new_input_line = True
        
        # History
        self.max_history_entries = max_history_entries
        self.histidx = None
        self.hist_wholeline = False
        assert isinstance(history_filename, (str, unicode))
        self.history_filename = history_filename
        self.rawhistory, self.history = self.load_history()
            
        # Context menu
        self.menu = None
        self.setup_context_menu()

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
        add_actions(self.menu, (self.cut_action, self.copy_action,
                                paste_action) )
          
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        state = self.hasSelectedText()
        self.copy_action.setEnabled(state)
        self.cut_action.setEnabled(state)
        self.menu.popup(event.globalPos())
        event.accept()        
        
        
    #------ Input buffer
    def get_current_line_to_cursor(self):
        line, index = self.getCursorPosition()
        pline, pindex = self.current_prompt_pos
        self.setSelection(pline, pindex, line, index)
        selected_text = unicode(self.selectedText())
        self.clear_selection()
        return selected_text
    
    def _select_input(self):
        """Select current line (without selecting console prompt)"""
        line, index = self.get_end_pos()
        pline, pindex = self.current_prompt_pos
        self.setSelection(pline, pindex, line, index)
            
    def clear_line(self):
        """Clear current line (without clearing console prompt)"""
        self._select_input()
        self.removeSelectedText()

    # The buffer being edited
    def _set_input_buffer(self, text):
        """Set input buffer"""
        self._select_input()
        self.replace(text)
        self.move_cursor_to_end()

    def _get_input_buffer(self):
        """Return input buffer"""
        self._select_input()
        input_buffer = self.selectedText()
        self.clear_selection()
        input_buffer = input_buffer.replace(os.linesep, '\n')
        return unicode(input_buffer)

    input_buffer = pyqtProperty("QString", _get_input_buffer, _set_input_buffer)
        
        
    #------ Prompt
    def new_prompt(self, prompt):
        """
        Print a new prompt and save its (line, index) position
        """
        self.write(prompt, flush=True)
        # now we update our cursor giving end of prompt
        self.current_prompt_pos = self.getCursorPosition()
        self.ensureCursorVisible()
        
    def check_selection(self):
        """
        Check if selected text is r/w,
        otherwise remove read-only parts of selection
        """
        line_from, index_from, line_to, index_to = self.getSelection()
        pline, pindex = self.current_prompt_pos
        if line_from < pline or \
           (line_from == pline and index_from < pindex):
            self.setSelection(pline, pindex, line_to, index_to)
        
        
    #------ Copy / Keyboard interrupt
    def copy(self):
        """Copy text to clipboard... or keyboard interrupt"""
        if self.hasSelectedText():
            QsciScintilla.copy(self)
        else:
            self.emit(SIGNAL("keyboard_interrupt()"))
        
        
    #------ Basic keypress event handler
    def keyPressEvent(self, event):
        """
        Reimplement Qt Method
        Basic keypress event handler
        (reimplemented in ShellBaseWidget to add more sophisticated features)
        """
        text = event.text()
        key = event.key()
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier
        last_line = self.lines()-1

        if self.new_input_line:
            # Move cursor to end
            self.move_cursor_to_end()
            self.current_prompt_pos = self.getCursorPosition()
            self.new_input_line = False

        line, index = self.getCursorPosition()

        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.insert_text('\n', at_end=True)
            command = self.input_buffer
            self.emit(SIGNAL("execute(QString)"), command)
            self.add_to_history(command)
            self.new_input_line = True
            
        elif key == Qt.Key_Delete:
            if self.hasSelectedText():
                self.check_selection()
                self.removeSelectedText()
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_CLEAR)
            
        elif key == Qt.Key_Backspace:
            if self.hasSelectedText():
                self.check_selection()
                self.removeSelectedText()
            elif self.current_prompt_pos == (line, index):
                # Avoid deleting prompt
                return
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_DELETEBACK)

        elif key == Qt.Key_Left:
            if self.current_prompt_pos == (line, index):
                # Avoid moving cursor on prompt
                return
            if shift:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDLEFTEXTEND)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARLEFTEXTEND)
            else:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDLEFT)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARLEFT)
                
        elif key == Qt.Key_Right:
            if self.is_cursor_at_end():
                return
            if shift:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDRIGHTEXTEND)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARRIGHTEXTEND)
            else:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDRIGHT)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARRIGHT)

        elif (key == Qt.Key_Home) or ((key == Qt.Key_Up) and ctrl):
            if self.isListActive():
                self.SendScintilla(QsciScintilla.SCI_VCHOME)
            elif self.is_cursor_on_last_line():
                self.setCursorPosition(*self.current_prompt_pos)

        elif (key == Qt.Key_End) or ((key == Qt.Key_Down) and ctrl):
            if self.isListActive():
                self.SendScintilla(QsciScintilla.SCI_LINEEND)
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_LINEEND)

        elif key == Qt.Key_Up:
            if line != last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() > self.getpointy(prompt=True):
                self.SendScintilla(QsciScintilla.SCI_LINEUP)
            else:
                self.browse_history(backward=True)
                
        elif key == Qt.Key_Down:
            if line != last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() < self.getpointy(end=True):
                self.SendScintilla(QsciScintilla.SCI_LINEDOWN)
            else:
                self.browse_history(backward=False)
            
        elif key == Qt.Key_PageUp:
            if self.isListActive() or self.isCallTipActive():
                self.SendScintilla(QsciScintilla.SCI_PAGEUP)
            
        elif key == Qt.Key_PageDown:
            if self.isListActive() or self.isCallTipActive():
                self.SendScintilla(QsciScintilla.SCI_PAGEDOWN)

        elif key == Qt.Key_Escape:
            if self.isListActive() or self.isCallTipActive():
                self.SendScintilla(QsciScintilla.SCI_CANCEL)
            else:
                self.clear_line()
                
        elif key == Qt.Key_C and ctrl:
            self.copy()
                
        elif key == Qt.Key_V and ctrl:
            self.paste()
            
        elif key == Qt.Key_X and ctrl:
            self.cut()
            
        elif key == Qt.Key_Z and ctrl:
            self.undo()
            
        elif key == Qt.Key_Y and ctrl:
            self.redo()

        elif ((key == Qt.Key_Plus) and ctrl) \
             or ((key==Qt.Key_Equal) and shift and ctrl):
            self.zoomIn()

        elif (key == Qt.Key_Minus) and ctrl:
            self.zoomOut()

        elif text.length():
            if self.hasSelectedText():
                self.check_selection()
            self.hist_wholeline = False
            QsciScintilla.keyPressEvent(self, event)
                
        else:
            # Let the parent widget handle the key press event
            event.ignore()
        
        
    #------ History Management
    def load_history(self):
        """Load history from a .py file in user home directory"""
        if osp.isfile(self.history_filename):
            rawhistory, _ = encoding.readlines(self.history_filename)
            rawhistory = [line.replace('\n','') for line in rawhistory]
            if rawhistory[1] != self.inithistory[1]:
                rawhistory = self.inithistory
        else:
            rawhistory = self.inithistory
        history = [line for line in rawhistory if not line.startswith('#')]
        rawhistory.append(self.separator)
        return rawhistory, history
    
    def save_history(self):
        """Save history to a .py file in user home directory"""
        if self.rawhistory[-1] == self.separator:
            self.rawhistory.remove(self.separator)
        encoding.writelines(self.rawhistory, self.history_filename)
        
    def add_to_history(self, command):
        """Add command to history
        commmand string must end with '\n'"""
        command = unicode(command)
        if not command.endswith('\n') or command == '\n' \
           or command.startswith('Traceback'):
            return
        command = command[:-1]
        self.histidx = None
        while len(self.history) >= self.max_history_entries:
            del self.history[0]
            while self.rawhistory[0].startswith('#'):
                del self.rawhistory[0]
            del self.rawhistory[0]
        if len(self.history)>0 and self.history[-1] == command:
            return
        self.history.append(command)
        self.rawhistory.append(command)
        
    def browse_history(self, backward):
        """Browse history"""
        line, index = self.getCursorPosition()
        if index < self.lineLength(line) and self.hist_wholeline:
            self.hist_wholeline = False
        tocursor = self.get_current_line_to_cursor()
        text, self.histidx = self.__find_in_history(tocursor,
                                                    self.histidx, backward)
        if text is not None:
            if self.hist_wholeline:
                self.clear_line()
                self.insert_text(text)
            else:
                # Removing text from cursor to the end of the line
                self.setSelection(line, index, line, self.lineLength(line))
                self.removeSelectedText()
                # Inserting history text
                self.insert_text(text)
                self.setCursorPosition(line, index)

    def __find_in_history(self, tocursor, start_idx, backward):
        """Find text 'tocursor' in history, from index 'start_idx'"""
        if start_idx is None:
            start_idx = len(self.history)
        # Finding text in history
        step = -1 if backward else 1
        idx = start_idx
        if len(tocursor) == 0 or self.hist_wholeline:
            idx += step
            if idx >= len(self.history):
                return "", len(self.history)
            elif idx < 0:
                idx = 0
            self.hist_wholeline = True
            return self.history[idx], idx
        else:
            for index in xrange(len(self.history)):
                idx = (start_idx+step*(index+1)) % len(self.history)
                entry = self.history[idx]
                if entry.startswith(tocursor):
                    return entry[len(tocursor):], idx
            else:
                return None, start_idx
    
    
    #------ Simulation standards input/output
    def write_error(self, text):
        """Simulate stderr"""
#        self.flush()
        self.write(text, flush=True, error=True)
        if self.debug:
            STDERR.write(text)

    def write(self, text, flush=False, error=False):
        """Simulate stdout and stderr"""
        if isinstance(text, QString):
            # This test is useful to discriminate QStrings from decoded str
            text = unicode(text)
        self.__buffer.append(text)
        ts = time.time()
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
        # Clear input buffer:
        self.new_input_line = True

        
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
        
    def mousePressEvent(self, event):
        """
        Re-implemented to handle the mouse press event.
        event: the mouse press event (QMouseEvent)
        """
        self.setFocus()
        ctrl = event.modifiers() & Qt.ControlModifier
        if event.button() == Qt.MidButton:
            self.paste()
        elif event.button() == Qt.LeftButton and ctrl:
            text = unicode(self.text(self.lineAt(event.pos())))
            self.emit(SIGNAL("go_to_error(QString)"), text)
        else:
            QsciScintilla.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        """Show Pointing Hand Cursor on error messages"""
        if event.modifiers() & Qt.ControlModifier:
            text = unicode(self.text(self.lineAt(event.pos())))
            if get_error_match(text):
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                return
        QApplication.restoreOverrideCursor()
        QsciScintilla.mouseMoveEvent(self, event)
    
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
