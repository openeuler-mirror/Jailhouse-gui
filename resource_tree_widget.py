import enum
import logging
from PySide2 import QtWidgets, QtCore, QtGui
from forms.ui_resource_tree import Ui_ResourceTree
from jh_resource import ResourceBase, ResourceGuestCell, ResourceGuestCellList, ResourceJailhouse, ResourceMgr, Resource, ResourcePCIDevice, ResourcePCIDeviceList, ResourcePlatform, ResourceCPU, ResourceBoard, ResourceSignals


class ResourceTreeModel(QtCore.QAbstractItemModel):
    """
    资源树数据模型。
    
    实现Qt的抽象项模型，用于在树形视图中显示资源结构。
    监听资源变化事件，实时更新树形显示。
    
    Attributes:
        _resource_mgr: 资源管理器实例。
        logger: 日志记录器。
    """
    logger = logging.getLogger("ResourceTreeModel")
    def __init__(self, parent=None):
        """
        初始化资源树数据模型。
        
        连接各种资源信号以便响应资源变化。
        
        Args:
            parent: 父对象，默认为None。
        """
        super().__init__(parent)
        self._resource_mgr = ResourceMgr.get_instance()

        ResourceSignals.add.connect(self._on_resource_update, self._resource_mgr)
        ResourceSignals.current_rsc.connect(self._on_resource_update, self._resource_mgr)
        ResourceSignals.value_changed.connect(self._on_resource_value_changed)
        ResourceSignals.add.connect(self._on_rsc_add)
        ResourceSignals.remove.connect(self._on_rsc_remove)
        ResourceSignals.modified.connect(self._on_rsc_modified)

    def _on_resource_update(self, sender, **kwargs):
        """
        处理资源更新事件。
        
        当资源被添加或当前资源改变时，重置整个模型。
        
        Args:
            sender: 信号发送者。
            **kwargs: 关键字参数。
        """
        self.beginResetModel()
        self.endResetModel()

    def _on_add_cell(self, sender):
        """
        处理添加单元格事件。
        
        当添加单元格时，重置整个模型。
        
        Args:
            sender: 信号发送者。
        """
        self.beginResetModel()
        self.endResetModel()

    def _create_index(self, row, data):
        """
        创建模型索引。
        
        使用资源对象作为内部指针创建模型索引。
        
        Args:
            row: 行号。
            data: 资源对象。
            
        Returns:
            创建的模型索引。
            
        Raises:
            Exception: 当data不是ResourceBase类型时抛出异常。
        """
        if not isinstance(data, ResourceBase):
            raise Exception()
        return self.createIndex(row, 0, data)

    def _on_rsc_add(self, sender, **kwargs):
        """
        处理资源添加事件。
        
        根据添加的资源类型，插入相应的行。
        
        Args:
            sender: 信号发送者。
            **kwargs: 关键字参数，包含添加的资源。
        """
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
        """
        处理资源移除事件。
        
        根据移除的资源类型，移除相应的行。
        
        Args:
            sender: 信号发送者。
            **kwargs: 关键字参数，包含移除的资源信息。
        """
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
        """
        处理资源修改事件。
        
        当资源被修改时，发出数据变化信号以更新显示。
        
        Args:
            sender: 信号发送者。
            **kwargs: 关键字参数。
        """
        if not isinstance(sender, ResourceBase):
            return
        rsc: ResourceBase = sender
        index = self._create_index(rsc.my_index(), rsc)
        self.dataChanged.emit(index, index)

    def _on_resource_value_changed(self, sender, **kwargs):
        """
        处理资源值变化事件。
        
        当资源的值变化时，更新相应项的显示。
        
        Args:
            sender: 信号发送者。
            **kwargs: 关键字参数。
        """
        if isinstance(sender, ResourceGuestCell):
            # 处理名字变化
            guestcell: ResourceGuestCell = sender
            index = self._create_index(guestcell.my_index(), guestcell)
            self.dataChanged.emit(index, index)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        获取列数。
        
        实现QAbstractItemModel接口，返回模型的列数。
        
        Args:
            parent: 父索引，默认为无效索引。
            
        Returns:
            int: 列数，固定为1。
        """
        return 1

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        获取行数。
        
        实现QAbstractItemModel接口，返回指定父索引下的行数。
        
        Args:
            parent: 父索引，默认为无效索引。
            
        Returns:
            int: 行数。
        """
        if not parent.isValid():
            return len(self._resource_mgr)

        rsc: ResourceBase = parent.internalPointer()
        if isinstance(rsc, Resource):
            if rsc is not self._resource_mgr.get_current():
                return 0

        return len(rsc)

    def data(self, index: QtCore.QModelIndex, role):
        """
        获取数据。
        
        实现QAbstractItemModel接口，返回指定索引和角色的数据。
        
        Args:
            index: 模型索引。
            role: 数据角色。
            
        Returns:
            显示的数据，如果资源已修改则在标签后添加"*"。
        """
        if not index.isValid():
            return None
        rsc: ResourceBase = index.internalPointer()

        if role == QtCore.Qt.DisplayRole:
            if rsc.is_modified():
                return rsc.label() + " *"
            return rsc.label()

    def flags(self, index):
        """
        获取项标志。
        
        实现QAbstractItemModel接口，返回指定索引的项标志。
        
        Args:
            index: 模型索引。
            
        Returns:
            int: 项标志，启用项和可选择项。
        """
        if not index.isValid():
            return 0
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """
        获取头部数据。
        
        实现QAbstractItemModel接口，返回头部数据。
        
        Args:
            section: 节索引。
            orientation: 方向(水平或垂直)。
            role: 数据角色，默认为显示角色。
            
        Returns:
            None: 不显示头部。
        """
        return None

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """
        创建索引。
        
        实现QAbstractItemModel接口，创建指定行、列和父索引的模型索引。
        
        Args:
            row: 行号。
            column: 列号。
            parent: 父索引，默认为无效索引。
            
        Returns:
            QModelIndex: 创建的模型索引。
        """
        if column > 0:
            return QtCore.QModelIndex()

        if not parent.isValid():
            return self._create_index(row, self._resource_mgr[row])

        rsc: ResourceBase = parent.internalPointer()
        return self._create_index(row, rsc[row])

    def parent(self, index: QtCore.QModelIndex):
        """
        获取父索引。
        
        实现QAbstractItemModel接口，返回指定索引的父索引。
        
        Args:
            index: 模型索引。
            
        Returns:
            QModelIndex: 父索引。
        """
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
    """
    资源树部件。
    
    显示资源树并处理用户交互。
    
    Attributes:
        _ui: 用户界面对象。
        _model: 资源树数据模型。
        item_clicked: 项点击信号。
        item_double_clicked: 项双击信号。
    """
    item_clicked = QtCore.Signal(object)
    item_double_clicked = QtCore.Signal(object)
    def __init__(self, parent=None):
        """
        初始化资源树部件。
        
        设置界面和连接信号槽。
        
        Args:
            parent: 父部件，默认为None。
        """
        super().__init__(parent)
        self._ui = Ui_ResourceTree()
        self._ui.setupUi(self)

        self._model = ResourceTreeModel(self._ui.treeview)
        self._ui.treeview.setModel(self._model)

        self._ui.treeview.setHeaderHidden(True)
        self._ui.treeview.clicked.connect(self._on_item_click)
        self._ui.treeview.doubleClicked.connect(self._on_item_double_click)

    def expand_all(self):
        """
        展开所有项。
        
        展开资源树中的所有节点。
        """
        self._ui.treeview.expandAll()

    def _on_item_click(self, index):
        """
        处理项点击事件。
        
        当用户点击树中的项时，发出项点击信号。
        
        Args:
            index: 被点击的项的模型索引。
        """
        rsc = index.internalPointer()
        self.item_clicked.emit(rsc)

    def _on_item_double_click(self, index):
        """
        处理项双击事件。
        
        当用户双击树中的项时，发出项双击信号并展开所有节点。
        
        Args:
            index: 被双击的项的模型索引。
        """
        rsc = index.internalPointer()
        self.item_double_clicked.emit(rsc)
        self._ui.treeview.expandAll()
