# -*- coding: utf-8 -*-
#
#    Copyright © 2009 Pierre Raybaut
#
#    This file is part of Pydee.
#
#    Pydee is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    Pydee is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Pydee; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Customized combobox widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QComboBox, QFont, QToolTip, QSizePolicy
from PyQt4.QtCore import SIGNAL, Qt

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.config import CONF


class EditableComboBox(QComboBox):
    """
    Editable QComboBox
    """
    def __init__(self, parent):
        super(EditableComboBox, self).__init__(parent)
        self.font = QFont()
        self.setEditable(True)
        self.connect(self, SIGNAL("editTextChanged(QString)"), self.validate)
        self.set_default_style()
        self.tips = {True: self.tr("Press enter to validate this entry"),
                     False: self.tr('This entry is incorrect')}
        
    def show_tip(self, tip=""):
        """Show tip"""
        QToolTip.showText(self.mapToGlobal(self.pos()), tip, self)
        
    def set_default_style(self):
        """Set widget style to default"""
        self.font.setBold(False)
        self.setFont(self.font)
        self.setStyleSheet("")
        self.show_tip()
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        raise NotImplementedError
        
    def validate(self, qstr):
        """Validate entered path"""
        if self.hasFocus():
            self.font.setBold(True)
            self.setFont(self.font)
            valid = self.is_valid(qstr)
            if valid:
                self.setStyleSheet("color:rgb(50, 155, 50);")
            else:
                self.setStyleSheet("color:rgb(200, 50, 50);")
            self.show_tip(self.tips[valid])
        else:
            self.set_default_style()


class PathComboBox(EditableComboBox):
    """
    QComboBox handling path locations
    """
    def __init__(self, parent):
        super(PathComboBox, self).__init__(parent)
        if CONF.get('shell', 'working_dir_adjusttocontents', False):
            self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr("Press enter to validate this path"),
                     False: self.tr('This path is incorrect.\n'
                                    'Enter a correct directory path.\n'
                                    'Then press enter to validate')}
        
    def is_valid(self, qstr):
        """Return True if string is valid"""
        return osp.isdir( unicode(qstr) )

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            directory = unicode(self.currentText())
            if osp.isdir( directory ):
                self.emit(SIGNAL("open_dir(QString)"), directory)
                self.set_default_style()
                if hasattr(self.parent(), 'main'):
                    if self.parent().main is not None:
                        self.parent().main.console.shell.setFocus()
        else:
            QComboBox.keyPressEvent(self, event)
