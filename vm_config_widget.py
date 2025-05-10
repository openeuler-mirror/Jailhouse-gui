from typing import Optional
from forms.ui_vm_config import Ui_VMConfigWidget
from PySide2 import QtWidgets
from jh_resource import ResourceJailhouse
from cpu_widget import CPUWidget
from board_widget import BoardWidget
from rootcell_widget import RootCellWidget
from ivshmem_widget import IVShMemWidget
from pci_device_widget import PCIDevicesWidget
from guestcell_widget import GuestCellsWidget


class VMConfigWidget(QtWidgets.QWidget):
    """
    虚拟机配置界面部件。
    
    提供用于配置Jailhouse虚拟机的界面，包括根单元格、共享内存、PCI设备和客户单元格等配置页面。
    使用标签按钮切换不同的配置页面。
    
    Attributes:
        _ui: 用户界面对象。
        _vm_config: 当前配置的虚拟机资源对象。
        _black_page: 空白页面。
        _rootcell_page: 根单元格配置页面。
        _ivshmem_page: 共享内存配置页面。
        _pci_device_page: PCI设备配置页面。
        _guestcells_page: 客户单元格配置页面。
    """
    def __init__(self, parent=None):
        """
        初始化虚拟机配置界面部件。
        
        创建子页面并设置信号连接。
        
        Args:
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_VMConfigWidget()
        self._ui.setupUi(self)

        self._vm_config: Optional[ResourceJailhouse] = None

        self._black_page = QtWidgets.QWidget(self)
        self._rootcell_page = RootCellWidget(self)
        self._ivshmem_page = IVShMemWidget(self)
        self._pci_device_page = PCIDevicesWidget(self)
        self._guestcells_page = GuestCellsWidget(self)
        self._ui.stacked_widget.addWidget(self._black_page)
        self._ui.stacked_widget.addWidget(self._rootcell_page)
        self._ui.stacked_widget.addWidget(self._ivshmem_page)
        self._ui.stacked_widget.addWidget(self._pci_device_page)
        self._ui.stacked_widget.addWidget(self._guestcells_page)

        self._ui.btn_rootcell.clicked.connect(self._on_submenu)
        self._ui.btn_ivshmem.clicked.connect(self._on_submenu)
        self._ui.btn_pci_device.clicked.connect(self._on_submenu)
        self._ui.btn_guestcells.clicked.connect(self._on_submenu)

    def set_vm_config(self, vm_config: ResourceJailhouse):
        """
        设置要显示和配置的虚拟机资源。
        
        将虚拟机资源传递给各个子页面，并显示根单元格配置页面。
        如果传入None，则清空所有配置并显示空白页面。
        
        Args:
            vm_config: 虚拟机资源对象，包含所有相关配置。
        """
        self._rootcell_page.set_rootcell(None)
        self._ivshmem_page.set_comm(None)
        self._pci_device_page.set_pci_devices(None)
        self._guestcells_page.set_guestcells(None)
        if vm_config is None:
            self._vm_config = None
            self._ui.stacked_widget.setCurrentWidget(self._black_page)
            return

        self._rootcell_page.set_rootcell(vm_config.rootcell())
        self._ivshmem_page.set_comm(vm_config.ivshmem())
        self._pci_device_page.set_pci_devices(vm_config.pci_devices())
        self._guestcells_page.set_guestcells(vm_config.guestcells())

        self._ui.btn_rootcell.setChecked(True)
        self._ui.stacked_widget.setCurrentWidget(self._rootcell_page)

        self._vm_config = vm_config

    def _on_submenu(self):
        """
        处理子菜单按钮点击事件。
        
        根据当前选中的菜单按钮，切换显示相应的配置页面。
        """
        if self._vm_config is None:
            return
        if self._ui.btn_rootcell.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._rootcell_page)
        if self._ui.btn_ivshmem.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._ivshmem_page)
        if self._ui.btn_pci_device.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._pci_device_page)
        if self._ui.btn_guestcells.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._guestcells_page)