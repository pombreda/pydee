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

"""Editor and terminal base widgets used only if QScintilla is not installed"""

from PyQt4.QtCore import Qt, QString, SIGNAL, QEvent, QRegExp, QPoint
from PyQt4.QtGui import (QTextEdit, QTextCursor, QColor, QFont, QCursor,
                         QSyntaxHighlighter, QApplication, QTextCharFormat,
                         QKeySequence, QToolTip, QTextImageFormat,
                         QTextDocument)

import __builtin__

import sys
try:
    PS1 = sys.ps1
except AttributeError:
    PS1 = ">>> "

# For debugging purpose:
STDOUT = sys.stdout

# Local import
from PyQtShell.config import get_font, CONF, get_image_path
from PyQtShell.dochelpers import getobj
from PyQtShell.qthelpers import mimedata2url


class AlmostQsciScintilla(QTextEdit):
    """Reimplement some of QScintilla editor widget features"""
    def __init__(self, parent=None):
        super(AlmostQsciScintilla, self).__init__(parent)
        # Undo/Redo
        self.undo_available = False
        self.redo_available = False
        self.connect(self, SIGNAL("undoAvailable(bool)"), self.set_undo)
        self.connect(self, SIGNAL("redoAvailable(bool)"), self.set_redo)
        # Indentation
        self.document().setIndentWidth(4)
        
    def isModified(self):
        """Reimplement QScintilla method
        Returns true if the text has been modified"""
        return self.document().isModified()
    
    def setModified(self, state):
        """Reimplement QScintilla method
        Sets the modified state of the text edit to state"""
        self.document().setModified(state)
        
    def hasSelectedText(self):
        """Reimplements QScintilla method
        Returns true if some text is selected"""
        return len(self.selectedText()) != 0
    
    def selectedText(self):
        """Reimplements QScintilla method
        Returns the selected text or an empty string
        if there is no currently selected text"""
        return self.textCursor().selectedText()
    
    def removeSelectedText(self):
        """Delete selected text"""
        self.textCursor().removeSelectedText()
        
    def set_undo(self, state):
        """Set undo availablity"""
        self.undo_available = state
        
    def set_redo(self, state):
        """Set redo availablity"""
        self.redo_available = state
        
    def isUndoAvailable(self):
        """Reimplements QScintilla method
        Returns true if there is something that can be undone"""
        return self.undo_available
        
    def isRedoAvailable(self):
        """Reimplements QScintilla method
        Returns true if there is something that can be redone"""
        return self.redo_available
    
    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False):
        """Find text"""
        findflag = QTextDocument.FindFlag()
        if not forward:
            findflag = findflag | QTextDocument.FindBackward
        if case:
            findflag = findflag | QTextDocument.FindCaseSensitively
        if words:
            findflag = findflag | QTextDocument.FindWholeWords
        if forward:
            moves = [QTextCursor.NextWord, QTextCursor.Start]
            if changed:
                self.moveCursor(QTextCursor.PreviousWord)
        else:
            moves = [QTextCursor.End]
        found = self.find(text, findflag)
        for move in moves:
            if found:
                break
            self.moveCursor(move)
            found = self.find(text, findflag)
        return found
        
    def replace(self, text):
        """Reimplements QScintilla method"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(text)
        cursor.endEditBlock()



#TODO: Improve "PythonHighlighter" performance... very slow for large files!
#      --> maybe grab some ideas from "idlelib/ColorDelegator.py"
class PythonHighlighter(QSyntaxHighlighter):
    """
    Copyright (c) 2007-8 Qtrac Ltd. All rights reserved.
    This program or module is free software: you can redistribute it and/or
    modify it under the terms of the GNU General Public License as published
    by the Free Software Foundation, either version 2 of the License, or
    version 3 of the License, or (at your option) any later version. It is
    provided for educational purposes and is distributed in the hope that
    it will be useful, but WITHOUT ANY WARRANTY; without even the implied
    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
    the GNU General Public License for more details.
    """
    Rules = []

    KEYWORDS = ["and", "as", "assert", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "exec", "finally",
            "for", "from", "global", "if", "import", "in", "is", "lambda",
            "not", "or", "pass", "print", "raise", "return", "try",
            "while", "with", "yield"]

    CONSTANTS = ["False", "True", "None", "NotImplemented", "Ellipsis"]

    def __init__(self, parent=None, font=None):
        super(PythonHighlighter, self).__init__(parent)
        
        self.formats = {}
        self.state = True
        self.set_font(font)

        PythonHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % keyword \
                for keyword in PythonHighlighter.KEYWORDS])),
                "keyword"))
        builtinlist = [str(name) for name in dir(__builtin__)
                       if not name.startswith('_')]
        PythonHighlighter.Rules.append((QRegExp(
                r"([^.'\"\\#]\b|^)(" + "|".join(builtinlist) + r")\b"),
                "builtin"))
        PythonHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % constant \
                for constant in PythonHighlighter.CONSTANTS])),
                "constant"))
        PythonHighlighter.Rules.append((QRegExp(
                r"\b[+-]?[0-9]+[lL]?\b"
                r"|\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b"
                r"|\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"),
                "number"))
        PythonHighlighter.Rules.append((QRegExp(
                r"\bPyQt4\b|\bQt?[A-Z][a-z]\w+\b"), "pyqt"))
        PythonHighlighter.Rules.append((QRegExp(r"\b@\w+\b"), "decorator"))
        PythonHighlighter.Rules.append((QRegExp(r"#[^\n]*"), "comment"))       
        string_re = QRegExp(r"""(?:'[^']*'|"[^"]*")""")
        string_re.setMinimal(True)
        PythonHighlighter.Rules.append((string_re, "string"))
        self.string_re = QRegExp(r"""(:?"["]".*"["]"|'''.*''')""")
        self.string_re.setMinimal(True)
        PythonHighlighter.Rules.append((self.string_re, "string"))
        self.triple_single_re = QRegExp(r"""'''(?!")""")
        self.triple_double_re = QRegExp(r'''"""(?!')''')

    def set_font(self, font=None):
        """
        Set QTextEdit font
        """
        base_format = QTextCharFormat()
        if font is None:
            base_format.setFontFamily("courier")
            base_format.setFontPointSize(10)
        else:
            base_format.setFont(font)
        for name, color, bold, italic in (
                ("normal", "#000000", False, False),
                ("keyword", Qt.blue, True, False),
                ("builtin", "#0000A0", False, False),
                ("constant", "#0000C0", False, False),
                ("decorator", "#0000E0", False, False),
                ("comment", "#007F00", False, True),
                ("string", Qt.darkGreen, False, False),
                ("number", "#924900", False, False),
                ("error", "#FF0000", False, False),
                ("pyqt", "#50621A", False, False)):
            format = QTextCharFormat(base_format)
            format.setForeground(QColor(color))
            if bold:
                format.setFontWeight(QFont.Bold)
            format.setFontItalic(italic)
            self.formats[name] = format

    def highlightBlock(self, text):
        """Overrides Qt method"""
        if not self.state:
            return
        
        normal, triplesingle, tripledouble, error = range(4)

        text_length = text.length()
        prev_state = self.previousBlockState()

        self.setFormat(0, text_length, self.formats["normal"])

        if text.startsWith("Traceback") or text.startsWith("Error: "):
            self.setCurrentBlockState(error)
            self.setFormat(0, text_length, self.formats["error"])
            return
        if prev_state == error and \
           not (text.startsWith(PS1) or text.startsWith("#")):
            self.setCurrentBlockState(error)
            self.setFormat(0, text_length, self.formats["error"])
            return
        
        for regex, format in PythonHighlighter.Rules:
            i = text.indexOf(regex)
            while i >= 0:
                length = regex.matchedLength()
                self.setFormat(i, length, self.formats[format])
                i = text.indexOf(regex, i + length)

        self.setCurrentBlockState(normal)

        if text.indexOf(self.string_re) != -1:
            return
        # This is fooled by triple quotes inside single quoted strings
        for i, state in ((text.indexOf(self.triple_single_re),
                          triplesingle),
                         (text.indexOf(self.triple_double_re),
                          tripledouble)):
            if self.previousBlockState() == state:
                if i == -1:
                    i = text.length()
                    self.setCurrentBlockState(state)
                self.setFormat(0, i + 3, self.formats["string"])
            elif i > -1:
                self.setCurrentBlockState(state)
                self.setFormat(i, text.length(), self.formats["string"])

    def disable(self, disable):
        """Enable/disable syntax highlighter"""
        self.state = not disable

    def rehighlight(self):
        """Overrides Qt method"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QSyntaxHighlighter.rehighlight(self)
        QApplication.restoreOverrideCursor()


class QtEditor(AlmostQsciScintilla):
    """
    Qt-based Editor Widget
    """
    def __init__(self, parent=None, margin=True):
        # The 'margin' argument is here only for QScintilla compatibility
        super(QtEditor, self).__init__(parent)
        self.highlighter = PythonHighlighter(self, get_font('editor'))
        self.connect(self, SIGNAL('textChanged()'), self.changed)
        
    def changed(self):
        """Emit changed signal"""
        self.emit(SIGNAL('modificationChanged(bool)'), self.isModified())
        
    def set_cursor_to(self, position):
        """
        Set cursor to position = "Start" or "End"
        """
        assert position in ["Start", "End"]
        self.moveCursor(getattr(QTextCursor, position))
        self.ensureCursorVisible()
    
    def lines(self):
        """Fake QScintilla method"""
        return 0
    
    def setup_api(self):
        """Fake QScintilla method"""
        pass
    
    def set_text(self, string):
        """Set the text of the editor"""
        self.setPlainText(string)

    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        if enable:
            self.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.setLineWrapMode(QTextEdit.NoWrap)

    def set_font(self, font):
        """Set shell font"""
        self.highlighter.set_font(font)

    def get_text(self):
        """Return editor text"""
        return self.toPlainText()

    def event(self, event):
        """Override Qt method"""
        if event.type() == QEvent.KeyPress and \
           event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            cursor.insertText(" "*4)
            return True
        return QTextEdit.event(self, event)
    
    def comment(self):
        """Comment current line or selection"""
        self._walk_the_lines(True, "#")

    def uncomment(self):
        """Uncomment current line or selection"""
        self._walk_the_lines(False, "#")
            
    def _walk_the_lines(self, insert, text):
        """Walk current/selected lines and insert or remove text"""
        user_cursor = self.textCursor()
        user_cursor.beginEditBlock()
        start = user_cursor.position()
        end = user_cursor.anchor()
        if start > end:
            start, end = end, start
        block = self.document().findBlock(start)
        while block.isValid():
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.StartOfBlock)
            if insert:
                cursor.insertText(text)
            else:
                cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor, len(text))
                if cursor.selectedText() == text:
                    cursor.removeSelectedText()        
            block = block.next()
            if block.position() > end:
                break
        user_cursor.endEditBlock()


class QtTerminal(AlmostQsciScintilla):
    """
    Terminal based on Qt only
    """    
    def __init__(self, parent=None):
        """
        parent : specifies the parent widget
        """
        super(QtTerminal, self).__init__(parent)
        self.format = QTextCharFormat()
        self.format.setFont(get_font('shell'))
        self.highlighter = PythonHighlighter(self, get_font('shell'))
        
        self.connect(self, SIGNAL("executing_command(bool)"),
                     self.highlighter.disable)
        
        self.setMouseTracking(True)
        
        # keyboard events management
        self.busy = False
        self.eventqueue = []
        
        # Python icon... just for fun
        image = QTextImageFormat()
        image.setName(get_image_path("python-small.png"))
        self.textCursor().insertImage(image)
        self.textCursor().insertText(' ')
        
        # history
        self.histidx = None
        self.hist_wholeline = False
        
        # completion widget
        self.completion_widget = None
        self.completion_text = None
        self.completion_match = None
        self.hide_completion_widget()
        
        self.help_action = None
        
        # flag: the interpreter needs more input to run the last lines. 
        self.more    = 0
        self.cursor_pos   = 0
        
        # Call-tips
        self.docviewer = None
        self.calltips = True
        
        self.emit(SIGNAL("status(QString)"), QString())

    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        if enable:
            self.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.setLineWrapMode(QTextEdit.NoWrap)
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state
                
    def set_font(self, font):
        """Set shell font"""
        if self.highlighter is not None:
            self.highlighter.set_font(font)
            self.format.setFont(font)
            self.highlighter.rehighlight()
            
    def clear_terminal(self):
        """Clear terminal window and write prompt"""
        self.clear()
        self.setUndoRedoEnabled(False)
        cursor = self.textCursor()
        cursor.insertBlock()
        cursor.insertText(self.prompt)
        self.setUndoRedoEnabled(True)
        
    def insert_text(self, text, at_end=False, error=False):
        """
        Insert text at the current cursor position
        or at the end of the command line
        """
        cursor = self.textCursor()
        if at_end:
            # Insert text at the end of the command line
            cursor.movePosition(QTextCursor.End)
            if error:
                if not text.startswith('  File "<'):
                    if text.startswith('  File'):
                        cursor.insertText("  ", self.format)
                        self.format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                        self.format.setForeground(Qt.blue)
                        text = text[2:]
                    else:
                        self.format.setForeground(Qt.red)
                    cursor.insertText(text, self.format)
                    self.format.setForeground(Qt.black)
                    self.format.setUnderlineStyle(QTextCharFormat.NoUnderline)
            else:
                cursor.insertText(text, self.format)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        else:
            # Insert text at current cursor position
            cursor.insertText(text, self.format)
            
    def writelines(self, text):
        """
        Simulate stdin, stdout, and stderr.
        """
        map(self.write, text)

    def clear_line(self):
        """
        Clear current line
        """
        cursor = self.textCursor()
        cursor.select( QTextCursor.BlockUnderCursor )
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertBlock()
        cursor.insertText(self.prompt)
        cursor.endEditBlock()
        self.hide_completion_widget()

    def paste(self):
        """Reimplemented slot to handle multiline paste action"""
        lines = unicode(QApplication.clipboard().text())
        lines = self.__get_current_line_to_cursor() + lines + \
                self.__get_current_line_from_cursor()
        self.clear_line()
        self.execute_lines(lines)
            
    def keyPressEvent(self, event):
        """
        Handle user input a key at a time.
        """
        if event == QKeySequence.Copy:
            if self.textCursor().selectedText().isEmpty():
                # Keyboard Interrupt
                if self.more:
                    self.write("\nKeyboardInterrupt\n", flush=True)
                    self.more = False
                    self.prompt = self.p1
                    self.write(self.prompt, flush=True)
                    self.interpreter.resetbuffer()
                else:
                    self.interrupted = True
            else:
                # Copy
                self.copy()
                self.hide_completion_widget()
            return
            
        text  = event.text()
        key   = event.key()
        shift = event.modifiers() & Qt.ShiftModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        self.eventqueue.append( (text, key, shift, ctrl) )
        
        if self.busy and (not self.input_mode):
            # Ignoring all events except KeyboardInterrupt (see above)
            # Keep however these events in self.eventqueue
            pass
        else:
            while self.eventqueue:
                past_event = self.eventqueue.pop(0)
                self.__process_keyevent(past_event)
        
    def __process_keyevent(self, keyevent):
        """Process keyboard event"""
        text, key, shift, ctrl = keyevent
        if shift:
            move_mode = QTextCursor.KeepAnchor
        else:
            move_mode = QTextCursor.MoveAnchor
            
        # Is cursor on the last line?
        if not self.__is_cursor_on_last_line() and len(text):
            # No? Moving it to the end of the last line, then!
            self.moveCursor(QTextCursor.End)
        
        if key == Qt.Key_Escape:
            self.clear_line()
            return
        
        if key == Qt.Key_Backspace:
            if self.textCursor().selectedText().isEmpty():
                if len(self.__get_current_line_to_cursor()) == 0:
                    return
                self.moveCursor(QTextCursor.PreviousCharacter,
                                QTextCursor.KeepAnchor)
            selected_length = self.textCursor().selectedText().length()
            self.textCursor().removeSelectedText()
            if self.completion_widget:
                if self.completion_text:
                    self.completion_text = self.completion_text[:-selected_length]
                    self.show_completion_widget()
                else:
                    self.hide_completion_widget()

        elif key == Qt.Key_Delete:
            if self.textCursor().selectedText().isEmpty():
                self.moveCursor(QTextCursor.NextCharacter,
                                QTextCursor.KeepAnchor)
            selected_length = self.textCursor().selectedText().length()
            self.textCursor().removeSelectedText()
            self.hide_completion_widget()
            
        elif shift and (key == Qt.Key_Return or key == Qt.Key_Enter):
            self.write('\n')
            self.append_command(unicode(self.line))
            self.__clear_line_buffer()
            self.hide_completion_widget()
            self.histidx = None
            
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            cursor = self.textCursor()
            cursor.select( QTextCursor.BlockUnderCursor )
            command = unicode( cursor.selectedText() )[len(self.prompt)+1:]
            self.hide_completion_widget()
            self.insert_text('\n', at_end=True)
            self.busy = True
            self.execute_command(command)
            self.busy = False
            self.moveCursor(QTextCursor.End)
            self.histidx = None
                
        elif key == Qt.Key_Tab:
            last_obj = self.__get_last_obj()
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.PreviousCharacter,
                                QTextCursor.KeepAnchor)
            last_char = unicode(cursor.selectedText())
            if last_obj and last_obj in "\'\"":
                self.show_file_completion()
                return
            elif last_char == ".":
                if last_obj:
                    self.show_code_completion(last_obj[:-1])
                    return
            elif self.completion_widget:
                self.__completion_list_selected()
            else:
                self.insert_text("    ")
            self.hide_completion_widget()
            
        elif key == Qt.Key_Left:
            if len(self.__get_current_line_to_cursor()) > 0:
                if ctrl:
                    self.moveCursor(QTextCursor.PreviousWord, move_mode)
                else:
                    self.moveCursor(QTextCursor.Left, move_mode)
                self.hide_completion_widget()
            elif (not ctrl) and (not shift):
                cursor = self.textCursor()
                cursor.clearSelection()
                self.setTextCursor(cursor)
                
        elif key == Qt.Key_Right:
            if not self.textCursor().atEnd():
                if ctrl:
                    self.moveCursor(QTextCursor.NextWord, move_mode)
                else:
                    self.moveCursor(QTextCursor.Right, move_mode)
                self.hide_completion_widget()

        elif (key == Qt.Key_Home) or ((key == Qt.Key_Up) and ctrl):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfLine, move_mode)
            cursor.movePosition(QTextCursor.Right, move_mode,
                                len(self.prompt))
            self.setTextCursor(cursor)
            self.hide_completion_widget()

        elif (key == Qt.Key_End) or ((key == Qt.Key_Down) and ctrl):
            self.moveCursor(QTextCursor.EndOfLine, move_mode)
            self.hide_completion_widget()

        elif key == Qt.Key_Up:
            if self.__is_cursor_on_last_line():
                self.hide_completion_widget()
                self.__browse_history(backward=True)
            else:
                self.moveCursor(QTextCursor.Up, move_mode)
                
        elif key == Qt.Key_Down:
            if self.__is_cursor_on_last_line():
                self.hide_completion_widget()
                self.__browse_history(backward=False)
            else:
                self.moveCursor(QTextCursor.Down, move_mode)
            
        elif key == Qt.Key_PageUp:
            if self.completion_widget:
                self.show_completion_widget(pagestep=-1)
            
        elif key == Qt.Key_PageDown:
            if self.completion_widget:
                self.show_completion_widget(pagestep=1)
                
        elif key == Qt.Key_V and ctrl:
            self.paste()
            self.hide_completion_widget()
            
        elif key == Qt.Key_X and ctrl:
            self.cut()
            self.hide_completion_widget()
            
        elif key == Qt.Key_Z and ctrl:
            self.undo()
            self.hide_completion_widget()
            
        elif key == Qt.Key_Y and ctrl:
            self.redo()
            self.hide_completion_widget()
                
        elif key == Qt.Key_Question:
            self.show_docstring(self.__get_last_obj())
            self.insert_text(text)
            self.hide_completion_widget()
                
        elif key == Qt.Key_ParenLeft:
            self.show_docstring(self.__get_last_obj(), call=True)
            self.insert_text(text)
                
        elif key == Qt.Key_Period:
            self.hide_completion_widget()
            last_obj = self.__get_last_obj()
            if last_obj:
                if len(last_obj)==1 or \
                   (len(last_obj)>1 and (not last_obj[-2].isdigit())):
                    self.show_code_completion(last_obj)
            self.insert_text(text)

        elif text.length():
            text = unicode(text)
            self.insert_text(text)
            if self.completion_widget:
                self.completion_text += text
                self.show_completion_widget()

    def __browse_history(self, backward):
        """Browse history"""
        if self.__get_current_line_from_cursor() and self.hist_wholeline:
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
                self.moveCursor(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                self.textCursor().removeSelectedText()
                # Inserting history text
                cursor = self.textCursor()
                pos = cursor.position()
                cursor.insertText(text, self.format)
                cursor.setPosition(pos)
                self.setTextCursor(cursor)

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

    def mouseMoveEvent(self, event):
        """Show Pointing Hand Cursor on error messages"""
        if event.modifiers() & Qt.ControlModifier:
            cursor = self.cursorForPosition(event.pos())
            text = unicode(cursor.block().text())
            if self.parent().get_error_match(text):
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                return
        QApplication.restoreOverrideCursor()

    def mousePressEvent(self, event):
        """Keep the cursor after the last prompt"""
        ctrl = event.modifiers() & Qt.ControlModifier
        if (event.button() == Qt.LeftButton) and ctrl:
            cursor = self.cursorForPosition(event.pos())
            text = unicode(cursor.block().text())
            self.parent().go_to_error(text)
        else:
            cursor = self.cursorForPosition(event.pos())
            cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
            if cursor.selectedText().length() >= len(self.prompt):
                QTextEdit.mousePressEvent(self, event)
            else:
                cursor.movePosition(QTextCursor.EndOfLine)
                if not cursor.atEnd():
                    QTextEdit.mousePressEvent(self, event)
            
    def contentsContextMenuEvent(self,ev):
        """Suppress the right button context menu"""
        pass
        
    def canInsertFromMimeData(self, source):
        """Reimplement Qt method
        Drag and *drop* implementation"""
        if source.hasUrls():
            if mimedata2url(source):
                return True
        return QTextEdit.canInsertFromMimeData(self, source)

    def insertFromMimeData(self, source):
        """Reimplement Qt method
        Drag and *drop* implementation"""
        if source.hasUrls():
            files = mimedata2url(source)
            if files:
                files = ["r'%s'" % path for path in files]
                if len(files) == 1:
                    text = files[0]
                else:
                    text = "[" + ", ".join(files) + "]"
                self.insert_text(text)
        else:
            lines = unicode(source.text())
            if not self.__is_cursor_on_last_line():
                self.moveCursor(QTextCursor.End)
            lines = self.__get_current_line_to_cursor() + lines + \
                    self.__get_current_line_from_cursor()
            self.clear_line()
            self.execute_lines(lines)
    
    def set_docviewer(self, docviewer):
        """Set DocViewer DockWidget reference"""
        self.docviewer = docviewer

    def __is_cursor_on_last_line(self):
        """
        Private method to check if the cursor is on the last line.
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine)
        return cursor.atEnd()

    def __get_current_line_to_cursor(self):
        """
        Return the current line: from the beginning to cursor position
        """
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor,
                            len(self.prompt))
        return unicode(cursor.selectedText())
    
    def __get_current_line_from_cursor(self):
        """
        Return the current line: from cursor position to the end of the line
        """
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        return unicode(cursor.selectedText())
    
    def __get_last_obj(self, last=False):
        """
        Return the last valid object on the current line
        """
        return getobj(self.__get_current_line_to_cursor(), last=last)

    def show_completion_widget(self, textlist=None, objtext=None, pagestep=0):
        """Show completion widget"""
        if self.completion_widget:
            textlist, objtext, page = self.completion_widget
        else:
            page = 0
            
        font = get_font('calltips')
        weight = 'bold' if font.bold() else 'normal'
        format1 = '<span style=\'font-size: %spt\'>' % font.pointSize()
        format2 = '\n<hr><span style=\'font-family: "%s"; font-size: %spt; font-weight: %s\'>' % (font.family(), font.pointSize(), weight)
        
        if self.completion_widget:
            textlist = [txt for txt in textlist \
                        if txt.startswith(self.completion_text)]
            if len(textlist)==0:
                self.completion_match = ""
                return
        else:
            self.completion_widget = (textlist, objtext, 0)
            self.completion_match = ""
            self.completion_text = ""
        self.completion_match = textlist[0]
        
        maxperpage = 52
        
        if len(textlist) > maxperpage:
            pagenb = len(textlist)/maxperpage
            if pagenb*maxperpage < len(textlist):
                pagenb += 1
            page += pagestep
            if page == -1:
                page = 0
            elif page == pagenb:
                page = pagenb-1
            self.completion_widget = (textlist, objtext, page)
            idx1 = page*maxperpage
            idx2 = min([(page+1)*maxperpage-1, len(textlist)])
            lastpage = (idx2 == len(textlist))
            textlist = textlist[idx1:idx2]
            if not lastpage:
                textlist.append("...")
            
#        if len(textlist) > 80:
#            colnb = 6
#            rownb = len(textlist)/colnb
#            if rownb*colnb < len(textlist):
#                rownb += 1
        if len(textlist) > 40:
            colnb = 4
            rownb = len(textlist)/colnb
            if rownb*colnb < len(textlist):
                rownb += 1
        elif len(textlist) > 15:
            rownb = 10
            colnb = len(textlist)/rownb
            if colnb*rownb < len(textlist):
                colnb += 1
        elif len(textlist) > 5:
            rownb = 5
            colnb = len(textlist)/rownb
            if colnb*rownb < len(textlist):
                colnb += 1
        else:
            rownb = len(textlist)
            colnb = 1
        
        text = "<table cellspacing=5>"
        for irow in range(0, rownb):
            text += "<tr>"
            for icol in range(0, colnb):
                text += "<td>"
                try:
                    celltext = textlist[irow+icol*rownb]
                except IndexError:
                    celltext = ""
                if irow == 0 and icol == 0:
                    celltext = "<b><span style=\'color: #0000FF\'>" + \
                               celltext + "</span></b>"
                text += celltext + "</td>"
            text += "</tr>"
        text += "</table>"

        text = format1+('<b>%s</b></span>:' % objtext)+format2+text+"</span>"
        rect = self.cursorRect()
        point = self.mapToGlobal(QPoint(rect.x(), rect.y()))
        QToolTip.showText(point, text, self)
        
    def hide_completion_widget(self):
        """Hide completion widget"""
        QToolTip.showText(QPoint(0, 0), "", self)
        self.completion_widget = None
        
    def __completion_list_selected(self):
        """
        Private slot to handle the selection from the completion list
        """
        if self.completion_match:
            extra = self.completion_match[len(self.completion_text):]
            if extra:
                self.insert_text(extra)
        self.hide_completion_widget()

    def show_calltip(self, text):
        """Show calltip"""
        if not self.calltips:
            return
        if text is None or len(text)==0:
            return
        tipsize = CONF.get('calltips', 'size')
        font = get_font('calltips')
        weight = 'bold' if font.bold() else 'normal'
        format1 = '<span style=\'font-size: %spt\'>' % font.pointSize()
        format2 = '\n<hr><span style=\'font-family: "%s"; font-size: %spt; font-weight: %s\'>' % (font.family(), font.pointSize(), weight)
        if isinstance(text, list):
            text = "\n    ".join(text)
            text = format1+'<b>Arguments</b></span>:'+format2+text+"</span>"
        else:
            if len(text) > tipsize:
                text = text[:tipsize] + " ..."
            text = text.replace('\n', '<br>')
            text = format1+'<b>Documentation</b></span>:'+format2+text+"</span>"
        rect = self.cursorRect()
        point = self.mapToGlobal(QPoint(rect.x(), rect.y()))
        QToolTip.showText(point, text)
        
