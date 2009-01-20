#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
PyQtShell
=========

Interactive Python shell and related widgets based on PyQt4

Copyright © 2009 Pierre Raybaut
This software is licensed under the terms of the GNU General Public
License version 3 as published by the Free Software Foundation.
"""

name = 'PyQtShell'
version = '0.0.9'
download_url = 'http://%s.googlecode.com/files/%s-%s-py2.5.egg' % (name.lower(), name, version)
py_modules = ['xyinstall']
packages = ['PyQt4.QtShell']
package_data={'PyQt4.QtShell': ['images/*.png', '*.qm']}
scripts = ['qons.pyw']
import os
if os.name == 'posix':
    scripts = ['qons']
description = 'Interactive Python shell and related widgets based on PyQt4'
long_description = 'PyQtShell is intended to be an extension to PyQt4 (module PyQt4.QtShell) providing a console application (see screenshots: %s) based on independent widgets interacting with each other: workspace (globals explorer with dict/list editor and numpy arrays editor), docstring viewer (calltip), history log, multiline code editor (support drag and drop, autocompletion, syntax coloring, ...) and working directory browser.' % download_url
keywords = 'PyQt4 shell console widgets'
classifiers = ['Development Status :: 3 - Alpha',
               'Topic :: Scientific/Engineering',
               'Topic :: Software Development :: Widget Sets',
               ]

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
      name = name,
      version = version,
      description = description,
      long_description = long_description,
      download_url = download_url,
      author = "Pierre Raybaut",
      author_email = 'contact@pythonxy.com',
      url = 'http://code.google.com/p/%s/' % name.lower(),
      license = 'GPLv3',
      keywords = keywords,
      platforms = ['any'],
      py_modules = py_modules,
      packages = packages,
      package_data = package_data,
      requires=["PyQt4 (>4.3)"],
      scripts = scripts,
      classifiers = classifiers + [
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.5',
        ],
    )
