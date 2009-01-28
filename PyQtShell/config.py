# -*- coding: utf-8 -*-
"""
PyQtShell configuration management
"""

import os
import os.path as osp
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont
from PyQt4.QtGui import QFontDatabase

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

DEFAULTS = [
            ('window',
             {
              'size' : (1000, 500),
              'position' : (30, 30),
              'state' : '000000ff00000000fd00000002000000000000017c0000019efc0200000001fc000000430000019e000000bc00080015fa000000000100000004fb000000180044006f0063005600690065007700650072005f006400770100000000ffffffff000000e00007fffffb000000120045006400690074006f0072005f006400770100000000ffffffff000000c80007fffffb0000001a0048006900730074006f00720079004c006f0067005f006400770100000000ffffffff000000c80007fffffb000000180057006f0072006b00730070006100630065005f0064007701000000000000017c000000500007ffff00000003000003e8fffffffcfc0100000001fb000000260057006f0072006b0069006e0067004400690072006500630074006f00720079005f0064007703000002440000019c000002bc00000000000002680000019e00000004000000040000000800000008fc00000003000000020000000200000016004d00610069006e0054006f006f006c0062006100720100000000000000d700000000000000000000002a005200e90070006500720074006f0069007200650020006400650020007400720061007600610069006c01000000d700000311000000000000000000000003000000000000000300000000',
              'statusbar' : True,
              }),
            ('lightwindow',
             {
              'size' : (650, 400),
              'position' : (30, 30),
              }),
            ('shell',
             {
              'working_dir_history' : 10,
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 10,
              'font/bold' : False,
              'wrap' : True,
              'autocompletion' : True,
              'autocompletion/case-sensitivity' : True,
              'autocompletion/threshold' : -1,
              'autocompletion/select-single' : True,
              'external_editor' : 'SciTE',
              }),
            ('editor',
             {
              'enable' : True,
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 9,
              'font/bold' : True,
              'margin/font/family/nt' : ['Consolas', 'Courier New'],
              'margin/font/family/posix' : 'Bitstream Vera Sans Mono',
              'margin/font/family/mac' : 'Monaco',
              'margin/font/size' : 8,
              'margin/font/bold' : True,
              'wrap' : True,
              'api' : osp.join(APP_PATH, 'python.api'),
              }),
            ('history',
             {
              'enable' : True,
              'max_entries' : 100,
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 9,
              'font/bold' : True,
              'margin/font/family/nt' : ['Consolas', 'Courier New'],
              'margin/font/family/posix' : 'Bitstream Vera Sans Mono',
              'margin/font/family/mac' : 'Monaco',
              'margin/font/size' : 8,
              'margin/font/bold' : True,
              'wrap' : True,
              }),
            ('docviewer',
             {
              'enable' : True,
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 9,
              'font/bold' : True,
              'wrap' : True,
              }),
            ('workspace',
             {
              'enable' : True,
              'filters' : type2str(FILTERS),
              'autosave' : False,
              'excluded': EXCLUDED,
              'exclude_private': True,
              'exclude_upper': True,
              }),
            ('arrayeditor',
             {
              'font/family/nt' : 'Courier New',
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 9,
              'font/bold' : False,
              }),
            ('dicteditor',
             {
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 8,
              'font/bold' : True,
              }),
            ]

DEV = osp.isfile(osp.join(osp.join(APP_PATH, osp.pardir), 'setup.py'))
DEV = False
from userconfig import UserConfig
CONF = UserConfig('PyQtShell', DEFAULTS, version='0.0.10', load=(not DEV))

def get_conf_path(filename):
    """
    Return absolute path for configuration file with specified filename
    """
    conf_dir = osp.join(osp.expanduser('~'), '.PyQtShell')
    if not osp.isdir(conf_dir):
        os.mkdir(conf_dir)
    return osp.join(conf_dir, filename)

def get_image_path( name, default="not_found.png" ):
    """
    Return image absolute path
    """
    img_path = osp.join(APP_PATH, 'images')
    full_path = osp.join(img_path, name)
    if osp.isfile(full_path):
        return osp.abspath(full_path)
    return osp.abspath(osp.join(img_path, default))

def get_icon( name, default="not_found.png" ):
    """
    Return image inside a QIcon object
    """
    return QIcon(get_image_path(name, default))

def get_image_label( name, default="not_found.png" ):
    """
    Return image inside a QLabel object
    """
    label = QLabel()
    label.setPixmap(QPixmap(get_image_path(name, default)))
    return label

def font_is_installed(font):
    """
    Check if font is installed
    """
    return [fam for fam in QFontDatabase().families() if str(fam)==font]
    
def get_font(section, option=None):
    """
    Get console font properties depending on OS and user options
    """
    if option is None:
        option = 'font'
    else:
        option += '/font'
    families = CONF.get(section, option+'/family/'+os.name)
    if not isinstance(families, list):
        families = [ families ]
    family = None
    for family in families:
        if font_is_installed(family):
            break
    else:
        print "Warning: font '%s' is not installed\n" % family
    weight = QFont.Normal
    if CONF.get(section, option+'/bold'):
        weight = QFont.Bold
    return QFont(family, CONF.get(section, option+'/size'), weight)

def set_font(font, section, option=None):
    """
    Set font
    """
    if option is None:
        option = 'font'
    else:
        option += '/font'
    CONF.set(section, option+'/family/'+os.name, str(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/bold', int(font.bold()))