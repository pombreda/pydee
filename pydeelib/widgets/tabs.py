# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see pydeelib/__init__.py for details)

"""Tabs widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QTabWidget, QMenu, QDrag, QApplication, QTabBar
from PyQt4.QtCore import SIGNAL, Qt, QPoint, QMimeData, QByteArray

# Local imports
from pydeelib.qthelpers import add_actions

# For debugging purpose:
import sys
STDOUT = sys.stdout


class TabsBase(QTabBar):
    """Tabs base class with drag and drop support"""
    def __init__(self, parent):
        QTabBar.__init__(self, parent)
            
        # Dragging tabs
        self.__drag_start_pos = QPoint()
        self.setAcceptDrops(True)

    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() == Qt.LeftButton:
            self.__drag_start_pos = QPoint(event.pos())
        QTabBar.mousePressEvent(self, event)
    
    def mouseMoveEvent(self, event):
        """Override Qt method"""
        if event.buttons() == Qt.MouseButtons(Qt.LeftButton) and \
           (event.pos() - self.__drag_start_pos).manhattanLength() > \
                QApplication.startDragDistance():
            drag = QDrag(self)
            mimeData = QMimeData()
            mimeData.setData("tabbar-id", QByteArray.number(id(self)))
            drag.setMimeData(mimeData)
            drag.exec_()
        QTabBar.mouseMoveEvent(self, event)
    
    def dragEnterEvent(self, event):
        """Override Qt method"""
        mimeData = event.mimeData()
        formats = mimeData.formats()
        if formats.contains("tabbar-id") and \
           mimeData.data("tabbar-id").toLong()[0] == id(self):
            event.acceptProposedAction()
        QTabBar.dragEnterEvent(self, event)
    
    def dropEvent(self, event):
        """Override Qt method"""
        index_from = self.tabAt(self.__drag_start_pos)
        index_to = self.tabAt(event.pos())
        if index_from != index_to:
            self.emit(SIGNAL("switch_tabs(int,int)"), index_from, index_to)
            event.acceptProposedAction()
        QTabBar.dropEvent(self, event)
        
        
class Tabs(QTabWidget):
    """TabWidget with a context-menu"""
    def __init__(self, parent, actions):
        QTabWidget.__init__(self, parent)
        tab_bar = TabsBase(self)
        self.connect(tab_bar, SIGNAL('switch_tabs(int,int)'), self.switch_tabs)
        self.setTabBar(tab_bar)
        self.menu = QMenu(self)
        if actions:
            add_actions(self.menu, actions)
        
    def contextMenuEvent(self, event):
        """Override Qt method"""
        if self.menu:
            self.menu.popup(event.globalPos())
            
    def mousePressEvent(self, event):
        """Override Qt method"""
        if event.button() == Qt.MidButton:
            if self.count():
                #TODO: [low-priority] Really close the clicked tab and not the last one
                self.emit(SIGNAL("close_tab(int)"), self.currentIndex())
                event.accept()
                return
        QTabWidget.mousePressEvent(self, event)

    def switch_tabs(self, index1, index2):
        """Switch tabs"""
        self.emit(SIGNAL('switch_data(int,int)'), index1, index2)

        tip, text = self.tabToolTip(index1), self.tabText(index1)
        icon, widget = self.tabIcon(index1), self.widget(index1)
        self.removeTab(index1)
        
        self.insertTab(index2, widget, icon, text)
        self.setTabToolTip(index2, tip)
        self.setCurrentIndex(index2)
