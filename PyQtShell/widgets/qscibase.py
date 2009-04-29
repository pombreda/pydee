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

"""Editor and terminal base widgets based on QScintilla"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os
from PyQt4.QtGui import QApplication, QClipboard, QCursor, QMouseEvent
from PyQt4.QtCore import Qt, SIGNAL, QString, QStringList, QEvent, QPoint
from PyQt4.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs

# For debugging purpose:
STDOUT = sys.stdout

# Local import
import re
from PyQtShell.config import CONF, get_font
from PyQtShell.dochelpers import getobj


class LexerPython(QsciLexerPython):
    """ 
    Subclass to implement some additional lexer dependant methods.
    """
    COMMENT_STRING = '#'
    
    def __init__(self, parent):
        QsciLexerPython.__init__(self, parent)
        self.setIndentationWarning(QsciLexerPython.Inconsistent)
    
    def getIndentationDifference(self, line, editor):
        """
        Private method to determine the difference for the new indentation.
        """
        indent_width = 4
        lead_spaces = editor.indentation(line)
        
        pline = line - 1
        while pline >= 0 and re.match('^\s*(#.*)?$',
                                      unicode(editor.text(pline))):
            pline -= 1
        
        if pline < 0:
            last = 0
        else:
            previous_lead_spaces = editor.indentation(pline)
            # trailing spaces
            m = re.search(':\s*(#.*)?$', unicode(editor.text(pline)))
            last = previous_lead_spaces
            if m:
                last += indent_width
            else:
                # special cases, like pass (unindent) or return (also unindent)
                m = re.search('(pass\s*(#.*)?$)|(^[^#]return)', 
                              unicode(editor.text(pline)))
                if m:
                    last -= indent_width
        
        if lead_spaces % indent_width != 0 or lead_spaces == 0 \
           or self.lastIndented != line:
            indentDifference = last - lead_spaces
        else:
            indentDifference = -indent_width

        return indentDifference
    
    def autoCompletionWordSeparators(self):
        """
        Public method to return the list of separators for autocompletion.
        """
        return QStringList() << '.'



class QsciEditor(QsciScintilla):
    """
    QScintilla Editor Widget
    """
    def __init__(self, parent=None, margin=True):
        QsciScintilla.__init__(self, parent)
        
        # Mouse selection copy feature
        self.always_copy_selection = False
        
        # UTF-8
        self.setUtf8(True)
        
        # Wrapping
        if CONF.get('editor', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
        # Indentation
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setTabIndents(True)
        self.setBackspaceUnindents(True)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setIndentationGuidesForegroundColor(Qt.lightGray)
        self.setFolding(QsciScintilla.BoxedFoldStyle)
        
        # Enable brace matching
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        
        # 80-columns edge
        self.setEdgeColumn(80)
        self.setEdgeMode(QsciScintilla.EdgeLine)
        
        # Auto-completion
        self.setAutoCompletionThreshold(-1)
        self.setAutoCompletionSource(QsciScintilla.AcsAll)

        # Lexer
        self.lex = LexerPython(self)
        self.setLexer(self.lex)
        self.api = None
        
        self.setMinimumWidth(200)
        self.setMinimumHeight(100)
        
        if margin:
            self.connect( self, SIGNAL('linesChanged()'), self.lines_changed )
        else:
            self.setup_margin(None)
        
    def setup_api(self):
        """Load and prepare API"""
        self.api = QsciAPIs(self.lex)
        is_api_ready = False
        api_path = CONF.get('editor', 'api')
        if not os.path.isfile(api_path):
            return False
        api_stat = CONF.get('editor', 'api_stat', None)
        current_api_stat = os.stat(api_path)
        if (api_stat is not None) and (api_stat == current_api_stat):
            if self.api.isPrepared():
                is_api_ready = self.api.loadPrepared()
        else:
            CONF.set('editor', 'api_stat', current_api_stat)
        if not is_api_ready:
            if self.api.load(api_path):
                self.api.prepare()
                self.connect(self.api, SIGNAL("apiPreparationFinished()"),
                             self.api.savePrepared)
        return is_api_ready

    def lines_changed(self):
        """Update margin"""
        self.setup_margin( get_font('editor', 'margin') )

    def setup_margin(self, font, width=None):
        """Set margin font and width"""
        if font is None:
            self.setMarginLineNumbers(1, False)
            self.setMarginWidth(1, 0)
        else:
            self.setMarginLineNumbers(1, True)
            self.setMarginsFont(font)
            if width is None:
                from math import log
                width = log(self.lines(), 10) + 2
            self.setMarginWidth(1, QString('0'*int(width)))

    def set_font(self, font):
        """Set shell font"""
        self.lex.setFont(font)
        self.setLexer(self.lex)
        
    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        self.setWrapMode(QsciScintilla.WrapWord if enable
                         else QsciScintilla.WrapNone)
        
    def set_cursor_to(self, position):
        """
        Set cursor to position = "Start" or "End"
        """
        assert position in ["Start", "End"]
        line_nb = {"Start" : 0, "End" : self.lines() - 1}
        self.setCursorPosition(line_nb[position], 0)
        self.ensureCursorVisible()
        
    def set_text(self, text):
        """Set the text of the editor"""
        self.setText(text)

    def get_text(self):
        """Return editor text"""
        return self.text()
    
    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False):
        """Find text"""
        # findFirst(expr, re, cs, wo, wrap, forward, line, index, show)
        if changed or not forward:
            line_from, index_from, _line_to, _index_to = self.getSelection()
            self.setCursorPosition(line_from, max([0, index_from-1]))
        return self.findFirst(text, False, case, words,
                              True, forward, -1, -1, True)
    
    def insert_text(self, text):
        """Insert text at cursor position"""
        line, col = self.getCursorPosition()
        self.insertAt(text, line, col)
        self.setCursorPosition(line, col + len(unicode(text)))
    
    def add_prefix(self, prefix):
        """Add prefix to current line or selected line(s)"""
        if self.hasSelectedText():
            # Add prefix to selected line(s)
            line_from, _, line_to, index_to = self.getSelection()
            if index_to == 0:
                end_line = line_to - 1
            else:
                end_line = line_to
            self.beginUndoAction()
            for line in range(line_from, end_line+1):
                self.insertAt(prefix, line, 0)
            self.setSelection(line_from, 0, end_line+1, 0)
            self.endUndoAction()
        else:
            # Add prefix to current line
            line, _index = self.getCursorPosition()
            self.beginUndoAction()
            self.insertAt(prefix, line, 0)
            self.endUndoAction()
    
    def remove_prefix(self, prefix):
        """Remove prefix from current line or selected line(s)"""
        if self.hasSelectedText():
            # Remove prefix from selected line(s)
            line_from, index_from, line_to, index_to = self.getSelection()
            if index_to == 0:
                end_line = line_to - 1
            else:
                end_line = line_to
            self.beginUndoAction()
            for line in range(line_from, end_line+1):
                if not self.text(line).startsWith(prefix):
                    continue
                self.setSelection(line, 0, line, len(prefix))
                self.removeSelectedText()
                if line == line_from:
                    index_from -= len(prefix)
                    if index_from < 0:
                        index_from = 0
                if line == line_to:
                    index_to -= len(prefix)
                    if index_to < 0:
                        index_to = 0
            self.setSelection(line_from, index_from, line_to, index_to)
            self.endUndoAction()
        else:
            # Remove prefix from current line
            line, _index = self.getCursorPosition()
            if not self.text(line).startsWith(prefix):
                return
            self.beginUndoAction()
            self.setSelection(line, 0, line, len(prefix))
            self.removeSelectedText()
            self.endUndoAction()
    
    def indent(self):
        """Indent current line or selection"""
        self.SendScintilla(QsciScintilla.SCI_TAB)
    
    def unindent(self):
        """Unindent current line or selection"""
        self.remove_prefix( " "*4 )
    
    def comment(self):
        """Comment current line or selection"""
        self.add_prefix( self.lex.COMMENT_STRING )

    def uncomment(self):
        """Uncomment current line or selection"""
        self.remove_prefix( self.lex.COMMENT_STRING )
            
    def keyPressEvent(self, event):
        """Reimplemented"""
        key = event.key()
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier
        if ((key == Qt.Key_Plus) and ctrl) \
             or ((key==Qt.Key_Equal) and shift and ctrl):
            self.zoomIn()
            event.accept()
        elif (key == Qt.Key_Minus) and ctrl:
            self.zoomOut()
            event.accept()
        else:
            QsciScintilla.keyPressEvent(self, event)
            
    def mousePressEvent(self, event):
        """Reimplemented"""
        self.setFocus()
        if event.button() == Qt.MidButton:
            event = QMouseEvent(QEvent.MouseButtonPress, event.pos(),
                                Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            QsciScintilla.mousePressEvent(self, event)
            QsciScintilla.mouseReleaseEvent(self, event)
            self.paste()
        else:
            QsciScintilla.mousePressEvent(self, event)
            
    def mouseReleaseEvent(self, event):
        """Reimplemented"""
        if self.hasSelectedText() and self.always_copy_selection:
            self.copy()
        QsciScintilla.mouseReleaseEvent(self, event)



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
class QsciTerminal(QsciScintilla):
    """
    Terminal based on QScintilla
    """
    def __init__(self, parent=None):
        """
        parent : specifies the parent widget
        """
        QsciScintilla.__init__(self, parent)
        
        # UTF-8
        self.setUtf8(True)
        
        # Wrapping
        if CONF.get('shell', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
        # Mouse selection copy feature
        self.always_copy_selection = False
        
        # keyboard events management
        self.busy = False
        self.eventqueue = []
        
        # history
        self.histidx = None
        self.hist_wholeline = False
        
        # Indentation
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setTabIndents(True)
        self.setTabWidth(4)
        
        # Enable brace matching
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        
        # Suppressing Scintilla margins
        self.setMarginWidth(0, 0)
        self.setMarginWidth(1, 0)
        self.setMarginWidth(2, 0)
        
        # Auto Completion setup
        self.setAutoCompletionThreshold( \
            CONF.get('shell', 'autocompletion/threshold') )
        self.setAutoCompletionCaseSensitivity( \
            CONF.get('shell', 'autocompletion/case-sensitivity') )
        self.setAutoCompletionShowSingle( \
            CONF.get('shell', 'autocompletion/select-single') )
        if CONF.get('shell', 'autocompletion/from-document'):
            self.setAutoCompletionSource(QsciScintilla.AcsDocument)
        else:
            self.setAutoCompletionSource(QsciScintilla.AcsNone)
        self.completion_chars = 0
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     self.__completion_list_selected)
        
        # Call-tips
        self.calltips = True
        self.docviewer = None
        
        # Minimum size
        self.setMinimumWidth(300)
        self.setMinimumHeight(150)
        
        # Lexer
        self.lexer = LexerPython(self)
        self.error_style = self.lexer.Decorator
        self.traceback_link_style = self.lexer.CommentBlock
        self.lexer.setColor(Qt.black, self.lexer.Default)
        self.lexer.setColor(Qt.red, self.error_style)
        self.lexer.setColor(Qt.blue, self.traceback_link_style)

        # Give focus to widget
        self.setFocus()
        
        # Clear status bar
        self.emit(SIGNAL("status(QString)"), QString())

    def setUndoRedoEnabled(self, state):
        """Fake Qt method (QTextEdit)"""
        pass

    def set_font(self, font):
        """Set shell font"""
        self.lexer.setFont(font)
        font.setUnderline(True)
        self.lexer.setFont(font, self.traceback_link_style)
        self.setLexer(self.lexer)
        
    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        self.setWrapMode(QsciScintilla.WrapWord if enable
                         else QsciScintilla.WrapNone)
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state
        
        
    #------ Utilities
    def getpointy(self, cursor=True, end=False, prompt=False):
        """Return point y of cursor, end or prompt"""
        line, index = self.getCursorPosition()
        if end:
            line, index = self.__get_end_pos()
        elif prompt:
            index = 0
        pos = self.positionFromLineIndex(line, index)
        return self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION,
                                  0, pos)
    def __remove_prompts(self, text):
        """Remove prompts from text"""
        return text[len(self.prompt):]
    
    def __extract_from_text(self, line_nb):
        """Extract clean text from line number 'line_nb'"""
        return self.__remove_prompts( unicode(self.text(line_nb)) )
                                          
    def __get_end_pos(self):
        """
        Private method to return the line and column of the last character.
        @return tuple of two values (int, int) giving the line and column
        """
        line = self.lines() - 1
        return (line, self.lineLength(line))

    def __is_cursor_on_last_line(self):
        """
        Private method to check, if the cursor is on the last line.
        """
        cline, _ = self.getCursorPosition()
        return cline == self.lines() - 1

    def __is_cursor_on_last_index(self):
        """
        Private method to check, if the cursor is on the last line and index
        """
        cline, cindex = self.getCursorPosition()
        return (cline, cindex) == self.__get_end_pos()

    def move_cursor_to_end(self):
        """Move cursor to end of text"""
        line, col = self.__get_end_pos()
        self.setCursorPosition(line, col)


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
            line, col = self.__get_end_pos()
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
                                   len(text), self.lexer.Default)
            self.prline, self.prcol = self.__get_end_pos()
            self.setCursorPosition(self.prline, self.prcol)
            self.ensureCursorVisible()
            self.ensureLineVisible(self.prline)
        else:
            # Insert text at current cursor position
            line, col = self.getCursorPosition()
            self.insertAt(text, line, col)
            self.setCursorPosition(line, col + len(unicode(text)))

            
    #------ Find text: same as QsciEditor.find_text (to be factorized)
    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False):
        """Find text"""
        # findFirst(expr, re, cs, wo, wrap, forward, line, index, show)
        if changed or not forward:
            line_from, index_from, _line_to, _index_to = self.getSelection()
            self.setCursorPosition(line_from, max([0, index_from-1]))
        return self.findFirst(text, False, case, words,
                              True, forward, -1, -1, True)    


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
    
    def mouseMoveEvent(self, event):
        """Show Pointing Hand Cursor on error messages"""
        if event.modifiers() & Qt.ControlModifier:
            text = unicode(self.text(self.lineAt(event.pos())))
            if self.parent().get_error_match(text):
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                return
        QApplication.restoreOverrideCursor()
        QsciScintilla.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Re-implemented to handle the mouse press event.
        event: the mouse press event (QMouseEvent)
        """
        self.setFocus()
        ctrl = event.modifiers() & Qt.ControlModifier
        if event.button() == Qt.MidButton:
            # Middle-button -> paste
            lines = unicode(QApplication.clipboard().text(QClipboard.Selection))
            self.execute_lines(lines)
        elif event.button() == Qt.LeftButton and ctrl:
            text = unicode(self.text(self.lineAt(event.pos())))
            self.parent().go_to_error(text)
        else:
            QsciScintilla.mousePressEvent(self, event)
            
    def mouseReleaseEvent(self, event):
        """Reimplemented"""
        if self.hasSelectedText() and self.always_copy_selection:
            self.copy()
        QsciScintilla.mouseReleaseEvent(self, event)

    def copy(self):
        """Copy text to clipboard... or keyboard interrupt"""
        if self.hasSelectedText():
            QsciScintilla.copy(self)
        else:
            if self.busy:
                # Interrupt only if console is busy
                self.interrupted = True
            elif self.more:
                self.write("\nKeyboardInterrupt\n", flush=True)
                self.more = False
                self.prompt = self.p1
                self.write(self.prompt, flush=True)
                self.interpreter.resetbuffer()
                
    def paste(self):
        """Reimplemented slot to handle multiline paste action"""
        lines = unicode(QApplication.clipboard().text())
        if len(lines.splitlines())>1:
            # Multiline paste
            self.removeSelectedText() # Remove selection, eventually
            cline, cindex = self.getCursorPosition()
            linetext = unicode(self.text(cline))
            lines = linetext[:cindex] + lines + linetext[cindex:]
            self.setSelection(cline, len(self.prompt),
                              cline, self.lineLength(cline))
            self.removeSelectedText()
            lines = self.__remove_prompts(lines)
            self.execute_lines(lines)
            cline2, _ = self.getCursorPosition()
            self.setCursorPosition(cline2,
               self.lineLength(cline2)-len(linetext[cindex:]) )
        else:
            # Standard paste
            QsciScintilla.paste(self)


    #---- Key handler
    def __delete_selected_text(self):
        """
        Private method to delete selected text
        """
        line_from, index_from, line_to, index_to = self.getSelection()

        # If not on last line, then move selection to last line
        last_line = self.lines()-1
        if line_from != last_line:
            line_from = last_line
            index_from = 0
            
        for prompt in [self.p1, self.p2]:
            if self.text(line_from).startsWith(prompt):
                if index_from < len(prompt):
                    index_from = len(prompt)
        if index_from < 0:
            index_from = index_to
            line_from = line_to
        self.setSelection(line_from, index_from, line_to, index_to)
        self.SendScintilla(QsciScintilla.SCI_CLEAR)
        self.setSelection(line_from, index_from, line_from, index_from)

    def get_new_line(self):
        """Enter or Return -> get new line"""
        self.histidx = None
        line, col = self.__get_end_pos()
        self.setCursorPosition(line, col)
        buf = self.__extract_from_text(line)
        self.insert_text('\n', at_end=True)
        return buf

    def keyPressEvent(self, event):
        """
        Re-implemented to handle the user input a key at a time.
        event: key event (QKeyEvent)
        """
        text = event.text()
        key = event.key()
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier
        current_event = (text, key, ctrl, shift)
        
        if self.busy and (not self.input_mode):
            # Ignoring all events except KeyboardInterrupt (see above)
            # Keep however these events in self.eventqueue
            self.eventqueue.append(current_event)
            event.accept()
        else:
            self.__flush_eventqueue() # Shouldn't be necessary
            self.__process_keyevent(current_event, event)
        
    def __flush_eventqueue(self):
        """Flush keyboard event queue"""
        while self.eventqueue:
            past_event = self.eventqueue.pop(0)
            self.__process_keyevent(past_event)
        
    def __process_keyevent(self, past_event, keyevent=None):
        """Process keyboard event"""
        (text, key, ctrl, shift), event = (past_event, keyevent)
        
        # Is cursor on the last line? and after prompt?
        line, index = self.getCursorPosition()
        last_line = self.lines()-1
        if len(text):
            if line!=last_line:
                # Moving cursor to the end of the last line
                self.move_cursor_to_end()
            elif index < len(self.prompt):
                # Moving cursor after prompt
                self.setCursorPosition(line, len(self.prompt))
            
        if key == Qt.Key_Backspace:
            if self.hasSelectedText():
                self.__delete_selected_text()
            elif self.__is_cursor_on_last_line():
                line, col = self.getCursorPosition()
                _is_active = self.isListActive()
                _old_length = self.text(line).length()
                if self.text(line).startsWith(self.prompt):
                    if col > len(self.prompt):
                        self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
                elif col > 0:
                    self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
                if self.isListActive():
                    self.completion_chars -= 1

        elif key == Qt.Key_Delete:
            if self.hasSelectedText():
                self.__delete_selected_text()
            elif self.__is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_CLEAR)
            
        elif shift and (key == Qt.Key_Return or key == Qt.Key_Enter):
            # Multiline entry
            self.append_command(self.get_new_line())
            
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            if self.__is_cursor_on_last_line():
                if self.isListActive():
                    self.SendScintilla(QsciScintilla.SCI_NEWLINE)
                else:
                    buf = self.get_new_line()
                    self.busy = True
                    self.execute_command(buf)
                    self.busy = False
                    self.__flush_eventqueue()
            # add and run selection
            else:
                text = self.selectedText()
                self.insert_text(text, at_end=True)
                
        elif key == Qt.Key_Tab:
            if self.isListActive():
                self.SendScintilla(QsciScintilla.SCI_TAB)
            elif self.__is_cursor_on_last_line():
                line, index = self.getCursorPosition()
                buf = self.__extract_from_text(line)
                lastchar_index = index-len(self.prompt)-1
                if self.more and not buf[:index-len(self.prompt)].strip():
                    self.SendScintilla(QsciScintilla.SCI_TAB)
                elif lastchar_index>=0:
                    text = self.__get_last_obj()
                    if buf[lastchar_index] == '.':
                        self.show_code_completion(text)
                    elif buf[lastchar_index] in ['"', "'"]:
                        self.show_file_completion()
            
        elif key == Qt.Key_Left:
            if line==last_line and (index==len(self.prompt)):
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
            if self.__is_cursor_on_last_index():
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
            elif self.__is_cursor_on_last_line():
                line, col = self.getCursorPosition()
                if self.text(line).startsWith(self.prompt):
                    col = len(self.prompt)
                else:
                    col = 0
                self.setCursorPosition(line, col)

        elif (key == Qt.Key_End) or ((key == Qt.Key_Down) and ctrl):
            if self.isListActive():
                self.SendScintilla(QsciScintilla.SCI_LINEEND)
            elif self.__is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_LINEEND)

        elif key == Qt.Key_Up:
            if line!=last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() > self.getpointy(prompt=True):
                self.SendScintilla(QsciScintilla.SCI_LINEUP)
            else:
                self.__browse_history(backward=True)
                
        elif key == Qt.Key_Down:
            if line!=last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() < self.getpointy(end=True):
                self.SendScintilla(QsciScintilla.SCI_LINEDOWN)
            else:
                self.__browse_history(backward=False)
            
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
                
        elif key == Qt.Key_V and ctrl:
            self.paste()
            
        elif key == Qt.Key_X and ctrl:
            self.cut()
            
        elif key == Qt.Key_Z and ctrl:
            self.undo()
            
        elif key == Qt.Key_Y and ctrl:
            self.redo()
                
        elif key == Qt.Key_Question:
            self.show_docstring(self.__get_last_obj())
            self.insert_text(text)
            
        elif key == Qt.Key_ParenLeft:
            self.cancelList()
            self.show_docstring(self.__get_last_obj(), call=True)
            self.insert_text(text)
            
        elif key == Qt.Key_Period:
            # Enable auto-completion only if last token isn't a float
            self.insert_text(text)
            last_obj = self.__get_last_obj()
            if last_obj and not last_obj[-1].isdigit():
                self.show_code_completion(last_obj)

        elif ((key == Qt.Key_Plus) and ctrl) \
             or ((key==Qt.Key_Equal) and shift and ctrl):
            self.zoomIn()

        elif (key == Qt.Key_Minus) and ctrl:
            self.zoomOut()

        elif text.length():
            self.hist_wholeline = False
            if keyevent is None:
                self.insert_text(text)
            else:
                QsciScintilla.keyPressEvent(self, event)
            if self.isListActive():
                self.completion_chars += 1
                
        elif keyevent:
            # Let the parent widget handle the key press event
            keyevent.ignore()

    
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
    
  
    #------ History Management
    def __browse_history(self, backward):
        """Browse history"""
        line, index = self.getCursorPosition()
        if index<self.lineLength(line) and self.hist_wholeline:
            self.hist_wholeline = False
        tocursor = self.__get_current_line_to_cursor()
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
        history = self.interpreter.history
        if start_idx is None:
            start_idx = len(history)
        # Finding text in history
        step = -1 if backward else 1
        idx = start_idx
        if len(tocursor) == 0 or self.hist_wholeline:
            idx += step
            if idx >= len(history):
                return "", len(history)
            elif idx < 0:
                idx = 0
            self.hist_wholeline = True
            return history[idx], idx
        else:
            for index in xrange(len(history)):
                idx = (start_idx+step*(index+1)) % len(history)
                entry = history[idx]
                if entry.startswith(tocursor):
                    return entry[len(tocursor):], idx
            else:
                return None, start_idx


    #------ Miscellanous
    def __get_current_line_to_cursor(self):
        """
        Return the current line: from the beginning to cursor position
        """
        line, index = self.getCursorPosition()
        buf = self.__extract_from_text(line)
        # Removing the end of the line from cursor position:
        return buf[:index-len(self.prompt)]
    
    def __get_last_obj(self, last=False):
        """
        Return the last valid object on the current line
        """
        return getobj(self.__get_current_line_to_cursor(), last=last)
        
    def set_docviewer(self, docviewer):
        """Set DocViewer DockWidget reference"""
        self.docviewer = docviewer
        
        
    #------ Code Completion Management            
    def __completion_list_selected(self, userlist_id, seltxt):
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

    def show_completion_widget(self, textlist, text):
        """Show completion widget"""
        self.showUserList(1, QStringList(textlist))

    def positionFromLineIndex(self, line, index):
        """
        Public method to convert line and index to an absolute position.
        """
        pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, line)
        # Allow for multi-byte characters
        for _i in range(index):
            pos = self.SendScintilla(QsciScintilla.SCI_POSITIONAFTER, pos)
        return pos

    def get_cursor_qpoint(self):
        """Return cursor global QPoint position"""
        line, index = self.getCursorPosition()
        pos = self.positionFromLineIndex(line, index)
        x_pt = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
        y_pt = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)
        return self.mapToGlobal(QPoint(x_pt, y_pt))
        
        