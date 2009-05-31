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
Pydee
=====

Interactive Python shell and related widgets based on PyQt4

Copyright © 2009 Pierre Raybaut
This software is licensed under the terms of the GNU General Public
License version 2 as published by the Free Software Foundation.
"""

name = 'pydee'
libname = 'pydeelib'
from pydeelib import __version__ as version
google_url = 'http://%s.googlecode.com' % name
download_url = '%s/files/%s-%s-py2.5.egg' % (google_url, name, version)
packages = [libname, '%s.widgets' % libname, '%s.plugins' % libname]
package_data={name: ['*.qm', 'python.api', 'images/*.png',
                     'images/console/*.png', 'images/docviewer/*.png',
                     'images/edit/*.png', 'images/editor/*.png',
                     'images/explorer/*.png', 'images/file/*.png',
                     'images/filetypes/*.png', 'images/workspace/*.png',
                     ]}
import os
if os.name == 'nt':
    scripts = ['pydee.pyw']
else:
    scripts = ['pydee']
description = 'Pydee development environment and its PyQt4-based IDE tools: interactive Python shell, Python code editor, workspace (dict/list/string/array editor), doc viewer, history log, environment variables editor, ...'
long_description = 'pydeelib is intended to be an extension to PyQt4 providing a simple development environment named "Pydee" - a powerful alternative to IDLE (see screenshots: %s) based on independent widgets interacting with each other: workspace (globals explorer with dict/list editor and numpy arrays editor), docstring viewer (calltip), history log, multiline code editor (support drag and drop, autocompletion, syntax coloring, ...), environment variables editor (including a Windows-specific editor to change current user environement variables) and working directory browser.' % google_url
keywords = 'PyQt4 shell console widgets IDE'
classifiers = ['Development Status :: 3 - Alpha',
               'Topic :: Scientific/Engineering',
               'Topic :: Software Development :: Widget Sets',
               ]

try:
    from setuptools import setup
    addl_args = dict(
        entry_points = {        
        'gui_scripts': [
            'pydee = pydeelib.pydee:main'
            ],
        },
        )
except ImportError:
    from distutils.core import setup
    addl_args = {}

setup(
      name = name,
      version = version,
      description = description,
      long_description = long_description,
      download_url = download_url,
      author = "Pierre Raybaut",
      author_email = 'contact@pythonxy.com',
      url = 'http://code.google.com/p/%s/' % name,
      license = 'GPLv2',
      keywords = keywords,
      platforms = ['any'],
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
      **addl_args
    )
