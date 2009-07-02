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
from pydeelib.widgets.monitor import (write_packet, read_packet,
                                      monitor_setattr, monitor_getattr)
from pydeelib.encoding import transcode
from pydeelib.widgets.qscishell import QsciShell
from pydeelib.widgets.dicteditor import RemoteDictEditorTableView
from pydeelib.qthelpers import create_toolbutton, translate
from pydeelib.config import get_icon, get_conf_path, CONF, get_font
from pydeelib.widgets import startup


class ExternalShellBase(QsciShell):
    def __init__(self, parent, history_filename, max_history_entries=100,
                 debug=False, profile=False):
        QsciShell.__init__(self, parent, history_filename,
                           max_history_entries, debug, profile)
        
    #------ Code completion / Calltips
    def show_code_completion(self, text):
        """Display a completion list based on the last token"""
        self.emit(SIGNAL('show_code_completion(QString)'), text)
    
    def show_docstring(self, text, call=False):
        """Show docstring or arguments"""
        if not self.calltips:
            return
        self.emit(SIGNAL('show_docstring(QString,bool)'), text, call)            


#TODO: Add a context-menu to customize wsfilter, ...
class GlobalsExplorer(QWidget):
    ID = 'workspace'
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        
        self.shell = parent
        
        hlayout = QHBoxLayout()
        hlayout.setAlignment(Qt.AlignLeft)
        
        # Setup toolbar
        self.toolbar_widgets = []
        explorer_label = QLabel(self.tr("<span style=\'color: #444444\'>"
                                        "<b>Global variables explorer</b>"
                                        "</span>"))
        self.toolbar_widgets.append(explorer_label)
        hide_button = create_toolbutton(self,
                                           text=self.tr("Hide"),
                                           icon=get_icon('hide.png'),
                                           triggered=self.collapse)
        self.toolbar_widgets.append(hide_button)
        refresh_button = create_toolbutton(self,
                                           text=self.tr("Refresh"),
                                           icon=get_icon('reload.png'),
                                           triggered=self.refresh)
        self.toolbar_widgets.append(refresh_button)
        
        for widget in self.toolbar_widgets:
            hlayout.addWidget(widget)
        hlayout.insertStretch(1, 1)
        
        # Dict editor:
        truncate = CONF.get(self.ID, 'truncate')
        inplace = CONF.get(self.ID, 'inplace')
        minmax = CONF.get(self.ID, 'minmax')
        collvalue = CONF.get(self.ID, 'collvalue')
        self.editor = RemoteDictEditorTableView(parent, None,
                                            truncate=truncate, inplace=inplace,
                                            minmax=minmax, collvalue=collvalue,
                                            getattr_func=self.getattr_func,
                                            setattr_func=self.setattr_func)
        self.editor.setFont(get_font(self.ID))
        self.connect(self.editor.delegate, SIGNAL('edit(QString)'),
                     lambda qstr: self.emit(SIGNAL('edit(QString)'), qstr))
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.editor)
        self.setLayout(vlayout)
        
    def getattr_func(self, name):
        return monitor_getattr(self.shell.monitor_socket, name)
        
    def setattr_func(self, name, value):
        monitor_setattr(self.shell.monitor_socket, name, value)
        self.emit(SIGNAL('refresh()'))
        
    def set_data(self, data):
        self.editor.set_data(data)
        
    def collapse(self):
        self.emit(SIGNAL('collapse()'))
        
    def refresh(self):
        self.emit(SIGNAL('refresh()'))
        

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
        self.shell = ExternalShellBase(parent, get_conf_path(history_filename))
        self.connect(self.shell, SIGNAL("execute(QString)"),
                     self.send_to_process)
        self.connect(self.shell, SIGNAL("keyboard_interrupt()"),
                     self.keyboard_interrupt)
        self.connect(self.shell, SIGNAL('show_code_completion(QString)'),
                     self.show_code_completion)
        self.connect(self.shell, SIGNAL('show_docstring(QString,bool)'),
                     self.show_docstring)
        
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
        
        #TODO: The following lines are ugly, aren't they? -> do something!!
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
        self.connect(self.globalsexplorer, SIGNAL('edit(QString)'),
                     self.globals_explorer_edit)
        
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
            from pydeelib.widgets.monitor import start_server
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
            import pydeelib.widgets
            scpath = osp.dirname(osp.abspath(pydeelib.widgets.__file__))
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
                        
        self.connect(self.process, SIGNAL("readyReadStandardError()"),
                     self.write_error)
        self.connect(self.process, SIGNAL("readyReadStandardOutput()"),
                     self.write_output)
        self.connect(self.process, SIGNAL("finished(int,QProcess::ExitStatus)"),
                     self.finished)
        
        self.connect(self.terminate_button, SIGNAL("clicked()"),
                     self.process.terminate)
        self.connect(self.kill_button, SIGNAL("clicked()"),
                     self.process.kill)
        
        if self.python:
            self.process.setProcessChannelMode(QProcess.SeparateChannels)
            self.process.start(sys.executable, p_args)
        else:
            self.process.setProcessChannelMode(QProcess.MergedChannels)
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
            #FIXME: print u"é" does not work (but it used to work??!!)
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
    
    def write_output(self):
        self.shell.write( self.get_stdout() )
        QApplication.processEvents()
    
    def write_error(self):
        lines = self.get_stderr().splitlines(True)
        for _index, line in enumerate(lines):
            self.shell.write_error(line)
#            if index < len(lines)-1:
#                self.shell.write_error('\n')
        
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
        print >>STDOUT, "Ctrl+%s: %r -- %s" % (letter, char, char)
        self.process.write(byte_array)
        self.process.waitForBytesWritten(-1)
        self.shell.write(QString(byte_array))
        
    def keyboard_interrupt(self):
        #TODO: Send ctrl keys to process --> dig deeper:
# Why don't the following code work? (for terminal)
#        self.send_ctrl_to_process('c')
        self.shell.emit(SIGNAL("execute(QString)"), "raise KeyboardInterrupt")
            
#===============================================================================
#    Namespace explorer
#===============================================================================
    def refresh_globals_explorer(self):
        if self.monitor_socket is None:
            return
        write_packet(self.monitor_socket, "glexp_make(globals())")
        data = read_packet(self.monitor_socket)
        obj = pickle.loads(data)
        self.globalsexplorer.set_data(obj)
        
    def toggle_globals_explorer(self, state):
        self.splitter.setSizes([1, 1 if state else 0])
        self.globalsexplorer_button.setChecked(state)
        if state:
            self.refresh_globals_explorer()
        
    def splitter_moved(self, pos, index):
        self.globalsexplorer_button.setChecked( self.splitter.sizes()[1] )
        
    def globals_explorer_edit(self, qstr):
        name = unicode(qstr)
        if self.monitor_socket is None:
            return
        obj = monitor_getattr(self.monitor_socket, name)
        from pydeelib.widgets.objecteditor import oedit
        result = oedit(obj)
        if result is not None:
            monitor_setattr(self.monitor_socket, name, result)
            self.refresh_globals_explorer()
        
        
#===============================================================================
#    Introspection
#===============================================================================
    def ask_monitor(self, command):
        if self.monitor_socket is None:
            return
        write_packet(self.monitor_socket, command)
        data = read_packet(self.monitor_socket)
        try:
            return pickle.loads(data)
        except EOFError:
            pass
        
    def show_code_completion(self, text):
        """Display a completion list based on the last token"""
        text = unicode(text)
        objdir = self.ask_monitor("dir(%s)" % text)
        if objdir:
            self.shell.show_completion_list(objdir, 'dir(%s)' % text) 
            
    #TODO: Refactoring with InteractiveShell --> into QsciShell
    def show_docstring(self, text, call=False):
        """Show docstring or arguments"""
        text = unicode(text)
        
        sh = self.shell
        done = False
        size, font = sh.calltip_size, sh.calltip_font
        if (sh.docviewer is not None) and \
           (sh.docviewer.dockwidget.isVisible()):
            # DocViewer widget exists and is visible
            sh.docviewer.refresh(text)
            if call:
                # Display argument list if this is function call
                iscallable = self.ask_monitor("callable(%s)" % text)
                if iscallable is not None:
                    if iscallable:
                        arglist = self.ask_monitor("getargtxt(%s)" % text)
                        if arglist:
                            done = True
                            sh.show_calltip(translate("QsciShell", "Arguments"),
                                            arglist, size, font, '#129625')
                    else:
                        done = True
                        sh.show_calltip(translate("QsciShell", "Warning"),
                                        translate("QsciShell", "Object `%1` is not callable"
                                                  " (i.e. not a function, "
                                                  "a method or a class "
                                                  "constructor)").arg(text),
                                        size, font, color='#FF0000')
        if not done:
            doc = self.ask_monitor("%s.__doc__" % text)
            if doc is None:
                return
            sh.show_calltip(translate("QsciShell", "Documentation"), doc, size, font)
        
    

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