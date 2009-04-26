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

"""Shell base widget: link between Terminal and Interpreter"""

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
from subprocess import Popen, PIPE
from time import time
import os.path as osp

STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import QMenu, QMessageBox, QKeySequence, QToolTip
from PyQt4.QtCore import SIGNAL, QString, QEventLoop, QCoreApplication

# Local import
from PyQtShell.qthelpers import (translate, keybinding, create_action,
                                 get_std_icon, add_actions)
from PyQtShell.interpreter import Interpreter
from PyQtShell.dochelpers import getargtxt
from PyQtShell.encoding import transcode
from PyQtShell.config import CONF, get_icon, get_font
try:
    from PyQtShell.widgets.qscibase import QsciTerminal as Terminal
except ImportError:
    print >> STDERR, "Warning: future versions of PyQtShell" + \
        " will be exclusively based on QScintilla2\n" + \
        "(http://www.riverbankcomputing.co.uk/software/qscintilla)"
    from PyQtShell.widgets.qtbase import QtTerminal as Terminal


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


class IOHandler(object):
    """Handle stream output"""
    def __init__(self, write):
        self._write = write
    def write(self, cmd):
        self._write(cmd)
    def flush(self):
        pass

class ShellBaseWidget(Terminal):
    """Shell base widget: link between Terminal and Interpreter"""
    try:
        p1 = sys.p1
    except AttributeError:
        p1 = ">>> "
    try:
        p2 = sys.p2
    except AttributeError:
        p2 = "... "
    def __init__(self, parent=None, namespace=None, commands=None, message="",
                 debug=False, exitfunc=None):
        self.__buffer = []
        self.__timestamp = 0.0
        Terminal.__init__(self, parent)
        
        # Context menu
        self.menu = None
        self.setup_context_menu()
        
        # raw_input support
        self.input_loop = None
        self.input_mode = False
        
        # KeyboardInterrupt support
        self.interrupted = False
        
        # Init interpreter
        #TODO: multithreaded Interpreter (if option.thread)
        self.interpreter = Interpreter(namespace, exitfunc, self.raw_input)
        
        # Multiline entry
        self.multiline_entry = []
        
        # Execution Status
        self.more = False
        
        # capture all interactive input/output 
        self.debug = debug
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        self.stdout = self
        self.stderr = IOHandler(self.write_error)
        self.stdin = self
        self.redirect_stds()

        # interpreter banner
        banner = create_banner(self.tr('Type "copyright", "credits" or "license" for more information.'), message)
        self.setUndoRedoEnabled(False) #-disable undo/redo for a time being
        self.write(banner, flush=True)

        # Initial commands
        for cmd in commands:
            self.run_command(cmd, history=False, multiline=True)
                
        # First prompt
        self.prompt = self.p1
        self.write(self.prompt, flush=True)
        self.setUndoRedoEnabled(True) #-enable undo/redo
        self.emit(SIGNAL("refresh()"))
  
    def setup_context_menu(self):
        """Setup shell context menu"""
        # Create a little context menu        
        self.menu = QMenu(self)
        self.cut_action = create_action(self,
                           translate("ShellBaseWidget", "Cut"),
                           shortcut=keybinding('Cut'),
                           icon=get_icon('cut.png'), triggered=self.cut)
        self.copy_action = create_action(self,
                           translate("ShellBaseWidget", "Copy"),
                           shortcut=keybinding('Copy'),
                           icon=get_icon('copy.png'), triggered=self.copy)
        paste_action = create_action(self,
                           translate("ShellBaseWidget", "Paste"),
                           shortcut=keybinding('Paste'),
                           icon=get_icon('paste.png'), triggered=self.paste)
        clear_line_action = create_action(self,
                           self.tr("Clear line"),
                           QKeySequence("Escape"),
                           tip=translate("ShellBaseWidget", "Clear line"),
                           triggered=self.clear_line)
        clear_action = create_action(self,
                           translate("ShellBaseWidget", "Clear shell"),
                           icon=get_std_icon("TrashIcon"),
                           tip=translate("ShellBaseWidget",
                                   "Clear shell contents ('cls' command)"),
                           triggered=self.clear_terminal)
        self.help_action = create_action(self,
                           translate("ShellBaseWidget", "Help..."),
                           shortcut="F1",
                           icon=get_std_icon('DialogHelpButton'),
                           triggered=self.help)
        add_actions(self.menu, (self.cut_action, self.copy_action, paste_action,
                                clear_line_action,
                                None, clear_action, None, self.help_action) )

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
          
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        state = self.hasSelectedText()
        self.copy_action.setEnabled(state)
        self.cut_action.setEnabled(state)
        self.menu.popup(event.globalPos())
        event.accept()

    def redirect_stds(self):
        """Redirects stds"""
        if not self.debug:
            sys.stdout = self.stdout
            sys.stderr = self.stderr
            sys.stdin  = self.stdin
        
    def restore_stds(self):
        """Restore stds"""
        if not self.debug:
            sys.stdout = self.initial_stdout
            sys.stderr = self.initial_stderr
            sys.stdin = self.initial_stdin

    def raw_input(self, prompt):
        """Reimplementation of raw_input builtin"""
        self.write(prompt, flush=True)
        old_prompt = self.prompt
        self.prompt = prompt
        inp = self.wait_input()
        self.prompt = old_prompt
        return inp
    
    def readline(self):
        """For help() support (to be implemented...)"""
        #TODO: help() support
        inp = self.wait_input()
        return inp
        
    def wait_input(self):
        """Wait for input (raw_input)"""
        self.input_data = None # If shell is closed, None will be returned
        self.input_mode = True
        self.input_loop = QEventLoop()
        self.input_loop.exec_()
        self.input_loop = None
        return self.input_data
    
    def end_input(self, cmd):
        """End of wait_input mode"""
        self.input_data = cmd
        self.input_mode = False
        self.input_loop.exit()

    def write_error(self, text):
        """Simulate stderr"""
#        self.flush()
        self.write(text, flush=True, error=True)
        STDERR.write(text)

    def write(self, text, flush=False, error=False):
        """Simulate stdout and stderr"""
        if isinstance(text, QString):
            # This test is useful to discriminate QStrings from decoded str
            text = unicode(text)
        self.__buffer.append(text)
        ts = time()
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
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt
        
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
        self.emit( SIGNAL("executing_command(bool)"), False )
        self.emit(SIGNAL("status(QString)"), QString())
    
    def show_code_completion(self, text):
        """
        Display a completion list based on the last token
        """
        try:
            obj = eval(text, self.interpreter.locals)
        except:
            # No valid object was extracted from text
            pass
        else:
            # Object obj is valid
            self.show_list(dir(obj), 'dir(%s)' % text) 

    def show_file_completion(self):
        """
        Display a completion list for files and directories
        """
        cwd = os.getcwdu()
        self.show_list(os.listdir(cwd), cwd)

    def show_list(self, completions, text):
        """
        Private method to display the possible completions.
        """
        if len(completions) == 0:
            return
        if len(completions) > 1:
            self.show_completion_widget( sorted(completions), text )
            self.completion_chars = 1
        else:
            txt = completions[0]
            if text != "":
                txt = txt.replace(text, "")
            self.insert_text(txt)
            self.completion_chars = 0
        
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
        QToolTip.showText(self.get_cursor_qpoint(), text)
        
    def show_docstring(self, text, call=False):
        """Show docstring or arguments"""
        try:
            obj = eval(text, self.interpreter.locals)
        except:
            # No valid object was extracted from text
            pass
        else:
            # Object obj is valid
            done = False
            if (self.docviewer is not None) and \
               (self.docviewer.dockwidget.isVisible()):
                # DocViewer widget exists and is visible
                self.docviewer.refresh(text)
                if call:
                    # Display argument list if this is function call
                    arglist = getargtxt(obj)
                    if arglist:
                        self.show_calltip(arglist)
                        done = True
            if not done:
                self.show_calltip(obj.__doc__)
                