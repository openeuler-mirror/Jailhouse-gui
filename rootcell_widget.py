import logging
from optparse import Option
from threading import TIMEOUT_MAX
from typing import Optional
from PySide2 import QtWidgets, QtCore
from forms.ui_rootcell_widget import Ui_RootCellWidget
from jh_resource import MemRegion, ResourceRootCell, Resource
from mem_edit_widget import MemEditWidget
from tip_widget import TipMgr
import utils

tip_hyp = """\
hypervisor固件所在的物理地址空间, 该空间应该位于DDR中
地址和大小和填入 数字值 (如1024) 和 常量表达式 (如1024*1204)
另外大小支持 <n>*KB <n>*MB 格式
"""

tip_vpci_irq = """\
指定虚拟PCI总线的起始中断号, Root Cell使用该中断号, 其他各个Guest Cell的虚拟PCI中断号按顺序递增
"""

tip_mem_msg = """\
显示内存大小，此处不是内存配置，内存配置需要在设备树中配置，是作为内存布局参考信息展示，\
后续考虑将配置信息作为参数传入到相关逻辑中, 后续逐步实现。目前地址从0x80000000开始, 大小1GB
"""

tip_mmconfig_base = """\
配置虚拟PCI配置空间的基地址, Guest Cell中应该使用该地址作为PCIE配置空间基地址, 通过枚举这个配置空间, Guest Cell可以获取到ivshmem设备和分配的PCI设备
"""

tip_mmconfig_bus_count = """\
配置虚拟PCI配置空间的总线数量, 每个BDF占用的配置空间为4KB, 每个总线上最多256个BDF, 因配置空间总大小为 4KB*256*总线数量, Guest Cell枚举时不能超过这个大小
"""

tip_mmconfig_domain = """\
虚拟PCI的domain, 该值仅用于Root Cell, Root Cell同时存在物理PCI总线和虚拟虚拟PCI总线, 需要通过domain区分
"""


class RootCellWidget(QtWidgets.QWidget):
    logger = logging.getLogger("RootCellWidget")
    not_use = "不使用"

    def __init__(self, parent=None):
        super().__init__(parent)

        self._rootcell: Optional[ResourceRootCell] = None
        self._ui = Ui_RootCellWidget()
        self._ui.setupUi(self)
        self._ui.combobox_debug_console.setView(QtWidgets.QListView())

        # FIXME 强制总线个数为1, 不能编辑
        self._ui.lineedit_pci_mmconfig_count.setEnabled(False)

        self._ui.combobox_debug_console.currentIndexChanged.connect(self._on_debug_console_changed)
        self._ui.lineedit_hyp_addr.editingFinished.connect(self._on_hyp_update)
        self._ui.lineedit_hyp_size.editingFinished.connect(self._on_hyp_update)
        self._ui.lineedit_name.editingFinished.connect(self._on_name_changed)

        self._ui.lineedit_pci_mmconfig_addr.editingFinished.connect(self._on_pci_mmconfig_update)
        self._ui.lineedit_pci_mmconfig_count.editingFinished.connect(self._on_pci_mmconfig_update)
        self._ui.lineedit_pci_mmconfig_domain.editingFinished.connect(self._on_pci_mmconfig_update)

        self._ui.lineedit_vpci_irq_base.editingFinished.connect(self._on_vpci_irq_edit_finished)

        self._sysmem_region = MemEditWidget(self)
        self._ui.frame_ram.layout().addWidget(self._sysmem_region)
        self._sysmem_region.signal_changed.connect(self._on_sysmem_changed)

        TipMgr.add(self._ui.combobox_debug_console, "调试串口")
        TipMgr.add(self._ui.lineedit_hyp_addr, tip_hyp)
        TipMgr.add(self._ui.lineedit_hyp_size, tip_hyp)
        TipMgr.add(self._ui.lineedit_vpci_irq_base, tip_vpci_irq)
        TipMgr.add(self._ui.lineedit_pci_mmconfig_addr, tip_mmconfig_base)
        TipMgr.add(self._ui.lineedit_pci_mmconfig_count, tip_mmconfig_bus_count)
        TipMgr.add(self._ui.lineedit_pci_mmconfig_domain, tip_mmconfig_domain)

        self._ui.frame_ram.setFocusPolicy(QtCore.Qt.ClickFocus)
        TipMgr.add(self._ui.frame_ram, tip_mem_msg)

    def set_rootcell(self, rootcell: ResourceRootCell):
        if rootcell is None:
            self._rootcell = None
            return

        rsc_vm: Resource = rootcell.parent()
        rsc: Resource = rsc_vm.parent()
        self._rootcell = None

        self._ui.lineedit_name.setText(rootcell.name())

        self._ui.combobox_debug_console.blockSignals(True)
        self._ui.combobox_debug_console.clear()
        self._ui.combobox_debug_console.addItem(self.not_use)
        for dev in rsc.platform().cpu().devices():
            if dev.name().startswith("uart"):
                self._ui.combobox_debug_console.addItem(dev.name())
        debug_console = rootcell.get_debug_console()
        if debug_console:
            self._ui.combobox_debug_console.setCurrentText(debug_console)
        else:
            self._ui.combobox_debug_console.setCurrentText(self.not_use)
        self._ui.combobox_debug_console.blockSignals(False)

        self._ui.lineedit_hyp_addr.setText(utils.to_human_addr(rootcell.hypervisor().addr()))
        self._ui.lineedit_hyp_size.setText(utils.to_human_size(rootcell.hypervisor().size()))
        self._sysmem_region.set_regions(rootcell.system_mem())
        self._ui.lineedit_vpci_irq_base.setText(str(rootcell.vpci_irq_base()))

        self._ui.lineedit_pci_mmconfig_addr.setText(utils.to_human_addr(rootcell.pci_mmconfig().base_addr))
        self._ui.lineedit_pci_mmconfig_count.setText(str(rootcell.pci_mmconfig().bus_count))
        self._ui.lineedit_pci_mmconfig_domain.setText(str(rootcell.pci_mmconfig().domain))

        self._rootcell = rootcell

    def _on_name_changed(self):
        if self._rootcell is None:
            return

        name = self._ui.lineedit_name.text().strip()
        if not ResourceRootCell.check_name(name):
            self.logger.error(f"invalid root name: {name}")
            return
        self._rootcell.set_name(name)

    def _on_debug_console_changed(self, index):
        if self._rootcell is None:
            return
        name = self._ui.combobox_debug_console.currentText()
        if name == self.not_use:
            self._rootcell.set_debug_console(None)
        else:
            self._rootcell.set_debug_console(name)

    def _on_hyp_update(self):
        if self._rootcell is None:
            return

        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(w.text())
        if value is None:
            self.logger.error(f"invalid value {w.text()}")
            return

        addr = utils.from_human_num(self._ui.lineedit_hyp_addr.text())
        size = utils.from_human_num(self._ui.lineedit_hyp_size.text())
        if addr is None or size is None:
            self.logger.error(f"invalid value")
            return

        hyp = MemRegion(addr, size)
        self._rootcell.set_hypervisor(hyp)

    def _on_pci_mmconfig_update(self):
        if self._rootcell is None:
            return
        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(w.text())
        if value is None:
            self.logger.error(f"invalid value {w.text()}")
            return

        pci_mmconfig = self._rootcell.pci_mmconfig()
        if w is self._ui.lineedit_pci_mmconfig_addr:
            pci_mmconfig.base_addr = value
        if w is self._ui.lineedit_pci_mmconfig_count:
            pci_mmconfig.bus_count = value
        if w is self._ui.lineedit_pci_mmconfig_domain:
            pci_mmconfig.domain = value
        self._rootcell.set_pci_mmconfig(pci_mmconfig)

    def _on_vpci_irq_edit_finished(self):
        if self._rootcell is None:
            return

        txt = self._ui.lineedit_vpci_irq_base.text()
        try:
            irq = int(txt)
            if irq < 32:
                self._ui.lineedit_vpci_irq_base.setText(str(self._rootcell.vpci_irq_base()))
                return
        except:
            self._ui.lineedit_vpci_irq_base.setText(str(self._rootcell.vpci_irq_base()))
            return

        self._rootcell.set_vpci_irq_base(irq)

    def _on_sysmem_changed(self):
        if self._rootcell is None:
            return
        regions = self._sysmem_region.get_value()
        self.logger.debug(f"set system memory: {regions}")
        self._rootcell.set_system_mem(regions)
