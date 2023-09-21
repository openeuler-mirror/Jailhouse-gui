from ctypes import util
import logging
from typing import Optional
from PySide2 import QtWidgets
from forms.ui_ivshmem_widget import Ui_IVShMemWidget
from jh_resource import ResourceComm
import utils
from tip_widget import TipMgr

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
    logger = logging.getLogger("IVShMemWidget")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_IVShMemWidget()
        self._ui.setupUi(self)
        self._comm: Optional[ResourceComm] = None

        self._ui.lineedit_ivshmem_phy.editingFinished.connect(self._on_ivshmem_changed)
        self._ui.lineedit_ivshmem_state_size.editingFinished.connect(self._on_ivshmem_changed)
        self._ui.lineedit_ivshmem_rw_size.editingFinished.connect(self._on_ivshmem_changed)
        self._ui.lineedit_ivshmem_out_size.editingFinished.connect(self._on_ivshmem_changed)

        TipMgr.add(self._ui.lineedit_ivshmem_phy, ivshmem_doc)
        TipMgr.add(self._ui.lineedit_ivshmem_state_size, ivshmem_doc)
        TipMgr.add(self._ui.lineedit_ivshmem_rw_size, ivshmem_doc)
        TipMgr.add(self._ui.lineedit_ivshmem_out_size, ivshmem_doc)

    def set_comm(self, comm: ResourceComm):
        self._comm = comm
        if comm is None:
            return

        self._ui.lineedit_ivshmem_phy.setText(utils.to_human_addr(comm.ivshmem_phys()))
        self._ui.lineedit_ivshmem_state_size.setText(utils.to_human_size(comm.ivshmem_state_size()))
        self._ui.lineedit_ivshmem_rw_size.setText(utils.to_human_size(comm.ivshmem_rw_size()))
        self._ui.lineedit_ivshmem_out_size.setText(utils.to_human_size(comm.ivshmem_out_size()))

    def _on_ivshmem_changed(self):
        if self._comm is None:
            return

        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(w.text())
        if value is None:
            self.logger.error(f"invalid value {w.text()}")
            return
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



