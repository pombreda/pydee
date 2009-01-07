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

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '0.0.1'

setup(
      name = 'PyQtShell',
      version = version,
      description = 'Interactive Python shell and related widgets based on PyQt4',
      author = "Pierre Raybaut",
      author_email = 'contact@pythonxy.com',
      url = 'http://code.google.com/p/pyqtshell/',
      license = 'GPLv3',
      keywords = 'PyQt4 shell console widgets',
      platforms = ['any'],
      packages = ['PyQt4.QtShell'],
      package_data={'PyQt4.QtShell': ['images/*.png']},
      classifiers = ['Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Intended Audience :: Science/Research',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.5',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Widget Sets',
        ],
    )
