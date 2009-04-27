#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This module is a contribution from Brian Clowers (04/23/2009)

import os, sys
from PyQt4.QtGui import QDialog, QColor, QDoubleValidator
from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.uic import loadUiType

LINE_STYLES = dict(Solid = '-', Dashed = '--', DashDot = '-.',
                   Dotted = ':', Steps = 'steps', none = 'None')

MARKER_STYLES = dict(none = 'None',
                     circles = 'o',
                     triangle_up = '^',
                     triangle_down  = 'v',
                     triangle_left  = '<',
                     triangle_right  = '>',
                     square  = 's',
                     plus  = '+',
                     cross  = 'x',
                     diamond  = 'D',
                     thin_diamond  = 'd',
                     tripod_down  = '1',
                     tripod_up  = '2',
                     tripod_left  = '3',
                     tripod_right  = '4',
                     hexagon  = 'h',
                     rotated_hexagon  = 'H',
                     pentagon  = 'p',
                     vertical_line  = '|',
                     horizontal_line  = '_',
                     dots = '.')

LINE_COLOR_DICT = {'b':'#0000ff', 'g':'#00ff00','r':'#ff0000','c':'#ff00ff',
                   'm':'#ff00ff','y':'#ffff00','k':'#000000','w':'#ffffff'}


sys.path.append(os.path.dirname(__file__))
UI = loadUiType(os.path.splitext(__file__)[0]+'.ui')[0]


class FigureParameters(QDialog, UI):
    def __init__(self, canvas=None, parent=None):
        super(FigureParameters, self).__init__(parent)
        self.setupUi(self)

        self.parent = parent
        self.canvas = canvas

        self.plot_title = "Plot Title"
        self.plot_title = self.canvas.ax.get_title()
        self.xmin = 0.0
        self.xmax = 10.0
        self.xmin, self.xmax = self.canvas.ax.get_xlim()
        self.xtitle = "X-Axis"
        self.xtitle = self.canvas.ax.get_xlabel()

        self.ymin = 0.0
        self.ymax = 20.0
        self.ymin, self.ymax = self.canvas.ax.get_ylim()
        self.ytitle = "Y-Axis"
        self.ytitle = self.canvas.ax.get_ylabel()

        line_dict = {}
        for line in self.canvas.ax.get_lines():
            line_dict[line.get_label()]=line
        self.activeplots = line_dict

        # Validators
        validator = QDoubleValidator(self)
        self.xmin_lineEdit.setValidator(validator)
        self.xmax_lineEdit.setValidator(validator)
        self.ymin_lineEdit.setValidator(validator)
        self.ymax_lineEdit.setValidator(validator)
        
        self.connect(self.activePlotListWidget,
                     SIGNAL("itemClicked(QListWidgetItem *)"),
                     self.getPlotItem)
        
        self.connect(self.mstyle_comboBox,
                     SIGNAL("currentIndexChanged(QString)"),
                     self.setMStyle)
        self.connect(self.ms_spinBox,
                     SIGNAL("valueChanged(double)"), 
                     self.setMSize)
        self.connect(self.lstyle_comboBox,
                     SIGNAL("currentIndexChanged(QString)"),
                     self.setLStyle)
        self.connect(self.lw_spinBox,
                     SIGNAL("valueChanged(double)"),
                     self.setLWidth)
        self.connect(self.lineColorBtn,
                     SIGNAL("colorChanged(QColor)"),
                     self.setLColor)
        self.connect(self.markerColorBtn,
                     SIGNAL("colorChanged(QColor)"),
                     self.setMColor)
        
        self.connect(self.toggleGrid_btn,
                     SIGNAL("clicked()"),
                     self.setGrid)

        self.populate_dialog()
        
        self.addLegend = False

    def accept(self):
        """Accept and apply changes"""
        
        # Figure title
        self.canvas.ax.set_title( unicode( self.plottitle_lineEdit.text() ) )
        
        # log/lin
        if self.logx_cb.checkState() == Qt.Checked:
            self.canvas.ax.set_xscale('log')
        else:
            self.canvas.ax.set_xscale('linear')
        if self.logy_cb.checkState() == Qt.Checked:
            self.canvas.ax.set_yscale('log')
        else:
            self.canvas.ax.set_yscale('linear')

        # xmin, xmax, xlabel
        self.canvas.ax.set_xlim( xmin=float(str( self.xmin_lineEdit.text() )) )
        self.canvas.ax.set_xlim( xmax=float(str( self.xmax_lineEdit.text() )) )
        self.canvas.ax.set_xlabel( unicode(self.xlabel_lineEdit.text()) )

        # ymin, ymax, ylabel
        self.canvas.ax.set_ylim( ymin=float(str( self.ymin_lineEdit.text() )) )
        self.canvas.ax.set_ylim( ymax=float(str( self.ymax_lineEdit.text() )) )
        self.canvas.ax.set_ylabel( unicode(self.ylabel_lineEdit.text()) )
        
        if self.addLegend:
            self.canvas.ax.legend(axespad = 0.03, pad=0.25)
            
#        self.canvas.ax.title.set_fontsize(10)
#        xLabel = self.canvas.ax.get_xlabel()
#        yLabel = self.canvas.ax.get_ylabel()
#        self.canvas.ax.set_xlabel(xLabel, fontsize = 9)
#        self.canvas.ax.set_ylabel(yLabel, fontsize = 9)
#        labels_x = self.canvas.ax.get_xticklabels()
#        labels_y = self.canvas.ax.get_yticklabels()
#        for xlabel in labels_x:
#            xlabel.set_fontsize(8)
#        for ylabel in labels_y:
#            ylabel.set_fontsize(8)
#            ylabel.set_color('b')
        if self.canvas.ax.get_legend() != None:
            texts = self.canvas.ax.get_legend().get_texts()
            for text in texts:
                text.set_fontsize(8)
        self.canvas.draw()
        
        QDialog.accept(self)

    def setGrid(self):
        self.canvas.ax.grid()

    def setMSize(self, value):
        #print "Set Marker Size"
        if self.activePlotListWidget.currentItem():
            activeLine = self.getPlotItem(self.activePlotListWidget.currentItem())
            activeLine.set_markersize(value)
            self.setupLineOptions(activeLine)

    def setMStyle(self, value):
        #print "Set Marker Style"
        if self.activePlotListWidget.currentItem():
            activeLine = self.getPlotItem(self.activePlotListWidget.currentItem())
            activeLine.set_marker(MARKER_STYLES.get(str(value)))#need to set value to str as it is QString
            self.setupLineOptions(activeLine)

    def setMColor(self, QColor):
        if self.activePlotListWidget.currentItem():
            activeLine = self.getPlotItem(self.activePlotListWidget.currentItem())
            #print str(QColor.name())
            activeLine.set_markerfacecolor(str(QColor.name()))#need to set value to str as it is QString
            self.setupLineOptions(activeLine)

    def setLWidth(self, value):
        #print "Set L Width"
        if self.activePlotListWidget.currentItem():
            activeLine = self.getPlotItem(self.activePlotListWidget.currentItem())
            activeLine.set_linewidth(value)
            self.setupLineOptions(activeLine)

    def setLStyle(self, value):
        #print "Set Line Style"
        if self.activePlotListWidget.currentItem():
            activeLine = self.getPlotItem(self.activePlotListWidget.currentItem())
            activeLine.set_linestyle(LINE_STYLES.get(str(value)))#need to set value to str as it is QString
            self.setupLineOptions(activeLine)

    def setLColor(self, QColor):
        if self.activePlotListWidget.currentItem():
            activeLine = self.getPlotItem(self.activePlotListWidget.currentItem())
            #print str(QColor.name())
            activeLine.set_color(str(QColor.name()))#need to set value to str as it is QString
            self.setupLineOptions(activeLine)

    def getPlotItem(self, item):
        linePlotItem = self.activeplots.get(str(item.text()))
        self.setupLineOptions(linePlotItem)
        return linePlotItem

    def getKey(self, dict, value):
        for key, val in dict.items():
            if val == value:
                return key

    def setupLineOptions(self, lineInstance):

        match_index = self.mstyle_comboBox.findText(self.getKey(MARKER_STYLES, lineInstance.get_marker()))
        self.mstyle_comboBox.setCurrentIndex(match_index)

        key = self.getKey(LINE_STYLES, lineInstance.get_linestyle())

        match_index = self.lstyle_comboBox.findText(str(key))
        self.lstyle_comboBox.setCurrentIndex(match_index)

        self.lw_spinBox.setValue(lineInstance.get_linewidth())
        self.ms_spinBox.setValue(lineInstance.get_markersize())

        if lineInstance.get_color() is None:
            pass
        else:
            lcolor = lineInstance.get_color()
            if LINE_COLOR_DICT.has_key(lcolor):
                lcolor = LINE_COLOR_DICT.get(lineInstance.get_color())
            #lcolor = QColor(lineInstance.get_color())
            self.lineColorBtn.setColor(QColor(lcolor))

        if lineInstance.get_markerfacecolor() is None:
            pass
        else:
            mcolor = lineInstance.get_markerfacecolor()
            if LINE_COLOR_DICT.has_key(mcolor):
                mcolor = LINE_COLOR_DICT.get(lineInstance.get_markerfacecolor())
            self.markerColorBtn.setColor(QColor(mcolor))

    def populate_dialog(self):
        #populate first tab
        self.plottitle_lineEdit.setText(self.plot_title)

        #Keeping the axis limits as strings
        #to avoid any problems with the min and maximum of the QT Dialog
        self.xmin_lineEdit.setText(str(self.xmin))
        self.xmax_lineEdit.setText(str(self.xmax))
        self.xlabel_lineEdit.setText(self.xtitle)

        self.ymin_lineEdit.setText(str(self.ymin))
        self.ymax_lineEdit.setText(str(self.ymax))
        self.ylabel_lineEdit.setText(self.ytitle)

        xScale = self.canvas.ax.get_xscale()
        if xScale == 'linear':
            self.logx_cb.setCheckState(Qt.Unchecked)
        elif xScale == 'log':
            self.logx_cb.setCheckState(Qt.Checked)

        yScale = self.canvas.ax.get_yscale()
        if yScale == 'linear':
            self.logy_cb.setCheckState(Qt.Unchecked)
        elif yScale == 'log':
            self.logy_cb.setCheckState(Qt.Checked)

        #populate second tab
        self.lstyle_comboBox.addItems(LINE_STYLES.keys())
        self.mstyle_comboBox.addItems(MARKER_STYLES.keys())
        if self.activeplots is not None and type(self.activeplots) is dict:
            activeList = self.activeplots.keys()
            for i,activeLine in enumerate(activeList):
                if activeLine == '_nolegend_':
                    activeList.pop(i)
            activeList.sort()
            if len(activeList) > 0:
                self.activePlotListWidget.addItems(activeList)
                self.activePlotListWidget.setCurrentRow(0)
                self.getPlotItem(self.activePlotListWidget.currentItem())
