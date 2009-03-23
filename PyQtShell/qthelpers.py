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
#    PyQtShell is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PyQtShell; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Qt utilities"""

from PyQt4.QtGui import (QAction, QStyle, QWidget, QIcon, QApplication,
                         QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
                         QKeySequence)
from PyQt4.QtCore import SIGNAL, QVariant

# Local import
from config import get_icon

def translate(context, string):
    """Translation"""
    return QApplication.translate(context, string)

def keybinding(attr):
    """Return keybinding"""
    ks = getattr(QKeySequence, attr)
    return QKeySequence.keyBindings(ks)[0].toString()

def mimedata2url(source):
    """Extract url list from MIME data"""
    if source.hasUrls():
        paths = [unicode(url.toString()) for url in source.urls()]
        return [path[8:] for path in paths if path.startswith(r"file://") \
                and (path.endswith(".py") or path.endswith(".pyw"))]

def toggle_actions(actions, enable):
    """Enable/disable actions"""
    if actions is not None:
        for action in actions:
            if action is not None:
                action.setEnabled(enable)

def create_action(parent, text, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None, data=None):
    """Create a QAction"""
    action = QAction(text, parent)
    if triggered is not None:
        parent.connect(action, SIGNAL("triggered()"), triggered)
    if toggled is not None:
        parent.connect(action, SIGNAL("toggled(bool)"), toggled)
        action.setCheckable(True)
    if icon is not None:
        if isinstance(icon, (str, unicode)):
            icon = get_icon(icon)
        action.setIcon( icon )
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if data is not None:
        action.setData(QVariant(data))
    return action

def add_actions(target, actions):
    """Add actions to a menu"""
    previous_action = None
    for action in actions:
        if (action is None) and (previous_action is not None):
            target.addSeparator()
        else:
            target.addAction(action)
        previous_action = action

def get_std_icon(name, size=None):
    """Get standard platform icon
    Call 'show_std_icons()' for details"""
    if not name.startswith('SP_'):
        name = 'SP_'+name
    icon = QWidget().style().standardIcon( getattr(QStyle, name) )
    if size is None:
        return icon
    else:
        return QIcon( icon.pixmap(size, size) )

class ShowStdIcons(QWidget):
    """
    Dialog showing standard icons
    """
    def __init__(self, parent):
        super(ShowStdIcons, self).__init__(parent)
        layout = QHBoxLayout()
        row_nb = 14
        cindex = 0
        for child in dir(QStyle):
            if child.startswith('SP_'):
                if cindex == 0:
                    col_layout = QVBoxLayout()
                icon_layout = QHBoxLayout()
                icon = get_std_icon(child)
                label = QLabel()
                label.setPixmap(icon.pixmap(32, 32))
                icon_layout.addWidget( label )
                icon_layout.addWidget( QLineEdit(child.replace('SP_', '')) )
                col_layout.addLayout(icon_layout)
                cindex = (cindex+1) % row_nb
                if cindex == 0:
                    layout.addLayout(col_layout)                    
        self.setLayout(layout)
        self.setWindowTitle('Standard Platform Icons')
        self.setWindowIcon(get_std_icon('TitleBarMenuButton'))

def show_std_icons():
    """
    Show all standard Icons
    """
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication(sys.argv)
    dialog = ShowStdIcons(None)
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    show_std_icons()