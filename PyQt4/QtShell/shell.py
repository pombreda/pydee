# -*- coding: utf-8 -*-

import sys, time
import os.path as osp
from code import InteractiveInterpreter

# Local import
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
            

class ShellInterface(object):
    """Generic shell interface (to be continued...)"""
    log_path = osp.join(osp.expanduser('~'), '.history.py')
    separator = '# ---(%s)---' % time.ctime()
    try:
        prompt = sys.p1
    except AttributeError:
        prompt = ">>> "
    try:
        prompt_more = sys.p2
    except AttributeError:
        prompt_more = "... "
        
    def __init__(self, namespace=None, commands=None):
        """
        namespace: locals send to InteractiveInterpreter object
        commands: list of commands executed at startup
        """
        self.interpreter = InteractiveInterpreter(namespace)
        self.namespace = self.interpreter.locals
        
        # capture all interactive input/output 
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        self.redirect_stds()
        
        # flag: readline() is being used for e.g. raw_input() and input()
        self.reading = 0
        
        # history
        self.max_history_entries = CONF.get('history', 'max_entries')
        self.rawhistory, self.history = self.load_history()
        
        for cmd in commands:
            self.interpreter.runsource(cmd)
        
    def redirect_stds(self):
        """Redirects stds"""
        sys.stdout   = self
        sys.stderr   = MultipleRedirection((sys.stderr, self))
        sys.stdin    = self
        
    def restore_stds(self):
        """Restore stds"""
        sys.stdout = self.initial_stdout
        sys.stderr = self.initial_stderr
        sys.stdin = self.initial_stdin
        
    def load_history(self):
        """Load history from a .py file in user home directory"""
        if osp.isfile(self.log_path):
            fileobj = open(self.log_path, 'r')
            rawhistory = [line.replace('\n','') for line in fileobj.readlines()]
            fileobj.close()
        else:
            rawhistory = []
        history = [line for line in rawhistory if not line.startswith('#')]
        rawhistory.append(self.separator)
        return rawhistory, history
    
    def save_history(self):
        """Save history to a .py file in user home directory"""
        if self.rawhistory[-1] == self.separator:
            self.rawhistory.remove(self.separator)
        fileobj = open(self.log_path, 'w')
        fileobj.writelines([line+"\n" for line in self.rawhistory])
        fileobj.close()
        
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
        

