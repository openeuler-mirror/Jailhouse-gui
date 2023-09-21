import imp
from typing import Optional
from PySide2 import QtWidgets, QtGui, QtCore
from jh_resource import ResourceCPU
from forms.ui_cpu_widget import Ui_CPUWidget
from jh_resource import PlatformMgr, ResourceSignals


class CPUWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_CPUWidget()
        self._ui.setupUi(self)
        self._cpu: Optional[ResourceCPU] = None

        self._ui.tablewidget_device.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)
        self._ui.tablewidget_device.setSizeAdjustPolicy(QtWidgets.QScrollArea.AdjustToContents)
        self._ui.tablewidget_regions.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)
        self._ui.tablewidget_regions.setSizeAdjustPolicy(QtWidgets.QScrollArea.AdjustToContents)

        self._ui.tablewidget_regions.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self._ui.tablewidget_device.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        self._ui.btn_update_from_plt.clicked.connect(self._on_update_from_plt)
        ResourceSignals.modified.connect(self._on_rsc_modified)

    def set_cpu(self, cpu: ResourceCPU):
        self._cpu = cpu
        self._update()

        self._ui.tablewidget_device.setFixedHeight(self._ui.tablewidget_device.sizeHint().height())
        self._ui.tablewidget_regions.setFixedHeight(self._ui.tablewidget_regions.sizeHint().height())

    def _update(self):
        cpu: ResourceCPU = self._cpu
        if cpu is None:
            self._ui.lineedit_gicc.clear()
            self._ui.lineedit_gicd.clear()
            self._ui.lineedit_gich.clear()
            self._ui.lineedit_gicr.clear()
            self._ui.lineedit_gicv.clear()
            self._ui.lineedit_cpu_count.clear()
            self._ui.tablewidget_device.clearContents()
            self._ui.tablewidget_regions.clearContents()
            return

        self._ui.lineedit_cpu_name.setText(cpu.name())
        self._ui.lineedit_cpu_count.setText(str(cpu.cpu_count()))
        self._ui.lineedit_gicc.setText(hex(cpu.gicc_base()))
        self._ui.lineedit_gicd.setText(hex(cpu.gicd_base()))
        self._ui.lineedit_gich.setText(hex(cpu.gich_base()))
        self._ui.lineedit_gicr.setText(hex(cpu.gicr_base()))
        self._ui.lineedit_gicv.setText(hex(cpu.gicv_base()))

        self._ui.tablewidget_device.clearContents()
        self._ui.tablewidget_device.setRowCount(len(cpu.devices()))
        for idx in range(len(cpu.devices())):
            dev = cpu.devices()[idx]
            self._ui.tablewidget_device.setItem(idx, 0, QtWidgets.QTableWidgetItem(dev.name()))
            self._ui.tablewidget_device.setItem(idx, 1, QtWidgets.QTableWidgetItem(hex(dev.addr())))
            self._ui.tablewidget_device.setItem(idx, 2, QtWidgets.QTableWidgetItem(hex(dev.size())))
            irq_str = ', '.join(map(lambda x: str(x), dev.irq()))
            self._ui.tablewidget_device.setItem(idx, 3, QtWidgets.QTableWidgetItem(irq_str))

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
        if sender is not self._cpu:
            return
        self._update()

    def _on_update_from_plt(self):
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
