from PySide2 import QtWidgets, QtGui, QtCore
import enum
from typing import List


class FramelessWindow(QtWidgets.QWidget):
    class Action(enum.Enum):
        MOVE = 'move'
        RESIZE_TOP = "top"
        RESIZE_RIGHT = "right"
        RESIZE_BOT = "bot"
        RESIZE_LEFT = "left"
        RESIZE_TOP_RIGHT = "top-right"
        RESIZE_TOP_LEFT = "top-left"
        RESIZE_BOT_RIGHT = "bot-right"
        RESIZE_BOT_LEFT = "bot-left"


    class ResizeOp():
        def __init__(self, action, rect, cursor) -> None:
            self.action = action
            self.rect: QtCore.QRect = rect
            self.cursor = cursor

    def __init__(self, widget: QtWidgets.QWidget, parent=None):
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        QtWidgets.QApplication.instance().installEventFilter(self)

        self._border = 3

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(widget)
        self._widget = widget

        self._title_height = 0
        self._move_anywhere = True
        self._press_pos = None
        self._press_global_pos = None
        self._action = None
        self._resize_ops: List[self.ResizeOp] = list()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.MouseMove:
            b = self._border
            pos = self.mapFromGlobal(event.globalPos())
            if QtCore.QRect(b, b, self.width()-2*b, self.height()-2*b).contains(pos):
                self.setCursor(QtCore.Qt.ArrowCursor)
            else:
                for op in self._resize_ops:
                    if op.rect.contains(event.pos()):
                        self.setCursor(op.cursor)

        return False

    def _update_resize_ops(self):
        w = self.width()
        h = self.height()
        b = self._border
        return (
            self.ResizeOp(self.Action.RESIZE_TOP, QtCore.QRect(b, 0, w-2*b, b), QtCore.Qt.SizeVerCursor),
            self.ResizeOp(self.Action.RESIZE_TOP_RIGHT, QtCore.QRect(w-b, 0, b, b), QtCore.Qt.SizeBDiagCursor),
            self.ResizeOp(self.Action.RESIZE_RIGHT, QtCore.QRect(w-b, 0, b, h-2*b), QtCore.Qt.SizeHorCursor),
            self.ResizeOp(self.Action.RESIZE_BOT_RIGHT ,QtCore.QRect(w-b, h-b, b, b), QtCore.Qt.SizeFDiagCursor),
            self.ResizeOp(self.Action.RESIZE_BOT ,QtCore.QRect(b, h-b, w-2*b, b), QtCore.Qt.SizeVerCursor),
            self.ResizeOp(self.Action.RESIZE_BOT_LEFT ,QtCore.QRect(0, h-b, b, b ), QtCore.Qt.SizeBDiagCursor),
            self.ResizeOp(self.Action.RESIZE_LEFT ,QtCore.QRect(0, b, b, h-2*b), QtCore.Qt.SizeHorCursor),
            self.ResizeOp(self.Action.RESIZE_TOP_LEFT ,QtCore.QRect(0, 0, b, b), QtCore.Qt.SizeFDiagCursor),
        )

    def is_movable_pos(self, pos: QtCore.QPoint):
        if self._move_anywhere:
            return True
        if pos.y() <= self._title_height:
            return True
        return False

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self._resize_ops = self._update_resize_ops()
        widget_geometry = QtCore.QRect(QtCore.QPoint(0,0), self.size())
        self._widget.setGeometry(widget_geometry)
        return super().showEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._resize_ops = self._update_resize_ops()
        widget_geometry = QtCore.QRect(QtCore.QPoint(0,0), self.size())
        self._widget.setGeometry(widget_geometry)
        return super().resizeEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._press_pos = event.pos()
        self._press_global_pos = event.globalPos()

        for op in self._resize_ops:
            if op.rect.contains(event.pos()):
                self.setCursor(op.cursor)
                self._action = op.action
                return

        if self.is_movable_pos(event.pos()):
            self._action = self.Action.MOVE

        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._action = None
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        geometry = self.geometry()
        if self._action is self.Action.MOVE:
            win_pos = event.globalPos() - self._press_pos
            geometry.moveTopLeft(win_pos)
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_TOP:
            geometry.setTop(event.globalY())
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_RIGHT:
            geometry.setRight(event.globalX())
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_BOT:
            geometry.setBottom(event.globalY())
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_LEFT:
            geometry.setLeft(event.globalX())
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_TOP_LEFT:
            geometry.setTopLeft(event.globalPos())
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_TOP_RIGHT:
            geometry.setTopRight(event.globalPos())
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_BOT_LEFT:
            geometry.setBottomLeft(event.globalPos())
            self.setGeometry(geometry)
            return
        if self._action is self.Action.RESIZE_BOT_RIGHT:
            geometry.setBottomRight(event.globalPos())
            self.setGeometry(geometry)
            return

        self.setCursor(QtCore.Qt.ArrowCursor)
        return super().mouseMoveEvent(event)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = FramelessWindow()
    w.setMinimumSize(100, 100)

    btn = QtWidgets.QPushButton(w, "exit")
    btn.clicked.connect(lambda: app.quit())

    w.show()
    app.exec_()
