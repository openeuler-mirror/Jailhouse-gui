from PySide2 import QtWidgets, QtGui, QtCore

def clean_layout(layout):
    while layout.count() > 0:
        child = layout.takeAt(0)
        widget = child.widget()
        if widget:
            widget.setParent(None)
            widget.deleteLater()

def set_lineedit_status(lineedit: QtWidgets.QLineEdit, ok: bool):
        pos = lineedit.mapToGlobal(QtCore.QPoint(0, lineedit.height()))
        palette = lineedit.palette()
        if ok:
            QtWidgets.QToolTip.hideText()
            palette.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
            lineedit.setPalette(palette)
        else:
            QtWidgets.QToolTip.showText(pos, "输入有误", lineedit)
            palette.setColor(QtGui.QPalette.Text, QtCore.Qt.red)
            lineedit.setPalette(palette)

class SelectButton(QtWidgets.QPushButton):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.setCheckable(True)

