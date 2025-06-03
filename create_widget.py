import logging
import os
import sys
import json
import logging
from PySide2 import QtWidgets, QtCore
from forms.ui_create_widget import Ui_CreateWidget
from jh_resource import PlatformMgr, ResourceMgr


class CreateDialog(QtWidgets.QDialog):
    """
    创建配置对话框
    
    提供两种配置创建方式：基于模板创建和基于已有演示配置创建。
    支持选择硬件平台、输入配置名称，并处理配置的初始化和加载操作。
    
    Attributes:
        logger: 类级日志记录器
        _ui: UI设计器生成的界面元素
        _demo_path: 演示配置文件所在路径
    """
    logger = logging.getLogger('CreateWidget')

    def __init__(self, parent=None):
        """
        初始化创建配置对话框
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._ui = Ui_CreateWidget()
        self._ui.setupUi(self)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        self._ui.combobox_demo.setView(QtWidgets.QListView())
        self._ui.combobox_platform.setView(QtWidgets.QListView())

        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.setWindowTitle("创建配置")

        pltmgr = PlatformMgr.get_instance()
        if pltmgr is None:
            return

        # 设置演示配置文件路径（支持打包后环境）
        self._demo_path = "demos"
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self._demo_path = os.path.join(getattr(sys, '_MEIPASS'), "demos")
            self.logger.info(f"demos path {self._demo_path}")

        # 加载演示配置文件列表
        for name in os.listdir(self._demo_path):
            if name.endswith('.jhr'):
                self._ui.combobox_demo.addItem(name)

        # 加载可用平台列表
        names = pltmgr.board_names()
        self._ui.combobox_platform.addItems(names)

        # 初始化界面状态
        self._ui.radiobtn_new.setChecked(True)  # 默认选择"新建配置"
        self._ui.stackedwidget_params.setCurrentIndex(0)    # 显示新建配置参数页

        # 连接信号与槽
        self._ui.btn_close.clicked.connect(self._on_close)  # 关闭按钮
        self._ui.radiobtn_new.clicked.connect(self._on_mode_select) # 新建配置单选按钮
        self._ui.radiobtn_demo.clicked.connect(self._on_mode_select)    # 演示配置单选按钮
        self._ui.btn_cancel.clicked.connect(self._on_close) # 取消按钮
        self._ui.btn_create.clicked.connect(self._on_create)    # 创建按钮

    def _on_close(self):
        """处理关闭对话框事件"""
        self.setResult(0)   # 设置结果代码为0（取消）
        self.close()

    def _on_mode_select(self):
        """处理创建模式选择事件（新建配置/演示配置）"""
        if self.sender() is self._ui.radiobtn_new:
            self._ui.stackedwidget_params.setCurrentIndex(0)    # 显示新建配置参数页
        elif self.sender() is self._ui.radiobtn_demo:
            self._ui.stackedwidget_params.setCurrentIndex(1)    # 显示演示配置参数页

    def _on_create(self):
        """处理创建配置事件"""
        if self._ui.radiobtn_new.isChecked():   # 新建配置模式
            plt = self._ui.combobox_platform.currentText()  # 获取选择的平台
            if len(plt) == 0:
                return
            name = self._ui.lineedit_name.text().strip()     # 获取配置名称
            if len(name) == 0:
                return

            # 创建新配置
            rsc = ResourceMgr().get_instance().create(name, plt)
            if rsc is None:
                return
            ResourceMgr().get_instance().set_current(rsc)   # 设置为当前配置
            self.close()
        elif self._ui.radiobtn_demo.isChecked():    # 演示配置模式
            name = self._ui.lineedit_name.text().strip()    # 获取配置名称
            if len(name) == 0:
                return

            demo = self._ui.combobox_demo.currentText() # 获取选择的演示配置
            demo_fn = os.path.join(self._demo_path, demo)   # 构建完整路径

            # 加载演示配置文件
            try:
                with open(demo_fn, "rt", encoding='utf8') as f:
                    value = json.load(f)
            except Exception as e:
                self.logger.error(f"open {demo_fn} failed: {e}")
                return None

            # 加载配置资源
            rsc = ResourceMgr().get_instance().load(value)
            if rsc is None:
                self.logger.error("load resource file failed.")
                return

            rsc.set_name(name)  # 设置配置名称
            ResourceMgr().get_instance().set_current(rsc)    # 设置为当前配置
            self.setResult(1)    设置结果代码为1（成功）
            self.close()
