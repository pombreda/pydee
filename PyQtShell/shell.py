# -*- coding: utf-8 -*-

import sys, time
import os.path as osp
import code

# Local import
import encoding
from config import CONF

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
    return SHELL.raw_input(prompt, echo)

class ShellInterface(object):
    """Generic shell interface (to be continued...)"""
    log_path = osp.join(osp.expanduser('~'), '.history.py')
    inithistory = [ '"# -*- coding: utf-8 -*-\n\r"' ]
    separator = '# ---(%s)---' % time.ctime()
    try:
        prompt = sys.p1
    except AttributeError:
        prompt = ">>> "
    try:
        prompt_more = sys.p2
    except AttributeError:
        prompt_more = "... "
        
    def __init__(self, namespace=None, commands=None, debug=False):
        """
        namespace: locals send to InteractiveInterpreter object
        commands: list of commands executed at startup
        """
        self.debug = debug
        self.interpreter = code.InteractiveInterpreter(namespace)
        global SHELL
        SHELL = self
        self.namespace = self.interpreter.locals
        self.namespace['raw_input'] = _raw_input
        
        # flag: readline() is being used for e.g. raw_input() and input()
        self.reading = 0

        # Running initial commands before redirecting I/O
        for cmd in commands:
            self.interpreter.runsource(cmd)
        
        # capture all interactive input/output 
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        self.redirect_stds()
        
        # history
        self.max_history_entries = CONF.get('history', 'max_entries')
        self.rawhistory, self.history = self.load_history()
        
    def raw_input(self, prompt, echo):
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
        if len(self.history) == self.max_history_entries:
            del self.history[0]
            del self.rawhistory[0]
        cmd = unicode(command)
        self.history.append( cmd )
        self.rawhistory.append( cmd )
    
    def get_interpreter(self):
        """Return the interpreter object"""
        return self.interpreter

    def flush(self):
        """Simulate stdin, stdout, and stderr"""
        pass

    def isatty(self):
        """Simulate stdin, stdout, and stderr"""
        return 1

    def clear(self):
        """ Clear """
        
