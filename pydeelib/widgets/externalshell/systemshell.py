# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""External System Shell widget: execute terminal in a separate process"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import QMessageBox
from PyQt4.QtCore import QProcess, SIGNAL, QString

# Local imports
from pydeelib.encoding import transcode
from pydeelib.config import get_icon
from pydeelib.widgets.externalshell import ExternalShellBase


class ExternalSystemShell(ExternalShellBase):
    """External Shell widget: execute Python script in a separate process"""
    def __init__(self, parent=None, wdir=None):
        ExternalShellBase.__init__(self, parent, wdir,
                                   history_filename='.history_extcons')

    def get_icon(self):
        return get_icon('cmdprompt.png')
    
    def create_process(self):
        self.shell.clear()
            
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        
        # Working directory
        if self.wdir is not None:
            self.process.setWorkingDirectory(self.wdir)
            
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
        
        self.connect(self.kill_button, SIGNAL("clicked()"),
                     self.process.kill)
        
        if os.name == 'nt':
            self.process.start('cmd.exe', p_args)
        else:
            shell = os.environ.get('SHELL')
            if shell is None:
                QMessageBox.critical(self, self.tr("Error"),
                                     self.tr("No shell has been configured"))
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
    
#===============================================================================
#    Input/Output
#===============================================================================
    def transcode(self, bytes):
        if os.name == 'nt':
            return transcode(str(bytes.data()), 'cp850')
        else:
            return ExternalShellBase.transcode(self, bytes)
    
    def send_to_process(self, qstr):
        if not isinstance(qstr, QString):
            qstr = QString(qstr)
        if qstr[:-1] in ["clear", "cls", "CLS"]:
            self.shell.clear()
            self.send_to_process(QString(os.linesep))
            return
        if not qstr.endsWith('\n'):
            qstr.append('\n')
        if os.name == 'nt':
            self.process.write(unicode(qstr).encode('cp850'))
        else:
            self.process.write(qstr.toLocal8Bit())
        self.process.waitForBytesWritten(-1)
        
    def keyboard_interrupt(self):
        # This does not work on Windows:
        # (unfortunately there is no easy way to send a Ctrl+C to cmd.exe)
        self.send_ctrl_to_process('c')

#        # The following code will soon be removed:
#        # (last attempt to send a Ctrl+C on Windows)
#        if os.name == 'nt':
#            pid = int(self.process.pid())
#            import ctypes, win32api, win32con
#            class _PROCESS_INFORMATION(ctypes.Structure):
#                _fields_ = [("hProcess", ctypes.c_int),
#                            ("hThread", ctypes.c_int),
#                            ("dwProcessID", ctypes.c_int),
#                            ("dwThreadID", ctypes.c_int)]
#            x = ctypes.cast( ctypes.c_void_p(pid),
#                             ctypes.POINTER(_PROCESS_INFORMATION) )
#            win32api.GenerateConsoleCtrlEvent(win32con.CTRL_C_EVENT,
#                                              x.dwProcessID)
#        else:
#            self.send_ctrl_to_process('c')
                