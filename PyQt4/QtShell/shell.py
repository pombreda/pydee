# -*- coding: utf-8 -*-

#TODO: log? -> save log in a .py file separate from the one containing history

import sys, os
import os.path as osp
from config import CONFIG

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
            

class Shell(object):
    """Generic shell interface (to be continued...)"""
    hlog = osp.join(osp.expanduser('~'), '.history.py')
    try:
        prompt = sys.p1
    except AttributeError:
        prompt = ">>> "
    try:
        prompt_more = sys.p2
    except AttributeError:
        prompt_more = "... "
        
    def __init__(self, interpreter=None, initcommands=None, log=''):
        if interpreter is None:
            from code import InteractiveInterpreter
            interpreter = InteractiveInterpreter()
        self.interpreter = interpreter
        
        # capture all interactive input/output 
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        self.redirect_stds()
        
        # flag: readline() is being used for e.g. raw_input() and input()
        self.reading = 0
        
        # history
        self.max_history_entries = CONFIG.get('History', 'max_entries')
        self.history = self.load_history()
        
        for command in initcommands:
            self.interpreter.runsource(command)
        
    def redirect_stds(self):
        sys.stdout   = self
        sys.stderr   = MultipleRedirection((sys.stderr, self))
        sys.stdin    = self
        
    def restore_stds(self):
        sys.stdout = self.initial_stdout
        sys.stderr = self.initial_stderr
        sys.stdin = self.initial_stdin
        
    def load_history(self):
        if osp.isfile(self.hlog):
            file = open(self.hlog, 'r')
            history = [line.replace('\n','') for line in file.readlines()
                       if not line.startswith('#')]
            file.close()
        else:
            history = []
        return history
    
    def save_history(self):
        file = open(self.hlog, 'w')
        file.writelines([line+"\n" for line in self.history])
        file.close()
        
    def add_to_history(self, command):
        if len(self.history) == self.max_history_entries:
            del self.history[0]
        self.history.append( unicode(command) )
    
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
        

