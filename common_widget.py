"""
通用界面组件模块。

本模块提供了一些常用的界面组件和工具函数，包括：
- 布局清理功能
- 输入框状态设置
- 可选择按钮组件

主要组件:
- clean_layout: 清理布局中的所有组件
- set_lineedit_status: 设置输入框的状态和提示
- SelectButton: 可选择的按钮组件
"""

from PySide2 import QtWidgets, QtGui, QtCore

def clean_layout(layout):
    """
    清理布局中的所有组件。
    
    递归删除布局中的所有子组件，包括：
    - 移除组件与布局的关联
    - 设置组件的父对象为None
    - 延迟删除组件
    
    Args:
        layout: 要清理的布局对象
    """
    while layout.count() > 0:
        child = layout.takeAt(0)
        widget = child.widget()
        if widget:
            widget.setParent(None)
            widget.deleteLater()

def set_lineedit_status(lineedit: QtWidgets.QLineEdit, ok: bool):
    """
    设置输入框的状态和提示信息。
    
    根据输入的有效性设置：
    - 文本颜色（有效为黑色，无效为红色）
    - 错误提示（无效时显示提示气泡）
    
    Args:
        lineedit: 要设置状态的输入框组件
        ok: 输入是否有效
    """
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
    """
    可选择的按钮组件。
    
    继承自QPushButton，添加了可选择（checkable）特性。
    用于创建可以切换选中状态的按钮。
    """
    
    def __init__(self, name, parent=None):
        """
        初始化可选择按钮。
        
        Args:
            name: 按钮显示的文本
            parent: 父窗口部件，默认为None
        """
        super().__init__(name, parent)
        self.setCheckable(True)

