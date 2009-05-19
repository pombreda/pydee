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

"""Shell base widget: link between QsciTerminal and Interpreter"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

#----Builtins
import __builtin__
try:
    from IPython.deep_reload import reload
    __builtin__.reload = reload
except ImportError:
    pass
from PyQtShell.widgets.objecteditor import oedit
__builtin__.oedit = oedit

import sys, os
from time import time
from subprocess import Popen, PIPE
import os.path as osp

STDOUT = sys.stdout

from PyQt4.QtGui import QCursor, QMessageBox, QToolTip, QClipboard, QApplication
from PyQt4.QtCore import SIGNAL, QString, Qt, QStringList

# Local import
from PyQtShell.qthelpers import (translate, create_action, get_std_icon,
                                 add_actions)
from PyQtShell.interpreter import Interpreter
from PyQtShell.dochelpers import getargtxt, getobj
from PyQtShell.encoding import transcode
from PyQtShell.config import CONF, get_font
try:
    from PyQt4.Qsci import QsciScintilla
    from PyQtShell.widgets.terminal import QsciTerminal
except ImportError, e:
    raise ImportError, str(e) + \
        "\nPyQtShell v0.3.23+ is exclusively based on QScintilla2\n" + \
        "(http://www.riverbankcomputing.co.uk/software/qscintilla)"


def guess_filename(filename):
    """Guess filename"""
    stw = filename.startswith
#    if stw('r"') or stw("r'") or stw('u"') or stw("u'"):
#        filename = filename[1:]
    if stw('"') or stw("'"):
        filename = filename[1:-1]
    if osp.isfile(filename):
        return filename
    pathlist = sys.path
    pathlist[0] = os.getcwdu()
    if not filename.endswith('.py'):
        filename += '.py'
    for path in pathlist:
        fname = osp.join(path, filename)
        if osp.isfile(fname):
            return fname
    return filename


def create_banner(moreinfo, message=''):
    """Create shell banner"""
    if message:
        message = '\n' + message + '\n'
    return 'Python %s on %s\n' % (sys.version, sys.platform) + \
            moreinfo+'\n' + message + '\n'



class ShellBaseWidget(QsciTerminal):
    """Shell base widget: link between QsciTerminal and Interpreter"""
    p1 = ">>> "
    p2 = "... "
    def __init__(self, parent=None, namespace=None, commands=None, message="",
                 debug=False, exitfunc=None, profile=False):
        QsciTerminal.__init__(self, parent, debug, profile)
        
        # Context menu
        self.menu = None
        self.setup_context_menu()
        
        # KeyboardInterrupt support
        self.interrupted = False
        
        self.docviewer = None
        
        # history
        self.histidx = None
        self.hist_wholeline = False
        
        # Code completion / calltips
        self.completion_chars = 0
        self.calltip_index = None
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
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     self.__completion_list_selected)
        
        # Call-tips
        self.calltips = True
        
        # keyboard events management
        self.busy = False
        self.eventqueue = []
        
        # Multiline entry
        self.multiline_entry = []
        
        # Execution Status
        self.more = False

        # Init interpreter
        self.exitfunc = exitfunc
        self.commands = commands
        self.message = message
        self.interpreter = None
        self.start_interpreter(namespace)
        
        # Clear status bar
        self.emit(SIGNAL("status(QString)"), QString())
        
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state
        
        
    #------ Interpreter
    def start_interpreter(self, namespace):
        """Start Python interpreter"""
        self.clear()
        
        #TODO: multithreaded Interpreter (if option.thread)
        self.interpreter = Interpreter(namespace, self.exitfunc, self.raw_input)

        # interpreter banner
        banner = create_banner(self.tr('Type "copyright", "credits" or "license" for more information.'), self.message)
        self.setUndoRedoEnabled(False) #-disable undo/redo for a time being
        self.write(banner, flush=True)

        # Initial commands
        for cmd in self.commands:
            self.run_command(cmd, history=False, multiline=True)
                
        # First prompt
        self.prompt = self.p1
        self.write(self.prompt, flush=True)
        self.setUndoRedoEnabled(True) #-enable undo/redo
        self.emit(SIGNAL("refresh()"))
        
        return self.interpreter
    
  
    #------ History Management
    def __browse_history(self, backward):
        """Browse history"""
        line, index = self.getCursorPosition()
        if index < self.lineLength(line) and self.hist_wholeline:
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
        
        
    #------ Code Completion / Calltips        
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


    #----- Menus, actions, ...
    def setup_context_menu(self):
        """Reimplement QsciTerminal method"""
        QsciTerminal.setup_context_menu(self)
        self.help_action = create_action(self,
                           translate("ShellBaseWidget", "Help..."),
                           shortcut="F1",
                           icon=get_std_icon('DialogHelpButton'),
                           triggered=self.help)
        add_actions(self.menu, (self.help_action,))

    def help(self):
        """Help on PyQtShell console"""
        QMessageBox.about(self,
            translate("ShellBaseWidget", "Help"),
            self.tr("""<b>%1</b>
            <p><i>%2</i><br>    edit foobar.py
            <p><i>%3</i><br>    xedit foobar.py
            <p><i>%4</i><br>    run foobar.py
            <p><i>%5</i><br>    clear x, y
            <p><i>%6</i><br>    !ls
            <p><i>%7</i><br>    object?
            <p><i>%8</i><br>    result = oedit(object)
            """) \
            .arg(translate("ShellBaseWidget", 'Shell special commands:')) \
            .arg(translate("ShellBaseWidget", 'Internal editor:')) \
            .arg(translate("ShellBaseWidget", 'External editor:')) \
            .arg(translate("ShellBaseWidget", 'Run script:')) \
            .arg(translate("ShellBaseWidget", 'Remove references:')) \
            .arg(translate("ShellBaseWidget", 'System commands:')) \
            .arg(translate("ShellBaseWidget", 'Python help:')) \
            .arg(translate("ShellBaseWidget", 'GUI-based editor:')) )
                
                
    #------ External editing
    def external_editor(self, filename, goto=None):
        """Edit in an external editor
        Recommended: SciTE (e.g. to go to line where an error did occur)"""
        editor_path = CONF.get('shell', 'external_editor')
        goto_option = CONF.get('shell', 'external_editor/gotoline')
        try:
            if (goto is not None) and goto_option:
                Popen(r'%s "%s" %s%d' % (editor_path, filename,
                                         goto_option, goto))
            else:
                Popen(r'%s "%s"' % (editor_path, filename))
        except OSError:
            self.write_error("External editor was not found:"
                             " %s\n" % editor_path)


    #------ I/O
    def raw_input(self, prompt):
        """Reimplementation of raw_input builtin"""
        self.write(prompt, flush=True)
        old_prompt = self.prompt
        self.prompt = prompt
        inp = self.wait_input()
        self.prompt = old_prompt
        return inp

    def flush(self, error=False):
        """Reimplement QsciTerminal method"""
        QsciTerminal.flush(self, error)
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt


    #------ Copy/paste
    def copy(self):
        """Copy text to clipboard... or keyboard interrupt"""
        if self.hasSelectedText():
            QsciScintilla.copy(self)
        else:
            self.keyboard_interrupt()
            
    def __remove_prompts(self, text):
        """Remove prompts from text"""
        return text[len(self.prompt):]
    
    def __extract_from_text(self, line_nb):
        """Extract clean text from line number 'line_nb'"""
        return self.__remove_prompts( unicode(self.text(line_nb)) )
                
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


    #------ Mouse events
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

    def mouseMoveEvent(self, event):
        """Show Pointing Hand Cursor on error messages"""
        if event.modifiers() & Qt.ControlModifier:
            text = unicode(self.text(self.lineAt(event.pos())))
            if self.parent().get_error_match(text):
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                return
        QApplication.restoreOverrideCursor()
        QsciScintilla.mouseMoveEvent(self, event)
            

    #------ Keyboard events
    def get_input_buffer(self):
        """Enter or Return -> get_input_buffer"""
        line, col = self.get_end_pos()
        self.setCursorPosition(line, col)
        buf = self.__extract_from_text(line)
        self.insert_text('\n', at_end=True)
        return buf
    
    def __delete_selected_text(self):
        """
        Private method to delete selected text
        without deleting prompts
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
            if line != last_line:
                # Moving cursor to the end of the last line
                self.move_cursor_to_end()
            elif index < len(self.prompt):
                # Moving cursor after prompt
                self.setCursorPosition(line, len(self.prompt))
            
        if key == Qt.Key_Backspace:
            if self.hasSelectedText():
                self.__delete_selected_text()
            elif self.is_cursor_on_last_line():
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
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_CLEAR)
            
        elif shift and (key == Qt.Key_Return or key == Qt.Key_Enter):
            # Multiline entry
            self.histidx = None
            self.append_command(self.get_input_buffer())
            
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            if self.is_cursor_on_last_line():
                if self.isListActive():
                    self.SendScintilla(QsciScintilla.SCI_NEWLINE)
                else:
                    self.histidx = None
                    buf = self.get_input_buffer()
                    self.busy = True
                    if self.profile:
                        # Simple profiling test
                        t0 = time()
                        for _ in range(10):
                            self.execute_command(buf)
                        self.insert_text(u"\n<Δt>=%dms\n" % (1e2*(time()-t0)))
                        self.insert_text(self.prompt)
                    else:
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
            elif self.is_cursor_on_last_line():
                buf = self.__extract_from_text(line)
                lastchar_index = index-len(self.prompt)-1
                if self.more and not buf[:index-len(self.prompt)].strip():
                    self.SendScintilla(QsciScintilla.SCI_TAB)
                elif lastchar_index >= 0:
                    text = self.__get_last_obj()
                    if buf[lastchar_index] == '.':
                        self.show_code_completion(text)
                    elif buf[lastchar_index] in ['"', "'"]:
                        self.show_file_completion()
            
        elif key == Qt.Key_Left:
            if line == last_line and (index == len(self.prompt)):
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
                line, col = self.getCursorPosition()
                if self.text(line).startsWith(self.prompt):
                    col = len(self.prompt)
                else:
                    col = 0
                self.setCursorPosition(line, col)

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
                self.__browse_history(backward=True)
                
        elif key == Qt.Key_Down:
            if line != last_line:
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
            _, self.calltip_index = self.getCursorPosition()
            self.insert_text(text)
            # In case calltip and completion are shown at the same time:
            if self.isListActive():
                self.completion_chars += 1
            
        elif key == Qt.Key_ParenLeft:
            self.cancelList()
            self.show_docstring(self.__get_last_obj(), call=True)
            _, self.calltip_index = self.getCursorPosition()
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

        
        if QToolTip.isVisible():
            # Hide calltip when necessary (this is handled here because
            # QScintilla does not support user-defined calltips)
            _, index = self.getCursorPosition() # need the new index
            try:
                if (self.text(line)[self.calltip_index] not in ['?','(']) or \
                   index < self.calltip_index or \
                   key in (Qt.Key_ParenRight, Qt.Key_Period, Qt.Key_Tab):
                    QToolTip.hideText()
            except IndexError:
                QToolTip.hideText()
            
            
    #------ Command execution
    def keyboard_interrupt(self):
        """Simulate keyboard interrupt"""
        if self.busy:
            # Interrupt only if console is busy
            self.interrupted = True
        elif self.more:
            self.write("\nKeyboardInterrupt\n", flush=True)
            self.more = False
            self.prompt = self.p1
            self.write(self.prompt, flush=True)
            self.interpreter.resetbuffer()
        
    def append_command(self, cmd):
        """Multiline command"""
        self.write(self.p2, flush=True)
        if len(cmd)>0:
            self.multiline_entry.append(cmd)

    def execute_command(self, cmd):
        """
        Execute a command.
        cmd: one-line command only, without '\n' at the end!
        """            
        if self.input_mode:
            self.end_input(cmd)
            return
        # cls command
        if cmd == 'cls':
            self.clear_terminal()
            return
        
        # Multiline entry support: very limited feature...
        # (bug after exiting an indented block, e.g. a for loop)
        if self.multiline_entry:
            self.multiline_entry.append(cmd)
            cmdlist = self.multiline_entry
        else:
            cmdlist = [cmd]
                
        for index, cmd in enumerate(cmdlist):
            self.run_command(cmd, multiline=(index!=len(cmdlist)-1))
        
        self.multiline_entry = []
        
    def execute_lines(self, lines):
        """
        Private method to execute a set of lines as multiple commands
        lines: multiple lines of text to be executed as single
            commands (string)
        """
        if isinstance(lines, list):
            lines = "\n".join(lines)
        for line in lines.splitlines(True):
            if line.endswith("\r\n"):
                fullline = True
                cmd = line[:-2]
            elif line.endswith("\r") or line.endswith("\n"):
                fullline = True
                cmd = line[:-1]
            else:
                fullline = False
            
            self.insert_text(line, at_end=True)
            if fullline:
                self.execute_command(cmd)
        
    def run_command(self, cmd, history=True, multiline=False):
        """Run command in interpreter"""
        
        # Before running command
        self.emit(SIGNAL("status(QString)"), self.tr('Busy...'))
        self.emit( SIGNAL("executing_command(bool)"), True )
        
        if not cmd:
            cmd = ''
        else:
            if history:
                self.interpreter.add_to_history(cmd)
            self.histidx = None

        #FIXME: use regexp instead of startswith for special commands detection
        #       --> will allow user to use "edit" or "run" as object name

        # -- Special commands type I
        #    (transformed into commands executed in the interpreter)
        # ? command
        if cmd.endswith('?'):
            cmd = 'help(%s)' % cmd[:-1]
        # run command
        elif cmd.startswith('run '):
            filename = guess_filename(cmd[4:])
            cmd = 'execfile(r"%s")' % filename
        # -- End of Special commands type I
            
        # -- Special commands type II
        #    (don't need code execution in interpreter)
        # (external) edit command
        if cmd.startswith('xedit '):
            filename = guess_filename(cmd[6:])
            self.external_editor(filename)
        # local edit command
        elif cmd.startswith('edit '):
            filename = guess_filename(cmd[5:])
            if osp.isfile(filename):
                self.parent().edit_script(filename)
            else:
                self.write_error("No such file or directory: %s\n" % filename)
        # remove reference (equivalent to MATLAB's clear command)
        elif cmd.startswith('clear '):
            varnames = cmd[6:].replace(' ', '').split(',')
            for varname in varnames:
                try:
                    self.interpreter.locals.pop(varname)
                except KeyError:
                    pass
        # Execute command
        elif cmd.startswith('!'):
            # System ! command
            pipe = Popen(cmd[1:], shell=True,
                         stdin=PIPE, stderr=PIPE, stdout=PIPE)
            txt_out = transcode( pipe.stdout.read() )
            txt_err = transcode( pipe.stderr.read().rstrip() )
            if txt_err:
                self.write_error(txt_err)
            if txt_out:
                self.write(txt_out)
            self.write('\n')
            self.more = False
        # -- End of Special commands type II
        else:
            # Command executed in the interpreter
            self.more = self.interpreter.push(cmd)
        
        self.emit(SIGNAL("refresh()"))
        self.prompt = self.p2 if self.more else self.p1
        if not multiline:
            self.write(self.prompt, flush=True)
        if not self.more:
            self.interpreter.resetbuffer()
            
        # After running command
        self.emit(SIGNAL("executing_command(bool)"), False)
        self.emit(SIGNAL("status(QString)"), QString())
    
    
    #------ Code completion / Calltips
    def show_code_completion(self, text):
        """
        Display a completion list based on the last token
        """
        obj, valid = self.interpreter.eval(text)
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
        obj, valid = self.interpreter.eval(text)
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

