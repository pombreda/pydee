# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""
Text Editor Dialog based on PyQt4
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL, SLOT
from PyQt4.QtGui import QVBoxLayout, QTextEdit, QDialog, QDialogButtonBox

# Local import
from pydeelib.config import get_icon, get_font


class TextEditor(QDialog):
    """Array Editor Dialog"""
    def __init__(self, text, title='', font=None, parent=None):
        super(TextEditor, self).__init__(parent)
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Text edit
        self.edit = QTextEdit(parent)
        self.edit.setPlainText(text)
        if font is None:
            font = get_font('texteditor')
        self.edit.setFont(font)
        self.layout.addWidget(self.edit)

        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        self.layout.addWidget(bbox)
        
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        
        self.setWindowIcon(get_icon('edit.png'))
        self.setWindowTitle(self.tr("Text editor") + \
                            "%s" % (" - "+str(title) if str(title) else ""))
        self.resize(400, 300)
        
    def get_copy(self):
        """Return modified text"""
        return unicode(self.edit.toPlainText())
    
    
def main():
    """Text editor demo"""
    from PyQt4.QtGui import QApplication
    QApplication([])
    dialog = TextEditor("""
    01234567890123456789012345678901234567890123456789012345678901234567890123456789
    dedekdh elkd ezd ekjd lekdj elkdfjelfjk e
    """)
    if dialog.exec_():
        text = dialog.get_copy()
        print "Accepted:", text
        dialog = TextEditor(text)
        dialog.exec_()
    else:
        print "Canceled"

if __name__ == "__main__":
    main()