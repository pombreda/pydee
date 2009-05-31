# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Files and Directories Explorer"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QDialog, QListWidget, QListWidgetItem, QVBoxLayout,
                         QLabel, QHBoxLayout, QDrag, QApplication, QMessageBox,
                         QInputDialog, QLineEdit, QMenu, QWidget, QToolButton)
from PyQt4.QtCore import Qt, SIGNAL, QMimeData

import os, sys
import os.path as osp
from sets import Set

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.qthelpers import (get_std_icon, translate, add_actions,
                                 create_action, get_filetype_icon,
                                 create_toolbutton)
from pydeelib.config import get_icon



def listdir(path, valid_types=('', '.py', '.pyw'),
            show_hidden=False, show_all=False):
    """List files and directories"""
    namelist = []
    dirlist = [osp.pardir]
    for item in os.listdir(path):
        if osp.isdir(osp.join(path, item)):
            dirlist.append(item)
        elif (show_all or (osp.splitext(item)[1] in valid_types)) and \
             (show_hidden or not item.startswith('.')):
            namelist.append(item)
    return sorted(dirlist) + sorted(namelist)



class ExplorerListWidget(QListWidget):
    """File and Directories Explorer Widget
    get_filetype_icon(fname): fn which returns a QIcon for file extension"""
    def __init__(self, parent=None, path=None, valid_types=('', '.py', '.pyw'),
                 show_hidden=False, show_all=False, wrap=True):
        QListWidget.__init__(self, parent)
        
        self.valid_types = valid_types
        self.show_hidden = show_hidden
        self.show_all = show_all
        self.wrap = wrap
        
        self.path = None
        self.itemdict = None
        self.nameset = None
        self.refresh(path)
        
#        self.setFlow(QListWidget.LeftToRight)
#        self.setUniformItemSizes(True)
#        self.setViewMode(QListWidget.IconMode)
        
        # Enable drag events
        self.setDragEnabled(True)
        
        # Setup context menu
        self.menu = QMenu(self)
        self.common_actions = self.setup_common_actions()
        
        
    #---- Context menu
    def setup_common_actions(self):
        """Setup context menu common actions"""
        # Wrap
        wrap_action = create_action(self,
                                    translate('Explorer', "Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked(self.wrap)
        self.toggle_wrap_mode(self.wrap)
        # Show hidden files
        hidden_action = create_action(self,
                                  translate('Explorer', "Show hidden files"),
                                  toggled=self.toggle_hidden)
        hidden_action.setChecked(self.show_hidden)
        self.toggle_hidden(self.show_hidden)
        # Show all files
        all_action = create_action(self,
                                   translate('Explorer', "Show all files"),
                                   toggled=self.toggle_all)
        all_action.setChecked(self.show_all)
        self.toggle_all(self.show_all)
        
        return [wrap_action, hidden_action, all_action]
        
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.parent().emit(SIGNAL('option_changed'), 'wrap', checked)
        self.wrap = checked
        self.refresh(clear=True)
        
    def toggle_hidden(self, checked):
        """Toggle hidden files mode"""
        self.parent().emit(SIGNAL('option_changed'), 'show_hidden', checked)
        self.show_hidden = checked
        self.refresh(clear=True)
        
    def toggle_all(self, checked):
        """Toggle all files mode"""
        self.parent().emit(SIGNAL('option_changed'), 'show_all', checked)
        self.show_all = checked
        self.refresh(clear=True)
        
    def update_menu(self):
        """Update option menu"""
        self.menu.clear()
        actions = []
        if self.currentItem() is not None:
            fname = self.get_filename()
            is_dir = osp.isdir(fname)
            ext = osp.splitext(fname)[1]
            run_action = create_action(self,
                                       translate('Explorer', "Run"),
                                       icon="run.png",
                                       triggered=self.run)
            edit_action = create_action(self,
                                        translate('Explorer', "Edit"),
                                        icon="edit.png",
                                        triggered=self.clicked)
            rename_action = create_action(self,
                                          translate('Explorer', "Rename"),
                                          icon="rename.png",
                                          triggered=self.rename)
            browse_action = create_action(self,
                                          translate('Explorer', "Browse"),
                                          icon=get_std_icon("CommandLink"),
                                          triggered=self.clicked)
            open_action = create_action(self,
                                        translate('Explorer', "Open"),
                                        triggered=self.startfile)
            if ext in ('.py', '.pyw'):
                actions.append(run_action)
            if ext in self.valid_types or os.name != 'nt':
                actions.append(browse_action if is_dir else edit_action)
            else:
                actions.append(open_action)
            actions.append(rename_action)
            if is_dir and os.name == 'nt':
                # Actions specific to Windows directories
                actions.append( create_action(self,
                           translate('Explorer', "Open in Windows Explorer"),
                           icon="magnifier.png",
                           triggered=self.startfile) )
        if os.name == 'nt':
            actions.append( create_action(self,
                       translate('Explorer', "Open command prompt here"),
                       icon="cmdprompt.png",
                       triggered=lambda cmd='cmd.exe': os.startfile(cmd)) )
        if actions:
            actions.append(None)
        actions += self.common_actions
        add_actions(self.menu, actions)
        
    #---- Refreshing widget
    def refresh(self, new_path=None, clear=False):
        """Refresh widget"""
        if new_path is None:
            new_path = os.getcwd()

        names = listdir(new_path, self.valid_types,
                        self.show_hidden, self.show_all)
        new_nameset = Set(names)
        
        if (new_path != self.path) or clear:
            self.path = new_path
            self.nameset = Set([])
            self.itemdict = {}
            self.clear()
            self.setWrapping(self.wrap)

        for name in self.nameset - new_nameset:
            self.takeItem(self.row(self.itemdict[name]))
            self.itemdict.pop(name)

        if new_nameset - self.nameset:
            for row, name in enumerate(names):
                if not self.itemdict.has_key(name):
                    # Adding new item
                    item = QListWidgetItem(name)
                    #item.setFlags(item.flags() | Qt.ItemIsEditable)
                    if osp.isdir(osp.join(self.path, name)):
                        item.setIcon(get_std_icon('DirClosedIcon'))
                    else:
                        item.setIcon( get_filetype_icon(name) )
                    self.itemdict[name] = item
                    self.insertItem(row, item)
            self.nameset = new_nameset
        
        
    #---- Events
    def contextMenuEvent(self, event):
        """Override Qt method"""
        self.update_menu()
        self.menu.popup(event.globalPos())
        
    def resizeEvent(self, event):
        """Reimplement Qt Method"""
        self.reset()
        QApplication.processEvents()
        event.ignore()

    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked()
            event.accept()
        elif event.key() == Qt.Key_F2:
            self.rename()
            event.accept()
        else:
            QListWidget.keyPressEvent(self, event)

    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if self.itemAt(event.pos()) is None:
            self.setCurrentItem(None)
            event.accept()
        else:
            QListWidget.mousePressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        self.clicked()
        event.accept()


    #---- Drag
    def dragEnterEvent(self, event):
        """Drag and Drop - Enter event"""
        event.setAccepted(event.mimeData().hasFormat("text/plain"))

    def dragMoveEvent(self, event):
        """Drag and Drop - Move event"""
        if (event.mimeData().hasFormat("text/plain")):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()
            
    def startDrag(self, dropActions):
        """Reimplement Qt Method - handle drag event"""
        item = self.currentItem()
        mimeData = QMimeData()
        mimeData.setText(unicode(item.text()))
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_()
            
            
    #---- Files/Directories Actions
    def get_filename(self):
        """Return selected filename"""
        if self.currentItem() is not None:
            return unicode(self.currentItem().text())
            
    def clicked(self):
        """Selected item was double-clicked or enter/return was pressed"""
        fname = self.get_filename()
        if fname:
            if osp.isdir(osp.join(self.path, fname)):
                self.parent().emit(SIGNAL("open_dir(QString)"), fname)
                self.refresh()
            else:
                self.open(fname)
        
    def open(self, fname):
        """Open filename with the appropriate application"""
        fname = unicode(fname)
        ext = osp.splitext(fname)[1]
        if ext in self.valid_types:
            self.parent().emit(SIGNAL("open_file(QString)"), fname)
        else:
            self.startfile(fname)
        
    def startfile(self, fname=None):
        """Windows only: open file in the associated application"""
        if fname is None:
            fname = self.get_filename()
        emit = False
        if os.name == 'nt':
            try:
                os.startfile(fname)
            except WindowsError:
                emit = True
        else:
            emit = True
        if emit:
            self.parent().emit(SIGNAL("edit(QString)"), fname)
        
    def run(self):
        """Run Python script"""
        self.parent().emit(SIGNAL("run(QString)"), self.get_filename())
            
    def rename(self):
        """Rename selected item"""
        fname = self.get_filename()
        if fname:
            path, valid = QInputDialog.getText(self,
                                          translate('Explorer', 'Rename item'),
                                          translate('Explorer', 'New name:'),
                                          QLineEdit.Normal, fname)
            if valid and path != fname:
                try:
                    os.rename(fname, path)
                except IOError, error:
                    QMessageBox.critical(self,
                        translate('Explorer', "Rename item"),
                        translate('Explorer',
                                  "<b>Unable to rename selected item</b>"
                                  "<br><br>Error message:<br>%1") \
                        .arg(str(error)))
                finally:
                    selected_row = self.currentRow()
                    self.refresh()
                    self.setCurrentRow(selected_row)
        

class ExplorerWidget(QWidget):
    """Explorer widget"""
    def __init__(self, parent=None, path=None, valid_types=('', '.py', '.pyw'),
                 show_hidden=False, show_all=False, wrap=True,
                 show_toolbar=True):
        QWidget.__init__(self, parent)
        
        self.listwidget = ExplorerListWidget(parent=self, path=path,
                                             valid_types=valid_types,
                                             show_hidden=show_hidden,
                                             show_all=show_all, wrap=wrap)        
        
        hlayout = QHBoxLayout()
        hlayout.setAlignment(Qt.AlignLeft)

        toolbar_action = create_action(self,
                                       translate('Explorer', "Show toolbar"),
                                       toggled=self.toggle_toolbar)
        self.listwidget.common_actions.append(toolbar_action)
        
        # Setup toolbar
        self.toolbar_widgets = []
        
        self.previous_button = create_toolbutton(self,
                    text=translate('Explorer', "Previous"),
                    icon=get_icon('previous.png'),
                    callback=lambda: self.emit(SIGNAL("open_previous_dir()")))
        self.toolbar_widgets.append(self.previous_button)
        self.previous_button.setEnabled(False)
        
        self.next_button = create_toolbutton(self,
                    text=translate('Explorer', "Next"),
                    icon=get_icon('next.png'),
                    callback=lambda: self.emit(SIGNAL("open_next_dir()")))
        self.toolbar_widgets.append(self.next_button)
        self.next_button.setEnabled(False)
        
        parent_button = create_toolbutton(self,
                    text=translate('Explorer', "Parent"),
                    icon=get_icon('up.png'),
                    callback=lambda: self.emit(SIGNAL("open_parent_dir()")))
        self.toolbar_widgets.append(parent_button)
        
        options_button = create_toolbutton(self,
                    text=translate('Explorer', "Options"),
                    icon=get_icon('tooloptions.png'))
        self.toolbar_widgets.append(options_button)
        options_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, self.listwidget.common_actions)
        options_button.setMenu(menu)
        
        for widget in self.toolbar_widgets:
            hlayout.addWidget(widget)
            
        toolbar_action.setChecked(show_toolbar)
        self.toggle_toolbar(show_toolbar)        
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.listwidget)
        self.setLayout(vlayout)
        
    def toggle_toolbar(self, state):
        """Toggle toolbar"""
        self.emit(SIGNAL('option_changed'), 'show_toolbar', state)
        for widget in self.toolbar_widgets:
            widget.setVisible(state)



class Test(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.explorer = ExplorerWidget(show_all=True)
        vlayout.addWidget(self.explorer)
        
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.connect(self.explorer, SIGNAL("open_file(QString)"),
                     self.label1.setText)
        
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)
        label = QLabel("<b>Open dir:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout2.addWidget(label)
        self.label2 = QLabel()
        hlayout2.addWidget(self.label2)
        self.connect(self.explorer, SIGNAL("open_dir(QString)"),
                     self.label2.setText)
        self.connect(self.explorer, SIGNAL("open_dir(QString)"),
                     lambda path: os.chdir(unicode(path)))
        
        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)
        self.connect(self.explorer, SIGNAL("option_changed"),
           lambda x, y: self.label3.setText('option_changed: %r, %r' % (x, y)))

        self.connect(self.explorer, SIGNAL("open_parent_dir()"),
                     lambda: self.explorer.listwidget.refresh('..'))

if __name__ == "__main__":
    QApplication([])
    test = Test()
    test.exec_()
