# -*- coding: utf-8 -*-
"""
PyQtShell configuration management
"""

import os, sys
import os.path as osp
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont, QFontDatabase

# Local import
from userconfig import UserConfig

APP_PATH = osp.dirname(__file__)

FILTERS = [int, long, float, list, dict, tuple, str, unicode]
try:
    from numpy import ndarray
    FILTERS.append(ndarray)
except ImportError:
    pass

EXCLUDED = ['nan', 'inf', 'infty', 'little_endian', 'colorbar_doc', 'e', 'pi',
            'sctypes', 'typecodes', 'rcParams', 'rcParamsDefault']

def type2str(types):
    """Convert types to strings"""
    return [typ.__name__ for typ in types]

def str2type(strings):
    """Convert strings to types"""
    return tuple( [eval(string) for string in strings] )

SANS_SERIF = ['Bitstream Vera Sans', 'Lucida Grande', 'Verdana', 'Geneva',
              'Lucid', 'Arial', 'Helvetica', 'Avant Garde', 'sans-serif']
SANS_SERIF.insert(0, unicode(QFont().family()))

MONOSPACE = ['Consolas', 'Courier New', 'Bitstream Vera Sans Mono',
             'Andale Mono', 'Monaco', 'Nimbus Mono L', 'Courier', 
             'Fixed', 'monospace', 'Terminal']
MEDIUM = 10
SMALL = 8

DEFAULTS = [
            ('window',
             {
              'size' : (1050, 550),
              'position' : (20, 20),
              'state' : '000000ff00000000fd0000000200000000000001b3000001befc0200000001fc00000043000001be000000c000080015fa000000000100000004fb000000180044006f0063005600690065007700650072005f006400770100000000ffffffff000001160007fffffb000000120045006400690074006f0072005f006400770100000000ffffffff000000e00007fffffb000000180057006f0072006b00730070006100630065005f006400770100000000ffffffff000000500007fffffb0000001a0048006900730074006f00720079004c006f0067005f00640077010000000000000100000000c80007ffff0000000300000426fffffffcfc0100000001fc00000238000002780000000000fffffffa000000000200000001fb00000010005300680065006c006c005f0064007701000001b40000016d00000000000000000000026f000001be00000004000000040000000800000008fc00000001000000020000000200000016004d00610069006e0054006f006f006c00620061007201000000000000014e00000000000000000000002a005200e90070006500720074006f0069007200650020006400650020007400720061007600610069006c010000014e000002d80000000000000000',
              'statusbar' : True,
              }),
            ('lightwindow',
             {
              'size' : (650, 400),
              'position' : (30, 30),
              }),
            ('shell',
             {
              'minimum_size' : (400, 300),
              'working_dir_history' : 10,
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'wrap' : True,
              'calltips' : True,
              'autocompletion' : True,
              'autocompletion/case-sensitivity' : True,
              'autocompletion/threshold' : -1,
              'autocompletion/select-single' : True,
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
              'minimum_size' : (400, 300),
              'enable' : True,
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'margin/font/family' : MONOSPACE,
              'margin/font/size' : SMALL,
              'margin/font/bold' : False,
              'wrap' : True,
              'api' : osp.join(APP_PATH, 'python.api'),
              }),
            ('history',
             {
              'minimum_size' : (400, 300),
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
              'minimum_size' : (400, 300),
              'enable' : True,
              'max_history_entries' : 20,
              'font/family' : MONOSPACE,
              'font/size' : MEDIUM,
              'font/bold' : False,
              'wrap' : True,
              }),
            ('workspace',
             {
              'minimum_size' : (400, 300),
              'enable' : True,
              'autorefresh' : True,
              'filters' : type2str(FILTERS),
              'autosave' : False,
              'excluded': EXCLUDED,
              'exclude_private': True,
              'exclude_upper': True,
              }),
            ('arrayeditor',
             {
              'font/family' : MONOSPACE,
              'font/size' : SMALL,
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
              'minimum_size' : (100, 100),
              'font/family' : SANS_SERIF,
              'font/size' : 11,
              'font/bold' : False,
              'statusbar/font/family' : SANS_SERIF,
              'statusbar/font/size' : 8,
              'statusbar/font/bold' : False,
              }),
            ]

DEV = not __file__.startswith(sys.prefix)
#DEV = False
CONF = UserConfig('PyQtShell', DEFAULTS, version='0.1.0', load=(not DEV))

def get_conf_path(filename):
    """Return absolute path for configuration file with specified filename"""
    conf_dir = osp.join(osp.expanduser('~'), '.PyQtShell')
    if not osp.isdir(conf_dir):
        os.mkdir(conf_dir)
    return osp.join(conf_dir, filename)

def get_image_path( name, default="not_found.png" ):
    """Return image absolute path"""
    img_path = osp.join(APP_PATH, 'images')
    full_path = osp.join(img_path, name)
    if osp.isfile(full_path):
        return osp.abspath(full_path)
    return osp.abspath(osp.join(img_path, default))

def get_icon( name, default="not_found.png" ):
    """Return image inside a QIcon object"""
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
    CONF.set(section, option+'/family/'+os.name, unicode(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/bold', int(font.bold()))