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

"""Editor widget based on QScintilla"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os
from PyQt4.QtGui import QMouseEvent, QColor
from PyQt4.QtCore import Qt, SIGNAL, QString, QEvent
from PyQt4.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs

# For debugging purpose:
STDOUT = sys.stdout

# Local import
from PyQtShell.config import CONF, get_font
from PyQtShell.widgets.qscibase import QsciBase


class QsciEditor(QsciBase):
    """
    QScintilla Base Editor Widget
    """
    def __init__(self, parent=None, margin=True):
        QsciBase.__init__(self, parent)
        
        # Mouse selection copy feature
        self.always_copy_selection = False
                
        if margin:
            self.connect( self, SIGNAL('linesChanged()'), self.lines_changed )
        else:
            self.setup_margin(None)
            
        # Scintilla Python API
        self.api = None
        
    def setup_scintilla(self):
        """Reimplement QsciBase method"""
        QsciBase.setup_scintilla(self)
        
        # Wrapping
        if CONF.get('editor', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
        # Indentation
        self.setIndentationGuides(True)
        self.setIndentationGuidesForegroundColor(Qt.lightGray)
        self.setFolding(QsciScintilla.BoxedFoldStyle)
        
        # 80-columns edge
        self.setEdgeColumn(80)
        self.setEdgeMode(QsciScintilla.EdgeLine)
        
        # Auto-completion
        self.setAutoCompletionThreshold(-1)
        self.setAutoCompletionSource(QsciScintilla.AcsAll)

        # Lexer
        self.setLexer( QsciLexerPython(self) )
                
        # Colors
        fcol = CONF.get('scintilla', 'margins/foregroundcolor')
        bcol = CONF.get('scintilla', 'margins/backgroundcolor')
        if fcol:
            self.setMarginsForegroundColor(QColor(fcol))
        if bcol:
            self.setMarginsBackgroundColor(QColor(bcol))
        fcol = CONF.get('scintilla', 'foldmarginpattern/foregroundcolor')
        bcol = CONF.get('scintilla', 'foldmarginpattern/backgroundcolor')
        if fcol and bcol:
            self.setFoldMarginColors(QColor(fcol), QColor(bcol))
        
    def setup_api(self):
        """Load and prepare API"""
        self.api = QsciAPIs(self.lexer())
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
        self.lexer().setFont(font)
        self.setLexer(self.lexer())
        
    def set_text(self, text):
        """Set the text of the editor"""
        self.setText(text)

    def get_text(self):
        """Return editor text"""
        return self.text()
    
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
        self.add_prefix( '#' )

    def uncomment(self):
        """Uncomment current line or selection"""
        self.remove_prefix( '#' )
            
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
