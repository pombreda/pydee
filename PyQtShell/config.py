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
              'size' : (1200, 650),
              'position' : (30, 30),
              'state' : '000000ff00000000fd00000001000000030000049500000247fc0100000002fc0000000000000227000001170007fffffa000000000200000003fb000000120045006400690074006f0072005f006400770100000000ffffffff000000aa0007fffffb000000180044006f0063005600690065007700650072005f006400770100000000ffffffff000000a60007fffffb000000180057006f0072006b00730070006100630065005f0064007701000001b40000016d000000540007fffffc0000022b0000026a000000c80007fffffa000000010200000002fb0000001a0048006900730074006f00720079004c006f0067005f006400770100000000ffffffff0000007a0007fffffb00000010005300680065006c006c005f0064007701000001b40000016d000000540007ffff000004950000000000000004000000040000000800000008fc00000001000000020000000200000016004d00610069006e0054006f006f006c00620061007201000000000000014e00000000000000000000002a005200e90070006500720074006f0069007200650020006400650020007400720061007600610069006c010000014e000003470000000000000000',
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
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 8,
              'font/bold' : False,
              'size' : 600,
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
              'margin/font/bold' : False,
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
              'max_history_entries' : 20,
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
              'autorefresh' : True,
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
#DEV = False
from userconfig import UserConfig
CONF = UserConfig('PyQtShell', DEFAULTS, version='0.0.19', load=(not DEV))

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