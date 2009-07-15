# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""External Python Shell widget: execute Python script in a separate process"""

import sys, os
import os.path as osp

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import QApplication, QMessageBox, QCheckBox, QSplitter
from PyQt4.QtCore import QProcess, SIGNAL, QString, Qt

# Local imports
from pydeelib.qthelpers import create_toolbutton
from pydeelib.config import get_icon
from pydeelib.widgets.externalshell import startup
from pydeelib.widgets.externalshell.globalsexplorer import GlobalsExplorer
from pydeelib.widgets.externalshell.monitor import communicate
from pydeelib.widgets.externalshell import ExternalShellBase


class ExternalPythonShell(ExternalShellBase):
    """External Shell widget: execute Python script in a separate process"""
    def __init__(self, parent=None, fname=None, wdir=None, commands=[],
                 interact=False, debug=False, path=[]):
        ExternalShellBase.__init__(self, parent, wdir,
                                   history_filename = '.history_extcons.py')

        self.toggle_globals_explorer(False)
        self.interact_check.setChecked(interact)
        self.debug_check.setChecked(debug)
        
        self.monitor_socket = None
        self.interpreter = fname is None
        self.fname = startup.__file__ if fname is None else fname
        
        if self.interpreter:
            self.interact_check.hide()
            self.debug_check.hide()
            self.terminate_button.hide()
        
        self.commands = ["import sys", "sys.path.insert(0, '')"] + commands
        
        # Additional python path list
        self.path = path
        
    def get_toolbar_buttons(self):
        ExternalShellBase.get_toolbar_buttons(self)
        self.globalsexplorer_button = create_toolbutton(self,
                          get_icon('dictedit.png'), self.tr("Variables"),
                          tip=self.tr("Show/hide global variables explorer"),
                          toggled=self.toggle_globals_explorer)
        self.terminate_button = create_toolbutton(self,
              get_icon('terminate.png'), self.tr("Terminate"),
              tip=self.tr("Attempts to terminate the process.\n"
                          "The process may not exit as a result of clicking "
                          "this button\n(it is given the chance to prompt "
                          "the user for any unsaved files, etc)."))        
        self.interact_check = QCheckBox(self.tr("Interact"), self)
        self.debug_check = QCheckBox(self.tr("Debug"), self)
        return [self.interact_check, self.debug_check,
                self.globalsexplorer_button, self.run_button,
                self.terminate_button, self.kill_button]
        
    def get_shell_widget(self):
        # Globals explorer
        self.globalsexplorer = GlobalsExplorer(self)
        self.connect(self.globalsexplorer, SIGNAL('collapse()'),
                     lambda: self.toggle_globals_explorer(False))
        
        # Shell splitter
        self.splitter = splitter = QSplitter(Qt.Vertical, self)
        self.connect(self.splitter, SIGNAL('splitterMoved(int, int)'),
                     self.splitter_moved)
        splitter.addWidget(self.shell)
        splitter.setCollapsible(0, False)
        splitter.addWidget(self.globalsexplorer)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        return splitter
    
    def get_icon(self):
        return get_icon('python.png')

    def set_buttons_runnning_state(self, state):
        ExternalShellBase.set_buttons_runnning_state(self, state)
        self.interact_check.setEnabled(not state)
        self.debug_check.setEnabled(not state)
        self.terminate_button.setEnabled(state)
        if not state:
            self.toggle_globals_explorer(False)
        self.globalsexplorer_button.setEnabled(state)
    
    def create_process(self):
        self.shell.clear()
            
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        
        # Working directory
        if self.wdir is not None:
            self.process.setWorkingDirectory(self.wdir)

        #-------------------------Python specific-------------------------------
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
                     self.globalsexplorer.refresh_table)
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
        #-------------------------Python specific-------------------------------
            
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
        
        #-------------------------Python specific-------------------------------
        self.process.start(sys.executable, p_args)
        #-------------------------Python specific-------------------------------
            
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Process failed to start"))
        else:
            self.shell.setFocus()
            self.emit(SIGNAL('started()'))
            
        return self.process
    
#===============================================================================
#    Input/Output
#===============================================================================
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
        if not qstr.endsWith('\n'):
            qstr.append('\n')
        self.process.write(qstr.toLocal8Bit())
        self.process.waitForBytesWritten(-1)
        
    def keyboard_interrupt(self):
        communicate(self.monitor_socket, "thread.interrupt_main()")
            
#===============================================================================
#    Globals explorer
#===============================================================================
    def toggle_globals_explorer(self, state):
        self.splitter.setSizes([1, 1 if state else 0])
        self.globalsexplorer_button.setChecked(state)
        if state:
            self.globalsexplorer.refresh_table()
        
    def splitter_moved(self, pos, index):
        self.globalsexplorer_button.setChecked( self.splitter.sizes()[1] )
