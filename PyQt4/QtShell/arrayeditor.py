# -*- coding: utf-8 -*-
"""
Qt-based array editor
"""

from PyQt4.QtCore import Qt, QVariant, QModelIndex, QAbstractTableModel
from PyQt4.QtCore import SIGNAL, SLOT
from PyQt4.QtGui import QFont, QColor, QLabel, QTableView, QLineEdit
from PyQt4.QtGui import QDialog, QDialogButtonBox, QMessageBox, QGridLayout
import numpy
import config


class FloatArrayModel(QAbstractTableModel):
    """Model for numpy array"""
    def __init__(self, data, fmt="%.3f", xy_mode=False):
        super(FloatArrayModel, self).__init__()
        self._data = data
        self._fmt = fmt
        self._xy = xy_mode
        vmin = data.min()
        vmax = data.max()
        if vmax == vmin:
            vmin -= 1
        self.interval = [vmin, vmax]
        font = QFont("courier")
        font.setStyleHint(font.TypeWriter)
        font.setFixedPitch(True)
        font.setPointSize(8)
        self.font = QVariant(font)
    
    def set_format(self, fmt):
        """Change display format"""
        self._fmt = fmt
        self.reset()

    def columnCount(self, qindex=QModelIndex()):
        """Array column number"""
        return self._data.shape[1]

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return self._data.shape[0]

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return QVariant()
        i = index.row()
        j = index.column()
        value = self._data[i, j]
        if role == Qt.DisplayRole:
            return QVariant( self._fmt % value )
        elif role == Qt.BackgroundColorRole:
            hueint = [.66, .99]
            hue = numpy.interp(value, self.interval, hueint,
                               left = hueint[0], right = hueint[1])
            color = QColor.fromHsvF(hue, .7, 1., .6)
            return QVariant(color)
        elif role == Qt.FontRole:
            return self.font
        else:
            return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        """Cell content change"""
        if not index.isValid():
            return False
        i = index.row()
        j = index.column()
        val, ok = value.toDouble()
        if ok:
            self._data[i, j] = val
            return True
        return False
    
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                            Qt.ItemIsEditable)
                
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return QVariant(int(section))
        else:
            if self._xy:
                if section == 0:
                    return QVariant('x')
                elif self.rowCount() == 2:
                    return QVariant('y')
                else:
                    return QVariant('y (channel='+str(section-1)+')')
            else:
                return QVariant(int(section))


class ArrayEditor(QDialog):
    def __init__(self, title, data, format="%.3f", xy=False):
        super(ArrayEditor, self).__init__()
        self.source = numpy.array(data, dtype=float, copy=True)
        self.data = self.source.view()
        if len(self.data.shape)==1:
            self.data.shape = (self.data.shape[0], 1)

        if len(self.data.shape)!=2:
            raise RuntimeError( "ArrayEditor doesn't support arrays with more than 2 dimensions" )
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.setWindowIcon(config.icon('arredit.png'))
        self.setWindowTitle(u"Array editor%s" % (" - "+title if title else ""))

        # Table configuration
        self.view = QTableView()
        self.model = FloatArrayModel(self.data, fmt=format, xy_mode=xy)
        self.view.setModel(self.model)
        self.resize_to_contents()
        total_width = 0
        for k in xrange(self.data.shape[1]):
            total_width += self.view.columnWidth(k)
        total_width = min(total_width, 1024)
        view_size = self.view.size()
        self.view.viewport().resize( total_width, view_size.height() )
        self.layout.addWidget(self.view, 0, 0)

        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        
        btn = bbox.addButton("Format", QDialogButtonBox.ActionRole)
        self.connect(btn, SIGNAL("clicked()"), self.change_format )
        self.layout.addWidget(bbox, 1, 0)
        self.setMinimumSize(400, 300)
        
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        
    def resize_to_contents(self):
        if self.data.shape[0]*self.data.shape[1] <= 1000:
            # Do not resize columns and rows if data are too big
            self.view.resizeColumnsToContents()
            self.view.resizeRowsToContents()
        
    def change_format(self):
        dlg = QDialog()
        layout = QGridLayout()
        dlg.setLayout(layout)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.connect(bbox, SIGNAL("accepted()"), dlg, SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), dlg, SLOT("reject()"))
        lbl = QLabel(u"Float formatting")
        edt = QLineEdit(self.model._fmt)
        layout.addWidget(lbl, 0, 0)
        layout.addWidget(edt, 0, 1)
        layout.addWidget(bbox, 1, 0, 1, 2)
        res = dlg.exec_()
        if res:
            new_fmt = str(edt.text())
            try:
                new_fmt % 1.1
            except:
                QMessageBox.critical(self, u"Error",
                                      u"Format (%s) is incorrect" % new_fmt)
                return
            self.model.set_format(new_fmt)
            self.resize_to_contents()

    def get_array(self):
        return self.source
    
    
def main():
    """
    Array editor demo
    """
    import sys
    from PyQt4.QtGui import QApplication
    from numpy import random
    arr = random.rand(30,30)
    app = QApplication([])
    dialog = ArrayEditor( '', arr )
    dialog.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()