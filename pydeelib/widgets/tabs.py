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
            self.emit(SIGNAL("move_tab(int,int)"), index_from, index_to)
            event.acceptProposedAction()
        QTabBar.dropEvent(self, event)
        
        
class Tabs(QTabWidget):
    """TabWidget with a context-menu"""
    def __init__(self, parent, actions=None):
        QTabWidget.__init__(self, parent)
        tab_bar = TabsBase(self)
        self.connect(tab_bar, SIGNAL('move_tab(int,int)'), self.move_tab)
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
            index = self.tabBar().tabAt(event.pos())
            if index >= 0:
                self.emit(SIGNAL("close_tab(int)"), index)
                event.accept()
                return
        QTabWidget.mousePressEvent(self, event)
        
    def keyPressEvent(self, event):
        """Override Qt method"""
        ctrl = event.modifiers() & Qt.ControlModifier
        key = event.key()
        handled = False
        if ctrl and self.count() > 0:
            index = self.currentIndex()
            if key == Qt.Key_PageUp and index > 0:
                self.setCurrentIndex(index-1)
                handled = True
            elif key == Qt.Key_PageDown and index < self.count()-1:
                self.setCurrentIndex(index+1)
                handled = True
        if handled:
            event.accept()
        else:
            QTabWidget.keyPressEvent(self, event)

    def move_tab(self, index_from, index_to):
        """Switch tabs"""
        self.emit(SIGNAL('move_data(int,int)'), index_from, index_to)

        tip, text = self.tabToolTip(index_from), self.tabText(index_from)
        icon, widget = self.tabIcon(index_from), self.widget(index_from)
        current_widget = self.currentWidget()
        
        self.removeTab(index_from)
        self.insertTab(index_to, widget, icon, text)
        self.setTabToolTip(index_to, tip)
        
        self.setCurrentWidget(current_widget)
