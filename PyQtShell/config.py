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

"""
PyQtShell configuration management
"""

import os, sys
import os.path as osp
from datetime import date
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont, QFontDatabase

# Local import
from userconfig import UserConfig

APP_PATH = osp.dirname(__file__)

FILTERS = [int, long, float, list, dict, tuple, str, unicode, date]
try:
    from numpy import ndarray
    FILTERS.append(ndarray)
except ImportError:
    pass

EXCLUDED = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc', 'e', 'pi',
            'typecodes']
# The following exhaustive list is no longer necessary since v0.3.27 and the
# improvements on Worskpace filter function:
# (to be removed)
#EXCLUDED = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc', 'e', 'pi',
#            'sctypes', 'typecodes', 'rcParams', 'rcParamsDefault',
#            'typeNA', 'nbytes', 'sctypeDict', 'sctypeNA', 'cast', 'typeDict']

def type2str(types):
    """Convert types to strings"""
    return [typ.__name__ for typ in types]

def str2type(strings):
    """Convert strings to types"""
    return tuple( [eval(string) for string in strings] )

SANS_SERIF = ['Bitstream Vera Sans', 'Bitstream Charter', 'Lucida Grande',
              'Verdana', 'Geneva', 'Lucid', 'Arial', 'Helvetica',
              'Avant Garde', 'sans-serif']
SANS_SERIF.insert(0, unicode(QFont().family()))

MONOSPACE = ['Consolas', 'Courier New', 'Bitstream Vera Sans Mono',
             'Andale Mono', 'Monaco', 'Nimbus Mono L', 'Courier', 
             'Fixed', 'monospace', 'Terminal']
MEDIUM = 9
SMALL = 8

try:
    from matplotlib import rcParams
    width, height = rcParams['figure.figsize']
    dpi = rcParams['figure.dpi']
    MPL_SIZE = (width*dpi, height*dpi)
except ImportError:
    MPL_SIZE = (400, 300)

DEFAULTS = [
            ('window',
             {
              'size' : (1050, 550),
              'position' : (20, 20),
              'state' : '000000ff00000000fd0000000200000000000001c9000001dcfc0200000001fc00000037000001dc0000009a00080015fa000000000100000004fb000000180044006f0063005600690065007700650072005f006400770100000000ffffffff0000012c0007fffffb000000180057006f0072006b00730070006100630065005f006400770100000000ffffffff000000500007fffffb000000120045006400690074006f0072005f00640077010000000000000184000000ad0007fffffb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770100000000ffffffff0000000000000000000000010000024d000001dcfc0200000002fb00000016004500780070006c006f007200650072005f00640077010000003700000083000000560007fffffc000000be000001550000007c00080015fa000000000100000002fb000000140043006f006e0073006f006c0065005f006400770100000000ffffffff000000500007fffffb0000001a0048006900730074006f00720079004c006f0067005f0064007701000001ed000001e9000000500007ffff00000000000001dc00000004000000040000000800000008fc00000001000000020000000200000016004d00610069006e0054006f006f006c00620061007201000000000000017700000000000000000000002a005200e90070006500720074006f0069007200650020006400650020007400720061007600610069006c0100000177000002a30000000000000000',
              'statusbar' : True,
              }),
            ('lightwindow',
             {
              'size' : (650, 400),
              'position' : (30, 30),
              }),
            ('scintilla',
             {
              'margins/backgroundcolor' : '#DADADA',
              'margins/foregroundcolor' : 'white',
              'foldmarginpattern/backgroundcolor' : '#ECECFF',
              'foldmarginpattern/foregroundcolor' : '#ECECFF',
              }),
            ('shell',
             {
              'working_dir_history' : 10,
              'working_dir_adjusttocontents' : False,
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'wrap' : True,
              'wrapflag' : True,
              'calltips' : True,
              'autocompletion' : True,
              'autocompletion/case-sensitivity' : True,
              'autocompletion/threshold' : -1,
              'autocompletion/select-single' : True,
              'autocompletion/from-document' : False,
              'external_editor' : 'SciTE',
              'external_editor/gotoline' : '-goto:',
              }),
            ('calltips',
             {
              'font/family' : MONOSPACE,
              'font/size' : SMALL,
              'font/bold' : False,
              'size' : 600,
              }),
            ('editor',
             {
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'margin/font/family' : MONOSPACE,
              'margin/font/size' : SMALL,
              'margin/font/bold' : False,
              'wrap' : False,
              'wrapflag' : True,
              'api' : osp.join(APP_PATH, 'python.api'),
              'valid_filetypes': ('', '.py', '.pyw', '.txt', '.patch',
                                  '.diff', '.rej', '.css', '.htm', '.html',
                                  '.c', '.cpp', '.h', '.properties',
                                  '.session', '.ini', '.inf', '.reg', '.cfg'),
              }),
            ('historylog',
             {
              'enable' : True,
              'max_entries' : 100,
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'margin/font/family' : MONOSPACE,
              'margin/font/size' : SMALL,
              'margin/font/bold' : True,
              'wrap' : True,
              }),
            ('docviewer',
             {
              'enable' : True,
              'max_history_entries' : 20,
              'font/family' : MONOSPACE,
              'font/size' : SMALL,
              'font/bold' : False,
              'wrap' : True,
              }),
            ('workspace',
             {
              'enable' : True,
              'autorefresh' : True,
              'filters' : type2str(FILTERS),
              'autosave' : False,
              'excluded': EXCLUDED,
              'exclude_private': True,
              'exclude_upper': True,
              'exclude_unsupported_datatypes': True,
              }),
            ('arrayeditor',
             {
              'font/family' : MONOSPACE,
              'font/size' : SMALL,
              'font/bold' : False,
              }),
            ('texteditor',
             {
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              }),
            ('dicteditor',
             {
              'font/family' : MONOSPACE,
              'font/size' : SMALL,
              'font/bold' : False,
              }),
            ('figure',
             {
              'size' : MPL_SIZE,
              'font/size' : MEDIUM,
              'statusbar/font/family' : SANS_SERIF,
              'statusbar/font/size' : SMALL,
              'statusbar/font/bold' : False,
              }),
            ('explorer',
             {
              'enable': True,
              'wrap': True,
              'valid_filetypes': ('', '.py', '.pyw', '.ws',
                                  '.txt', '.csv', '.mat', '.h5'),
              'show_hidden_files': True,
              'show_all_files': True,
              }),
            ]

DEV = not __file__.startswith(sys.prefix)
#DEV = False
CONF = UserConfig('PyQtShell', DEFAULTS, version='0.3.0', load=(not DEV))

def get_conf_path(filename):
    """Return absolute path for configuration file with specified filename"""
    conf_dir = osp.join(osp.expanduser('~'), '.PyQtShell')
    if not osp.isdir(conf_dir):
        os.mkdir(conf_dir)
    return osp.join(conf_dir, filename)

IMG_PATH_ROOT = osp.join(APP_PATH, 'images')
IMG_PATH = [IMG_PATH_ROOT]
for root, dirs, files in os.walk(IMG_PATH_ROOT):
    for dir in dirs:
        IMG_PATH.append(osp.join(IMG_PATH_ROOT, dir))

def get_image_path( name, default="not_found.png" ):
    """Return image absolute path"""
    for img_path in IMG_PATH:
        full_path = osp.join(img_path, name)
        if osp.isfile(full_path):
            return osp.abspath(full_path)
    if default is not None:
        return osp.abspath(osp.join(img_path, default))

def get_icon( name, default=None ):
    """Return image inside a QIcon object"""
    if default is None:
        return QIcon(get_image_path(name))
    elif isinstance(default, QIcon):
        icon_path = get_image_path(name, default=None)
        return default if icon_path is None else QIcon(icon_path)
    else:
        return QIcon(get_image_path(name, default))

def get_image_label( name, default="not_found.png" ):
    """Return image inside a QLabel object"""
    label = QLabel()
    label.setPixmap(QPixmap(get_image_path(name, default)))
    return label

def font_is_installed(font):
    """Check if font is installed"""
    return [fam for fam in QFontDatabase().families() if unicode(fam)==font]
    
def get_family(families):
    """Return the first installed font family in family list"""
    if not isinstance(families, list):
        families = [ families ]
    for family in families:
        if font_is_installed(family):
            return family
    else:
        print "Warning: None of the following fonts is installed: %r" % families
        return QFont()
    
def get_font(section, option=None):
    """Get console font properties depending on OS and user options"""
    if option is None:
        option = 'font'
    else:
        option += '/font'
    family = get_family( CONF.get(section, option+"/family") )
    weight = QFont.Normal
    if CONF.get(section, option+'/bold'):
        weight = QFont.Bold
    size = CONF.get(section, option+'/size')
    return QFont(family, size, weight)

def set_font(font, section, option=None):
    """Set font"""
    if option is None:
        option = 'font'
    else:
        option += '/font'
    CONF.set(section, option+'/family', unicode(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/bold', int(font.bold()))