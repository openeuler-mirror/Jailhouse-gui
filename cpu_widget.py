"""
CPU配置信息显示界面模块。

本模块提供了用于显示和管理CPU配置信息的图形界面组件，包括：
- CPU基本信息显示（名称、核心数等）
- GIC（Generic Interrupt Controller）配置显示
- 设备列表显示（地址、大小、中断等）
- 内存区域配置显示
- 平台配置更新功能

主要类:
- CPUWidget: CPU配置信息显示界面组件
"""

import imp
from typing import Optional
from PySide2 import QtWidgets, QtGui, QtCore
from jh_resource import ResourceCPU
from forms.ui_cpu_widget import Ui_CPUWidget
from jh_resource import PlatformMgr, ResourceSignals


class CPUWidget(QtWidgets.QWidget):
    """
    CPU配置信息显示界面组件。
    
    提供完整的CPU配置信息显示界面，包括：
    - CPU名称和核心数
    - GIC各组件基地址
    - 设备列表（名称、地址、大小、中断）
    - 内存区域列表（名称、属性、类型、地址、大小）
    
    属性:
        _cpu: 当前显示的CPU资源对象
    """
    
    def __init__(self, parent=None):
        """
        初始化CPU配置信息显示界面。
        
        设置表格显示属性并连接信号槽。
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._ui = Ui_CPUWidget()
        self._ui.setupUi(self)
        self._cpu: Optional[ResourceCPU] = None

        # 设置表格显示属性
        self._ui.tablewidget_device.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)
        self._ui.tablewidget_device.setSizeAdjustPolicy(QtWidgets.QScrollArea.AdjustToContents)
        self._ui.tablewidget_regions.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)
        self._ui.tablewidget_regions.setSizeAdjustPolicy(QtWidgets.QScrollArea.AdjustToContents)

        self._ui.tablewidget_regions.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self._ui.tablewidget_device.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        # 连接信号槽
        self._ui.btn_update_from_plt.clicked.connect(self._on_update_from_plt)
        ResourceSignals.modified.connect(self._on_rsc_modified)

    def set_cpu(self, cpu: ResourceCPU):
        """
        设置要显示的CPU资源对象。
        
        更新界面显示并调整表格高度。
        
        Args:
            cpu: CPU资源对象
        """
        self._cpu = cpu
        self._update()

        self._ui.tablewidget_device.setFixedHeight(self._ui.tablewidget_device.sizeHint().height())
        self._ui.tablewidget_regions.setFixedHeight(self._ui.tablewidget_regions.sizeHint().height())

    def _update(self):
        """
        更新界面显示。
        
        根据当前CPU资源对象更新所有显示内容：
        1. 基本信息（名称、核心数）
        2. GIC配置信息
        3. 设备列表
        4. 内存区域列表
        """
        cpu: ResourceCPU = self._cpu
        if cpu is None:
            # 清空所有显示内容
            self._ui.lineedit_gicc.clear()
            self._ui.lineedit_gicd.clear()
            self._ui.lineedit_gich.clear()
            self._ui.lineedit_gicr.clear()
            self._ui.lineedit_gicv.clear()
            self._ui.lineedit_cpu_count.clear()
            self._ui.tablewidget_device.clearContents()
            self._ui.tablewidget_regions.clearContents()
            return

        # 更新基本信息和GIC配置
        self._ui.lineedit_cpu_name.setText(cpu.name())
        self._ui.lineedit_cpu_count.setText(str(cpu.cpu_count()))
        self._ui.lineedit_gicc.setText(hex(cpu.gicc_base()))
        self._ui.lineedit_gicd.setText(hex(cpu.gicd_base()))
        self._ui.lineedit_gich.setText(hex(cpu.gich_base()))
        self._ui.lineedit_gicr.setText(hex(cpu.gicr_base()))
        self._ui.lineedit_gicv.setText(hex(cpu.gicv_base()))

        # 更新设备列表
        self._ui.tablewidget_device.clearContents()
        self._ui.tablewidget_device.setRowCount(len(cpu.devices()))
        for idx in range(len(cpu.devices())):
            dev = cpu.devices()[idx]
            self._ui.tablewidget_device.setItem(idx, 0, QtWidgets.QTableWidgetItem(dev.name()))
            self._ui.tablewidget_device.setItem(idx, 1, QtWidgets.QTableWidgetItem(hex(dev.addr())))
            self._ui.tablewidget_device.setItem(idx, 2, QtWidgets.QTableWidgetItem(hex(dev.size())))
            irq_str = ', '.join(map(lambda x: str(x), dev.irq()))
            self._ui.tablewidget_device.setItem(idx, 3, QtWidgets.QTableWidgetItem(irq_str))

        # 更新内存区域列表
        self._ui.tablewidget_regions.clearContents()
        self._ui.tablewidget_regions.setRowCount(len(cpu.regions()))
        for idx in range(len(cpu.regions())):
            region = cpu.regions()[idx]
            self._ui.tablewidget_regions.setItem(idx, 0, QtWidgets.QTableWidgetItem(region.name()))
            self._ui.tablewidget_regions.setItem(idx, 1, QtWidgets.QTableWidgetItem(region.attr()))
            self._ui.tablewidget_regions.setItem(idx, 2, QtWidgets.QTableWidgetItem(region.type().value))
            self._ui.tablewidget_regions.setItem(idx, 3, QtWidgets.QTableWidgetItem(hex(region.addr())))
            self._ui.tablewidget_regions.setItem(idx, 4, QtWidgets.QTableWidgetItem(hex(region.size())))

    def _on_rsc_modified(self, sender, **kwargs):
        """
        处理资源修改事件。
        
        当CPU资源对象被修改时更新界面显示。
        
        Args:
            sender: 发送信号的对象
            kwargs: 附加参数
        """
        if sender is not self._cpu:
            return
        self._update()

    def _on_update_from_plt(self):
        """
        处理从平台更新按钮点击事件。
        
        从平台管理器获取最新的CPU配置并更新当前CPU资源对象。
        """
        if self._cpu is None:
            return

        cpu: PlatformMgr.CPU = PlatformMgr.get_instance().find_cpu(self._cpu.name())
        if cpu is None:
            self.logger.error(f"can not find cpu {self._cpu.name()} from platform")
            return

        if not self._cpu.from_dict(cpu.value):
            self.logger.error(f"update cpu failed.")
            return

        self._cpu.set_modified()
