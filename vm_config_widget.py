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
    def __init__(self, parent=None):
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