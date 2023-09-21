import enum
import logging
from PySide2 import QtWidgets, QtCore, QtGui
from forms.ui_resource_tree import Ui_ResourceTree
from jh_resource import ResourceBase, ResourceGuestCell, ResourceGuestCellList, ResourceJailhouse, ResourceMgr, Resource, ResourcePCIDevice, ResourcePCIDeviceList, ResourcePlatform, ResourceCPU, ResourceBoard, ResourceSignals


class ResourceTreeModel(QtCore.QAbstractItemModel):
    logger = logging.getLogger("ResourceTreeModel")
    def __init__(self, parent=None):
        super().__init__(parent)
        self._resource_mgr = ResourceMgr.get_instance()

        ResourceSignals.add.connect(self._on_resource_update, self._resource_mgr)
        ResourceSignals.current_rsc.connect(self._on_resource_update, self._resource_mgr)
        ResourceSignals.value_changed.connect(self._on_resource_value_changed)
        ResourceSignals.add.connect(self._on_rsc_add)
        ResourceSignals.remove.connect(self._on_rsc_remove)
        ResourceSignals.modified.connect(self._on_rsc_modified)

    def _on_resource_update(self, sender, **kwargs):
        self.beginResetModel()
        self.endResetModel()

    def _on_add_cell(self, sender):
        self.beginResetModel()
        self.endResetModel()

    def _create_index(self, row, data):
        if not isinstance(data, ResourceBase):
            raise Exception()
        return self.createIndex(row, 0, data)

    def _on_rsc_add(self, sender, **kwargs):
        print("on_rsc_add", sender)
        if isinstance(sender, ResourceGuestCellList):
            rsc_cells: ResourceGuestCellList = sender
            rsc = kwargs.get('rsc')
            if isinstance(rsc, ResourceGuestCell):
                # 添加GuestCell
                self.beginInsertRows(self._create_index(rsc_cells.my_index(), rsc_cells), 0, -1)
                self.endInsertRows()

        elif isinstance(sender, ResourcePCIDeviceList):
            # 添加PCI设备
            pci_devs: ResourcePCIDeviceList = sender
            pci_dev: ResourcePCIDevice = kwargs.get("rsc")
            self.beginInsertRows(
                self._create_index(pci_devs.my_index(), pci_devs),
                pci_devs.device_count()-1, pci_devs.device_count()
            )
            self.endInsertRows()

    def _on_rsc_remove(self, sender, **kwargs):
        print("on_rsc_remove", sender)
        if isinstance(sender, ResourcePCIDeviceList):
            # 删除PCI设备（清空？）
            pci_devs: ResourcePCIDeviceList = sender
            count = kwargs['count']
            self.beginRemoveRows(
                self._create_index(pci_devs.my_index(), pci_devs),
                0, count-1
            )
            self.endRemoveRows()
        if isinstance(sender, ResourceGuestCellList):
            guestcells: ResourceGuestCellList = sender
            self.beginRemoveRows(
                self._create_index(guestcells.my_index(), guestcells),
                0, guestcells.cell_count()
            )
            self.endRemoveRows()

    def _on_rsc_modified(self, sender, **kwargs):
        if not isinstance(sender, ResourceBase):
            return
        rsc: ResourceBase = sender
        index = self._create_index(rsc.my_index(), rsc)
        self.dataChanged.emit(index, index)

    def _on_resource_value_changed(self, sender, **kwargs):
        if isinstance(sender, ResourceGuestCell):
            # 处理名字变化
            guestcell: ResourceGuestCell = sender
            index = self._create_index(guestcell.my_index(), guestcell)
            self.dataChanged.emit(index, index)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return len(self._resource_mgr)

        rsc: ResourceBase = parent.internalPointer()
        if isinstance(rsc, Resource):
            if rsc is not self._resource_mgr.get_current():
                return 0

        return len(rsc)

    def data(self, index: QtCore.QModelIndex, role):
        if not index.isValid():
            return None
        rsc: ResourceBase = index.internalPointer()

        if role == QtCore.Qt.DisplayRole:
            if rsc.is_modified():
                return rsc.label() + " *"
            return rsc.label()

    def flags(self, index):
        if not index.isValid():
            return 0
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if column > 0:
            return QtCore.QModelIndex()

        if not parent.isValid():
            return self._create_index(row, self._resource_mgr[row])

        rsc: ResourceBase = parent.internalPointer()
        return self._create_index(row, rsc[row])

    def parent(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return QtCore.QModelIndex()

        rsc: ResourceBase = index.internalPointer()
        if not isinstance(rsc, ResourceBase):
            self.logger.error("why")
            return QtCore.QModelIndex()

        if isinstance(rsc, Resource):
            return QtCore.QModelIndex()

        p = rsc.parent()
        if p is None:
            self.logger.error(f"{rsc} parent is None")
        return self._create_index(p.parent().index(p), p)


class ResourceTreeWidget(QtWidgets.QWidget):
    item_clicked = QtCore.Signal(object)
    item_double_clicked = QtCore.Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_ResourceTree()
        self._ui.setupUi(self)

        self._model = ResourceTreeModel(self._ui.treeview)
        self._ui.treeview.setModel(self._model)

        self._ui.treeview.setHeaderHidden(True)
        self._ui.treeview.clicked.connect(self._on_item_click)
        self._ui.treeview.doubleClicked.connect(self._on_item_double_click)

    def expand_all(self):
        self._ui.treeview.expandAll()

    def _on_item_click(self, index):
        rsc = index.internalPointer()
        self.item_clicked.emit(rsc)

    def _on_item_double_click(self, index):
        rsc = index.internalPointer()
        self.item_double_clicked.emit(rsc)
        self._ui.treeview.expandAll()
