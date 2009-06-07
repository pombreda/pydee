# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""QScintilla base class"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys
from PyQt4.QtGui import QFont, QToolTip
from PyQt4.QtCore import QPoint, SIGNAL, QString, QRegExp
from PyQt4.Qsci import QsciScintilla

# For debugging purpose:
STDOUT = sys.stdout


class QsciBase(QsciScintilla):
    """
    QScintilla base class
    """
    def __init__(self, parent=None):
        QsciScintilla.__init__(self, parent)
        self.setup_scintilla()
        
    def setup_scintilla(self):
        """Configure Scintilla"""
        # UTF-8
        self.setUtf8(True)
        
        # Indentation
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setTabIndents(True)
        self.setBackspaceUnindents(True)
        self.setTabWidth(4)
        
        # Enable brace matching
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        
    def remove_margins(self):
        """Suppressing Scintilla margins"""
        self.setMarginWidth(0, 0)
        self.setMarginWidth(1, 0)
        self.setMarginWidth(2, 0)
        
    def set_wrap_mode(self, enable):
        """Enable/disable wrap mode"""
        self.setWrapMode(QsciScintilla.WrapWord if enable
                         else QsciScintilla.WrapNone)
        
    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False):
        """Find text"""
        # findFirst(expr, re, cs, wo, wrap, forward, line, index, show)
        if changed or not forward:
            line_from, index_from, _line_to, _index_to = self.getSelection()
            self.setCursorPosition(line_from, max([0, index_from-1]))
        return self.findFirst(text, False, case, words,
                              True, forward, -1, -1, True)    

    #----Positions/Cursor
    def position_from_lineindex(self, line, index):
        """Convert (line, index) to position"""
        pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, line)
        # Allow for multi-byte characters
        for _i in range(index):
            pos = self.SendScintilla(QsciScintilla.SCI_POSITIONAFTER, pos)
        return pos
    
    def get_end_pos(self):
        """Return (line, index) position of the last character"""
        line = self.lines() - 1
        return (line, self.text(line).length())

    def move_cursor_to_start(self):
        """Move cursor to start of text"""
        self.setCursorPosition(0, 0)
        self.ensureCursorVisible()

    def move_cursor_to_end(self):
        """Move cursor to end of text"""
        line, index = self.get_end_pos()
        self.setCursorPosition(line, index)
        self.ensureCursorVisible()
        
    def is_cursor_on_last_line(self):
        """Return True if cursor is on the last line"""
        cline, _ = self.getCursorPosition()
        return cline == self.lines() - 1

    def is_cursor_at_end(self):
        """Return True if cursor is at the end of text"""
        cline, cindex = self.getCursorPosition()
        return (cline, cindex) == self.get_end_pos()

    def get_coordinates_from_lineindex(self, line, index):
        """Return cursor x, y point coordinates for line, index position"""
        pos = self.position_from_lineindex(line, index)
        x_pt = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
        y_pt = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)
        return x_pt, y_pt

    def get_cursor_coordinates(self):
        """Return cursor x, y point coordinates"""
        line, index = self.getCursorPosition()
        return self.get_coordinates_from_lineindex(line, index)

    
    def is_a_word(self, text):
        """Is 'text' a word? (according to current lexer)"""
        regexp = QRegExp( QString('[^%1]').arg(self.wordCharacters()) )
        return not regexp.exactMatch(text)


    def clear_selection(self):
        """Clear current selection"""
        line, index = self.getCursorPosition()
        self.setSelection(line, index, line, index)


    def show_calltip(self, title, text, tipsize=600, font=None,
                     color='#2D62FF', at_line=None):
        """
        Show calltip
        This is here because QScintilla does not implement well calltips
        """
        if text is None or len(text)==0:
            return
        if font is None:
            font = QFont()
        weight = 'bold' if font.bold() else 'normal'
        format1 = '<div style=\'font-size: %spt; color: %s\'>' % (font.pointSize(), color)
        format2 = '<hr><div style=\'font-family: "%s"; font-size: %spt; font-weight: %s\'>' % (font.family(), font.pointSize(), weight)
        if isinstance(text, list):
            text = "\n    ".join(text)
        else:
            text = text.replace('\n', '<br>')
        if len(text) > tipsize:
            text = text[:tipsize] + " ..."
        tiptext = format1 + ('<b>%s</b></div>' % title) \
                  + format2 + text + "</div>"
        # Showing tooltip at cursor position:
        cx, cy = self.get_cursor_coordinates()
        if at_line is not None:
            cx = 5
            _, cy = self.get_coordinates_from_lineindex(at_line, 0)
        QToolTip.showText(self.mapToGlobal(QPoint(cx, cy)), tiptext)


    #----Focus
    def focusInEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        QsciScintilla.focusInEvent(self, event)
        
    def focusOutEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        QsciScintilla.focusOutEvent(self, event)
