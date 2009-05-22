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
                         QMessageBox, QLabel, QCursor, QInputDialog, QLineEdit,
                         QCheckBox)
from PyQt4.QtCore import QProcess, SIGNAL, QByteArray, QString, Qt, QTimer
from PyQt4.Qsci import QsciScintilla

# Local imports
from PyQtShell.widgets.terminal import QsciTerminal
from PyQtShell.widgets.shellhelpers import get_error_match
from PyQtShell.qthelpers import create_toolbutton
from PyQtShell.config import get_font, get_icon


class SafeShellBaseWidget(QsciTerminal):
    def __init__(self, parent=None, debug=False, profile=False, history=None):
        QsciTerminal.__init__(self, parent, debug, profile)
        self.set_font(get_font('shell'))
        self.new_input_line = True
        self.prompt_index = 0
        # history
        self.histidx = None
        self.hist_wholeline = False
        if history is None:
            self.history = ['']
        else:
            self.history = history
            
    #------ History Management
    def __get_current_line_to_cursor(self):
        line, index = self.getCursorPosition()
        self.setSelection(line, self.prompt_index, line, index)
        return self.selectedText()
    
    def clear_line(self):
        line, index = self.get_end_pos()
        self.setSelection(line, self.prompt_index, line, index)
        self.removeSelectedText()
        
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
        history = self.history
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
        
    def get_buffer(self):
        line, index = self.get_end_pos()
        self.setSelection(line, self.prompt_index, line, index)
#        print >>STDOUT, "prompt_index, index:", self.prompt_index, index
        return self.selectedText()
        
    def reset_buffer(self):
        self.new_input_line = True
    
    def keyPressEvent(self, event):
        text = event.text()
        key = event.key()
        last_line = self.lines()-1
        line, _ = self.getCursorPosition()

        if len(text):
            self.hist_wholeline = False
            if self.new_input_line:
                # Move cursor to end
                self.move_cursor_to_end()
                _, self.prompt_index = self.getCursorPosition()
                self.new_input_line = False

        if key == Qt.Key_Return or key == Qt.Key_Enter:
            buffer = self.get_buffer()
            self.insert('\n')
#            print >>STDOUT, "buffer:", repr(buffer)
            self.emit(SIGNAL("send_to_process(QString)"), buffer)
            self.histidx = None
            self.history.append(unicode(buffer).strip())
            self.new_input_line = True
            
        elif key == Qt.Key_Escape:
            self.clear_line()

        elif key == Qt.Key_Up:
            if line == last_line:
                self.__browse_history(backward=True)
            else:
                self.SendScintilla(QsciScintilla.SCI_LINEUP)

        elif key == Qt.Key_Down:
            if line == last_line:
                self.__browse_history(backward=False)
            else:
                self.SendScintilla(QsciScintilla.SCI_LINEDOWN)

        else:
            QsciScintilla.keyPressEvent(self, event)
        
    #------ Mouse events
    def mousePressEvent(self, event):
        """
        Re-implemented to handle the mouse press event.
        event: the mouse press event (QMouseEvent)
        """
        self.setFocus()
        ctrl = event.modifiers() & Qt.ControlModifier
        if event.button() == Qt.MidButton:
            self.paste()
        elif event.button() == Qt.LeftButton and ctrl:
            text = unicode(self.text(self.lineAt(event.pos())))
            self.emit(SIGNAL("go_to_error(QString)"), text)
        else:
            QsciScintilla.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        """Show Pointing Hand Cursor on error messages"""
        if event.modifiers() & Qt.ControlModifier:
            text = unicode(self.text(self.lineAt(event.pos())))
            if get_error_match(text):
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                return
        QApplication.restoreOverrideCursor()
        QsciScintilla.mouseMoveEvent(self, event)


class SafeShell(QWidget):
    def __init__(self, parent, fname, ask_arguments=False, interact=True):
        QWidget.__init__(self, parent)
        self.fname = fname
        self.directory = osp.dirname(fname)
        
        self.shell = SafeShellBaseWidget(parent)
        self.connect(self.shell, SIGNAL("send_to_process(QString)"),
                     self.send_to_process)
        
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
        
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.state_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.time_label)
        hlayout.addStretch(0)
        hlayout.addWidget(self.interact_check)
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
        arguments, valid = QInputDialog.getText(self, self.tr('Arguments'),
                          self.tr('Command line arguments:'),
                          QLineEdit.Normal,
                          self.arguments)
        if valid:
            self.arguments = unicode(arguments)
            self.create_process(self.arguments.split(' '))
        else:
            self.set_running_state(False)
    
    def create_process(self, args=None):
        self.shell.clear()
        if args is None:
            args = []
        args = ['-u', self.fname] + args
        if self.interact_check.isChecked():
            args.insert(1, '-i')
        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.directory)
        self.process.setProcessChannelMode(QProcess.SeparateChannels)
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.write_output)
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     self.write_error)
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
        self.connect(self.terminate_button, SIGNAL("clicked()"),
                     self.process.terminate)
        self.connect(self.kill_button, SIGNAL("clicked()"), self.process.kill)
        self.process.start(sys.executable, args)
        if not self.process.waitForStarted():
            QMessageBox.critical(self, self.tr("Error"), self.tr("Python "
                                 "interpreter failed to start"))
        self.set_running_state(True)
        self.shell.setFocus()
        return self.process
    
    def finished(self, exit_code, exit_status):
        self.set_running_state(False)
        self.show_time(end=True)
        self.emit(SIGNAL('finished()'))
    
    def write_output(self):
        self.process.setReadChannel(QProcess.StandardOutput)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardOutput()
        text = QString.fromUtf8(bytes.data())
        self.shell.write(text)
#        print >>STDOUT, text
        self.shell.reset_buffer()
        QApplication.processEvents()
    
    def write_error(self):
        self.process.setReadChannel(QProcess.StandardError)
        bytes = QByteArray()
        while self.process.bytesAvailable():
            bytes += self.process.readAllStandardError()
        text = unicode(QString.fromUtf8(bytes.data()))
        
        # Ugly, but still haven't found out how to get this right:
        text = text.replace('>>> >>>', '>>>')
        
        lines = text.splitlines()
        if len(lines) == 1:
            self.shell.write_error(text)
        else:
            for line in lines:
                self.shell.write_error(line + os.linesep)
#        print >>STDERR, "***", text, "***"
        self.shell.reset_buffer()
        
    def send_to_process(self, qstr):
        qstr.append('\n')
        self.process.write(qstr.toUtf8())
        self.process.waitForBytesWritten(-1)


def test():
    app=QApplication(sys.argv)
    from PyQtShell import qthelpers
    safeshell = SafeShell(None, qthelpers.__file__)
    safeshell.show()
    sys.exit(app.exec_())
#    safeshell.process.waitForFinished()

if __name__ == "__main__":
    test()