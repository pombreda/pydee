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

"""Shell Interpreter"""

import time, atexit, os, code
import os.path as osp

# Local import
from PyQtShell import __version__
import encoding
from config import CONF, get_conf_path


class Interpreter(code.InteractiveConsole):
    """Interpreter"""
    log_path = get_conf_path('.history.py')
    inithistory = [
                   '# -*- coding: utf-8 -*-',
                   '# *** PyQtShell v%s -- History log ***' % __version__,
                   '',
                   ]
    separator = '%s# ---(%s)---' % (os.linesep, time.ctime())
        
    def __init__(self, namespace=None, exitfunc=None,
                 rawinputfunc=None):
        """
        namespace: locals send to InteractiveConsole object
        commands: list of commands executed at startup
        """
        code.InteractiveConsole.__init__(self, namespace)
        
        if exitfunc is not None:
            atexit.register(exitfunc)
        
        self.namespace = self.locals
        self.namespace['__name__'] = '__main__'
        if rawinputfunc is not None:
            self.namespace['raw_input'] = rawinputfunc
        
        # history
        self.max_history_entries = CONF.get('historylog', 'max_entries')
        self.rawhistory, self.history = self.load_history()
        
    def eval(self, text):
        """
        Evaluate text and return (obj, valid)
        where *obj* is the object represented by *text*
        and *valid* is True if object evaluation did not raise any exception
        """
        assert isinstance(text, (str, unicode))
        try:
            return eval(text, self.locals), True
        except:
            return None, False
        
    def load_history(self):
        """Load history from a .py file in user home directory"""
        if osp.isfile(self.log_path):
            rawhistory, _ = encoding.readlines(self.log_path)
            rawhistory = [line.replace('\n','') for line in rawhistory]
            if rawhistory[1] != self.inithistory[1]:
                rawhistory = self.inithistory
        else:
            rawhistory = self.inithistory
        history = [line for line in rawhistory if not line.startswith('#')]
        rawhistory.append(self.separator)
        return rawhistory, history
    
    def save_history(self):
        """Save history to a .py file in user home directory"""
        if self.rawhistory[-1] == self.separator:
            self.rawhistory.remove(self.separator)
        encoding.writelines(self.rawhistory, self.log_path)
        
    def add_to_history(self, command):
        """Add command to history"""
        while len(self.history) >= self.max_history_entries:
            del self.history[0]
            while self.rawhistory[0].startswith('#'):
                del self.rawhistory[0]
            del self.rawhistory[0]
        cmd = unicode(command)
        if len(self.history)>0 and self.history[-1] == cmd:
            return
        self.history.append( cmd )
        self.rawhistory.append( cmd )
        
