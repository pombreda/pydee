# -*- coding: utf-8 -*-
"""Shell Interpreter"""

import time, atexit
import os.path as osp
import code

# Local import
import encoding
from config import CONF, get_conf_path
            
class Interpreter(code.InteractiveConsole):
    """Interpreter"""
    log_path = get_conf_path('.history.py')
    inithistory = [
                   '# -*- coding: utf-8 -*-',
                   '# *** history: v0.2 ***',
                   '',
                   ]
    separator = '# ---(%s)---' % time.ctime()
        
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
        if rawinputfunc is not None:
            self.namespace['raw_input'] = rawinputfunc
        
        # history
        self.max_history_entries = CONF.get('history', 'max_entries')
        self.rawhistory, self.history = self.load_history()
        
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
        