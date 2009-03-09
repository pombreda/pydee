# -*- coding: utf-8 -*-
"""
Environment variable utilities
"""

from PyQt4.QtGui import QDialog, QMessageBox, QApplication

import os

# Local imports
from dicteditor import DictEditorDialog
from qthelpers import translate

def envdict2listdict(envdict):
    """Dict --> Dict of lists"""
    for key in envdict:
        if ";" in envdict[key]:
            envdict[key] = [path.strip() for path in envdict[key].split(';')]
    return envdict

def listdict2envdict(listdict):
    """Dict of lists --> Dict"""
    for key in listdict:
        if isinstance(listdict[key], list):
            listdict[key] = ";".join(listdict[key])
    return listdict

class EnvDialog(DictEditorDialog):
    """Environment variables Dialog"""
    def __init__(self):
        super(EnvDialog, self).__init__(envdict2listdict( dict(os.environ) ),
                                        title="os.environ", width=600)
    def accept(self):
        """Reimplement Qt method"""
        os.environ = listdict2envdict( self.get_copy() )
        QDialog.accept(self)


try:
    #---- Windows platform
    from _winreg import OpenKey, EnumValue, QueryInfoKey, SetValueEx, QueryValueEx
    from _winreg import HKEY_CURRENT_USER, KEY_SET_VALUE

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
            _, types[name] = QueryValueEx(key, name)
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
            QDialog.accept(self)

except ImportError:
    #---- Other platforms
    pass

if __name__ == "__main__":
    qapp = QApplication([])
    dialog = WinUserEnvDialog()
    dialog.exec_()
