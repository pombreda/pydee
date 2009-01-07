# -*- coding: utf-8 -*-
"""
PyQtShell configuration management
"""

import os
import os.path as osp
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont
from PyQt4.QtGui import QFontDatabase

APP_PATH = osp.dirname(__file__)
USER_PATH = osp.expanduser('~')
IMG_PATH = osp.join(APP_PATH,'images')

DEFAULTS = [
            ('Font',
             {
              'family/nt' : ['Consolas', 'Courier New'],
              'family/posix' : 'Bitstream Vera Sans Mono',
              'family/mac' : 'Monaco',
              'pointSize' : 10,
              'weight' : 50,
              }),
            ]

from userconfig import UserConfig
CONFIG = UserConfig('PyQtShell', DEFAULTS, load=False)

def imagepath( name, default="not_found.png" ):
    """
    Return image absolute path
    """
    full_path = osp.join(IMG_PATH, name)
    if osp.isfile( full_path ):
        return osp.abspath(full_path)
    return osp.abspath( osp.join(IMG_PATH, default ) )

def icon( name, default="not_found.png" ):
    """
    Return image inside a QIcon object
    """
    return QIcon(imagepath(name, default))

def imagelabel( name, default="not_found.png" ):
    """
    Return image inside a QLabel object
    """
    label = QLabel()
    label.setPixmap(QPixmap(imagepath(name, default)))
    return label

def font_is_installed(font):
    """
    Check if font is installed
    """
    return [fam for fam in QFontDatabase().families() if str(fam)==font]
    
def get_font():
    """
    Get console font properties depending on OS and user options
    """
    families = CONFIG.get('Font', 'family/'+os.name)
    if not isinstance(families, list):
        families = [ families ]
    family = None
    for family in families:
        if font_is_installed(family):
            break
    else:
        print "Warning: font '%s' is not installed\n" % family
    return QFont(family, 
                 CONFIG.get('Font', 'pointSize'),
                 CONFIG.get('Font', 'weight'))
