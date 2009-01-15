# -*- coding: utf-8 -*-
"""
PyQtShell configuration management
"""

import os
import os.path as osp
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont
from PyQt4.QtGui import QFontDatabase

APP_PATH = osp.dirname(__file__)
DEFAULTS = [
            ('shell',
             {
              'window/size' : (750, 450),
              'window/position' : (30, 30),
              'window/state' : '000000ff00000000fd00000002000000010000010000000146fc0200000001fb000000120045006400690074006f0072005f00640077010000003700000146000000ac0007ffff00000003000002ee00000041fc0100000001fb000000260057006f0072006b0069006e0067004400690072006500630074006f00720079005f006400770100000000000002ee000001bb0007ffff000001ea0000014600000004000000040000000800000008fc00000001000000020000000100000016004d00610069006e0054006f006f006c0062006100720100000000000002ee0000000000000000',
              'history/max_entries' : 30,
              'working_dir_history' : 10,
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 10,
              'font/weight' : 50,
              'wrap' : True,
              }),
            ('editor',
             {
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 10,
              'font/weight' : 50,
              'wrap' : True,
              }),
            ('arrayeditor',
             {
              'font/family/nt' : 'Courier New',
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 9,
              'font/weight' : 50,
              }),
            ]

dev_mode = osp.isfile(osp.join(osp.join(osp.join(APP_PATH, osp.pardir), osp.pardir), 'setup.py'))
#dev_mode = False
from userconfig import UserConfig
CONF = UserConfig('PyQtShell', DEFAULTS, version='0.0.2', load=(not dev_mode))

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
    
def get_font(section):
    """
    Get console font properties depending on OS and user options
    """
    families = CONF.get(section, 'font/family/'+os.name)
    if not isinstance(families, list):
        families = [ families ]
    family = None
    for family in families:
        if font_is_installed(family):
            break
    else:
        print "Warning: font '%s' is not installed\n" % family
    return QFont(family, 
                 CONF.get(section, 'font/size'),
                 CONF.get(section, 'font/weight'))
