# -*- coding: utf-8 -*-
"""
PyQtShell configuration management
"""

import os
import os.path as osp
from PyQt4.QtGui import QLabel, QIcon, QPixmap, QFont
from PyQt4.QtGui import QFontDatabase

DEFAULTS = [
            ('shell',
             {
              'window/size' : 'PyQt4.QtCore.QSize(700, 450)',
              'window/position' : 'PyQt4.QtCore.QPoint(30, 30)',
              'window/state' : 'PyQt4.QtCore.QByteArray("")',
              'font/family/nt' : ['Consolas', 'Courier New'],
              'font/family/posix' : 'Bitstream Vera Sans Mono',
              'font/family/mac' : 'Monaco',
              'font/size' : 10,
              'font/weight' : 50,
              'history/max_entries' : 30,
              'working_dir_history' : 10,
              'scintilla/wrap' : True,
              }),
            ]

from userconfig import UserConfig
CONF = UserConfig('PyQtShell', DEFAULTS, version='0.0.2')

def imagepath( name, default="not_found.png" ):
    """
    Return image absolute path
    """
    img_path = osp.join(osp.dirname(__file__), 'images')
    full_path = osp.join(img_path, name)
    if osp.isfile(full_path):
        return osp.abspath(full_path)
    return osp.abspath(osp.join(img_path, default))

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
    families = CONF.get('shell', 'font/family/'+os.name)
    if not isinstance(families, list):
        families = [ families ]
    family = None
    for family in families:
        if font_is_installed(family):
            break
    else:
        print "Warning: font '%s' is not installed\n" % family
    return QFont(family, 
                 CONF.get('shell', 'font/size'),
                 CONF.get('shell', 'font/weight'))
