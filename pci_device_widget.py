import logging
from typing import Optional
from PySide2 import QtWidgets, QtCore
from jh_resource import ResourcePCIDevice, ResourcePCIDeviceList
from common_widget import clean_layout
from rpc_server.rpc_client import RPCClient
from rpc_server.pci_device import PCICapID, PCIExtCapID
from forms.ui_pci_device_widget import Ui_PCIDeviceWidget
from forms.ui_pci_devices_widget import Ui_PCIDevicesWidget
from forms.ui_pci_device_item import Ui_PCIDeviceItemWidget
from forms.ui_pci_cap_widget import Ui_PCICapWidget
from forms.ui_pci_bar_widget import Ui_PCIBarWidget


class PCICapWidget(QtWidgets.QWidget):
    """
    PCI设备能力显示部件。
    
    用于显示PCI设备的单个能力(Capability)信息，包括ID、描述、起始地址和长度。
    
    Attributes:
        _ui: 用户界面对象。
        _cap: PCI能力对象。
    """
    def __init__(self, cap: ResourcePCIDevice.PCICap, parent=None):
        """
        初始化PCI能力显示部件。
        
        Args:
            cap: PCI能力对象，包含能力的ID、起始地址、长度等信息。
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_PCICapWidget()
        self._ui.setupUi(self)

        self._cap = cap

        cap_desc = ""
        if cap.is_extended():
            cap_id = PCIExtCapID.from_value(cap.id())
        else:
            cap_id = PCICapID.from_value(cap.id())
        if cap_id is not None:
            cap_desc = cap_id.descript()

        cap_name = f'0x{cap.id():02x}  ' + cap_desc

        self._ui.label_id_or_name.setText(cap_name)
        self._ui.lineedit_start.setText(str(cap.start()))
        self._ui.lineedit_len.setText(str(cap.len()))
        self._ui.lineedit_start.setEnabled(False)
        self._ui.lineedit_len.setEnabled(False)


class PCIBarWidget(QtWidgets.QWidget):
    """
    PCI基址寄存器(BAR)显示部件。
    
    用于显示PCI设备的单个基址寄存器信息，包括地址、大小、类型和掩码。
    
    Attributes:
        _ui: 用户界面对象。
        _bar: PCI基址寄存器对象。
    """
    def __init__(self, bar: ResourcePCIDevice.PCIBar, parent=None):
        """
        初始化PCI基址寄存器显示部件。
        
        Args:
            bar: PCI基址寄存器对象，包含地址、大小、类型和掩码等信息。
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_PCIBarWidget()
        self._ui.setupUi(self)

        self._bar = bar
        self._ui.label_addr.setText(hex(bar.start()))
        self._ui.label_size.setText(hex(bar.size()))
        self._ui.label_type.setText(bar.type())
        self._ui.label_mask.setText(hex(bar.mask()))


class PCIDeviceWidget(QtWidgets.QWidget):
    """
    PCI设备详细信息显示部件。
    
    用于显示单个PCI设备的详细信息，包括设备基本信息、能力和基址寄存器。
    
    Attributes:
        _ui: 用户界面对象。
        _caps_layout: 能力列表的布局。
        _bars_layout: 基址寄存器列表的布局。
        _pcidev: PCI设备对象。
    """
    def __init__(self, parent=None):
        """
        初始化PCI设备详细信息显示部件。
        
        Args:
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_PCIDeviceWidget()
        self._ui.setupUi(self)

        self._caps_layout = QtWidgets.QVBoxLayout(self._ui.frame_caps)
        self._bars_layout = QtWidgets.QVBoxLayout(self._ui.frame_bars)

        self._pcidev: Optional[ResourcePCIDevice] = None

    def set_resource(self, rsc: ResourcePCIDevice):
        """
        设置要显示的PCI设备资源。
        
        Args:
            rsc: PCI设备资源对象。
        """
        self._pcidev = rsc
        self._update()

    def _update(self):
        """
        更新界面显示。
        
        根据当前的PCI设备对象更新界面上的信息。
        
        Returns:
            bool: 如果更新成功则返回True，否则返回False。
        """
        if self._pcidev is None:
            return False

        bdf = self._pcidev.bdf()
        self._ui.label_name.setText(self._pcidev.name())
        self._ui.label_path.setText(self._pcidev.path())
        self._ui.label_domain_value.setText(str(self._pcidev.domain()))
        self._ui.label_bus_value.setText(str(bdf[0]))
        self._ui.label_device_value.setText(str(bdf[1]))
        self._ui.label_func_value.setText(str(bdf[2]))

        clean_layout(self._caps_layout)
        for cap in self._pcidev.caps():
            w = PCICapWidget(cap)
            self._caps_layout.addWidget(w)

        clean_layout(self._bars_layout)
        for bar in self._pcidev.bars():
            w = PCIBarWidget(bar)
            self._bars_layout.addWidget(w)


class PCIDeviceItemWidget(QtWidgets.QWidget):
    """
    PCI设备列表项显示部件。
    
    用于在设备列表中显示单个PCI设备的简要信息。
    
    Attributes:
        _ui: 用户界面对象。
    """
    def __init__(self, rsc: ResourcePCIDevice, parent=None):
        """
        初始化PCI设备列表项显示部件。
        
        Args:
            rsc: PCI设备资源对象。
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_PCIDeviceItemWidget()
        self._ui.setupUi(self)

        self._ui.label_name.setText(rsc.name())
        self._ui.label_path.setText(rsc.path())

class PCIDeviceListWidget(QtWidgets.QWidget):
    """
    PCI设备列表显示部件。
    
    用于显示多个PCI设备的列表。
    
    Attributes:
        _ui: 用户界面对象。
        _item_layout: 列表项的布局。
        _pcidevs: PCI设备列表对象。
        logger: 日志记录器。
    """
    logger = logging.getLogger("PCIDeviceListWidget")

    def __init__(self, parent=None):
        """
        初始化PCI设备列表显示部件。
        
        Args:
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_PCIDevicesWidget()
        self._ui.setupUi(self)
        self._ui.btn_update.clicked.connect(self._on_update)
        self._item_layout = QtWidgets.QVBoxLayout(self._ui.frame_items)

        self._pcidevs: Optional[ResourcePCIDeviceList] = None

        client: RPCClient = RPCClient.get_instance()
        self._ui.btn_update.setEnabled(client.is_connected())
        client.state_changed.connect(self._on_rpc_client_state_changed)

    def set_resource(self, resource: ResourcePCIDeviceList):
        """
        设置要显示的PCI设备列表资源。
        
        Args:
            resource: PCI设备列表资源对象。
        """
        self._pcidevs = resource
        self._update()

    def _update(self):
        """
        更新界面显示。
        
        清空布局并根据当前的PCI设备列表更新界面。
        """
        # 清空
        clean_layout(self._item_layout)
        if self._pcidevs is None:
            return

        for i in range(self._pcidevs.device_count()):
            pci_dev = self._pcidevs.device_at(i)
            item_widget = PCIDeviceItemWidget(pci_dev)
            self._item_layout.addWidget(item_widget)

    def _on_rpc_client_state_changed(self, sender):
        """
        处理RPC客户端状态变化事件。
        
        当RPC客户端连接状态改变时，更新更新按钮的可用性。
        
        Args:
            sender: 信号发送者。
        """
        if RPCClient.get_instance() is not sender:
            return

        client: RPCClient = sender
        self._ui.btn_update.setEnabled(client.is_connected())

    def _on_update(self):
        """
        处理更新按钮点击事件。
        
        从RPC服务器获取最新的PCI设备列表，并更新显示。
        """
        client: RPCClient = RPCClient.get_instance()
        if not client.is_connected():
            return

        if self._pcidevs is None:
            return

        # 清空
        clean_layout(self._item_layout)

        result = client.pci_devices()
        if result is None:
            self.logger.error("get pci device failed.")
            return
        if not result.status:
            self.logger.error(f"get pci device failed. {result.message}")
            return
        pci_devices = result.result

        self._pcidevs.remove_all_device()

        for pci in pci_devices:
            # 过滤桥设备
            if not isinstance(pci, dict):
                continue
            dev_type: str = pci.get('type')
            if dev_type == 'bridge':
                continue

            pci_dev = self._pcidevs.add_device(pci)
            if pci_dev is None:
                self.logger.error(f"add device failed {pci_dev}.")
                continue

        self._update()

class PCIDevicesWidget(QtWidgets.QWidget):
    """
    PCI设备管理部件。
    
    用于显示和管理PCI设备列表，提供设备详情查看和更新功能。
    
    Attributes:
        _ui: 用户界面对象。
        _pcidevs: PCI设备列表对象。
        logger: 日志记录器。
    """
    logger = logging.getLogger("PCIDeviceListWidget")

    def __init__(self, parent=None):
        """
        初始化PCI设备管理部件。
        
        Args:
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_PCIDevicesWidget()
        self._ui.setupUi(self)
        self._ui.btn_update.clicked.connect(self._on_update)

        self._pcidevs: Optional[ResourcePCIDeviceList] = None

        client: RPCClient = RPCClient.get_instance()
        self._ui.btn_update.setEnabled(client.is_connected())
        client.state_changed.connect(self._on_rpc_client_state_changed)

        self._ui.listwidget_pci_devices.currentRowChanged.connect(self._on_pcidevice_selected)

        self._ui.tablewidget_caps.verticalHeader().hide()
        self._ui.tablewidget_caps.setSizeAdjustPolicy(QtWidgets.QScrollArea.AdjustToContents)

        self._ui.tablewidget_bars.verticalHeader().hide()
        self._ui.tablewidget_bars.setSizeAdjustPolicy(QtWidgets.QScrollArea.AdjustToContents)

    def set_pci_devices(self, resource: ResourcePCIDeviceList):
        """
        设置要显示的PCI设备列表。
        
        Args:
            resource: PCI设备列表资源对象。
        """
        self._pcidevs = resource
        self._update()

    def _update(self):
        """
        更新界面显示。
        
        清空列表并根据当前的PCI设备列表更新界面显示。
        """
        self._ui.listwidget_pci_devices.clear()
        if self._pcidevs is None:
            return
        for i in range(self._pcidevs.device_count()):
            pci_dev = self._pcidevs.device_at(i)
            txt = f'{pci_dev.name()}\n{pci_dev.path()}'
            item = QtWidgets.QListWidgetItem(txt)
            self._ui.listwidget_pci_devices.addItem(item)

        fixed_height = self._ui.listwidget_pci_devices.sizeHintForRow(0) * self._ui.listwidget_pci_devices.count()
        self._ui.listwidget_pci_devices.setFixedHeight(fixed_height+5)
        if self._pcidevs.device_count() > 0:
            self._ui.listwidget_pci_devices.setCurrentRow(0)
            self._update_pci_device_info(self._pcidevs.device_at(0))

    def _update_pci_device_info(self, pci_dev: ResourcePCIDevice):
        """
        更新PCI设备详细信息显示。
        
        根据选定的PCI设备更新界面上的详细信息。
        
        Args:
            pci_dev: 要显示的PCI设备对象。
        """
        self._ui.lineedit_domain.clear()
        self._ui.lineedit_bus.clear()
        self._ui.lineedit_device.clear()
        self._ui.lineedit_func.clear()
        self._ui.tablewidget_bars.clearContents()
        self._ui.tablewidget_caps.clearContents()

        if pci_dev is None:
            return

        self._ui.lineedit_domain.setText(str(pci_dev.domain()))
        self._ui.lineedit_bus.setText(str(pci_dev.bdf()[0]))
        self._ui.lineedit_device.setText(str(pci_dev.bdf()[1]))
        self._ui.lineedit_func.setText(str(pci_dev.bdf()[2]))

        caps = pci_dev.caps()
        self._ui.tablewidget_caps.setRowCount(len(caps))
        for idx, cap in enumerate(caps):
            cap_desc = ""
            if cap.is_extended():
                cap_id = PCIExtCapID.from_value(cap.id())
            else:
                cap_id = PCICapID.from_value(cap.id())
            if cap_id is not None:
                cap_desc = cap_id.descript()

            self._ui.tablewidget_caps.setItem(idx, 0, QtWidgets.QTableWidgetItem(str(cap.id())))
            self._ui.tablewidget_caps.setItem(idx, 1, QtWidgets.QTableWidgetItem(cap_desc))
            self._ui.tablewidget_caps.setItem(idx, 2, QtWidgets.QTableWidgetItem(hex(cap.start())))
            self._ui.tablewidget_caps.setItem(idx, 3, QtWidgets.QTableWidgetItem(hex(cap.len())))

        bars = pci_dev.bars()
        self._ui.tablewidget_bars.setRowCount(len(bars))
        for idx, bar in enumerate(bars):
            self._ui.tablewidget_bars.setItem(idx, 0, QtWidgets.QTableWidgetItem(hex(bar.start())))
            self._ui.tablewidget_bars.setItem(idx, 1, QtWidgets.QTableWidgetItem(hex(bar.size())))
            self._ui.tablewidget_bars.setItem(idx, 2, QtWidgets.QTableWidgetItem(hex(bar.mask())))
            self._ui.tablewidget_bars.setItem(idx, 3, QtWidgets.QTableWidgetItem(bar.type()))

        self._ui.tablewidget_caps.setFixedHeight(self._ui.tablewidget_caps.sizeHint().height())
        self._ui.tablewidget_bars.setFixedHeight(self._ui.tablewidget_bars.sizeHint().height())
        self._ui.tablewidget_caps.resizeColumnsToContents()
        self._ui.tablewidget_bars.resizeColumnsToContents()


    def _on_rpc_client_state_changed(self, sender):
        """
        处理RPC客户端状态变化事件。
        
        当RPC客户端连接状态改变时，更新更新按钮的可用性。
        
        Args:
            sender: 信号发送者。
        """
        if RPCClient.get_instance() is not sender:
            return

        client: RPCClient = sender
        self._ui.btn_update.setEnabled(client.is_connected())

    def _on_pcidevice_selected(self, row):
        """
        处理PCI设备选择事件。
        
        当用户在列表中选择一个PCI设备时，更新设备详细信息显示。
        
        Args:
            row: 选中的行索引。
        """
        if self._pcidevs is None:
            return
        pci_dev = self._pcidevs.device_at(row)
        if pci_dev is None:
            return
        self._update_pci_device_info(pci_dev)

    def _on_update(self):
        """
        处理更新按钮点击事件。
        
        从RPC服务器获取最新的PCI设备列表，并更新显示。
        """
        client: RPCClient = RPCClient.get_instance()
        if not client.is_connected():
            return

        if self._pcidevs is None:
            return

        result = client.pci_devices()
        if result is None:
            self.logger.error("get pci device failed.")
            return
        if not result.status:
            self.logger.error(f"get pci device failed. {result.message}")
            return
        pci_devices = result.result

        self._pcidevs.remove_all_device()

        for pci in pci_devices:
            # 过滤桥设备
            if not isinstance(pci, dict):
                continue
            dev_type: str = pci.get('type')
            if dev_type == 'bridge':
                continue

            pci_dev = self._pcidevs.add_device(pci)
            if pci_dev is None:
                self.logger.error(f"add device failed {pci_dev}.")
                continue

        self._update()
