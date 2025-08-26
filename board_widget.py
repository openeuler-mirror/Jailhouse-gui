import logging
from PySide2 import QtWidgets
from typing import Optional
from forms.ui_board_widget import Ui_BoardWidget
from forms.ui_device_widget import Ui_DeviceWidget
from jh_resource import ResourceBoard, ResourceCPU
from jh_resource import PlatformMgr, ResourceSignals
from flowlayout import FlowLayout
from common_widget import SelectButton, clean_layout
from cpu_edit_widget import CPUEditWidget
from mem_edit_widget import MemEditWidget
import utils


class BoardWidget(QtWidgets.QWidget):
    """
    开发板信息显示与编辑部件。
    
    用于展示和编辑开发板的硬件信息，包括厂商型号、CPU配置、内存区域及设备列表。
    支持与平台管理器的数据同步，响应资源修改信号自动更新界面。
    
    Attributes:
        logger: 日志记录器，用于记录部件运行时信息。
        _ui: 由UI设计器生成的用户界面对象。
        _board_mem_editor: 内存编辑子部件，用于管理开发板内存区域。
        _board: 开发板资源对象，存储当前编辑的开发板数据。
        _device_layout: 设备列表布局管理器，使用流式布局展示设备选择按钮。
        _cpu_editor: CPU配置编辑子部件，负责处理CPU数量和参数配置。
    """
    logger = logging.getLogger('BoardWidget')

    def __init__(self, parent=None):
        """
        初始化开发板信息部件。
        
        Args:
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)

        # 初始化UI界面
        self._ui = Ui_BoardWidget()
        self._ui.setupUi(self)

        # 初始化内存编辑子部件并添加到布局
        self._board_mem_editor = MemEditWidget()
        self._ui.frame_board_mems.layout().addWidget(self._board_mem_editor)

        # 核心数据对象及布局管理器
        self._board: Optional[ResourceBoard] = None
        self._device_layout = FlowLayout(self._ui.frame_devices_items)  # 流式布局管理设备选择按钮
        self._cpu_editor = CPUEditWidget(self)  # CPU配置编辑部件
        self._ui.frame_cpus_content.layout().addWidget(self._cpu_editor)

        # 信号连接
        self._ui.btn_update_from_plt.clicked.connect(self._on_update_from_plt)  # 平台数据同步按钮
        self._cpu_editor.cpus_changed.connect(self._on_cpus_changed)    # CPU配置变更信号
        self._board_mem_editor.signal_changed.connect(self._on_board_mems_changed)  # 内存配置变更信号

        ResourceSignals.modified.connect(self._on_rsc_modified) # 资源修改全局信号监听

    def set_board(self, board: ResourceBoard):
        """
        设置当前编辑的开发板对象并触发界面更新。
        
        Args:
            board: 开发板资源对象
        """
        self._board = board
        self._update()

    def _update(self):
        """
        刷新界面显示以匹配当前开发板数据。
        
        包括清空旧数据、更新基础信息、填充设备列表、同步CPU和内存配置。
        """
        board = self._board
        # 初始化界面状态
        self._ui.label_model.setText("")
        self._ui.label_vendor.setText("")
        clean_layout(self._device_layout)   # 清空设备列表布局
        self._cpu_editor.set_cpu_count(0)
        self._board_mem_editor.set_regions(list())

        if board is None:
            return

        # 更新基础信息
        self._ui.label_model.setText(board.model)
        self._ui.label_vendor.setText(board.vendor)

        # 获取父级CPU资源
        cpu: ResourceCPU = board.parent().cpu()

        # 构建设备选择按钮列表
        dev_names = sorted(map(lambda x: x.name(), cpu.devices()))
        for dev in dev_names:
            w = SelectButton(dev, self)
            self._device_layout.addWidget(w)
            # 标记已选中的设备
            if dev in board.devices:
                w.setChecked(True)

        # 同步CPU配置
        self._cpu_editor.set_cpu_count( cpu.cpu_count() )
        self._cpu_editor.set_cpus(board.cpus())
        # 同步内存区域配置
        self._board_mem_editor.set_regions(board.ram_regions())

    def _on_rsc_modified(self, sender, **kwargs):
        """
        处理资源修改信号。
        
        当监测到当前开发板数据被修改时，自动刷新界面显示。
        
        Args:
            sender: 发出修改信号的对象
        """
        if sender is not self._board:
            return
        self._update()

    def _on_update_from_plt(self):
        """
        处理从平台管理器同步数据的请求。
        
        从平台获取开发板最新配置并更新到当前资源对象。
        """
        if self._board is None:
            return

        # 从平台管理器查找开发板
        board: PlatformMgr.Board = PlatformMgr.get_instance().find_board(self._board.name())
        if board is None:
            self.logger.error(f"can not find board {self._board.name()} from platform")
            return

        # 同步平台数据到资源对象
        if not self._board.from_dict(board.value):
            self.logger.error(f"update board failed.")
            return

        # 标记资源已修改
        self._board.set_modified()

    def _on_cpus_changed(self):
        """
        处理CPU配置变更事件。
        
        将CPU编辑部件的最新数据同步到开发板资源对象。
        """
        if self._board is None:
            return
        self._board.set_cpus(self._cpu_editor.get_cpus())

    def _on_board_mems_changed(self):
        """
        处理内存配置变更事件。
        
        将内存编辑部件的最新数据同步到开发板资源对象。
        """
        if self._board is None:
            return
        self._board.set_ram_regions(self._board_mem_editor.get_value())
