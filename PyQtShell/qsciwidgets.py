# -*- coding: utf-8 -*-
"""Widgets based on QScintilla"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os
from PyQt4.QtGui import QKeySequence, QApplication, QClipboard, QMenu
from PyQt4.QtGui import QMessageBox
from PyQt4.QtCore import Qt, SIGNAL, QString, QStringList
from PyQt4.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs

# For debugging purpose:
STDOUT = sys.stdout

# Local import
import encoding, re
from shell import Interpreter, create_banner
from config import CONF, get_icon
from dochelpers import getargtxt
from qthelpers import create_action, add_actions, get_std_icon, translate


class LexerPython(QsciLexerPython):
    """ 
    Subclass to implement some additional lexer dependant methods.
    """
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
    def __init__(self, parent=None):
        QsciScintilla.__init__(self, parent)
        
        self.setUtf8(True)
        
        # Indentation
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setTabIndents(True)
        self.setTabWidth(4)
        
        # Auto-completion
        self.setAutoCompletionThreshold(-1)
        self.setAutoCompletionSource(QsciScintilla.AcsAll)
        
        self.setFolding(QsciScintilla.BoxedTreeFoldStyle)

        # Lexer
        self.lex = LexerPython(self)
        self.setLexer(self.lex)
        self.api = None
        
        self.setMinimumWidth(200)
        self.setMinimumHeight(100)
        
    def setup_api(self):
        """Load and prepare API"""
        self.api = QsciAPIs(self.lex)
        is_api_ready = False
        api_path = CONF.get('editor', 'api')
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

    def setup_margin(self, font, width=None):
        """Set margin font and width"""
        if font is None:
            self.setMarginLineNumbers(1, False)
            self.setMarginWidth(1, 0)
        else:
            self.setMarginLineNumbers(1, True)
            self.setMarginsFont(font)
            if width is None:
                linenb = self.lines()
                if linenb < 10:
                    linenb = 100
                from math import ceil, log
                width = ceil(log(linenb, 10))+1
            self.setMarginWidth(1, QString('0'*int(width+1)))

    def set_font(self, font):
        """Set shell font"""
        self.lex.setFont(font)
        self.setLexer(self.lex)
        
    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        self.setWrapMode(QsciScintilla.WrapWord if enable
                         else QsciScintilla.WrapNone)
        
    def go_to_line(self, linenb):
        """Go to line number"""
        self.ensureLineVisible(linenb)
        
    def set_text(self, text):
        """Set the text of the editor"""
        self.setText(text)

    def get_text(self):
        """Return editor text"""
        return self.text()
    

class QsciShell(QsciScintilla, Interpreter):
    """
    Python shell based on QScintilla
    Derived from:
        PyCute (pycute.py): http://gerard.vermeulen.free.fr (GPL)
        Eric4 shell (shell.py): http://www.die-offenbachs.de/eric/index.html (GPL)
    """
    def __init__(self, namespace=None, commands=[], message="",
    			 parent=None, debug=False, exitfunc=None):
        """
        namespace : locals send to InteractiveInterpreter object
        commands: list of commands executed at startup
        message : welcome message string
        parent : specifies the parent widget
        If no parent widget has been specified, it is possible to
        exit the interpreter by Ctrl-D
        """
        Interpreter.__init__(self, namespace, debug, exitfunc)       
        QsciScintilla.__init__(self, parent)
        
        self.setUtf8(True)

        # Indentation
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setTabIndents(True)
        self.setTabWidth(4)
        
        # Auto Completion setup
        self.setAutoCompletionThreshold( \
            CONF.get('shell', 'autocompletion/threshold') )
        self.setAutoCompletionCaseSensitivity( \
            CONF.get('shell', 'autocompletion/case-sensitivity') )
        self.setAutoCompletionShowSingle( \
            CONF.get('shell', 'autocompletion/select-single') )
        self.setAutoCompletionSource(QsciScintilla.AcsDocument)
        self.completion_chars = 0
        
        # Call-tips
        self.docviewer = None
        
        # Create a little context menu
        self.menu = QMenu(self)
        cut_action   = create_action(self, translate("ShellBaseWidget", "Cut"),
                           icon=get_icon('cut.png'), triggered=self.cut)
        copy_action  = create_action(self, translate("ShellBaseWidget", "Copy"),
                           icon=get_icon('copy.png'), triggered=self.copy)
        paste_action = create_action(self,
                           translate("ShellBaseWidget", "Paste"),
                           icon=get_icon('paste.png'), triggered=self.paste)
        clear_action = create_action(self,
                           translate("ShellBaseWidget", "Clear shell"),
                           icon=get_std_icon("TrashIcon"),
                           tip=translate("ShellBaseWidget",
                                   "Clear shell contents ('cls' command)"),
                           triggered=self.__clear)
        self.help_action = create_action(self,
                           translate("ShellBaseWidget", "Help..."),
                           icon=get_std_icon('DialogHelpButton'),
                           triggered=self.help)
        add_actions(self.menu, (cut_action, copy_action, paste_action,
                                None, clear_action, None, self.help_action) )

        self.setMinimumWidth(400)
        self.setMinimumHeight(150)
        
        # Lexer
        self.lexer = QsciLexerPython(self)

        # Search
        self.incremental_search_string = ""
        self.incremental_search_active = False
        
        # interpreter banner
        moreinfo, helpmsg = self.get_banner()
        self.write( create_banner(moreinfo, message) )
        self.write(helpmsg + '\n\n')

        # Initial commands
        for cmd in commands:
            if not self.push(cmd):
                self.resetbuffer()
                
        # First prompt
        self.write(self.prompt)
        self.emit(SIGNAL("refresh()"))

        #self.standardCommands().clearKeys()
        self.keymap = {
            Qt.Key_Backspace : self.__qsci_delete_back,
            Qt.Key_Delete : self.__qsci_delete,
            Qt.Key_Return : self.__qsci_newline,
            Qt.Key_Enter : self.__qsci_newline,
            Qt.Key_Tab : self.__qsci_tab,
            Qt.Key_Left : self.__qsci_char_left,
            Qt.Key_Right : self.__qsci_char_right,
            Qt.Key_Up : self.__qsci_line_up,
            Qt.Key_Down : self.__qsci_line_down,
            Qt.Key_Home : self.__qsci_vchome,
            Qt.Key_End : self.__qsci_line_end,
            Qt.Key_PageUp : self.__qsci_pageup,
            Qt.Key_PageDown : self.__qsci_pagedown,
            Qt.Key_Escape : self.__qsci_cancel,
            }
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     self.__completion_list_selected)
        self.setFocus()
        self.emit(SIGNAL("status(QString)"), QString())

    def get_menu(self):
        """Return shell context menu"""
        return self.menu
        
    def help(self):
        """Help on PyQtShell console"""
        QMessageBox.about(self,
            translate("ShellBaseWidget", "Help"),
            self.tr("""<b>%1</b>
            <p><i>%2</i><br>    edit foobar.py
            <p><i>%3</i><br>    run foobar.py
            <p><i>%4</i><br>    !ls
            <p><i>%5</i><br>    object?
            """) \
            .arg(translate("ShellBaseWidget", 'Shell special commands:')) \
            .arg(translate("ShellBaseWidget", 'External editor:')) \
            .arg(translate("ShellBaseWidget", 'Run script:')) \
            .arg(translate("ShellBaseWidget", 'System commands:')) \
            .arg(translate("ShellBaseWidget", 'Python help:')))

    def get_banner(self):
        """Return interpreter banner and a one-line message"""
        return (self.tr('Type "copyright", "credits" or "license" for more information.'),
                self.tr('Type "object?" for details on "object"'))

    def set_font(self, font):
        """Set shell font"""
        self.lexer.setFont(font)
        self.setLexer(self.lexer)
        
    def set_wrap_mode(self, enable):
        """Set wrap mode"""
        self.setWrapMode(QsciScintilla.WrapWord if enable
                         else QsciScintilla.WrapNone)
        
    #------ Utilities
    def __remove_prompts(self, text):
        """Remove prompts from text"""
        return text.replace(self.prompt, "").replace(self.prompt_more, "")
    
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


    #------ stdin, stdout, stderr
    def readline(self):
        """Simulate stdin, stdout, and stderr"""
        self.reading = 1
        line, col = self.__get_end_pos()
        self.setCursorPosition(line, col)
        buf = ""
        if len(buf) == 0:
            return '\n'
        else:
            return buf

    def write(self, text):
        """Simulate stdin, stdout, and stderr"""
        line, col = self.__get_end_pos()
        self.setCursorPosition(line, col)
        self.insert(encoding.to_unicode(text))
        line, col = self.__get_end_pos()
        self.setCursorPosition(line, col)
        self.prline, self.prcol = self.getCursorPosition()
        self.ensureCursorVisible()
        self.ensureLineVisible(line)
    
        
    #------ Command Execution
    def __execute_lines(self, lines):
        """
        Private method to execute a set of lines as multiple commands
        lines: multiple lines of text to be executed as single
            commands (string)
        """
        for line in lines.splitlines(True):
            if line.endswith("\r\n"):
                fullline = True
                cmd = line[:-2]
            elif line.endswith("\r") or line.endswith("\n"):
                fullline = True
                cmd = line[:-1]
            else:
                fullline = False
            
            self.__insert_text(line, at_end=True)
            if fullline:
                self.__execute_command(cmd)

    def __execute_command(self, cmd):
        """
        Private slot to execute a command.
        cmd: one-line command only, without '\n' at the end!
        """
        # cls command
        if cmd == 'cls':
            self.__clear()
            return
                
        # Before running command
        self.emit(SIGNAL("status(QString)"), self.tr('Busy...'))
        
        self.run_command(cmd)
            
        self.emit(SIGNAL("status(QString)"), QString())
            
        # The following signal must be connected to any other related widget:
        self.emit(SIGNAL("refresh()"))
    
    #------ Text Insertion
    def __insert_text(self, text, at_end=False):
        """
        Insert text at the current cursor position
        or at the end of the command line
        """
        if at_end:
            # Insert text at the end of the command line
            line, col = self.__get_end_pos()
            self.setCursorPosition(line, col)
            self.insert(text)
            self.prline, self.prcol = self.__get_end_pos()
            self.setCursorPosition(self.prline, self.prcol)
        else:
            # Insert text at current cursor position
            line, col = self.getCursorPosition()
            self.insertAt(text, line, col)
            self.setCursorPosition(line, col + len(str(text)))
        

    #------ Re-implemented Qt Methods
    def contextMenuEvent(self, event):
        """
        Re-implemented to hide context menu
        """
        self.menu.popup(event.globalPos())
        event.accept()

    def mousePressEvent(self, event):
        """
        Re-implemented to handle the mouse press event.
        event: the mouse press event (QMouseEvent)
        """
        self.setFocus()
        if event.button() == Qt.MidButton:
            self.__middle_mouse_button()
        else:
            QsciScintilla.mousePressEvent(self, event)

    def keyPressEvent(self, key_event):
        """
        Re-implemented to handle the user input a key at a time.
        key_event: key event (QKeyEvent)
        """
        txt = key_event.text()
        key = key_event.key()
        ctrl = key_event.modifiers() & Qt.ControlModifier
        shift = key_event.modifiers() & Qt.ShiftModifier
        line, index = self.getCursorPosition()
        last_line = self.lines()-1
        if (self.keymap.has_key(key) and not shift and not ctrl):
            self.keymap[key]()
        elif key_event == QKeySequence.Paste:
            self.paste()
        elif line==last_line and txt.length():
            prompt = self.prompt_more if self.more else self.prompt
            if index<len(prompt):
                self.setCursorPosition(line, len(prompt))
            self.__keypressed(txt, key_event)
        elif ctrl or shift:
            QsciScintilla.keyPressEvent(self, key_event)
        elif line!=last_line:
            line, index = self.__get_end_pos()
            self.setCursorPosition(line, index)
            self.__keypressed(txt, key_event)
        else:
            key_event.ignore()

    def __keypressed(self, txt, key_event):
        """Private key pressed event handler"""
        QsciScintilla.keyPressEvent(self, key_event)
        self.incremental_search_active = True
        if txt == '.':
            # Enable auto-completion only if last token isn't a float
            text = self.__get_current_line_to_cursor()
            tokens = text.split(" ")
            if not tokens[-1].isdigit():
                self.__show_dyn_completion(text)
        if txt == '(' or txt =='?':
            self.__show_docstring()
        elif self.isListActive():
            self.completion_chars += 1

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
            self.__insert_text(text, at_end=True)
            self.setFocus()
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()


    #------ Paste, middle-button, ...    
    def paste(self):
        """Reimplemented slot to handle multiline paste action"""
        lines = unicode(QApplication.clipboard().text())
        if self.__is_cursor_on_last_line():
            # Paste at cursor position
            cline, cindex = self.getCursorPosition()
            linetext = unicode(self.text(cline))
            lines = linetext[:cindex] + lines + linetext[cindex:]
            self.setSelection(cline, len(self.prompt),
                              cline, self.lineLength(cline))
            self.removeSelectedText()
            lines = self.__remove_prompts(lines)
            self.__execute_lines(lines)
            cline2, _ = self.getCursorPosition()
            self.setCursorPosition(cline2,
               self.lineLength(cline2)-len(linetext[cindex:]) )
        else:
            self.__execute_lines(lines)
            
    def __clear(self):
        """Reimplemented to write prompt after clearing shell"""
        self.clear()
        if self.more:
            self.write(self.prompt_more)
        else:
            self.write(self.prompt)
            
    def __middle_mouse_button(self):
        """Private method to handle the middle mouse button press"""
        lines = unicode(QApplication.clipboard().text(
            QClipboard.Selection))
        self.__execute_lines(lines)
    

    #------ QScintilla Key Management                                          
    def __qsci_tab(self):
        """
        Private method to handle the Tab key.
        """
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_TAB)
        elif self.__is_cursor_on_last_line():
            line, index = self.getCursorPosition()
            buf = self.__extract_from_text(line)
            lastchar_index = index-len(self.prompt)-1
            if self.more and not buf[:index-len(self.prompt_more)].strip():
                self.SendScintilla(QsciScintilla.SCI_TAB)
            elif lastchar_index>=0:
                if buf[lastchar_index] == '.':
                    self.__show_dyn_completion()
                elif buf[lastchar_index] in ['"', "'"]:
                    self.__show_file_completion()
             
    def __qsci_delete_back(self):
        """
        Private method to handle the Backspace key.
        """
        if self.hasSelectedText():
            self.__delete_selected_text()
        if self.__is_cursor_on_last_line():
            line, col = self.getCursorPosition()
            is_active = self.isListActive()
            old_length = self.text(line).length()
            if self.text(line).startsWith(self.prompt):
                if col > len(self.prompt):
                    self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
            elif self.text(line).startsWith(self.prompt_more):
                if col > len(self.prompt_more):
                    self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
            elif col > 0:
                self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
            if self.isListActive():
                self.completion_chars -= 1

    def __qsci_delete(self):
        """
        Private method to handle the delete command.
        """
        if self.hasSelectedText():
            self.__delete_selected_text()
        if self.__is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_CLEAR)
                
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
            
        for prompt in [self.prompt, self.prompt_more]:
            if self.text(line_from).startsWith(prompt):
                if index_from < len(prompt):
                    index_from = len(prompt)
        if index_from < 0:
            index_from = index_to
            line_from = line_to
        self.setSelection(line_from, index_from, line_to, index_to)
        self.SendScintilla(QsciScintilla.SCI_CLEAR)
        self.setSelection(line_to, index_to, line_to, index_to)

    def __qsci_newline(self):
        """
        Private method to handle the Return key.
        """
        if self.__is_cursor_on_last_line():
            if self.isListActive():
                self.SendScintilla(QsciScintilla.SCI_NEWLINE)
            elif self.reading:
                self.reading = 0
            else:
                self.incremental_search_string = ""
                self.incremental_search_active = False
                line, col = self.__get_end_pos()
                self.setCursorPosition(line, col)
                buf = self.__extract_from_text(line)
                self.insert('\n')
                self.__execute_command(buf)
        # add and run selection
        else:
            text = self.selectedText()
            self.__insert_text(text, at_end=True)

    def __qsci_char_left(self, all_lines_allowed = False):
        """
        Private method to handle the Cursor Left command.
        """
        if self.__is_cursor_on_last_line() or all_lines_allowed:
            line, col = self.getCursorPosition()
            if self.text(line).startsWith(self.prompt):
                if col > len(self.prompt):
                    self.SendScintilla(QsciScintilla.SCI_CHARLEFT)
            elif self.text(line).startsWith(self.prompt_more):
                if col > len(self.prompt_more):
                    self.SendScintilla(QsciScintilla.SCI_CHARLEFT)
            elif col > 0:
                self.SendScintilla(QsciScintilla.SCI_CHARLEFT)

    def __qsci_char_right(self):
        """
        Private method to handle the Cursor Right command.
        """
        if self.__is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_CHARRIGHT)

    def __qsci_vchome(self):
        """
        Private method to handle the Home key.
        """
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_VCHOME)
        elif self.__is_cursor_on_last_line():
            line, col = self.getCursorPosition()
            if self.text(line).startsWith(self.prompt):
                col = len(self.prompt)
            elif self.text(line).startsWith(self.prompt_more):
                col = len(self.prompt_more)
            else:
                col = 0
            self.setCursorPosition(line, col)

    def __qsci_line_end(self):
        """
        Private method to handle the End key.
        """
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_LINEEND)
        elif self.__is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_LINEEND)

    def __qsci_line_up(self):
        """
        Private method to handle the Up key.
        """
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_LINEUP)
        else:
            line, _ = self.__get_end_pos()
            buf = self.__extract_from_text(line)
            if buf and self.incremental_search_active:
                if self.incremental_search_string:
                    idx = self.__rsearch_history( \
                        self.incremental_search_string, self.histidx)
                    if idx >= 0:
                        self.histidx = idx
                        self.__use_history()
                else:
                    idx = self.__rsearch_history(buf)
                    if idx >= 0:
                        self.histidx = idx
                        self.incremental_search_string = buf
                        self.__use_history()
            else:
                if self.histidx < 0:
                    self.histidx = len(self.history)
                if self.histidx > 0:
                    self.histidx = self.histidx - 1
                    self.__use_history()

    def __qsci_line_down(self):
        """
        Private method to handle the Down key.
        """
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_LINEDOWN)
        else:
            line, _col = self.__get_end_pos()
            buf = self.__extract_from_text(line)
            if buf and self.incremental_search_active:
                if self.incremental_search_string:
                    idx = self.__search_history( \
                        self.incremental_search_string, self.histidx)
                    if idx >= 0:
                        self.histidx = idx
                        self.__use_history()
                else:
                    idx = self.__search_history(buf)
                    if idx >= 0:
                        self.histidx = idx
                        self.incremental_search_string = buf
                        self.__use_history()
            else:
                if self.histidx >= 0 and self.histidx < len(self.history):
                    self.histidx += 1
                    self.__use_history()
  
    def __qsci_pageup(self):
        """
        Private method to handle the PGUP key
        """
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(QsciScintilla.SCI_PAGEUP)
  
    def __qsci_pagedown(self):
        """
        Private method to handle the PGDOWN key
        """
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(QsciScintilla.SCI_PAGEDOWN)
  
    def __qsci_cancel(self):
        """
        Private method to handle the Esc key
        """
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(QsciScintilla.SCI_CANCEL)
  
    #------ History Management
    def __use_history(self):
        """
        Private method to display a command from the history
        """
        if self.histidx < len(self.history):
            cmd = QString( self.history[self.histidx] )
        else:
            cmd = QString()
            self.incremental_search_string = ""
            self.incremental_search_active = False
        self.setCursorPosition(self.prline, self.prcol \
            + len(self.more and self.prompt or self.prompt_more))
        self.setSelection(self.prline, self.prcol, \
            self.prline,self.lineLength(self.prline))
        self.removeSelectedText()
        self.__insert_text(cmd)

    def __search_history(self, txt, start_index = -1):
        """
        Private method used to search the history
        txt: text to match at the beginning (string or QString)
        start_index: index to start search from (integer)
        @return index of 
        """
        if start_index == -1:
            idx = 0
        else:
            idx = start_index + 1
        while idx < len(self.history) and \
              not self.history[idx].startswith(txt):
            idx += 1
        return idx
    
    def __rsearch_history(self, txt, start_index = -1):
        """
        Private method used to reverse search the history
        txt: text to match at the beginning (string or QString)
        start_index: index to start search from (integer)
        @return index of 
        """
        if start_index == -1:
            idx = len(self.history) - 1
        else:
            idx = start_index - 1
        while idx >= 0 and \
              not self.history[idx].startswith(txt):
            idx -= 1
        return idx


    #------ Miscellanous
    def __get_current_line_to_cursor(self):
        """
        Return the current line: from the beginning to cursor position
        """
        line, index = self.getCursorPosition()
        buf = self.__extract_from_text(line)
        # Removing the end of the line from cursor position:
        buf = buf[:index-len(self.prompt)]
        # Keeping only last word, without its last character:
        return buf.split()[-1][:-1]
        
    def set_docviewer(self, docviewer):
        """Set DocViewer DockWidget reference"""
        self.docviewer = docviewer
        
    def __show_docstring(self):
        """Show docstring or arguments"""
        text = self.__get_current_line_to_cursor()
        try:
            obj = eval(text, globals(), self.locals)
        except:
            # No valid object was extracted from text
            pass
        else:
            # Object obj is valid
            if (self.docviewer is not None) and \
               (self.docviewer.dockwidget.isVisible()):
                # DocViewer widget exists and is visible
                self.docviewer.refresh(text)
                arglist = getargtxt(obj)
                if arglist:
                    self.showUserList(10, QStringList(arglist))
            else:
                self.showUserList(10, QStringList( obj.__doc__.split('\n') ))
        
    #------ Code Completion Management            
    def __show_dyn_completion(self, text=None):
        """
        Display a completion list based on the last token
        """
        if text is None:
            text = self.__get_current_line_to_cursor()
        try:
            obj = eval(text, globals(), self.locals)
        except:
            # No valid object was extracted from text
            pass
        else:
            # Object obj is valid
            self.__show_completions(dir(obj), text) 

    def __show_file_completion(self):
        """
        Display a completion list for files and directories
        """
        text = self.__get_current_line_to_cursor()
        self.__show_completions(os.listdir(os.getcwd()), text) 

    def __show_completions(self, completions, text):
        """
        Private method to display the possible completions.
        """
        if len(completions) == 0:
            return
        if len(completions) > 1:
            self.showUserList(1, QStringList(sorted(completions)))
            self.completion_chars = 1
        else:
            txt = completions[0]
            if text != "":
                txt = txt.replace(text, "")
            self.__insert_text(txt)
            self.completion_chars = 0

    def __completion_list_selected(self, userlist_id, seltxt):
        """
        Private slot to handle the selection from the completion list
        userlist_id: ID of the user list (should be 1) (integer)
        seltxt: selected text (QString)
        """
        if userlist_id == 1:
            cline, cindex = self.getCursorPosition()
            self.setSelection(cline, cindex-self.completion_chars+2,
                              cline, cindex)
            self.removeSelectedText()
            seltxt = unicode(seltxt)
            self.__insert_text(seltxt)
            self.completion_chars = 0
