# -*- coding: utf-8 -*-
"""Shell Mixin"""

import sys, time, atexit
import os.path as osp
import code

# Local import
import encoding
from config import CONF, get_conf_path

def create_banner(moreinfo, message=''):
    """Create shell banner"""
    if message:
        message = '\n' + message + '\n'
    return 'Python %s on %s\n' % (sys.version, sys.platform) + \
            moreinfo+'\n' + message + '\n'


class MultipleRedirection:
    """ Dummy file which redirects stream to multiple file """
    def __init__(self, files):
        """ The stream is redirect to the file list 'files' """
        self.files = files
    def write(self, str):
        """ Emulate write function """
        for fileobj in self.files:
            fileobj.write(str)
            
SHELL = None
def _raw_input(prompt="", echo=1):
    """Reimplementation of raw_input builtin (for future developments)"""
    return SHELL.raw_input(prompt, echo)

class Interpreter(code.InteractiveInterpreter):
    """Interpreter (to be continued...)"""
    log_path = get_conf_path('.history.py')
    inithistory = [
                   '# -*- coding: utf-8 -*-',
                   '# *** history: v0.2 ***',
                   '',
                   ]
    separator = '# ---(%s)---' % time.ctime()
    try:
        prompt = sys.p1
    except AttributeError:
        prompt = ">>> "
    try:
        prompt_more = sys.p2
    except AttributeError:
        prompt_more = "... "
        
    def __init__(self, namespace=None, commands=None,
                 debug=False, exitfunc=None):
        """
        namespace: locals send to InteractiveInterpreter object
        commands: list of commands executed at startup
        """
        code.InteractiveInterpreter.__init__(self, namespace)
        
        if commands is None:
            commands = []
        
        if exitfunc is not None:
            atexit.register(exitfunc)
        self.debug = debug
        global SHELL
        SHELL = self
        self.namespace = self.locals
        self.namespace['raw_input'] = _raw_input
        
        # flag: readline() is being used for e.g. raw_input() and input()
        self.reading = 0

        # Running initial commands before redirecting I/O
        for cmd in commands:
            self.runsource(cmd)
        
        # capture all interactive input/output 
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        self.redirect_stds()
        
        # history
        self.max_history_entries = CONF.get('history', 'max_entries')
        self.rawhistory, self.history = self.load_history()
        
    def raw_input(self, prompt, echo):
        """Reimplementation of raw_input builtin (for future developments)"""
        raise NotImplementedError("raw_input is not yet supported in PyQtShell")
        
    def redirect_stds(self):
        """Redirects stds"""
        if not self.debug:
            sys.stdout   = self
            sys.stderr   = MultipleRedirection((sys.stderr, self))
            sys.stdin    = self
        
    def restore_stds(self):
        """Restore stds"""
        if not self.debug:
            sys.stdout = self.initial_stdout
            sys.stderr = self.initial_stderr
            sys.stdin = self.initial_stdin
        
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
    
    def get_interpreter(self):
        """Return the interpreter object"""
        return self

    def flush(self):
        """Simulate stdin, stdout, and stderr"""
        pass

    def isatty(self):
        """Simulate stdin, stdout, and stderr"""
        return 1
        

