"""
CPU核心选择编辑界面模块。

本模块提供了用于选择和编辑CPU核心分配的图形界面组件。主要功能包括：
- 显示可用的CPU核心列表
- 支持多选CPU核心
- 动态调整CPU核心数量
- 可编辑状态控制

主要类:
- CPUEditWidget: CPU核心选择编辑界面组件
"""

from PySide2 import QtWidgets, QtCore
from typing import Set, List
from forms.ui_cpu_edit_widget import Ui_CPUEditWidget
from flowlayout import FlowLayout
from common_widget import SelectButton, clean_layout


class CPUEditWidget(QtWidgets.QWidget):
    """
    CPU核心选择编辑界面组件。
    
    提供图形化的CPU核心选择界面，使用流式布局展示CPU核心按钮。
    每个CPU核心都可以独立选择或取消选择。
    
    信号:
        cpus_changed: 当CPU核心选择发生变化时发出
    
    属性:
        _editable: 是否可编辑
        _items: CPU核心选择按钮列表
        _cpu_count: CPU核心总数
    """
    
    cpus_changed = QtCore.Signal()

    def __init__(self, parent=None):
        """
        初始化CPU核心选择编辑界面。
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._ui = Ui_CPUEditWidget()
        self._ui.setupUi(self)
        self._ui.frame_ops.hide()
        self._layout = FlowLayout(self._ui.frame_cpus)

        self._editable = True
        self._items: List[SelectButton] = list()
        self._cpu_count = 0

    def set_cpu_count(self, count):
        """
        设置CPU核心数量。
        
        根据指定的数量创建对应数量的选择按钮。
        
        Args:
            count: CPU核心数量
        """
        self._cpu_count = count
        clean_layout(self._layout)
        self._items.clear()

        for i in range(count):
            item = SelectButton(str(i), self._ui.frame_cpus)
            self._layout.addWidget(item)
            item.clicked.connect(self._on_item_changed)
            self._items.append(item)

    def set_editable(self, editable: bool):
        """
        设置是否可编辑。
        
        控制所有CPU核心选择按钮的可用状态。
        
        Args:
            editable: 是否允许编辑
        """
        for item in self._items:
            item.setEnabled(editable)

    def set_cpus(self, cpus: Set[int]):
        """
        设置选中的CPU核心。
        
        根据提供的CPU核心集合更新选择状态。
        
        Args:
            cpus: 要选中的CPU核心索引集合
        """
        for idx, item in enumerate(self._items):
            item.setChecked(idx in cpus)

    def get_cpus(self) -> Set[int]:
        """
        获取当前选中的CPU核心。
        
        Returns:
            Set[int]: 当前选中的CPU核心索引集合
        """
        cpus = set()
        for idx, item in enumerate(self._items):
            if item.isChecked():
                cpus.add(idx)
        return cpus

    def _on_item_changed(self):
        """
        处理CPU核心选择变化事件。
        
        当任何CPU核心的选择状态发生改变时，发出cpus_changed信号。
        """
        cpus = list()
        for idx, item in enumerate(self._items):
            if item.isChecked():
                cpus.append(idx)

        self.cpus_changed.emit()


if __name__ == '__main__':
    """主程序入口，用于测试CPU核心选择编辑界面。"""
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = CPUEditWidget()
    w.set_cpu_count(4)
    w.show()
    app.exec_()
    pass