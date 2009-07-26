# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""External Shell widget: execute Python script/terminal in a separate process"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys
import os.path as osp
from time import time, strftime, gmtime

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                         QLabel, QInputDialog, QLineEdit)
from PyQt4.QtCore import QProcess, SIGNAL, QByteArray, QString, QTimer

# Local imports
from pydeelib.encoding import transcode
from pydeelib.qthelpers import create_toolbutton
from pydeelib.config import get_icon, get_conf_path
from pydeelib.widgets.qscishell import QsciShell
from pydeelib.widgets.externalshell.monitor import communicate


class ExternalQsciShell(QsciShell):
    def __init__(self, parent, history_filename, max_history_entries=100,
                 debug=False, profile=False, externalshell=None):
        QsciShell.__init__(self, parent, history_filename,
                           max_history_entries, debug, profile)
        # ExternalShellBase instance:
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
            
    def get__doc__(self, objtxt):
        """Get object __doc__"""
        return self.ask_monitor("%s.__doc__" % objtxt)
    
    def get_doc(self, objtxt):
        """Get object documentation"""
        return self.ask_monitor("getdoc(%s)" % objtxt)
    
    def get_source(self, objtxt):
        """Get object source"""
        return self.ask_monitor("getsource(%s)" % objtxt)


class ExternalShellBase(QWidget):
    """External Shell widget: execute Python script in a separate process"""
    def __init__(self, parent=None, wdir=None, history_filename=None):
        QWidget.__init__(self, parent)
        if wdir is None:
            wdir = osp.dirname(osp.abspath(self.fname))
        self.wdir = wdir if osp.isdir(wdir) else None
        self.arguments = ""
        
        self.shell = ExternalQsciShell(parent, get_conf_path(history_filename),
                                       externalshell=self)
        self.connect(self.shell, SIGNAL("execute(QString)"),
                     self.send_to_process)
        self.connect(self.shell, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        
        self.state_label = QLabel()
        self.time_label = QLabel()
                
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.state_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.time_label)
        hlayout.addStretch(0)
        for button in self.get_toolbar_buttons():
            hlayout.addWidget(button)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.get_shell_widget())
        self.setLayout(vlayout)
        self.resize(640, 480)
        if parent is None:
            self.setWindowIcon(self.get_icon())
            self.setWindowTitle(self.tr("Console"))

        self.t0 = None
        self.timer = QTimer(self)

        self.process = None
        
        self.is_closing = False
        
    def is_running(self):
        if self.process is not None:
            return self.process.state() == QProcess.Running
        
    def get_toolbar_buttons(self):
        self.run_button = create_toolbutton(self, get_icon('execute.png'),
                              self.tr("Run"),
                              tip=self.tr("Run again this program"),
                              triggered=self.start)
        self.kill_button = create_toolbutton(self, get_icon('kill.png'),
                              self.tr("Kill"),
                              tip=self.tr("Kills the current process, "
                                          "causing it to exit immediately"))
        return [self.run_button, self.kill_button]
        
    def get_shell_widget(self):
        return self.shell
    
    def get_icon(self):
        raise NotImplementedError
        
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
            self.is_closing = True
            self.process.kill()
        self.disconnect(self.timer, SIGNAL("timeout()"), self.show_time)
    
    def set_running_state(self, state=True):
        self.set_buttons_runnning_state(state)
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

    def set_buttons_runnning_state(self, state):
        self.run_button.setEnabled(not state)
        self.kill_button.setEnabled(state)
    
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
        raise NotImplementedError
    
    def finished(self, exit_code, exit_status):
        # Saving console history:
        self.shell.save_history()
        if self.is_closing:
            return
        self.set_running_state(False)
        self.show_time(end=True)
        self.emit(SIGNAL('finished()'))
    
#===============================================================================
#    Input/Output
#===============================================================================
    def transcode(self, bytes):
        return unicode( QString.fromLocal8Bit(bytes.data()) )
    
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
    
    def write_output(self):
        text = self.get_stdout()
        self.shell.write(text)
        QApplication.processEvents()
        
    def send_to_process(self, qstr):
        raise NotImplementedError
        
    def send_ctrl_to_process(self, letter):
        char = chr("abcdefghijklmnopqrstuvwxyz".index(letter) + 1)
        byte_array = QByteArray()
        byte_array.append(char)
        self.process.write(byte_array)
        self.process.waitForBytesWritten(-1)
        self.shell.write(QString(byte_array))
        
    def keyboard_interrupt(self):
        raise NotImplementedError


def test():
    from pydeelib.widgets.externalshell.pythonshell import ExternalPythonShell
    from pydeelib.widgets.externalshell.systemshell import ExternalSystemShell
    app = QApplication(sys.argv)
    import pydeelib
#    shell = ExternalPythonShell(wdir=osp.dirname(pydeelib.__file__),
#                                interact=True)
    shell = ExternalSystemShell(wdir=osp.dirname(pydeelib.__file__))
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