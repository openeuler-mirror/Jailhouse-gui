"""
IVShMem 配置编辑界面模块。

本模块提供 ivshmem 参数配置的图形界面组件，负责：
- 展示当前通信配置中的共享内存参数
- 校验用户输入并同步回 ResourceComm
- 为参数输入框提供统一的说明提示

主要类：
- IVShMemWidget: ivshmem 参数编辑组件
"""

from ctypes import util
import logging
from typing import Optional
from PySide2 import QtWidgets
from forms.ui_ivshmem_widget import Ui_IVShMemWidget
from jh_resource import ResourceComm
import utils
from tip_widget import TipMgr

# 所有输入框共用的提示文案。
ivshmem_doc = """\
配置基于ivshmem的核间通信参数

核间通信使用共享内存，共享内存是连续的一段物理内存空间，所有的GuestOS和主机都可以访问这段内存空间，内存空间的划分为
1. state section
2. read/wirte section
3. output section， 每个GuestOS都存在独立的output section

核间通信主要使用 output section

起始物理地址： 配置物理内存空间，应该位于DDR中
state section大小： 推荐保持1KB大小
read/write section大小：推荐保持1KB大小
output section： 根据应用实际情况指定，通常1MB就够用
"""


class IVShMemWidget(QtWidgets.QWidget):
    """
    IVShMem 参数编辑组件。

    负责在界面中展示和维护通信共享内存配置，包含：
    - 起始物理地址
    - state section 大小
    - read/write section 大小
    - output section 大小

    属性：
        _comm: 当前绑定的通信配置对象。
        logger: 组件日志记录器。
    """

    logger = logging.getLogger("IVShMemWidget")

    def __init__(self, parent=None):
        """
        初始化 IVShMem 参数编辑组件。

        完成 UI 初始化、信号绑定与输入框提示文案设置。

        Args:
            parent: 父窗口部件，默认为 None。
        """
        super().__init__(parent)
        self._ui = Ui_IVShMemWidget()
        self._ui.setupUi(self)
        self._comm: Optional[ResourceComm] = None

        # 四个参数输入框统一复用同一个变更处理函数。
        self._ui.lineedit_ivshmem_phy.editingFinished.connect(self._on_ivshmem_changed)
        self._ui.lineedit_ivshmem_state_size.editingFinished.connect(self._on_ivshmem_changed)
        self._ui.lineedit_ivshmem_rw_size.editingFinished.connect(self._on_ivshmem_changed)
        self._ui.lineedit_ivshmem_out_size.editingFinished.connect(self._on_ivshmem_changed)

        # 为每个输入框设置一致的参数说明。
        TipMgr.add(self._ui.lineedit_ivshmem_phy, ivshmem_doc)
        TipMgr.add(self._ui.lineedit_ivshmem_state_size, ivshmem_doc)
        TipMgr.add(self._ui.lineedit_ivshmem_rw_size, ivshmem_doc)
        TipMgr.add(self._ui.lineedit_ivshmem_out_size, ivshmem_doc)

    def set_comm(self, comm: ResourceComm):
        """
        绑定通信配置对象并刷新界面显示。

        Args:
            comm: 待绑定的通信配置对象。
        """
        self._comm = comm
        if comm is None:
            return

        self._ui.lineedit_ivshmem_phy.setText(utils.to_human_addr(comm.ivshmem_phys()))
        self._ui.lineedit_ivshmem_state_size.setText(utils.to_human_size(comm.ivshmem_state_size()))
        self._ui.lineedit_ivshmem_rw_size.setText(utils.to_human_size(comm.ivshmem_rw_size()))
        self._ui.lineedit_ivshmem_out_size.setText(utils.to_human_size(comm.ivshmem_out_size()))

    def _on_ivshmem_changed(self):
        """
        处理 ivshmem 参数输入框编辑完成事件。

        将输入框中的文本解析为数值，并根据触发来源回写对应配置项。
        """
        if self._comm is None:
            return

        # 通过 sender() 识别哪个输入框触发了信号。
        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(w.text())
        if value is None:
            self.logger.error(f"invalid value {w.text()}")
            return

        # 仅在值有变化时回写，避免重复设置。
        if w is self._ui.lineedit_ivshmem_phy:
            if value != self._comm.ivshmem_phys():
                self._comm.set_ivshmem_phys(value)
        if w is self._ui.lineedit_ivshmem_state_size:
            if value != self._comm.ivshmem_state_size():
                self._comm.set_ivshmem_state_size(value)
        if w is self._ui.lineedit_ivshmem_rw_size:
            if value != self._comm.ivshmem_rw_size():
                self._comm.set_ivshmem_rw_size(value)
        if w is self._ui.lineedit_ivshmem_out_size:
            if value != self._comm.ivshmem_out_size():
                self._comm.set_ivshmem_out_size(value)



