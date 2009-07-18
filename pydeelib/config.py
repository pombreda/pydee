# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
Pydee configuration management
"""

import os, sys
import os.path as osp
from datetime import date
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont, QFontDatabase

# Local import
from userconfig import UserConfig, get_home_dir

APP_PATH = osp.dirname(__file__)

FILTERS = [int, long, float, list, dict, tuple, str, unicode, date]
try:
    from numpy import ndarray
    FILTERS.append(ndarray)
except ImportError:
    pass

# Max number of filter iterations for worskpace display:
# (for workspace saving, itermax == -1, see Workspace.save)
ITERMAX = -1 #XXX: To be adjusted if it takes too much to compute... 2, 3?

EXCLUDED = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc', 'e', 'pi',
            'typecodes', '__builtins__', '__main__', '__doc__']
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
            ('main',
             {
              'translation': True,
              }),
            ('window',
             {
              'size' : (1260, 700),
              'is_maximized' : False,
              'position' : (10, 10),
              'state' : '000000ff00000000fd0000000200000000000002b400000272fc0200000006fc0000003700000272000000b600080015fa000000000100000003fb000000120045006400690074006f0072005f00640077010000000000000184000000e90007fffffb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000000ffffffff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000000ffffffff0000000000000000fc0000015b000000b80000000000fffffffa000000000200000002fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f00640077020000030a00000111000001d70000019dfb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000000ffffffff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff0000000000000000fb00000026004d006100740070006c006f0074006c00690062004600690067007500720065005f006400770000000114000000ff0000000000000000000000010000023400000272fc0200000002fc0000003700000120000000e000080015fa000000000100000004fb000000180044006f0063005600690065007700650072005f006400770100000000ffffffff000001310007fffffb000000180057006f0072006b00730070006100630065005f006400770100000000ffffffff000000500007fffffb00000016004500780070006c006f007200650072005f006400770100000000ffffffff000001970007fffffb0000001c00460069006e00640049006e00460069006c00650073005f006400770100000000ffffffff000001ca0007fffffc0000015b0000014e0000007c00080015fa000000010100000004fb0000002400450078007400650072006e0061006c0043006f006e0073006f006c0065005f006400770100000000ffffffff000000a80007fffffb000000140043006f006e0073006f006c0065005f006400770100000000ffffffff000000500007fffffb0000001a0048006900730074006f00720079004c006f0067005f006400770100000000ffffffff000000500007fffffb0000001c00530061006600650043006f006e0073006f006c0065005f006400770100000000ffffffff0000000000000000000000000000027200000004000000040000000800000008fc00000001000000020000000200000016004d00610069006e0054006f006f006c00620061007201000000000000023d00000000000000000000002a005200e90070006500720074006f0069007200650020006400650020007400720061007600610069006c010000023d000002af0000000000000000',
              }),
            ('lightwindow',
             {
              'size' : (650, 400),
              'position' : (30, 30),
              }),
            ('scintilla',
             {
              'margins/backgroundcolor' : 'white',
              'margins/foregroundcolor' : 'darkGray',
              'foldmarginpattern/backgroundcolor' : 0xEEEEEE,
              'foldmarginpattern/foregroundcolor' : 0xEEEEEE,
              'default_style/foregroundcolor' : 0x000000,
              'default_style/backgroundcolor' : 0xFFFFFF,
              'default_style/bold' : False,
              'default_style/italic' : False,
              'default_style/underline' : False,
              'error_style/foregroundcolor' : 0x0000FF,
              'error_style/backgroundcolor' : 0xFFFFFF,
              'error_style/bold' : False,
              'error_style/italic' : False,
              'error_style/underline' : False,
              'traceback_link_style/foregroundcolor' : 0xFF0000,
              'traceback_link_style/backgroundcolor' : 0xFFFFFF,
              'traceback_link_style/bold' : True,
              'traceback_link_style/italic' : False,
              'traceback_link_style/underline' : True,
              'prompt_style/foregroundcolor' : 0x00AA00,
              'prompt_style/backgroundcolor' : 0xFFFFFF,
              'prompt_style/bold' : True,
              'prompt_style/italic' : False,
              'prompt_style/underline' : False,
              }),
            ('shell',
             {
              'shortcut': "Ctrl+Shift+C",
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
            ('external_shell',
             {
              'shortcut': "Ctrl+Shift+X",
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'wrap' : True,
              'single_tab' : True,
              'autocompletion' : True,
              'autocompletion/case-sensitivity' : True,
              'autocompletion/threshold' : -1,
              'autocompletion/select-single' : True,
              'autocompletion/from-document' : False,
              'filters' : type2str(FILTERS),
              'itermax' : ITERMAX,
              'excluded_names': EXCLUDED,
              'exclude_private': True,
              'exclude_upper': True,
              'exclude_unsupported': True,
              'inplace': False,
              'truncate': True,
              'minmax': True,
              'collvalue': False,
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
              'shortcut': "Ctrl+Shift+E",
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'margin/font/family' : MONOSPACE,
              'margin/font/size' : MEDIUM,
              'margin/font/bold' : False,
              'wrap' : False,
              'wrapflag' : True,
              'code_analysis' : True,
              'class_browser' : True,
              'code_folding' : True,
              'api' : osp.join(APP_PATH, 'python.api'),
              'valid_filetypes': ['', '.py', '.pyw', '.txt', '.patch',
                                  '.diff', '.rej', '.css', '.htm', '.html',
                                  '.c', '.cpp', '.h', '.properties',
                                  '.session', '.ini', '.inf', '.reg', '.cfg'],
              }),
            ('historylog',
             {
              'shortcut': "Ctrl+Shift+H",
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
              'shortcut': "Ctrl+Shift+D",
              'enable' : True,
              'max_history_entries' : 20,
              'font/family' : MONOSPACE,
              'font/size' : SMALL,
              'font/bold' : False,
              'wrap' : True,
              }),
            ('workspace',
             {
              'shortcut': "Ctrl+Shift+W",
              'enable' : True,
              'autorefresh' : True,
              'filters' : type2str(FILTERS),
              'itermax' : ITERMAX,
              'autosave' : False,
              'excluded_names': EXCLUDED,
              'exclude_private': True,
              'exclude_upper': True,
              'exclude_unsupported': True,
              'inplace': False,
              'truncate': True,
              'minmax': True,
              'collvalue': False,
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
              'shortcut': "Ctrl+Shift+F",
              'enable': True,
              'wrap': True,
              'include': '.',
              'exclude': r'\.pyc$|^\.',
              'valid_filetypes': ['', '.py', '.pyw', '.ws',
                                  '.txt', '.csv', '.mat', '.h5'],
              'show_hidden': True,
              'show_all': False,
              'show_toolbar': True,
              'show_icontext': True,
              }),
            ('find_in_files',
             {
              'enable': True,
              'supported_encodings': ["utf-8", "iso-8859-1", "cp1252"],
              'include': ['.', r'\.pyw?$|\.txt$|\.c$|\.cpp$|\.h$|\.f$|\.ini$'],
              'include_regexp': True,
              'exclude': [r'\.pyc$|\.orig$|\.hg|\.svn'],
              'exclude_regexp': True,
              'search_text_regexp': True,
              'search_text': [''],
              'search_text_samples': [r'# ?TODO|# ?FIXME|# ?XXX'],
              }),
            ]

DEV = not __file__.startswith(sys.prefix)
DEV = False
CONF = UserConfig('pydee', DEFAULTS, version='0.4.22', load=(not DEV))

def get_conf_path(filename):
    """Return absolute path for configuration file with specified filename"""
    conf_dir = osp.join(get_home_dir(), '.pydee')
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
    
FONT_CACHE = {}
def get_font(section, option=None):
    """Get console font properties depending on OS and user options"""
    font = FONT_CACHE.get((section, option))
    if font is None:
        if option is None:
            option = 'font'
        else:
            option += '/font'
        families = CONF.get(section, option+"/family", None)
        if families is None:
            return QFont()
        family = get_family( families )
        weight = QFont.Normal
        if CONF.get(section, option+'/bold'):
            weight = QFont.Bold
        size = CONF.get(section, option+'/size')
        font = QFont(family, size, weight)
        FONT_CACHE[(section, option)] = font
    return font

def set_font(font, section, option=None):
    """Set font"""
    if option is None:
        option = 'font'
    else:
        option += '/font'
    CONF.set(section, option+'/family', unicode(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/bold', int(font.bold()))
    FONT_CACHE[(section, option)] = font
    