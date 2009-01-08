# -*- coding: utf-8 -*-

#TODO: write/open history to/from a text file located in HOME directory
#TODO: log? -> save log in a .py file separate from the one containing history

import sys

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
    try:
        prompt = sys.p1
    except AttributeError:
        prompt = ">>> "
    try:
        prompt_more = sys.p2
    except AttributeError:
        prompt_more = "... "
        
    def __init__(self, interpreter=None, initcommands=None, message='', log=''):
        if interpreter is None:
            from code import InteractiveInterpreter
            interpreter = InteractiveInterpreter()
        self.interpreter = interpreter
        
        # capture all interactive input/output 
        self.save_stds()
        sys.stdout   = self
        sys.stderr   = MultipleRedirection((sys.stderr, self))
        sys.stdin    = self
        
        # flag: readline() is being used for e.g. raw_input() and input()
        self.reading = 0
        
        # history
        self.history = []
        
        # banner
        if message:
            message = '\n'+message+'\n'
        self.banner = 'Python %s on %s\n' % (sys.version, sys.platform) + \
                      'Type "copyright", "credits" or "license" for more information.\n' + \
                      message+'\n'
                      
        for command in initcommands:
            self.interpreter.runsource(command)
        
    def save_stds(self):
        self.initial_stdout = sys.stdout
        self.initial_stderr = sys.stderr
        self.initial_stdin = sys.stdin
        
    def restore_stds(self):
        sys.stdout = self.initial_stdout
        sys.stderr = self.initial_stderr
        sys.stdin = self.initial_stdin
        
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
        

