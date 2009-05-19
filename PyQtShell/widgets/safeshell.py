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

"""Safe Shell widget: execute Python script in another process"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

#TODO: Open a window with a console and process state/control widgets
#      -> dedicated console widget for output/errors (see sandbox.pyw)
#      -> buttons to act on process (terminate)

#TODO: Before that, move write method (and others) from ShellBaseWidget to QsciTerminal

import sys
import os.path as osp

from PyQt4.QtCore import QProcess

def create_process(fname, directory):
    """Temporary implementation -> will be replaced by a widget"""
    args = [fname]
    process = QProcess()
    process.setWorkingDirectory(directory)
    process.start(sys.executable, args)
    return process

def test():
    from PyQt4.QtGui import QApplication
    QApplication([])
    from PyQtShell import qthelpers
    fname = qthelpers.__file__
    dirname = osp.dirname(osp.abspath(fname))
    process = create_process(fname, dirname)
    process.waitForFinished()

if __name__ == "__main__":
    test()