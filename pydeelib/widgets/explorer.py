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

from __future__ import with_statement

try:
    # PyQt4 4.3.3 on Windows (static DLLs) with py2exe installed:
    # -> pythoncom must be imported first, otherwise py2exe's boot_com_servers
    #    will raise an exception ("ImportError: DLL load failed [...]") when
    #    calling any of the QFileDialog static methods (getOpenFileName, ...)
    import pythoncom #@UnusedImport
except ImportError:
    pass

from PyQt4.QtGui import (QDialog, QListWidget, QListWidgetItem, QVBoxLayout,
                         QLabel, QHBoxLayout, QDrag, QApplication, QMessageBox,
                         QInputDialog, QLineEdit, QMenu, QWidget, QToolButton,
                         QFileDialog, QToolBar)
from PyQt4.QtCore import Qt, SIGNAL, QMimeData

import os, sys, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.widgets.formlayout import fedit
from pydeelib.qthelpers import (get_std_icon, create_action, add_actions,
                                translate, get_filetype_icon, create_toolbutton)
from pydeelib import encoding
from pydeelib.config import get_icon


def create_script(fname):
    """Create a new Python script"""
    text = os.linesep.join(["# -*- coding: utf-8 -*-", "", ""])
    encoding.write(unicode(text), fname, 'utf-8')

def listdir(path, include='.', exclude=r'\.pyc$|^\.', show_all=False):
    """List files and directories"""
    namelist = []
    dirlist = [unicode(osp.pardir)]
    for item in os.listdir(unicode(path)):
        if re.search(exclude, item) and not show_all:
            continue
        if osp.isdir(osp.join(path, item)):
            dirlist.append(item)
        elif re.search(include, item) or show_all:
            namelist.append(item)
    return sorted(dirlist, key=unicode.lower) + \
           sorted(namelist, key=unicode.lower)


class ExplorerListWidget(QListWidget):
    """File and Directories Explorer Widget
    get_filetype_icon(fname): fn which returns a QIcon for file extension"""
    def __init__(self, parent=None, path=None, include='.',
                 exclude=r'\.pyc$|^\.', valid_types= ('.py', '.pyw'),
                 show_all=False, wrap=True):
        QListWidget.__init__(self, parent)
        
        self.include = include
        self.exclude = exclude
        self.valid_types = valid_types
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
        # Filters
        filters_action = create_action(self,
                                       translate('Explorer',
                                                 "Edit filename filter..."),
                                       None, get_icon('filter.png'),
                                       triggered=self.edit_filter)
        # Show all files
        all_action = create_action(self,
                                   translate('Explorer', "Show all files"),
                                   toggled=self.toggle_all)
        all_action.setChecked(self.show_all)
        self.toggle_all(self.show_all)
        # Wrap
        wrap_action = create_action(self,
                                    translate('Explorer', "Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked(self.wrap)
        self.toggle_wrap_mode(self.wrap)
        
        return [filters_action, all_action, None, wrap_action]
        
    def edit_filter(self):
        """Edit include/exclude filter"""
        filter = [(translate('Explorer', 'Type'),
                   [True, (True, translate('Explorer', 'regular expressions')),
                    (False, translate('Explorer', 'global patterns'))]),
                  (translate('Explorer', 'Include'), self.include),
                  (translate('Explorer', 'Exclude'), self.exclude),]
        result = fedit(filter, title=translate('Explorer', 'Edit filter'),
                       parent=self)
        if result:
            regexp, self.include, self.exclude = result
            if not regexp:
                import fnmatch
                self.include = fnmatch.translate(self.include)
                self.exclude = fnmatch.translate(self.exclude)
            self.parent().emit(SIGNAL('option_changed'),
                               'include', self.include)
            self.parent().emit(SIGNAL('option_changed'),
                               'exclude', self.exclude)
            self.refresh()
        
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.parent().emit(SIGNAL('option_changed'), 'wrap', checked)
        self.wrap = checked
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
        if self.currentItem() is None:
            # No selection
            newdir_action = create_action(self,
                                          translate('Explorer',
                                                    "New folder..."),
                                          icon="folder_new.png",
                                          triggered=self.new_folder)
            actions.append(newdir_action)
            newfile_action = create_action(self,
                                           translate('Explorer',
                                                     "New file..."),
                                           icon="filenew.png",
                                           triggered=self.new_file)
            actions.append(newfile_action)
        else:
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
            delete_action = create_action(self,
                                          translate('Explorer', "Delete..."),
                                          icon="delete.png",
                                          triggered=self.delete)
            rename_action = create_action(self,
                                          translate('Explorer', "Rename..."),
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
            actions += [delete_action, rename_action]
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
            new_path = os.getcwdu()

        names = listdir(new_path, self.include, self.exclude, self.show_all)
        new_nameset = set(names)
        
        if (new_path != self.path) or clear:
            self.path = new_path
            self.nameset = set([])
            self.itemdict = {}
            self.clear()
            self.setWrapping(self.wrap)

        for name in self.nameset - new_nameset:
            try:
                self.takeItem(self.row(self.itemdict[name]))
                self.itemdict.pop(name)
            except KeyError:
                pass

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
            
    def delete(self):
        """Delete selected item"""
        fname = self.get_filename()
        if fname:
            answer = QMessageBox.warning(self,
                translate("Explorer", "Delete"),
                translate("Explorer", "Do you really want to delete <b>%1</b>?") \
                .arg(osp.basename(fname)), QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return
            try:
                os.remove(fname)
                self.parent().emit(SIGNAL("removed(QString)"), fname)
            except EnvironmentError, error:
                QMessageBox.critical(self,
                    translate('Explorer', "Delete"),
                    translate('Explorer',
                              "<b>Unable to delete selected file</b>"
                              "<br><br>Error message:<br>%1") \
                    .arg(str(error)))
            finally:
                self.refresh()
            
    def rename(self):
        """Rename selected item"""
        fname = self.get_filename()
        if fname:
            path, valid = QInputDialog.getText(self,
                                          translate('Explorer', 'Rename'),
                                          translate('Explorer', 'New name:'),
                                          QLineEdit.Normal, fname)
            if valid and path != fname:
                try:
                    os.rename(fname, path)
                    self.parent().emit(SIGNAL("renamed(QString,QString)"),
                                       fname, path)
                except EnvironmentError, error:
                    QMessageBox.critical(self,
                        translate('Explorer', "Rename"),
                        translate('Explorer',
                                  "<b>Unable to rename selected file</b>"
                                  "<br><br>Error message:<br>%1") \
                        .arg(str(error)))
                finally:
                    selected_row = self.currentRow()
                    self.refresh()
                    self.setCurrentRow(selected_row)
        
    def new_folder(self):
        """Create a new folder"""
        datalist = [(translate('Explorer', 'Folder name'), ''),
                    (translate('Explorer', 'Python package'), False),]
        answer = fedit( datalist, title=translate('Explorer', "New folder"),
                        parent=self, icon=get_icon('pydee.png') )
        if answer is not None:
            name, pack = answer
            try:
                os.mkdir(name)
            except EnvironmentError, error:
                QMessageBox.critical(self,
                    translate('Explorer', "New folder"),
                    translate('Explorer',
                              "<b>Unable to create folder <i>%1</i></b>"
                              "<br><br>Error message:<br>%2") \
                    .arg(name).arg(str(error)))
            finally:
                if pack:
                    create_script( osp.join(name, '__init__.py') )
                self.refresh()

    def new_file(self):
        """Create a new file"""
        _temp = sys.stdout
        sys.stdout = None
        fname = QFileDialog.getSaveFileName(self,
                    translate('Explorer', "New Python script"), os.getcwdu(),
                    translate('Explorer', "Python scripts")+" (*.py ; *.pyw)"+"\n"+\
                    translate('Explorer', "All files")+" (*.*)")
        sys.stdout = _temp
        if not fname.isEmpty():
            fname = unicode(fname)
            try:
                if osp.splitext(fname)[1] in ('.py', '.pyw'):
                    create_script(fname)
                else:
                    file(fname, 'wb').write('')
            except EnvironmentError, error:
                QMessageBox.critical(self,
                    translate('Explorer', "New file"),
                    translate('Explorer',
                              "<b>Unable to create file <i>%1</i></b>"
                              "<br><br>Error message:<br>%2") \
                    .arg(fname).arg(str(error)))
            finally:
                self.refresh()
                self.open(fname)


class ExplorerWidget(QWidget):
    """Explorer widget"""
    def __init__(self, parent=None, path=None, include='.',
                 exclude=r'\.pyc$|^\.', valid_types=('.py', '.pyw'),
                 show_all=False, wrap=True,
                 show_toolbar=True, show_icontext=True):
        QWidget.__init__(self, parent)
        
        self.listwidget = ExplorerListWidget(parent=self, path=path,
                                             include=include, exclude=exclude,
                                             valid_types=valid_types,
                                             show_all=show_all, wrap=wrap)        
        
        toolbar_action = create_action(self,
                                       translate('Explorer', "Show toolbar"),
                                       toggled=self.toggle_toolbar)
        icontext_action = create_action(self,
                                       translate('Explorer',
                                                 "Show icons and text"),
                                       toggled=self.toggle_icontext)
        self.listwidget.common_actions += [toolbar_action, icontext_action]
        
        # Setup toolbar
        self.toolbar = QToolBar(self)
        
        self.previous_action = create_action(self,
                    text=translate('Explorer', "Previous"),
                    icon=get_icon('previous.png'),
                    triggered=lambda: self.emit(SIGNAL("open_previous_dir()")))
        self.toolbar.addAction(self.previous_action)
        self.previous_action.setEnabled(False)
        
        self.next_action = create_action(self,
                    text=translate('Explorer', "Next"),
                    icon=get_icon('next.png'),
                    triggered=lambda: self.emit(SIGNAL("open_next_dir()")))
        self.toolbar.addAction(self.next_action)
        self.next_action.setEnabled(False)
        
        parent_action = create_action(self,
                    text=translate('Explorer', "Parent"),
                    icon=get_icon('up.png'),
                    triggered=lambda: self.emit(SIGNAL("open_parent_dir()")))
        self.toolbar.addAction(parent_action)
                
        refresh_action = create_action(self,
                    text=translate('Explorer', "Refresh"),
                    icon=get_icon('reload.png'),
                    triggered=lambda: self.listwidget.refresh(clear=True))
        self.toolbar.addAction(refresh_action)

        options_action = create_action(self,
                    text=translate('Explorer', "Options"),
                    icon=get_icon('tooloptions.png'))
        self.toolbar.addAction(options_action)
        widget = self.toolbar.widgetForAction(options_action)
        widget.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, self.listwidget.common_actions)
        options_action.setMenu(menu)
            
        toolbar_action.setChecked(show_toolbar)
        self.toggle_toolbar(show_toolbar)   
        icontext_action.setChecked(show_icontext)
        self.toggle_icontext(show_icontext)     
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.listwidget)
        self.setLayout(vlayout)
        
    def toggle_toolbar(self, state):
        """Toggle toolbar"""
        self.emit(SIGNAL('option_changed'), 'show_toolbar', state)
        self.toolbar.setVisible(state)
            
    def toggle_icontext(self, state):
        """Toggle icon text"""
        self.emit(SIGNAL('option_changed'), 'show_icontext', state)
        for action in self.toolbar.actions():
            widget = self.toolbar.widgetForAction(action)
            if state:
                widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            else:
                widget.setToolButtonStyle(Qt.ToolButtonIconOnly)



class Test(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.explorer = ExplorerWidget()
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
