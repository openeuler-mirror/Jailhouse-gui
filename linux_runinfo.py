"""
Linux运行信息配置界面模块。

本模块提供了用于显示和管理Linux系统运行信息的图形界面组件，包括：
- 内核路径配置与选择
- 设备树文件配置与生成
- initramdisk文件管理及覆盖层编辑
- 启动参数（Boot Args）实时编辑
- 根文件系统覆盖层的上下文菜单管理
- Linux系统启动功能集成

主要类:
- LinuxRunInfoWidget: Linux运行信息配置界面组件
"""

import os
import copy
from typing import Optional
from PySide2 import QtWidgets, QtCore
from jh_resource import OSRunInfoBase, LinuxRunInfo
from jh_resource import ResourceGuestCell
from jh_resource import ResourceGuestCell, ResourceCPU
from generator import GuestCellGenerator
from forms.ui_linux_runinfo import Ui_LinuxRunInfoWidget
from commonos_runinfo import OSRunInfoWidget
from rpc_server.rpc_client import RPCClient
from utils import CpioUtil

class LinuxRunInfoWidget(OSRunInfoWidget):
    """
    Linux运行信息配置界面组件。
    
    提供Linux系统运行参数的配置界面，支持：
    - 内核、设备树、initramdisk路径的图形化选择
    - 启动参数的多行文本编辑与自动高度调整
    - 根文件系统覆盖层的添加/删除/清空操作（通过上下文菜单）
    - 与Jailhouse虚拟化环境的集成启动功能
    
    属性:
        _runinfo: 当前配置的Linux运行信息对象
        _ui: 自动生成的UI组件对象
    """
    def __init__(self, parent=None):
        """
        初始化Linux运行信息配置界面。
        
        设置UI组件、初始化运行信息对象、配置信号槽连接及表格属性。
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._runinfo = LinuxRunInfo()  # Linux运行信息数据模型

        self._ui = Ui_LinuxRunInfoWidget()
        self._ui.setupUi(self)

        # 配置根文件系统覆盖层列表的上下文菜单
        self._ui.listwidget_rootfs_overlay.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # 固定启动参数文本框高度并连接变更事件
        self._ui.textedit_bootargs.setFixedHeight(80)
        self._ui.textedit_bootargs.textChanged.connect(self._on_bootargs_changed)

        # 连接文件路径输入框的编辑完成事件
        self._ui.lineedit_kernel_path.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_devicetree_path.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_ramdisk_path.editingFinished.connect(self._on_edit_finished)

        # 连接文件选择按钮的点击事件
        self._ui.btn_select_kernel.clicked.connect(self._on_select_file)
        self._ui.btn_select_devicetree.clicked.connect(self._on_select_file)
        self._ui.btn_select_ramdisk.clicked.connect(self._on_select_file)
        # 连接覆盖层列表的上下文菜单请求事件
        self._ui.listwidget_rootfs_overlay.customContextMenuRequested.connect(self._on_rootfs_overlay_listwidget_menu)

    def reset(self):
        """清空所有配置输入字段"""
        self._ui.textedit_bootargs.clear()
        self._ui.lineedit_kernel_path.clear()
        self._ui.lineedit_devicetree_path.clear()
        self._ui.lineedit_ramdisk_path.clear()
        self._ui.listwidget_rootfs_overlay.clear()

    def set_runinfo(self, runinfo: OSRunInfoBase):
        """
        设置并显示指定的运行信息对象
        
        Args:
            runinfo: 运行信息对象（需为LinuxRunInfo类型）
        """
        self._runinfo = None
        if not isinstance(runinfo, LinuxRunInfo):
            self.logger.error("type error")
        # 更新界面显示
        self._ui.lineedit_kernel_path.setText(runinfo.kernel)
        self._ui.lineedit_devicetree_path.setText(runinfo.devicetree)
        self._ui.lineedit_ramdisk_path.setText(runinfo.ramdisk)
        self._ui.textedit_bootargs.setText(runinfo.bootargs)
        self._ui.listwidget_rootfs_overlay.clear()
        for item in runinfo.ramdisk_overlay:
            self._ui.listwidget_rootfs_overlay.addItem(item)
        self._runinfo = copy.deepcopy(runinfo)   # 深拷贝防止引用修改

    def _on_rootfs_overlay_listwidget_menu(self, pos: QtCore.QPoint):
        """处理根文件系统覆盖层列表的上下文菜单事件"""
        if self._runinfo is None:
            return

        global_pos = self._ui.listwidget_rootfs_overlay.mapToGlobal(pos)
        menu = QtWidgets.QMenu(self)
        item = self._ui.listwidget_rootfs_overlay.itemAt(pos)

        action_del = None
        if item is not None:
            action_del = menu.addAction("删除文件")
        action_add = menu.addAction("添加文件")
        action_del_all = menu.addAction("删除所有")

        selected = menu.exec_(global_pos)
        if selected is None:
            return
        # 处理不同菜单操作
        if selected is action_add:
            filename = QtWidgets.QFileDialog.getOpenFileName(self, "打开文件", "", "tar(*.tar);; data(*.*);;")[0]
            if len(filename) == 0:
                return
            self._ui.listwidget_rootfs_overlay.addItem(filename)
        if selected is action_del:
            self._ui.listwidget_rootfs_overlay.takeItem(self._ui.listwidget_rootfs_overlay.row(item))
        if selected is action_del_all:
            self._ui.listwidget_rootfs_overlay.clear()

        # 更新运行信息中的覆盖层列表并触发值变更信号
        overlay = list()
        for i in range(self._ui.listwidget_rootfs_overlay.count()):
            overlay.append(self._ui.listwidget_rootfs_overlay.item(i).text())
        self._runinfo.ramdisk_overlay = overlay
        self.value_changed.emit()

    def _on_edit_finished(self):
        """处理文件路径输入框的编辑完成事件"""
        changed = False
        if self.sender() is self._ui.lineedit_kernel_path:
            kernel = self._ui.lineedit_kernel_path.text()
            changed = (kernel != self._runinfo.kernel)
            self._runinfo.kernel = kernel
        if self.sender() is self._ui.lineedit_devicetree_path:
            devicetree = self._ui.lineedit_devicetree_path.text()
            changed = (devicetree != self._runinfo.devicetree)
            self._runinfo.devicetree = devicetree
        if self.sender() is self._ui.lineedit_ramdisk_path:
            ramdisk = self._ui.lineedit_ramdisk_path.text()
            changed = (ramdisk != self._runinfo.ramdisk)
            self._runinfo.ramdisk = ramdisk

        if changed:
            self.value_changed.emit()   # 触发值变更信号

    def _on_select_file(self):
        """处理文件选择按钮的点击事件"""
        caption = ''
        filter = ''
        if self.sender() is self._ui.btn_select_kernel:
            caption = "选择linux内核文件"
            filename = self._ui.lineedit_kernel_path.text()
        elif self.sender() is self._ui.btn_select_devicetree:
            caption = "选择设备树文件"
            filter = "device tree(*.dtb)"
            filename = self._ui.lineedit_devicetree_path.text()
        elif self.sender() is self._ui.btn_select_ramdisk:
            caption = "选择initramdisk"
            filter = "ramdisk(*.cpio)"
            filename = self._ui.lineedit_ramdisk_path.text()

        # 打开文件选择对话框
        filename = QtWidgets.QFileDialog.getOpenFileName(self, caption, os.path.dirname(filename), filter )[0]
        if len(filename) == 0:
            return

        # 根据按钮类型更新对应路径并触发信号
        if self.sender() is self._ui.btn_select_kernel:
            self._ui.lineedit_kernel_path.setText(filename)
            self._runinfo.kernel = filename
        elif self.sender() is self._ui.btn_select_devicetree:
            self._ui.lineedit_devicetree_path.setText(filename)
            self._runinfo.devicetree = filename
        elif self.sender() is self._ui.btn_select_ramdisk:
            self._ui.lineedit_ramdisk_path.setText(filename)
            self._runinfo.ramdisk = filename

        self.value_changed.emit()

    def _resize_textedit(self):
        """自动调整启动参数文本框的高度"""
        self._ui.textedit_bootargs.blockSignals(True)
        text = self._ui.textedit_bootargs.toPlainText()
        text = text.replace('\n', ' ')  # 替换换行符为空格
        pos = self._ui.textedit_bootargs.textCursor().position()
        self._ui.textedit_bootargs
        height = 0
        # 计算文本框高度
        if len(text) == 0:
            self._ui.textedit_bootargs.append(' ')
            height = self._ui.textedit_bootargs.document().size().height()
            self._ui.textedit_bootargs.clear()
        else:
            self._ui.textedit_bootargs.setPlainText(text)
            height = self._ui.textedit_bootargs.document().size().height() + 10
        if height < 40:
            height = 40

        # 恢复光标位置并更新高度
        cursor = self._ui.textedit_bootargs.textCursor()
        cursor.setPosition(pos)
        self._ui.textedit_bootargs.setTextCursor(cursor)
        self._ui.textedit_bootargs.blockSignals(False)
        self._ui.textedit_bootargs.setFixedHeight(height)
        # 自动调整父容器高度（如果是堆叠窗口）
        if isinstance(self.parentWidget(), QtWidgets.QStackedWidget):
            self.parentWidget().setFixedHeight(self.sizeHint().height())

    def _on_bootargs_changed(self):
        """处理启动参数文本变更事件"""
        if self._runinfo is None:
            return
        bootargs = self._ui.textedit_bootargs.toPlainText().strip()
        if bootargs == self._runinfo.bootargs:
            return
        self._runinfo.bootargs = bootargs
        self.value_changed.emit()   # 触发值变更信号

    def run(self, cell: ResourceGuestCell) -> bool:
        """
        启动Linux系统实例
        
        Args:
            cell: 目标Guest Cell资源对象
        Returns:
            启动是否成功
        """
        client = RPCClient.get_instance()
        if cell is None:
            return False
        if not client.is_connected():
            return False

        cellname = cell.name()
        cpuname = cell.find(ResourceCPU).name()
        os_runinfo: LinuxRunInfo = self._runinfo

        # linux系统的入口地址固定为0
        if cell.reset_addr() != 0:
            cell.set_reset_addr(0)

        def read_file(filename) -> Optional[bytes]:
             """辅助函数：读取文件内容"""
            try:
                with open(filename, "rb") as f:
                    return f.read()
            except:
                self.logger.error(f"read {filename} failed.")
                return None

        # 读取内核文件
        self.logger.info("read kernel")
        kernel = read_file(self.abspath(cell, os_runinfo.kernel))
        if kernel is None:
            self.logger.error("read kernel failed.")
            return False

        # 处理设备树文件（支持自动生成）
        self.logger.info("read devicetree")
        devicetree = None
        if len(os_runinfo.devicetree) > 0:
            devicetree = read_file(self.abspath(cell, os_runinfo.devicetree))
            if devicetree is None:
                self.logger.error("read devicetree failed.")
                return False
        else:
            devicetree = GuestCellGenerator.gen_guestlinux_dtb(cell)    # 自动生成设备树
            if devicetree is None:
                self.logger.error("generate dtb failed.")
                return False

        # 处理initramdisk文件（支持覆盖层追加）
        ramdisk = None
        if len(os_runinfo.ramdisk) > 0:
            if not os.path.exists(self.abspath(cell, os_runinfo.ramdisk)):
                self.logger.error(f"ramdisk {os_runinfo.ramdisk} not exist.")
                return False

            cpio = CpioUtil(self.abspath(cell, os_runinfo.ramdisk))
            for filename in os_runinfo.ramdisk_overlay:
                self.logger.info(f"append {filename} to ramdisk")
                try:
                    with open(filename, "rb") as f:
                        data = f.read()
                except:
                    self.logger.error(f"read {filename} failed")
                    return False

                if not cpio.append(os.path.basename(filename), data):   # 追加覆盖层文件到cpio
                    self.logger.error("append file to cpio failed.")
                    return False
            ramdisk = cpio.get_bytes()  # 获取处理后的ramdisk数据

        # 生成Cell配置二进制
        self.logger.info("generate cell config.")
        cell_config = GuestCellGenerator.gen_config_bin(cell)
        if cell_config is None:
            self.logger.error("generate cell config failed.")
            return False

        # 检查并销毁已存在的Cell实例
        cell_exist = False
        result = client.list_cell()
        if not result:
            self.logger.error("get cell list failed.")
            return False
        for _cell in result.result:
            if _cell['name'] == cellname:
                cell_exist = True
                break

        if cell_exist:
            client.destroy_cell(cellname)

        # 调用RPC服务启动Linux系统
        self.logger.info("run linux.")
        result = client.run_linux(cell_config, kernel, devicetree, ramdisk, os_runinfo.bootargs)
        if not result:
            self.logger.error(f"run linux failed {result.message}.")
            return False

        self.logger.info("run linux done.")
