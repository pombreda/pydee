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
#    Foobar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Foobar; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
Environment variable utilities
"""

from PyQt4.QtGui import QDialog, QMessageBox, QApplication

import os

# Local imports
from PyQtShell.widgets.dicteditor import DictEditorDialog
from PyQtShell.qthelpers import translate

def envdict2listdict(envdict):
    """Dict --> Dict of lists"""
    for key in envdict:
        if os.path.pathsep in envdict[key]:
            envdict[key] = [path.strip() for path in envdict[key].split(';')]
    return envdict

def listdict2envdict(listdict):
    """Dict of lists --> Dict"""
    for key in listdict:
        if isinstance(listdict[key], list):
            listdict[key] = os.path.pathsep.join(listdict[key])
    return listdict

class EnvDialog(DictEditorDialog):
    """Environment variables Dialog"""
    def __init__(self):
        super(EnvDialog, self).__init__(envdict2listdict( dict(os.environ) ),
                                        title="os.environ", width=600,
                                        icon='environ.png')
    def accept(self):
        """Reimplement Qt method"""
        os.environ = listdict2envdict( self.get_copy() )
        QDialog.accept(self)


try:
    #---- Windows platform
    from _winreg import OpenKey, EnumValue, QueryInfoKey, SetValueEx, QueryValueEx
    from _winreg import HKEY_CURRENT_USER, KEY_SET_VALUE, REG_EXPAND_SZ

    def get_user_env():
        """Return HKCU (current user) environment variables"""
        reg = dict()
        key = OpenKey(HKEY_CURRENT_USER, "Environment")
        for index in range(0, QueryInfoKey(key)[1]):
            try:
                value = EnumValue(key, index)
                reg[value[0]] = value[1]
            except:
                break
        return envdict2listdict(reg)
    
    def set_user_env(reg):
        """Set HKCU (current user) environment variables"""
        reg = listdict2envdict(reg)
        types = dict()
        key = OpenKey(HKEY_CURRENT_USER, "Environment")
        for name in reg:
            try:
                _, types[name] = QueryValueEx(key, name)
            except WindowsError:
                types[name] = REG_EXPAND_SZ
        key = OpenKey(HKEY_CURRENT_USER, "Environment", 0, KEY_SET_VALUE)
        for name in reg:
            SetValueEx(key, name, 0, types[name], reg[name])
            
    class WinUserEnvDialog(DictEditorDialog):
        """Windows User Environment Variables Editor"""
        def __init__(self, parent=None):
            super(WinUserEnvDialog, self).__init__(get_user_env(),
               title="HKEY_CURRENT_USER\Environment", width=600)
            if parent is None:
                parent = self
            QMessageBox.warning(parent, translate("WinUserEnvDialog", "Warning"),
                translate("WinUserEnvDialog", "If you accept changes, this will modify the current user environment variables (in Windows registry). Use it with precautions, at your own risks."))
            
        def accept(self):
            """Reimplement Qt method"""
            set_user_env( listdict2envdict(self.get_copy()) )
            try:
                from win32gui import SendMessageTimeout
                from win32con import (HWND_BROADCAST, WM_SETTINGCHANGE,
                                      SMTO_ABORTIFHUNG)
                SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                                   "Environment", SMTO_ABORTIFHUNG, 5000)
            except ImportError:
                QMessageBox.warning(self, translate("WinUserEnvDialog", "Warning"),
                    translate("WinUserEnvDialog",
                              "Module pywin32 was not found: restart session to take these changes into account."))
            QDialog.accept(self)

except ImportError:
    #---- Other platforms
    pass

if __name__ == "__main__":
    qapp = QApplication([])
    dialog = WinUserEnvDialog()
    dialog.exec_()
