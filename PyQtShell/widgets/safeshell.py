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

"""Safe Shell widget: execute Python script in another process"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os
import os.path as osp
from time import time, strftime, gmtime

# Debug
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                         QMessageBox, QLabel, QInputDialog, QLineEdit,
                         QCheckBox)
from PyQt4.QtCore import QProcess, SIGNAL, QByteArray, QString, QTimer

# Local imports
from PyQtShell.widgets.terminal import QsciTerminal
from PyQtShell.qthelpers import create_toolbutton
from PyQtShell.config import get_icon, get_conf_path
from PyQtShell.widgets import startup


class SafeShell(QWidget):
    def __init__(self, parent=None, fname=None, wdir=None,
                 ask_arguments=False, interact=False, debug=False,
                 commands=None):
        QWidget.__init__(self, parent)
        self.fname = startup.__file__ if fname is None else fname
        self.directory = osp.dirname(self.fname) if wdir is None else wdir
        self.commands = commands
        
        self.shell = QsciTerminal(parent, get_conf_path('.history_extcons.py'))
        self.connect(self.shell, SIGNAL("execute(QString)"),
                     self.send_to_process)
        self.connect(self.shell, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        
        self.state_label = QLabel()
        self.time_label = QLabel()
        
        self.run_button = create_toolbutton(self, get_icon('execute.png'),
                              self.tr("Run"),
                              tip=self.tr("Run again this program"),
                              callback=self.run)
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
        
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.state_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.time_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.interact_check)
        hlayout.addWidget(self.debug_check)
        hlayout.addWidget(self.run_button)
        hlayout.addWidget(self.terminate_button)
        hlayout.addWidget(self.kill_button)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.shell)
        self.setLayout(vlayout)
        self.resize(640, 480)
        if parent is None:
            self.setWindowIcon(get_icon('python.png'))
        self.setWindowTitle(self.tr("Console"))

        self.t0 = None
        self.timer = QTimer(self)

        self.arguments = ""
        self.process = None
        
        if ask_arguments:
            self.run()
        else:
            self.create_process()

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
    
    def run(self):
        if self.fname != startup.__file__:
            self.create_process()
        else:
            arguments, valid = QInputDialog.getText(self, self.tr('Arguments'),
                              self.tr('Command line arguments:'),
                              QLineEdit.Normal,
                              self.arguments)
            if valid:
                self.arguments = unicode(arguments)
                self.create_process(self.arguments.split(' ') if self.arguments \
                                    else None)
            else:
                self.set_running_state(False)
    
    def create_process(self, args=None):
        self.shell.clear()
        p_args = ['-u']
        if self.interact_check.isChecked():
            p_args.append('-i')
        if self.debug_check.isChecked():
            p_args.extend(['-m', 'pdb'])
        p_args.append(self.fname)
        if args:
            p_args.extend(args)
        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.directory)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        if self.commands:
            env = self.process.systemEnvironment()
            env.append('PYTHONINITCOMMANDS=%s' % ';'.join(self.commands))
            self.process.setEnvironment(env)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     self.write_error)
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.write_output)
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
        self.connect(self.terminate_button, SIGNAL("clicked()"),
                     self.process.terminate)
        self.connect(self.kill_button, SIGNAL("clicked()"), self.process.kill)
        self.process.start(sys.executable, p_args)
        running = self.process.waitForStarted()
        self.set_running_state(running)
        if not running:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Python "
                                 "interpreter failed to start"))
        else:
            self.shell.setFocus()
        return self.process
    
    def finished(self, exit_code, exit_status):
        self.set_running_state(False)
        self.show_time(end=True)
        self.emit(SIGNAL('finished()'))
        # Saving console history:
        self.shell.save_history()
    
    def write_output(self):
        self.process.setReadChannel(QProcess.StandardOutput)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardOutput()
        text = QString.fromUtf8(bytes.data())
        self.shell.write(text)
        QApplication.processEvents()
    
    def write_error(self):
        self.process.setReadChannel(QProcess.StandardError)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardError()
        text = unicode(QString.fromUtf8(bytes.data()))
        lines = text.splitlines()
        for index, line in enumerate(lines):
            self.shell.write_error(line)
            if index < len(lines)-1:
                self.shell.write_error(os.linesep)
        
    def send_to_process(self, qstr):
        if not qstr.endsWith('\n'):
            qstr.append('\n')
        self.process.write(qstr.toUtf8())
        self.process.waitForBytesWritten(-1)
        
    def keyboard_interrupt(self):
        #TODO: How to send directly the interrupt key to the process?
        self.shell.emit(SIGNAL("execute(QString)"), "raise KeyboardInterrupt")


def test():
    app=QApplication(sys.argv)
    import PyQtShell
    from PyQtShell.config import get_font
    safeshell = SafeShell(wdir=osp.dirname(PyQtShell.__file__), interact=True)
    safeshell.shell.set_font(get_font('external_shell'))
    safeshell.show()
    sys.exit(app.exec_())
#    safeshell.process.waitForFinished()

if __name__ == "__main__":
    test()