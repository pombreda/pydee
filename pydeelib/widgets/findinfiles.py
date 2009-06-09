# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Find in files widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from __future__ import with_statement

from PyQt4.QtGui import (QHBoxLayout, QWidget, QTreeWidgetItem, QSizePolicy,
                         QComboBox, QRadioButton, QVBoxLayout, QLabel,
                         QFileDialog)
from PyQt4.QtCore import SIGNAL, Qt, QThread, QMutexLocker, QMutex

import sys, os, re, fnmatch
import os.path as osp
from subprocess import Popen, PIPE

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from pydeelib.qthelpers import (get_std_icon, create_toolbutton, translate,
                                get_filetype_icon)
from pydeelib.config import get_icon
from pydeelib.widgets.comboboxes import PathComboBox
from pydeelib.widgets import OneColumnTree


def abspardir(path):
    """Return absolute parent dir"""
    return osp.abspath(osp.join(path, os.pardir))

def is_hg_installed():
    fname = 'hg.exe' if os.name == 'nt' else 'hg'
    for path in os.environ["PATH"].split(os.pathsep):
        if osp.isfile(osp.join(path, fname)):
            return True
    else:
        return False

def get_hg_root():
    path = os.getcwd()
    previous_path = path
    while not osp.isdir(osp.join(path, '.hg')):
        path = abspardir(path)
        if path == previous_path:
            return
        else:
            previous_path = path
    return osp.abspath(path)

def fmatch(name, patlist):
    for pat in patlist:
        cmp = re.compile(pat)
        if cmp.search(name):
            return True
    return False

#def find_files_in_hg_manifest(include, exclude):
#    p = Popen("hg manifest", stdout=PIPE)
#    found = []
#    hgroot = get_hg_root()
#    for path in p.stdout.read().splitlines():
#        dirname = osp.join('.', osp.dirname(path))
#        if fmatch(dirname+os.sep, exclude):
#            continue
#        filename = osp.join('.', osp.dirname(path))
#        if fmatch(filename, exclude):
#            continue
#        if fmatch(filename, include):
#            found.append(osp.join(hgroot, path))
#    return found
#
#def find_files_in_path(rootpath, include, exclude):
#    found = []
#    for path, dirs, files in os.walk(rootpath):
#        for d in dirs[:]:
#            dirname = os.path.join(path, d)
#            if fmatch(dirname+os.sep, exclude):
#                dirs.remove(d)
#        for f in files:
#            filename = os.path.join(path, f)
#            if fmatch( filename, exclude):
#                continue
#            if fmatch( filename, include):
#                found.append(filename)
#    return found


#def find_string_in_files(texts, filenames, regexp=False):
#    results = {}
#    nb = 0
#    for fname in filenames:
#        for lineno, line in enumerate(file(fname)):
#            for text in texts:
#                if regexp:
#                    found = re.search(text, line)
#                    if found is not None:
#                        break
#                else:
#                    found = line.find(text)
#                    if found > -1:
#                        break
#            if regexp:
#                for match in re.finditer(text, line):
#                    res = results.get(osp.abspath(fname), [])
#                    res.append((lineno+1, match.start(), line))
#                    results[osp.abspath(fname)] = res
#                    nb += 1
#            else:
#                while found > -1:
#                    res = results.get(osp.abspath(fname), [])
#                    res.append((lineno+1, found, line))
#                    results[osp.abspath(fname)] = res
#                    for text in texts:
#                        found = line.find(text, found+1)
#                        if found>-1:
#                            break
#                    nb += 1
#    return results, nb


class SearchThread(QThread):
    def __init__(self, parent):
        QThread.__init__(self, parent)
        self.mutex = QMutex()
        self.stopped = False
        
    def initialize(self, path, hg_manifest,
                   include, exclude, texts, text_re):
        self.rootpath = path
        self.hg_manifest = hg_manifest
        self.include = [include]
        self.exclude = [exclude]
        self.texts = texts
        self.text_re = text_re
        self.stopped = False
        self.completed = False
        
    def run(self):
        if self.hg_manifest:
            ok = self.find_files_in_hg_manifest()
        else:
            ok = self.find_files_in_path()
        if ok:
            self.find_string_in_files()
        self.stop()
        self.emit(SIGNAL("finished(bool)"), self.completed)
        
    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True

    def find_files_in_hg_manifest(self):
        p = Popen("hg manifest", stdout=PIPE)
        self.filenames = []
        hgroot = get_hg_root()
        for path in p.stdout.read().splitlines():
            with QMutexLocker(self.mutex):
                if self.stopped:
                    return False
            dirname = osp.dirname(path)
            if fmatch(dirname+os.sep, self.exclude):
                continue
            filename = osp.dirname(path)
            if fmatch(filename, self.exclude):
                continue
            if fmatch(filename, self.include):
                self.filenames.append(osp.join(hgroot, path))
        return True
    
    def find_files_in_path(self):
        self.filenames = []
        for path, dirs, files in os.walk(self.rootpath):
            with QMutexLocker(self.mutex):
                if self.stopped:
                    return False
            for d in dirs[:]:
                dirname = os.path.join(path, d)
                if fmatch(dirname+os.sep, self.exclude):
                    dirs.remove(d)
            for f in files:
                filename = os.path.join(path, f)
                if fmatch(filename, self.exclude):
                    continue
                if fmatch(filename, self.include):
                    self.filenames.append(filename)
        return True
        
    def find_string_in_files(self):
        self.results = {}
        self.nb = 0
        for fname in self.filenames:
            with QMutexLocker(self.mutex):
                if self.stopped:
                    return
            for lineno, line in enumerate(file(fname)):
                for text in self.texts:
                    if self.text_re:
                        found = re.search(text, line)
                        if found is not None:
                            break
                    else:
                        found = line.find(text)
                        if found > -1:
                            break
                if self.text_re:
                    for match in re.finditer(text, line):
                        res = self.results.get(osp.abspath(fname), [])
                        res.append((lineno+1, match.start(), line))
                        self.results[osp.abspath(fname)] = res
                        self.nb += 1
                else:
                    while found > -1:
                        res = self.results.get(osp.abspath(fname), [])
                        res.append((lineno+1, found, line))
                        self.results[osp.abspath(fname)] = res
                        for text in self.texts:
                            found = line.find(text, found+1)
                            if found>-1:
                                break
                        self.nb += 1
        self.completed = True
    
    def get_results(self):
        return self.results, self.nb
        

class FindOptions(QWidget):
    """
    Find widget with options
    """
    def __init__(self, parent, include, include_regexp,
                 exclude, exclude_regexp, supported_encodings):
        QWidget.__init__(self, parent)

        self.supported_encodings = supported_encodings
        hg_repository = is_hg_installed() and get_hg_root() is not None

        # Layout 1
        hlayout1 = QHBoxLayout()
        self.search_text = QComboBox(self)
        self.search_text.setEditable(True)
        self.search_text.setSizePolicy(QSizePolicy.Expanding,
                                       QSizePolicy.Fixed)
        self.search_text.setToolTip(translate('FindInFiles', "Search pattern"))
        search_label = QLabel(translate('FindInFiles', "Search text:"))
        search_label.setBuddy(self.search_text)
        self.edit_regexp = create_toolbutton(self, get_icon("advanced.png"),
                         tip=translate('FindInFiles', "Regular expression"))
        self.edit_regexp.setCheckable(True)
        self.edit_regexp.setChecked(False)
        self.ok_button = create_toolbutton(self,
                                text=translate('FindInFiles', "Search"),
                                callback=lambda: self.emit(SIGNAL('find()')),
                                icon=get_std_icon("DialogApplyButton"),
                                tip=translate('FindInFiles', "Start search"))
        self.stop_button = create_toolbutton(self,
                                callback=lambda: self.emit(SIGNAL('stop()')),
                                icon=get_icon("terminate.png"),
                                tip=translate('FindInFiles', "Stop search"))
        self.stop_button.setEnabled(False)
        for widget in [search_label, self.search_text, self.edit_regexp,
                       self.ok_button, self.stop_button]:
            hlayout1.addWidget(widget)

        # Layout 2
        hlayout2 = QHBoxLayout()
        self.include_pattern = QComboBox(self)
        self.include_pattern.setSizePolicy(QSizePolicy.Expanding,
                                           QSizePolicy.Fixed)
        self.include_pattern.setEditable(True)
        self.include_pattern.addItem(include)
        self.include_pattern.setToolTip(translate('FindInFiles',
                                                  "Included filenames pattern"))
        self.include_regexp = create_toolbutton(self, get_icon("advanced.png"),
                                            tip=translate('FindInFiles',
                                                          "Regular expression"))
        self.include_regexp.setCheckable(True)
        self.include_regexp.setChecked(include_regexp)
        include_label = QLabel(translate('FindInFiles', "Include:"))
        include_label.setBuddy(self.include_pattern)
        self.exclude_pattern = QComboBox(self)
        self.exclude_pattern.setSizePolicy(QSizePolicy.Expanding,
                                           QSizePolicy.Fixed)
        self.exclude_pattern.setEditable(True)
        self.exclude_pattern.addItem(exclude)
        self.exclude_pattern.setToolTip(translate('FindInFiles',
                                                  "Excluded filenames pattern"))
        self.exclude_regexp = create_toolbutton(self, get_icon("advanced.png"),
                                            tip=translate('FindInFiles',
                                                          "Regular expression"))
        self.exclude_regexp.setCheckable(True)
        self.exclude_regexp.setChecked(exclude_regexp)
        exclude_label = QLabel(translate('FindInFiles', "Exclude:"))
        exclude_label.setBuddy(self.exclude_pattern)
        for widget in [include_label, self.include_pattern,
                       self.include_regexp,
                       exclude_label, self.exclude_pattern,
                       self.exclude_regexp]:
            hlayout2.addWidget(widget)

        # Layout 3
        hlayout3 = QHBoxLayout()
        searchin_label = QLabel(translate('FindInFiles', "Search in:"))
        self.hg_manifest = QRadioButton(translate('FindInFiles',
                                                  "Hg repository"), self)
        self.hg_manifest.setEnabled(hg_repository)
        self.hg_manifest.setToolTip(translate('FindInFiles',
                              "Search in current directory hg repository"))
        searchin_label.setBuddy(self.hg_manifest)
        self.custom_dir = QRadioButton(translate('FindInFiles',
                                                 "Directory:"), self)
        self.custom_dir.setChecked(True)
        self.dir_combo = PathComboBox(self)
        self.dir_combo.addItem(os.getcwdu())
        self.dir_combo.setToolTip(translate('FindInFiles',
                                    "Search recursively in this directory"))
        self.connect(self.hg_manifest, SIGNAL('toggled(bool)'),
                     self.dir_combo.setDisabled)
        browse = create_toolbutton(self, get_std_icon('DirOpenIcon'),
                                   tip=translate('FindInFiles',
                                                 'Browse a search directory'),
                                   callback=self.select_directory)
        for widget in [searchin_label, self.hg_manifest, self.custom_dir,
                       self.dir_combo, browse]:
            hlayout3.addWidget(widget)
            
        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout1)
        vlayout.addLayout(hlayout2)
        vlayout.addLayout(hlayout3)
        self.setLayout(vlayout)
                
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
    def set_search_text(self, text):
        self.search_text.setEditText(text)
        self.search_text.lineEdit().selectAll()
        self.search_text.setFocus()
        
    def get_options(self):
        # Getting options
        utext = unicode(self.search_text.currentText())
        if not utext:
            return
        try:
            texts = [str(utext)]
        except UnicodeDecodeError:
            texts = []
            for encoding in self.supported_encodings:
                try:
                    texts.append( utext.encode(encoding) )
                except UnicodeDecodeError:
                    pass
        text_re = self.edit_regexp.isChecked()
        include = unicode(self.include_pattern.currentText())
        include_re = self.include_regexp.isChecked()
        exclude = unicode(self.exclude_pattern.currentText())
        exclude_re = self.exclude_regexp.isChecked()
        hg_manifest = self.hg_manifest.isChecked()
        path = osp.abspath(self.dir_combo.currentText())
        
        # Finding text occurences
        if not include_re:
            include = fnmatch.translate(include)
        if not exclude_re:
            exclude = fnmatch.translate(exclude)
            
        return path, hg_manifest, include, exclude, texts, text_re
        
    def select_directory(self):
        """Select directory"""
        self.parent().emit(SIGNAL('redirect_stdio(bool)'), False)
        directory = QFileDialog.getExistingDirectory(self,
                    translate('FindInFiles', "Select directory"),
                    self.dir_combo.currentText())
        if not directory.isEmpty():
            self.set_directory(directory)
        self.parent().emit(SIGNAL('redirect_stdio(bool)'), True)
        
    def set_directory(self, directory):
        self.dir_combo.setEditText(unicode(osp.abspath(directory)))        
        
    def keyPressEvent(self, event):
        """Reimplemented to handle key events"""
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier
        if event.key() == Qt.Key_Escape:
            self.parent().emit(SIGNAL('toggle_visibility(bool)'), False)
            event.accept()
            return
        elif event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.emit(SIGNAL('find()'))
        elif event.key() == Qt.Key_F and ctrl and shift:
            # Toggle find widgets
            self.parent().emit(SIGNAL('toggle_visibility(bool)'),
                               not self.isVisible())
            event.accept()
        else:
            event.ignore()


class ResultsBrowser(OneColumnTree):
    def __init__(self, parent):
        OneColumnTree.__init__(self, parent)
        self.results = None
        self.nb = None
        self.data = None
        self.set_title('')
        self.root_item = None
        
    def activated(self):
        itemdata = self.data.get(self.currentItem())
        if itemdata is not None:
            filename, lineno = itemdata
            self.parent().emit(SIGNAL("edit_goto(QString,int)"),
                               filename, lineno)
        
    def set_results(self, search_text, results, nb):
        self.search_text = search_text
        self.results = results
        self.nb = nb
        self.refresh()
        self.restore()
        
    def restore(self):
        self.collapseAll()
        if self.root_item is not None:
            self.root_item.setExpanded(True)
        
    def refresh(self):
        nb_files = len(self.results)
        title = "'%s' - " % self.search_text
        if nb_files == 0:
            text = translate('FindInFiles', 'String not found')
        else:
            text_matches = translate('FindInFiles', 'matches in')
            text_files = translate('FindInFiles', 'file')
            if nb_files > 1:
                text_files += 's'
            text = "%d %s %d %s" % (self.nb, text_matches, nb_files, text_files)
        self.set_title(title+text)
        self.clear()
        self.data = {}
        # Root path
        root_path = None
        dir_set = set()
        for filename in self.results:
            dirname = osp.dirname(filename)
            dir_set.add(dirname)
            if root_path is None or root_path not in dirname:
                root_path = dirname
        # Populating tree: directories
        def create_dir_item(dirname, parent):
            if dirname != root_path:
                displayed_name = osp.basename(dirname)
            else:
                displayed_name = dirname
            item = QTreeWidgetItem(parent, [displayed_name])
            item.setIcon(0, get_std_icon('DirClosedIcon'))
            return item
        dirs = {}
        for dirname in sorted(list(dir_set)):
            if dirname == root_path:
                parent = self
            else:
                parent_dirname = abspardir(dirname)
                parent = dirs.get(parent_dirname)
                if parent is None:
                    # This is related to directories which contain found
                    # results only in some of their children directories
                    items_to_create = []
                    while dirs.get(parent_dirname) is None:
                        items_to_create.append(parent_dirname)
                        parent_dirname = abspardir(parent_dirname)
                    items_to_create.reverse()
                    for item_dir in items_to_create:
                        item_parent = dirs[abspardir(item_dir)]
                        dirs[item_dir] = create_dir_item(item_dir, item_parent)
                    parent_dirname = abspardir(dirname)
                    parent = dirs[parent_dirname]
            dirs[dirname] = create_dir_item(dirname, parent)
        self.root_item = dirs[root_path]
        # Populating tree: files
        for filename in sorted(self.results.keys()):
            parent_item = dirs[osp.dirname(filename)]
            file_item = QTreeWidgetItem(parent_item, [osp.basename(filename)])
            file_item.setIcon(0, get_filetype_icon(filename))
            for lineno, colno, line in self.results[filename]:
                item = QTreeWidgetItem(file_item,
                           ["%d (%d): %s" % (lineno, colno, line.rstrip())])
                item.setIcon(0, get_icon('arrow.png'))
                self.data[item] = (filename, lineno)


class FindInFilesWidget(QWidget):
    """
    Find in files widget
    """
    def __init__(self, parent, include=".", include_regexp=True,
                 exclude=r"\.pyc$|\.orig$|\.hg|\.svn", exclude_regexp=True,
                 supported_encodings=("utf-8", "iso-8859-1", "cp1252")):
        QWidget.__init__(self, parent)

        self.search_thread = SearchThread(self)
        self.connect(self.search_thread, SIGNAL("finished()"),
                     self.search_complete)
        
        self.find_options = FindOptions(self, include, include_regexp,
                                        exclude, exclude_regexp,
                                        supported_encodings)
        self.connect(self.find_options, SIGNAL('find()'), self.find)
        self.connect(self.find_options, SIGNAL('stop()'), self.stop)
        
        self.result_browser = ResultsBrowser(self)
        
        collapse_btn = create_toolbutton(self, get_icon("collapse.png"),
                                 tip=translate('FindInFiles', "Collapse all"),
                                 callback=self.result_browser.collapseAll)
        expand_btn = create_toolbutton(self, get_icon("expand.png"),
                                 tip=translate('FindInFiles', "Expand all"),
                                 callback=self.result_browser.expandAll)
        restore_btn = create_toolbutton(self, get_icon("restore.png"),
                                 tip=translate('FindInFiles',
                                               "Restore original tree layout"),
                                 callback=self.result_browser.restore)
        btn_layout = QVBoxLayout()
        btn_layout.setAlignment(Qt.AlignTop)
        for widget in [collapse_btn, expand_btn, restore_btn]:
            btn_layout.addWidget(widget)
        
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.result_browser)
        hlayout.addLayout(btn_layout)
        
        layout = QVBoxLayout()
        left, _, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(left, 0, right, bottom)
        layout.addWidget(self.find_options)
        layout.addLayout(hlayout)
        self.setLayout(layout)
            
    def set_search_text(self, text):
        self.find_options.set_search_text(text)

    def find(self):
        """Call the find function"""
        options = self.find_options.get_options()
        if options is None:
            return
        self.search_thread.initialize(*options)
        self.search_thread.start()
        self.find_options.stop_button.setEnabled(True)
            
    def stop(self):
        if self.search_thread.isRunning():
            self.search_thread.stop()
            
    def search_complete(self):
        self.find_options.stop_button.setEnabled(False)
        found = self.search_thread.get_results()
        if found is not None:
            results, nb = found
            search_text = unicode( self.find_options.search_text.currentText() )
            self.result_browser.set_results(search_text, results, nb)
            self.result_browser.show()
            
            
if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    app = QApplication([])
    
    widget = FindInFilesWidget(None)
    widget.show()
    
    sys.exit(app.exec_())
