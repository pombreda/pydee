# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
Object Editor Dialog based on PyQt4
"""

def oedit(obj):
    """
    Edit the object 'obj' in a GUI-based editor and return the edited copy
    (if Cancel is pressed, return None)

    The object 'obj' is a container
    
    Supported container types:
    dict, list, tuple, str/unicode or numpy.array
    
    (instantiate a new QApplication if necessary,
    so it can be called directly from the interpreter)
    """
    # Local import
    from pydeelib.widgets.texteditor import TextEditor
    from pydeelib.widgets.dicteditor import DictEditor, ndarray, FakeObject
    from pydeelib.widgets.arrayeditor import ArrayEditor

    # Creating QApplication if necessary
    from PyQt4.QtGui import QApplication
    if QApplication.startingUp():
        QApplication([])
        
    if isinstance(obj, ndarray) and ndarray is not FakeObject:
        dialog = ArrayEditor(obj)
    elif isinstance(obj, (str, unicode)):
        dialog = TextEditor(obj)
    else:
        dialog = DictEditor(obj)
    if dialog.exec_():
        return dialog.get_copy()

if __name__ == "__main__":
    import datetime
    import numpy as N
    example = {'str': 'kjkj kj k j j kj k jkj',
               'list': [1, 3, 4, 'kjkj', None],
               'dict': {'d': 1, 'a': N.random.rand(10, 10), 'b': [1, 2]},
               'float': 1.2233,
               'array': N.random.rand(10, 10),
               'date': datetime.date(1945, 5, 8),
               'datetime': datetime.datetime(1945, 5, 8),
               }
    print "result:", oedit(example)
    print "result:", oedit(N.random.rand(10, 10))
    print "result:", oedit(oedit.__doc__)