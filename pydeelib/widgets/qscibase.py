# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This file is part of Pydee.
#
#    Pydee is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    Pydee is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Pydee; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""QScintilla base class"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, re
from PyQt4.QtGui import QFont, QToolTip
from PyQt4.QtCore import QPoint
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

    def get_cursor_coordinates(self):
        """Return cursor x, y point coordinates"""
        line, index = self.getCursorPosition()
        pos = self.position_from_lineindex(line, index)
        x_pt = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
        y_pt = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)
        return x_pt, y_pt

    
    def is_a_word(self, text):
        """Is 'text' a word? (according to current lexer)"""
        re_iter = re.finditer('[^%s]' % self.wordCharacters(), text)
        try:
            re_iter.next()
            return False
        except StopIteration:
            return True


    def clear_selection(self):
        """Clear current selection"""
        line, index = self.getCursorPosition()
        self.setSelection(line, index, line, index)


    def show_calltip(self, title, text, tipsize=600,
                     font=None, color='#2D62FF'):
        """Show calltip
        This is here because QScintilla does not implement calltips"""
        if text is None or len(text)==0:
            return
        if font is None:
            font = QFont()
        weight = 'bold' if font.bold() else 'normal'
        format1 = '<span style=\'font-size: %spt; color: %s\'>' % (font.pointSize(), color)
        format2 = '\n<hr><span style=\'font-family: "%s"; font-size: %spt; font-weight: %s\'>' % (font.family(), font.pointSize(), weight)
        if isinstance(text, list):
            text = "\n    ".join(text)
        else:
            text = text.replace('\n', '<br>')
        if len(text) > tipsize:
            text = text[:tipsize] + " ..."
        tiptext = format1 + ('<b>%s</b></span>' % title) \
                  + format2 + text + "</span>"
        # Showing tooltip at cursor position:
        cx, cy = self.get_cursor_coordinates()
        QToolTip.showText(self.mapToGlobal(QPoint(cx, cy)), tiptext)
