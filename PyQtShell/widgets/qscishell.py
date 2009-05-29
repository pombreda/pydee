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

from PyQt4.QtGui import QMenu, QApplication, QCursor, QToolTip
from PyQt4.QtCore import (Qt, QString, QCoreApplication, SIGNAL, pyqtProperty,
                          QStringList)
from PyQt4.Qsci import QsciScintilla, QsciLexerPython

# For debugging purpose:
STDOUT = sys.stdout
STDERR = sys.stderr

# Local import
from PyQtShell import __version__, encoding
from PyQtShell.config import CONF, get_icon, get_font
from PyQtShell.dochelpers import getobj, getargtxt
from PyQtShell.qthelpers import (translate, keybinding, create_action,
                                 add_actions, restore_keyevent)
from PyQtShell.widgets.qscibase import QsciBase
from PyQtShell.widgets.shellhelpers import get_error_match


class QsciShell(QsciBase):
    """
    Shell based on QScintilla
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
        
        self.docviewer = None
        
        # History
        self.max_history_entries = max_history_entries
        self.histidx = None
        self.hist_wholeline = False
        assert isinstance(history_filename, (str, unicode))
        self.history_filename = history_filename
        self.rawhistory, self.history = self.load_history()
        
        # Code completion / calltips
        self.completion_chars = 0
        self.calltip_index = None
        self.setAutoCompletionThreshold( \
            CONF.get('external_shell', 'autocompletion/threshold') )
        self.setAutoCompletionCaseSensitivity( \
            CONF.get('external_shell', 'autocompletion/case-sensitivity') )
        self.setAutoCompletionShowSingle( \
            CONF.get('external_shell', 'autocompletion/select-single') )
        if CONF.get('external_shell', 'autocompletion/from-document'):
            self.setAutoCompletionSource(QsciScintilla.AcsDocument)
        else:
            self.setAutoCompletionSource(QsciScintilla.AcsNone)
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     self.completion_list_selected)
        
        # Call-tips
        self.calltips = True
            
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
        
        # Mouse cursor
        self.__cursor_changed = False

        # Give focus to widget
        self.setFocus()
        
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state
            
                
    def setup_scintilla(self):
        """Reimplement QsciBase method"""
        QsciBase.setup_scintilla(self)
        
        # Wrapping
        if CONF.get('shell', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
        # Caret
        self.setCaretForegroundColor(Qt.darkGray)
        self.setCaretWidth(2)
        
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
                           translate("InteractiveShell", "Cut"),
                           shortcut=keybinding('Cut'),
                           icon=get_icon('editcut.png'), triggered=self.cut)
        self.copy_action = create_action(self,
                           translate("InteractiveShell", "Copy"),
                           shortcut=keybinding('Copy'),
                           icon=get_icon('editcopy.png'), triggered=self.copy)
        paste_action = create_action(self,
                           translate("InteractiveShell", "Paste"),
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

    def cut(self):
        """Cut text"""
        self.check_selection()
        if self.hasSelectedText():
            QsciScintilla.cut(self)

    def delete(self):
        """Remove selected text"""
        self.check_selection()
        if self.hasSelectedText():
            QsciScintilla.removeSelectedText(self)
        
        
    #------ Basic keypress event handler
    def on_enter(self, command):
        """on_enter"""
        self.emit(SIGNAL("execute(QString)"), command)
        self.add_to_history(command)
        self.new_input_line = True
        
    def keyPressEvent(self, event):
        """
        Reimplement Qt Method
        Basic keypress event handler
        (reimplemented in InteractiveShell to add more sophisticated features)
        """
        if self.new_input_line:
            # Move cursor to end
            self.move_cursor_to_end()
            self.current_prompt_pos = self.getCursorPosition()
            self.new_input_line = False
            
        self.process_keyevent(event)
        
    def process_keyevent(self, event):
        """Process keypress event"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        
        last_line = self.lines()-1
        
        # Copy must be done first to be able to copy read-only text parts
        # (otherwise, right below, we would remove selection
        #  if not on current line)                        
        if key == Qt.Key_C and ctrl:
            self.copy()
            event.accept()
            return
        
        # Is cursor on the last line? and after prompt?
        if len(text):
            if self.hasSelectedText():
                self.check_selection()
            line, index = self.getCursorPosition()
            _pline, pindex = self.current_prompt_pos
            if line != last_line:
                # Moving cursor to the end of the last line
                self.move_cursor_to_end()
            elif index < pindex:
                # Moving cursor after prompt
                self.setCursorPosition(line, pindex)

        line, index = self.getCursorPosition()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.is_cursor_on_last_line():
                if self.isListActive():
                    self.SendScintilla(QsciScintilla.SCI_NEWLINE)
                else:
                    self.insert_text('\n', at_end=True)
                    command = self.input_buffer
                    self.on_enter(command)
            # add and run selection
            else:
                text = self.selectedText()
                self.insert_text(text, at_end=True)
            event.accept()
            
        elif key == Qt.Key_Delete:
            if self.hasSelectedText():
                self.check_selection()
                self.removeSelectedText()
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_CLEAR)
            event.accept()
            
        elif key == Qt.Key_Backspace:
            event.accept()
            if self.hasSelectedText():
                self.check_selection()
                self.removeSelectedText()
            elif self.current_prompt_pos == (line, index):
                # Avoid deleting prompt
                return
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
            
        elif key == Qt.Key_Tab:
            if self.isListActive():
                self.SendScintilla(QsciScintilla.SCI_TAB)
            elif self.is_cursor_on_last_line():
                buf = self.get_current_line_to_cursor()
                empty_line = not buf.strip()
                if empty_line:
                    self.SendScintilla(QsciScintilla.SCI_TAB)
                elif buf.endswith('.'):
                    self.show_code_completion(self.get_last_obj())
                elif buf[-1] in ['"', "'"]:
                    self.show_file_completion()
            event.accept()

        elif key == Qt.Key_Left:
            event.accept()
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
            event.accept()
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
            event.accept()

        elif (key == Qt.Key_End) or ((key == Qt.Key_Down) and ctrl):
            if self.isListActive():
                self.SendScintilla(QsciScintilla.SCI_LINEEND)
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_LINEEND)
            event.accept()

        elif key == Qt.Key_Up:
            if line != last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() > self.getpointy(prompt=True):
                self.SendScintilla(QsciScintilla.SCI_LINEUP)
            else:
                self.browse_history(backward=True)
            event.accept()
                
        elif key == Qt.Key_Down:
            if line != last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() < self.getpointy(end=True):
                self.SendScintilla(QsciScintilla.SCI_LINEDOWN)
            else:
                self.browse_history(backward=False)
            event.accept()
            
        elif key == Qt.Key_PageUp:
            if self.isListActive() or self.isCallTipActive():
                self.SendScintilla(QsciScintilla.SCI_PAGEUP)
            event.accept()
            
        elif key == Qt.Key_PageDown:
            if self.isListActive() or self.isCallTipActive():
                self.SendScintilla(QsciScintilla.SCI_PAGEDOWN)
            event.accept()

        elif key == Qt.Key_Escape:
            if self.isListActive() or self.isCallTipActive():
                self.SendScintilla(QsciScintilla.SCI_CANCEL)
            else:
                self.clear_line()
            event.accept()
                
        elif key == Qt.Key_V and ctrl:
            self.paste()
            event.accept()
            
        elif key == Qt.Key_X and ctrl:
            self.cut()
            event.accept()
            
        elif key == Qt.Key_Z and ctrl:
            self.undo()
            event.accept()
            
        elif key == Qt.Key_Y and ctrl:
            self.redo()
            event.accept()
                
        elif key == Qt.Key_Question:
            if self.get_current_line_to_cursor():
                self.show_docstring(self.get_last_obj())
                _, self.calltip_index = self.getCursorPosition()
            self.insert_text(text)
            # In case calltip and completion are shown at the same time:
            if self.isListActive():
                self.completion_chars += 1
            event.accept()
            
        elif key == Qt.Key_ParenLeft:
            self.cancelList()
            if self.get_current_line_to_cursor():
                self.show_docstring(self.get_last_obj(), call=True)
                _, self.calltip_index = self.getCursorPosition()
            self.insert_text(text)
            event.accept()
            
        elif key == Qt.Key_Period:
            # Enable auto-completion only if last token isn't a float
            self.insert_text(text)
            last_obj = self.get_last_obj()
            if last_obj and not last_obj[-1].isdigit():
                self.show_code_completion(last_obj)
            event.accept()

        elif ((key == Qt.Key_Plus) and ctrl) \
             or ((key==Qt.Key_Equal) and shift and ctrl):
            self.zoomIn()
            event.accept()

        elif (key == Qt.Key_Minus) and ctrl:
            self.zoomOut()
            event.accept()

        elif text.length():
            self.hist_wholeline = False
            QsciScintilla.keyPressEvent(self, event)
            if self.isListActive():
                self.completion_chars += 1
            event.accept()
                
        else:
            # Let the parent widget handle the key press event
            event.ignore()

        
        if QToolTip.isVisible():
            # Hide calltip when necessary (this is handled here because
            # QScintilla does not support user-defined calltips)
            _, index = self.getCursorPosition() # need the new index
            try:
                if (self.text(line)[self.calltip_index] not in ['?','(']) or \
                   index < self.calltip_index or \
                   key in (Qt.Key_ParenRight, Qt.Key_Period, Qt.Key_Tab):
                    QToolTip.hideText()
            except (IndexError, TypeError):
                QToolTip.hideText()
        
        
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
        """Add command to history"""
        command = unicode(command)
        if command in ['', '\n'] or command.startswith('Traceback'):
            return
        if command.endswith('\n'):
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
        if index < self.text(line).length() and self.hist_wholeline:
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
    
  
    #------ Code Completion / Calltips        
    def completion_list_selected(self, userlist_id, seltxt):
        """
        Private slot to handle the selection from the completion list
        userlist_id: ID of the user list (should be 1) (integer)
        seltxt: selected text (QString)
        """
        if userlist_id == 1:
            cline, cindex = self.getCursorPosition()
            self.setSelection(cline, cindex-self.completion_chars+1,
                              cline, cindex)
            self.removeSelectedText()
            seltxt = unicode(seltxt)
            self.insert_text(seltxt)
            self.completion_chars = 0

    def show_completion_list(self, completions, text):
        """Private method to display the possible completions"""
        if len(completions) == 0:
            return
        if len(completions) > 1:
            self.showUserList(1, QStringList(sorted(completions)))
            self.completion_chars = 1
        else:
            txt = completions[0]
            if text != "":
                txt = txt.replace(text, "")
            self.insert_text(txt)
            self.completion_chars = 0
            
    def eval(self, text):
        """Is text a valid object?"""
        try:
            return eval(text), True
        except:
            try:
                return __import__(text), True
            except:
                return None, False

    def show_code_completion(self, text):
        """
        Display a completion list based on the last token
        """
        obj, valid = self.eval(text)
        if valid:
            self.show_completion_list(dir(obj), 'dir(%s)' % text) 

    def show_file_completion(self):
        """
        Display a completion list for files and directories
        """
        cwd = os.getcwdu()
        self.show_completion_list(os.listdir(cwd), cwd)
    
    def show_docstring(self, text, call=False):
        """Show docstring or arguments"""
        if not self.calltips:
            return
        obj, valid = self.eval(text)
        if valid:
            tipsize = CONF.get('calltips', 'size')
            font = get_font('calltips')
            done = False
            if (self.docviewer is not None) and \
               (self.docviewer.dockwidget.isVisible()):
                # DocViewer widget exists and is visible
                self.docviewer.refresh(text)
                if call:
                    # Display argument list if this is function call
                    if callable(obj):
                        arglist = getargtxt(obj)
                        if arglist:
                            done = True
                            self.show_calltip(self.tr("Arguments"),
                                              arglist, tipsize, font,
                                              color='#129625')
                    else:
                        done = True
                        self.show_calltip(self.tr("Warning"),
                                          self.tr("Object `%1` is not callable"
                                                  " (i.e. not a function, "
                                                  "a method or a class "
                                                  "constructor)").arg(text),
                                          font=font, color='#FF0000')
            if not done:
                self.show_calltip(self.tr("Documentation"),
                                  obj.__doc__, tipsize, font)
        
        
    #------ Miscellanous
    def get_last_obj(self, last=False):
        """
        Return the last valid object on the current line
        """
        return getobj(self.get_current_line_to_cursor(), last=last)
        
    def set_docviewer(self, docviewer):
        """Set DocViewer DockWidget reference"""
        self.docviewer = docviewer


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
        #TODO: improve the error text styling
        # -> remove these ugly startswith (replace by a regexp -> see get_error_match)
        # -> replace the traceback_link_style by an underline QScintilla indicator
        #    (it should be possible to detect the indicator on mouse hover)
        if error and text.startswith('  File "<'):
            return
        if at_end:
            # Insert text at the end of the command line
            self.move_cursor_to_end()
            self.SendScintilla(QsciScintilla.SCI_STARTSTYLING,
                               self.text().length(), 0xFF)
            self.append(text)
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
            self.move_cursor_to_end()
        else:
            # Insert text at current cursor position
            line, col = self.getCursorPosition()
            self.insertAt(text, line, col)
            self.setCursorPosition(line, col + len(unicode(text)))

            
    #------ Re-implemented Qt Methods
    def focusNextPrevChild(self, next):
        """
        Reimplemented to stop Tab moving to the next window
        """
        if next:
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
            if get_error_match(text) and not self.__cursor_changed:
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                self.__cursor_changed = True
                return
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False
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
