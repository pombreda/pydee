# -*- coding: utf-8 -*-
"""Widgets used only if QScintilla is not installed"""

from PyQt4.QtGui import QTextEdit, QTextCursor, QColor, QFont, QCursor
from PyQt4.QtCore import Qt, QString, SIGNAL, QEvent, QRegExp, QPoint
from PyQt4.QtGui import QSyntaxHighlighter, QApplication, QTextCharFormat
from PyQt4.QtGui import QListWidget, QShortcut, QKeySequence, QToolTip

import sys
try:
    PS1 = sys.ps1
except AttributeError:
    PS1 = ">>> "

# For debugging purpose:
STDOUT = sys.stdout

# Local import
from config import get_font, CONF


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

    BUILTINS = ["abs", "all", "any", "basestring", "bool", "callable",
            "chr", "classmethod", "cmp", "compile", "complex", "delattr",
            "dict", "dir", "divmod", "enumerate", "eval", "execfile",
            "exit", "file", "filter", "float", "frozenset", "getattr",
            "globals", "hasattr", "hex", "id", "int", "isinstance",
            "issubclass", "iter", "len", "list", "locals", "long", "map",
            "max", "min", "object", "oct", "open", "ord", "pow",
            "property", "range", "reduce", "repr", "reversed", "round",
            "set", "setattr", "slice", "sorted", "staticmethod", "str",
            "sum", "super", "tuple", "type", "unichr", "unicode", "vars",
            "xrange", "zip"] 

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
        PythonHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % builtin \
                for builtin in PythonHighlighter.BUILTINS])),
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
        PythonHighlighter.Rules.append((QRegExp(r"#.*"), "comment"))       
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
        #TODO: change font for already displayed text
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


class QtEditor(QTextEdit):
    """
    Qt-based Editor Widget
    """
    def __init__(self, parent=None):
        super(QtEditor, self).__init__(parent)
        self.is_modified = False
        self.highlighter = PythonHighlighter(self, get_font('editor'))
        
    def isModified(self):
        """Fake QScintilla method"""
        return self.is_modified
    
    def setModified(self, state):
        """Fake QScintilla method"""
        self.is_modified = state
        
    def setCursorPosition(self, arg1, arg2):
        """Fake QScintilla method"""
        self.moveCursor(QTextCursor.End)
        self.ensureCursorVisible()
    
    def lines(self):
        """Fake QScintilla method"""
        return 0
    
    def setup_api(self):
        """Fake QScintilla method"""
        pass
    
    def setup_margin(self, font, width=None):
        """Fake QScintilla method"""
        pass
           
    def go_to_line(self, linenb):
        """Fake QScintilla method"""
        pass
        
    def set_text(self, str):
        """Set the text of the editor"""
        self.setPlainText(str)

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
            cursor.insertText("    ")
            return True
        return QTextEdit.event(self, event)


class QtTerminal(QTextEdit):
    """
    Terminal based on Qt only
    """    
    def __init__(self, parent=None):
        """
        parent : specifies the parent widget
        """
        QTextEdit.__init__(self, parent)
        self.format = QTextCharFormat()
        self.format.setFont(get_font('shell'))
        self.highlighter = PythonHighlighter(self, get_font('shell'))
        
        self.connect(self, SIGNAL("executing_command(bool)"),
                     self.highlighter.disable)
        
        self.completion_widget = None
        self.completion_chars = 0
        
        self.help_action = None
        
        # last line + last incomplete lines
        self.line    = QString()
        # the cursor position in the last line
        self.point   = 0
        # flag: the interpreter needs more input to run the last lines. 
        self.more    = 0
        self.pointer = 0
        self.cursor_pos   = 0

        # user interface setup
        #self.setLineWrapMode(QTextEdit.NoWrap)
        
        # Call-tips
        self.docviewer = None
        
        self.emit(SIGNAL("status(QString)"), QString())
    
    def get_banner(self):
        """Return interpreter banner and a one-line message"""
        return (self.tr('Type "copyright", "credits" or "license" for more information.'),
                self.tr('This version of PyQtShell is based on PyQt4 only')+'\n'+
                self.tr('Please install QScintilla to try the PyQt4/QScintilla-based version')+
                ':'+'\n'+'http://www.riverbankcomputing.co.uk/qscintilla')      

    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        if enable:
            self.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.setLineWrapMode(QTextEdit.NoWrap)
                
    def set_font(self, font):
        """Set shell font"""
        if self.highlighter is not None:
            self.highlighter.set_font(font)
            
    def clear_terminal(self):
        """Clear terminal window and write prompt"""
        self.clear()
        self.write(self.prompt, flush=True)
        
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
                    #TODO: remove underlined spaces!!
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
            self.ensureCursorVisible()
        else:
            # Insert text at current cursor position
            self.line.insert(self.point, text)
            self.point += len(text)
            cursor.insertText(text, self.format)
            
    def writelines(self, text):
        """
        Simulate stdin, stdout, and stderr.
        """
        map(self.write, text)

    def __clear_line(self):
        """
        Clear input line buffer
        """
        self.line.truncate(0)
        self.point = 0

    def keyPressEvent(self, event):
        """
        Handle user input a key at a time.
        """
        text  = event.text()
        key   = event.key()
        shift = event.modifiers() & Qt.ShiftModifier
        
        if key == Qt.Key_Backspace:
            if self.point:
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.PreviousCharacter,
                                    QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
            
                self.point -= 1 
                self.line.remove(self.point, 1)
                if self.completion_widget is not None and \
                   self.completion_widget.isVisible():
                    self.completion_chars -= 1

        elif key == Qt.Key_Delete:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.NextCharacter,
                                QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.line.remove(self.point, 1)
            
        elif shift and (key == Qt.Key_Return or key == Qt.Key_Enter):
            self.write('\n')
            self.pointer = 0
            self.append_command(unicode(self.line))
            self.__clear_line()
            
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            self.insert_text('\n', at_end=True)
            self.pointer = 0
            self.execute_command(unicode(self.line))
            self.__clear_line()
            self.moveCursor(QTextCursor.End)
                
        elif key == Qt.Key_Tab:
            current_line = self.__get_current_line_to_cursor()
            if len(current_line)>0 and current_line[-1] in ['"', "'"]:
                self.show_file_completion(current_line)
            elif len(current_line)>0 and current_line[-1] == ".":
                self.show_completion(current_line[:-1])
            else:
                self.insert_text("    ")
            
        elif key == Qt.Key_Left:
            if self.point : 
                self.moveCursor(QTextCursor.Left)
                self.point -= 1 
                
        elif key == Qt.Key_Right:
            if self.point < self.line.length():
                self.moveCursor(QTextCursor.Right)
                self.point += 1 

        elif key == Qt.Key_Home:
            cursor = self.textCursor ()
            cursor.setPosition(self.cursor_pos)
            self.setTextCursor (cursor)
            self.point = 0 

        elif key == Qt.Key_End:
            self.moveCursor(QTextCursor.EndOfLine)
            self.point = self.line.length() 

        elif key == Qt.Key_Up:
            if len(self.interpreter.history):
                if self.pointer == 0:
                    self.pointer = len(self.interpreter.history)
                self.pointer -= 1
                self.__recall()
                
        elif key == Qt.Key_Down:
            if len(self.interpreter.history):
                self.pointer += 1
                if self.pointer == len(self.interpreter.history):
                    self.pointer = 0
                self.__recall()
                
        elif event == QKeySequence.Copy:
            self.copy()
            
        elif event == QKeySequence.Paste:
            self.paste()
            
        elif event == QKeySequence.Cut:
            self.cut()
            
        elif event == QKeySequence.Undo:
            self.undo()
            
        elif event == QKeySequence.Redo:
            self.redo()
                
        elif key == Qt.Key_ParenLeft or key == Qt.Key_Question:
            self.show_docstring(self.__get_current_line_to_cursor())
            self.insert_text(text)
                
#        elif key == Qt.Key_Period:
#            current_line = self.__get_current_line_to_cursor()
#            tokens = current_line.split(" ")
#            if not tokens[-1].isdigit():
#                self.show_completion(current_line)
#            self.insert_text(text)

        elif text.length():
            text = unicode(text)
            if self.completion_widget is not None and \
               self.completion_widget.isVisible():
                self.completion_chars += 1
            self.insert_text(text)

    def __recall(self):
        """
        Display the current item from the command history.
        """
        cursor = self.textCursor()
        cursor.select( QTextCursor.LineUnderCursor )
        cursor.removeSelectedText()
        self.write(self.prompt)            
        self.__clear_line()
        self.insert_text( QString(self.interpreter.history[self.pointer]) )

    def mousePressEvent(self, event):
        """Keep the cursor after the last prompt"""
        ctrl = event.modifiers() & Qt.ControlModifier
        if event.button() == Qt.LeftButton:
            if ctrl:
                cursor = self.cursorForPosition(event.pos())
                text = unicode(cursor.block().text())
                if text.startswith("  File "):
                    pos1 = text.find('File ')
                    pos2 = text.find('", line ')
                    pos3 = text.find(', in')
                    if  (pos1 > 0) and (pos2 > 0) and (pos3 > 0):
                        fname = text[pos1+6:pos2]
                        lnb = int( text[pos2+8:pos3] )
                        self.external_editor(fname, lnb)
            else:
                self.moveCursor(QTextCursor.End)
            
    def contentsContextMenuEvent(self,ev):
        """Suppress the right button context menu"""
        pass

    def insertFromMimeData(self, source):
        """Paste"""
        self.insert_text( source.text() )
    
    def set_docviewer(self, docviewer):
        """Set DocViewer DockWidget reference"""
        self.docviewer = docviewer

    def __get_current_line_to_cursor(self):
        """
        Return the current line: from the beginning to cursor position
        """
        return unicode(self.textCursor().block().text()).split(" ")[-1]

    def showUserList(self, _id, words):
        """Reimplements QScintilla method"""
        firsttime = False
        if self.completion_widget is None:
            self.completion_widget = QListWidget(self)
            self.completion_widget.setFont(get_font('shell'))
            self.completion_widget.setWindowFlags(Qt.Popup)
            QShortcut(QKeySequence("Escape"), self.completion_widget,
                      self.completion_widget.close)
            self.connect(self.completion_widget,
                    SIGNAL("itemActivated(QListWidgetItem*)"),
                         self.__completion_list_selected)
            firsttime = True
        self.completion_widget.clear()
        self.completion_widget.addItems(sorted(words))
        self.completion_widget.setCurrentItem(self.completion_widget.item(0))
        self.completion_widget.scrollTo(
                self.completion_widget.currentIndex(),
                QListWidget.PositionAtCenter)
                
        rect = self.cursorRect()
        point = self.mapToGlobal(QPoint(rect.x(), rect.y()))
        if not firsttime:
            screen_rect = QApplication.desktop().availableGeometry(self)
            x_diff = screen_rect.width() - (point.x() + \
                    self.completion_widget.width())
            if x_diff < 0:
                point.setX(point.x() + x_diff)
            y_diff = screen_rect.height() - (point.y() + \
                    self.completion_widget.height())
            if y_diff < 0:
                point.setY(point.y() + y_diff)
#        point.setX(point.x())
        self.completion_widget.move(point)
        self.completion_widget.show()

    def show_calltip(self, text):
        """Show calltip"""
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
        
    def __completion_list_selected(self):
        """
        Private slot to handle the selection from the completion list
        """
        extra = self.completion_widget.currentItem().text(). \
                mid(self.completion_chars-1)
        if not extra.isEmpty():
            self.insert_text(extra)
        self.completion_widget.close()
        self.completion_chars = 0
