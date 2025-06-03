from typing import Optional
from forms.ui_hw_platform_widget import Ui_HwPlatformWidget
from PySide2 import QtWidgets
from jh_resource import ResourcePlatform
from cpu_widget import CPUWidget
from board_widget import BoardWidget


class HwPlatformWidget(QtWidgets.QWidget):
    """
    硬件平台配置主界面组件。
    
    提供硬件平台配置的主界面，管理CPU和开发板配置的显示与切换。
    包含以下主要功能：
    - 管理子页面（CPU配置页、开发板配置页）
    - 提供子菜单按钮切换不同配置页面
    - 设置和更新当前硬件平台资源
    
    属性:
        _platform: 当前显示的硬件平台资源对象
        _blank_page: 空白页面，用于初始状态显示
        _cpu_page: CPU配置信息显示页面
        _board_page: 开发板配置信息显示页面
    """
    def __init__(self, parent=None):
        """
        初始化硬件平台配置主界面。
        
        设置UI并初始化子页面，连接菜单按钮信号。
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._ui = Ui_HwPlatformWidget()
        self._ui.setupUi(self)

        # 初始化成员变量
        self._platform: Optional[ResourcePlatform] = None

        # 创建并添加子页面到堆栈窗口
        self._blank_page = QtWidgets.QWidget(self)  # 空白初始页面
        self._cpu_page = CPUWidget(self)    # CPU配置页面
        self._board_page = BoardWidget()    # 开发板配置页面
        self._ui.stacked_widget.addWidget(self._blank_page)
        self._ui.stacked_widget.addWidget(self._cpu_page)
        self._ui.stacked_widget.addWidget(self._board_page)
        self._ui.stacked_widget.setCurrentWidget(self._blank_page)  # 默认显示空白页

        # 连接菜单按钮点击事件到处理函数
        self._ui.btn_cpu.clicked.connect(self._on_submenu)
        self._ui.btn_board.clicked.connect(self._on_submenu)

    def set_platform(self, platform: ResourcePlatform):
        """
        设置并显示指定的硬件平台资源。
        
        清除现有显示，加载新平台的CPU和开发板配置信息，
        并切换到CPU配置页面。
        
        Args:
            platform: 要显示的硬件平台资源对象，若为None则清除显示
        """
        # 清除现有显示
        self._cpu_page.set_cpu(None)
        self._board_page.set_board(None)

        # 处理平台为None的情况
        if platform is None:
            self._platform = platform
            return

        # 临时设置为None，防止信号干扰
        self._platform = None

        # 设置并显示新平台的CPU和开发板信息
        self._cpu_page.set_cpu(platform.cpu())
        self._board_page.set_board(platform.board())

        # 最终设置平台并切换到CPU页面
        self._platform = platform
        self._ui.btn_cpu.setChecked(True)
        self._ui.stacked_widget.setCurrentWidget(self._cpu_page)

    def _on_submenu(self):
        """
        处理子菜单按钮点击事件。
        
        根据被点击的按钮切换显示对应的配置页面。
        """

        # 若平台未设置则不执行任何操作
        if self._platform is None:
            return
        
        # 根据按钮状态切换显示页面
        if self._ui.btn_cpu.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._cpu_page)
        if self._ui.btn_board.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._board_page)
