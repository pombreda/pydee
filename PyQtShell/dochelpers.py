# -*- coding: utf-8 -*-
"""Utilities and wrappers around inspect module"""

import inspect

def getdoc(obj):
    """Wrapper around inspect.getdoc"""
    #TODO: Add exception handling: is it really necessary?
    return inspect.getdoc(obj)

def getsource(obj):
    """Wrapper around inspect.getsource"""
    try:
        src = inspect.getsource(obj)
    except TypeError:
        if hasattr(obj, '__class__'):
            src = inspect.getsource(obj.__class__)
    return src

def getargtxt(obj, one_arg_per_line=True):
    """Get the names and default values of a function's arguments"""
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        func_obj = obj
    elif inspect.ismethod(obj):
        func_obj = obj.im_func
    elif inspect.isclass(obj):
        func_obj = getattr(obj, '__init__')
    else:
        return None
    args, _, _ = inspect.getargs(func_obj.func_code)
    defaults = func_obj.func_defaults
    for index, default in enumerate(defaults):
        args[index+len(args)-len(defaults)] += '='+str(default)
    textlist = ['']
    for i_arg, arg in enumerate(args):
        textlist[-1] += arg
        if i_arg < len(args)-1:
            textlist[-1] += ', '
            if len(textlist[-1])>=32 or one_arg_per_line:
                textlist.append('')
    return textlist
    
#import subprocess
#t = getargtxt(subprocess.Popen)
#print subprocess.Popen
#print t
#print len(t[0])