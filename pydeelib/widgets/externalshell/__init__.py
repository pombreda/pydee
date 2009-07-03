# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""External Shell widget: execute Python script in a separate process"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os, pickle
import os.path as osp
from time import time, strftime, gmtime

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                         QMessageBox, QLabel, QInputDialog, QLineEdit,
                         QCheckBox, QSplitter)
from PyQt4.QtCore import QProcess, SIGNAL, QByteArray, QString, QTimer, Qt

# Local imports
from pydeelib.encoding import transcode
from pydeelib.qthelpers import create_toolbutton, translate
from pydeelib.config import get_icon, get_conf_path, CONF, get_font
from pydeelib.widgets.qscishell import QsciShell
from pydeelib.widgets.dicteditor import RemoteDictEditorTableView
from pydeelib.widgets.externalshell import startup
from pydeelib.widgets.externalshell.globalsexplorer import GlobalsExplorer
from pydeelib.widgets.externalshell.monitor import (communicate,
                                                    monitor_set_value,
                                                    monitor_get_value)


class ExternalShellBase(QsciShell):
    def __init__(self, parent, history_filename, max_history_entries=100,
                 debug=False, profile=False, externalshell=None):
        QsciShell.__init__(self, parent, history_filename,
                           max_history_entries, debug, profile)
        # ExternalShell instance:
        self.externalshell = externalshell
        
    #------ Code completion / Calltips
    def ask_monitor(self, command):
        sock = self.externalshell.monitor_socket
        if sock is None:
            return
        return communicate(sock, command, pickle_try=True)
            
    def get_dir(self, objtxt):
        """Return dir(object)"""
        return self.ask_monitor("dir(%s)" % objtxt)
            
    def iscallable(self, objtxt):
        """Is object callable?"""
        return self.ask_monitor("callable(%s)" % objtxt)
    
    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        return self.ask_monitor("getargtxt(%s)" % objtxt)
            
    def get_doc(self, objtxt):
        """Get object documentation"""
        return self.ask_monitor("%s.__doc__" % objtxt)


#TODO: [low-priority] Split ExternalShell into three classes:
#        1. shell base class
#        2. python shell class (inherits base class)
#        3. terminal shell class (inherits base class)
class ExternalShell(QWidget):
    """External Shell widget: execute Python script in a separate process"""
    def __init__(self, parent=None, fname=None, wdir=None, commands=[],
                 interact=False, debug=False, python=True, path=[]):
        QWidget.__init__(self, parent)
        self.python = python
        self.monitor_socket = None
        self.interpreter = fname is None
        self.fname = startup.__file__ if fname is None else fname
        if wdir is None:
            wdir = osp.dirname(osp.abspath(self.fname))
        self.wdir = wdir if osp.isdir(wdir) else None
        self.commands = ["import sys", "sys.path[0] = ''"] + commands
        self.arguments = ""
        
        # Additional python path list
        self.path = path
        
        history_filename = '.history_extcons'
        if python:
            history_filename += '.py'
        self.shell = ExternalShellBase(parent, get_conf_path(history_filename),
                                       externalshell=self)
        self.connect(self.shell, SIGNAL("execute(QString)"),
                     self.send_to_process)
        self.connect(self.shell, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        
        self.state_label = QLabel()
        self.time_label = QLabel()
        
        self.globalsexplorer_button = create_toolbutton(self,
                          get_icon('dictedit.png'), self.tr("Variables"),
                          tip=self.tr("Show/hide global variables explorer"),
                          toggled=self.toggle_globals_explorer)
        self.run_button = create_toolbutton(self, get_icon('execute.png'),
                              self.tr("Run"),
                              tip=self.tr("Run again this program"),
                              triggered=self.start)
        self.terminate_button = create_toolbutton(self,
              get_icon('terminate.png'), self.tr("Terminate"),
              tip=self.tr("Attempts to terminate the process.\n"
                          "The process may not exit as a result of clicking "
                          "this button\n(it is given the chance to prompt "
                          "the user for any unsaved files, etc)."))
        self.kill_button = create_toolbutton(self, get_icon('kill.png'),
                              self.tr("Kill"),
                              tip=self.tr("Kills the current process, "
                                          "causing it to exit immediately"))
        
        self.interact_check = QCheckBox(self.tr("Interact"), self)
        self.interact_check.setChecked(interact)
        self.debug_check = QCheckBox(self.tr("Debug"), self)
        self.debug_check.setChecked(debug)
        
        #TODO: Code cleaning
        # The following lines are ugly, aren't they? -> do something about it!!
        if self.interpreter or not self.python:
            self.interact_check.hide()
            self.debug_check.hide()
            self.terminate_button.hide()
        if not self.python:
            self.globalsexplorer_button.hide()
        
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.state_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.time_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.interact_check)
        hlayout.addWidget(self.debug_check)
        hlayout.addWidget(self.globalsexplorer_button)
        hlayout.addWidget(self.run_button)
        hlayout.addWidget(self.terminate_button)
        hlayout.addWidget(self.kill_button)
        
        # Namespace explorer
        self.globalsexplorer = GlobalsExplorer(self)
        self.connect(self.globalsexplorer, SIGNAL('refresh()'),
                     self.refresh_globals_explorer)
        self.connect(self.globalsexplorer, SIGNAL('collapse()'),
                     lambda: self.toggle_globals_explorer(False))
        
        self.splitter = splitter = QSplitter(Qt.Vertical, self)
        self.connect(self.splitter, SIGNAL('splitterMoved(int, int)'),
                     self.splitter_moved)
        splitter.addWidget(self.shell)
        splitter.setCollapsible(0, False)
        splitter.addWidget(self.globalsexplorer)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        self.toggle_globals_explorer(False)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(splitter)
        self.setLayout(vlayout)
        self.resize(640, 480)
        if parent is None:
            if self.python:
                self.setWindowIcon(get_icon('python.png'))
            else:
                self.setWindowIcon(get_icon('cmdprompt.png'))
            self.setWindowTitle(self.tr("Console"))

        self.t0 = None
        self.timer = QTimer(self)

        self.process = None
        
    def show_time(self, end=False):
        elapsed_time = time()-self.t0
        if elapsed_time > 24*3600: # More than a day...!
            format = "%d %H:%M:%S"
        else:
            format = "%H:%M:%S"
        if end:
            color = "#AAAAAA"
        else:
            color = "#AA6655"
        text = "<span style=\'color: %s\'><b>%s" \
               "</b></span>" % (color, strftime(format, gmtime(elapsed_time)))
        self.time_label.setText(text)
        
    def closeEvent(self, event):
        if self.process is not None:
            self.process.kill()
        self.disconnect(self.timer, SIGNAL("timeout()"), self.show_time)
    
    def set_running_state(self, state=True):
        self.run_button.setEnabled(not state)
        self.interact_check.setEnabled(not state)
        self.debug_check.setEnabled(not state)
        self.terminate_button.setEnabled(state)
        self.kill_button.setEnabled(state)
        self.shell.setReadOnly(not state)
        if state:
            self.state_label.setText(self.tr("<span style=\'color: #44AA44\'>"
                                             "<b>Running...</b></span>"))
            self.t0 = time()
            self.connect(self.timer, SIGNAL("timeout()"), self.show_time)
            self.timer.start(1000)        
        else:
            self.state_label.setText(self.tr('Terminated.'))
            self.disconnect(self.timer, SIGNAL("timeout()"), self.show_time)
    
    def start(self, ask_for_arguments=False):
        """Start shell"""
        if ask_for_arguments and not self.get_arguments():
            self.set_running_state(False)
            return
        self.create_process()

    def get_arguments(self):
        arguments, valid = QInputDialog.getText(self, self.tr('Arguments'),
                          self.tr('Command line arguments:'),
                          QLineEdit.Normal, self.arguments)
        if valid:
            self.arguments = unicode(arguments)
        return valid
    
    def create_process(self):
        self.shell.clear()
            
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        
        # Working directory
        if self.wdir is not None:
            self.process.setWorkingDirectory(self.wdir)
            
        if self.python:
            # Python arguments
            p_args = ['-u']
            if self.interact_check.isChecked():
                p_args.append('-i')
            if self.debug_check.isChecked():
                p_args.extend(['-m', 'pdb'])
            p_args.append(self.fname)
            
            env = self.process.systemEnvironment()
            
            # Monitor
            env.append('SHELL_ID=%s' % id(self))
            from pydeelib.widgets.externalshell.monitor import start_server
            server, port = start_server()
            self.notification_thread = server.register(str(id(self)), self)
            self.connect(self.notification_thread, SIGNAL('refresh()'),
                         self.refresh_globals_explorer)
            env.append('PYDEE_PORT=%d' % port)
            
            # Python init commands (interpreter only)
            if self.commands and self.interpreter:
                env.append('PYTHONINITCOMMANDS=%s' % ';'.join(self.commands))
                self.process.setEnvironment(env)
                
            pathlist = []

            # Fix encoding with custom "sitecustomize.py"
            scpath = osp.dirname(osp.abspath(__file__))
            pathlist.append(scpath)
            
            # Adding Pydee path
            pathlist += self.path
            
            # Adding path list to PYTHONPATH environment variable
            pypath = "PYTHONPATH"
            pathstr = os.pathsep.join(pathlist)
            if os.environ.get(pypath) is not None:
                env.replaceInStrings(pypath+'=', pypath+'='+pathstr+os.pathsep,
                                     Qt.CaseSensitive)
            else:
                env.append(pypath+'='+pathstr)
            self.process.setEnvironment(env)
        else:
            # Shell arguments
            if os.name == 'nt':
                p_args = ['/Q']
            else:
                p_args = ['-i']
            
        if self.arguments:
            p_args.extend( self.arguments.split(' ') )
                        
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.write_output)
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
        
        self.connect(self.terminate_button, SIGNAL("clicked()"),
                     self.process.terminate)
        self.connect(self.kill_button, SIGNAL("clicked()"),
                     self.process.kill)
        
        if self.python:
            self.process.start(sys.executable, p_args)
        else:
            if os.name == 'nt':
                self.process.start('cmd.exe', p_args)
            else:
                shell = os.environ.get('SHELL')
                if shell is None:
                    QMessageBox.critical(self, self.tr("Error"),
                                         self.tr("No shell has been "
                                                 "configured"))
                    self.set_running_state(False)
                    return
                else:
                    self.process.start(shell, p_args)
            
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Process failed to start"))
        else:
            self.shell.setFocus()
            self.emit(SIGNAL('started()'))
            
        return self.process
    
    def finished(self, exit_code, exit_status):
        self.set_running_state(False)
        self.show_time(end=True)
        self.emit(SIGNAL('finished()'))
        # Saving console history:
        self.shell.save_history()
    
#===============================================================================
#    Input/Output
#===============================================================================
    def transcode(self, bytes):
        if self.python or os.name != 'nt':
            text = unicode( QString.fromLocal8Bit(bytes.data()) )
        else:
            text = transcode(str(bytes.data()), 'cp850')
        return text
    
    def get_stdout(self):
        self.process.setReadChannel(QProcess.StandardOutput)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardOutput()
        return self.transcode(bytes)
    
    def get_stderr(self):
        self.process.setReadChannel(QProcess.StandardError)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardError()
        return self.transcode(bytes)
    
    def _write_error(self, text, findstr):
        pos = text.find(findstr)
        if pos != -1:
            self.shell.write(text[:pos])
            if text.endswith(">>> "):
                self.shell.write_error(text[pos:-5])
                self.shell.write(text[-5:], flush=True)
            else:
                self.shell.write_error(text[pos:])
            return True
        return False
    
    def write_output(self):
        text = self.get_stdout()
        if not self._write_error(text, 'Traceback (most recent call last):') \
           and not self._write_error(text, 'File "<stdin>", line 1'):
            self.shell.write(text)
        QApplication.processEvents()
        
    def send_to_process(self, qstr):
        if not isinstance(qstr, QString):
            qstr = QString(qstr)
        if not self.python and qstr[:-1] in ["clear", "cls", "CLS"]:
            self.shell.clear()
            self.send_to_process(QString(os.linesep))
            return
        if not qstr.endsWith('\n'):
            qstr.append('\n')
        if self.python or os.name != 'nt':
            self.process.write(qstr.toLocal8Bit())
        else:
            self.process.write(unicode(qstr).encode('cp850'))
        self.process.waitForBytesWritten(-1)
        
    def send_ctrl_to_process(self, letter):
        char = chr("abcdefghijklmnopqrstuvwxyz".index(letter) + 1)
        byte_array = QByteArray()
        byte_array.append(char)
        self.process.write(byte_array)
        self.process.waitForBytesWritten(-1)
        self.shell.write(QString(byte_array))
        
    def keyboard_interrupt(self):
        if self.python:
            communicate(self.monitor_socket, "thread.interrupt_main()")
        else:
            # This does not work on Windows:
            # (unfortunately there is no easy way to send a Ctrl+C to cmd.exe)
            self.send_ctrl_to_process('c')

#            # The following code will soon be removed:
#            # (last attempt to send a Ctrl+C on Windows)
#            if os.name == 'nt':
#                pid = int(self.process.pid())
#                import ctypes, win32api, win32con
#                class _PROCESS_INFORMATION(ctypes.Structure):
#                    _fields_ = [("hProcess", ctypes.c_int),
#                                ("hThread", ctypes.c_int),
#                                ("dwProcessID", ctypes.c_int),
#                                ("dwThreadID", ctypes.c_int)]
#                x = ctypes.cast( ctypes.c_void_p(pid),
#                                 ctypes.POINTER(_PROCESS_INFORMATION) )
#                win32api.GenerateConsoleCtrlEvent(win32con.CTRL_C_EVENT,
#                                                  x.dwProcessID)
#            else:
#                self.send_ctrl_to_process('c')
            
#===============================================================================
#    Globals explorer
#===============================================================================
    def refresh_globals_explorer(self):
        if self.monitor_socket is None:
            return
        data = communicate(self.monitor_socket, "glexp_make(globals())")
        obj = pickle.loads(data)
        self.globalsexplorer.set_data(obj)
        
    def toggle_globals_explorer(self, state):
        self.splitter.setSizes([1, 1 if state else 0])
        self.globalsexplorer_button.setChecked(state)
        if state:
            self.refresh_globals_explorer()
        
    def splitter_moved(self, pos, index):
        self.globalsexplorer_button.setChecked( self.splitter.sizes()[1] )
    

def test():
    app = QApplication(sys.argv)
    import pydeelib
    shell = ExternalShell(wdir=osp.dirname(pydeelib.__file__), interact=True)
#    shell = ExternalShell(wdir=osp.dirname(pydeelib.__file__), python=False)
    shell.shell.set_wrap_mode(True)
    shell.start(False)
    from PyQt4.QtGui import QFont
    font = QFont("Lucida console")
    font.setPointSize(10)
    shell.shell.set_font(font)
    shell.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    test()