"""
无边框窗口模块。

本模块提供了一个自定义的无边框窗口实现，具有以下特性：
- 支持窗口移动
- 支持八个方向的窗口大小调整
- 自定义边框大小
- 可设置标题栏高度
- 支持全窗口拖动或仅标题栏拖动

主要类:
- FramelessWindow: 无边框窗口实现
"""

from PySide2 import QtWidgets, QtGui, QtCore
import enum
from typing import List


class FramelessWindow(QtWidgets.QWidget):
    """
    无边框窗口实现。
    
    提供了一个去除系统标准边框的窗口容器，自行处理窗口移动和大小调整逻辑。
    用户可以通过鼠标在窗口边缘进行大小调整，并在窗口内部拖动来移动窗口。
    
    属性:
        _border: 窗口边框大小
        _title_height: 标题栏高度
        _move_anywhere: 是否允许在窗口任意位置拖动
        _widget: 包含的内容组件
    """
    
    class Action(enum.Enum):
        """
        窗口操作类型枚举。
        
        定义了窗口可以进行的各种操作类型，包括移动和八个方向的大小调整。
        """
        MOVE = 'move'  # 移动窗口
        RESIZE_TOP = "top"  # 调整上边界
        RESIZE_RIGHT = "right"  # 调整右边界
        RESIZE_BOT = "bot"  # 调整下边界
        RESIZE_LEFT = "left"  # 调整左边界
        RESIZE_TOP_RIGHT = "top-right"  # 调整右上角
        RESIZE_TOP_LEFT = "top-left"  # 调整左上角
        RESIZE_BOT_RIGHT = "bot-right"  # 调整右下角
        RESIZE_BOT_LEFT = "bot-left"  # 调整左下角


    class ResizeOp():
        """
        窗口大小调整操作类。
        
        用于定义窗口边缘的可调整区域、对应的操作类型和鼠标光标样式。
        
        属性:
            action: 操作类型
            rect: 操作区域矩形
            cursor: 鼠标光标样式
        """
        def __init__(self, action, rect, cursor) -> None:
            """
            初始化大小调整操作。
            
            Args:
                action: 操作类型
                rect: 操作区域矩形
                cursor: 鼠标光标样式
            """
            self.action = action
            self.rect: QtCore.QRect = rect
            self.cursor = cursor

    def __init__(self, widget: QtWidgets.QWidget, parent=None):
        """
        初始化无边框窗口。
        
        设置无边框窗口标志，并添加内容组件。
        
        Args:
            widget: 要包含在窗口中的组件
            parent: 父窗口组件，默认为None
        """
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        QtWidgets.QApplication.instance().installEventFilter(self)

        self._border = 3  # 边框宽度

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(widget)
        self._widget = widget

        self._title_height = 0  # 标题栏高度
        self._move_anywhere = True  # 是否允许在窗口任意位置拖动
        self._press_pos = None  # 鼠标按下位置
        self._press_global_pos = None  # 鼠标按下的全局位置
        self._action = None  # 当前操作类型
        self._resize_ops: List[self.ResizeOp] = list()  # 大小调整操作列表

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """
        事件过滤器。
        
        处理应用程序级别的鼠标移动事件，用于更新鼠标光标样式。
        
        Args:
            watched: 被监控的对象
            event: 事件对象
            
        Returns:
            bool: 是否已处理事件
        """
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
        """
        更新大小调整操作列表。
        
        根据当前窗口大小计算八个方向的调整区域。
        
        Returns:
            tuple: 包含八个调整操作的元组
        """
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
        """
        判断指定位置是否可用于移动窗口。
        
        根据_move_anywhere和_title_height设置判断给定位置是否可以用于拖动窗口。
        
        Args:
            pos: 窗口内坐标位置
            
        Returns:
            bool: 是否可用于移动窗口
        """
        if self._move_anywhere:
            return True
        if pos.y() <= self._title_height:
            return True
        return False

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """
        显示事件处理。
        
        窗口显示时更新调整操作并设置内容组件大小。
        
        Args:
            event: 显示事件对象
        """
        self._resize_ops = self._update_resize_ops()
        widget_geometry = QtCore.QRect(QtCore.QPoint(0,0), self.size())
        self._widget.setGeometry(widget_geometry)
        return super().showEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """
        大小调整事件处理。
        
        窗口大小改变时更新调整操作并调整内容组件大小。
        
        Args:
            event: 大小调整事件对象
        """
        self._resize_ops = self._update_resize_ops()
        widget_geometry = QtCore.QRect(QtCore.QPoint(0,0), self.size())
        self._widget.setGeometry(widget_geometry)
        return super().resizeEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        鼠标按下事件处理。
        
        记录鼠标按下位置，并根据位置确定操作类型（移动或调整大小）。
        
        Args:
            event: 鼠标事件对象
        """
        self._press_pos = event.pos()
        self._press_global_pos = event.globalPos()

        # 检查是否在调整区域内
        for op in self._resize_ops:
            if op.rect.contains(event.pos()):
                self.setCursor(op.cursor)
                self._action = op.action
                return

        # 检查是否可移动
        if self.is_movable_pos(event.pos()):
            self._action = self.Action.MOVE

        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        鼠标释放事件处理。
        
        重置当前操作类型。
        
        Args:
            event: 鼠标事件对象
        """
        self._action = None
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        鼠标移动事件处理。
        
        根据当前操作类型执行窗口移动或大小调整。
        
        Args:
            event: 鼠标事件对象
        """
        geometry = self.geometry()
        
        # 处理移动操作
        if self._action is self.Action.MOVE:
            win_pos = event.globalPos() - self._press_pos
            geometry.moveTopLeft(win_pos)
            self.setGeometry(geometry)
            return
            
        # 处理各方向的大小调整
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
    """主程序入口，用于测试无边框窗口。"""
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = FramelessWindow()
    w.setMinimumSize(100, 100)

    btn = QtWidgets.QPushButton(w, "exit")
    btn.clicked.connect(lambda: app.quit())

    w.show()
    app.exec_()
