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
    logger = logging.getLogger('BoardWidget')

    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_BoardWidget()
        self._ui.setupUi(self)

        self._board_mem_editor = MemEditWidget()
        self._ui.frame_board_mems.layout().addWidget(self._board_mem_editor)

        self._board: Optional[ResourceBoard] = None
        self._device_layout = FlowLayout(self._ui.frame_devices_items)
        self._cpu_editor = CPUEditWidget(self)
        self._ui.frame_cpus_content.layout().addWidget(self._cpu_editor)

        self._ui.btn_update_from_plt.clicked.connect(self._on_update_from_plt)
        self._cpu_editor.cpus_changed.connect(self._on_cpus_changed)
        self._board_mem_editor.signal_changed.connect(self._on_board_mems_changed)

        ResourceSignals.modified.connect(self._on_rsc_modified)

    def set_board(self, board: ResourceBoard):
        self._board = board
        self._update()

    def _update(self):
        board = self._board
        self._ui.label_model.setText("")
        self._ui.label_vendor.setText("")
        clean_layout(self._device_layout)
        self._cpu_editor.set_cpu_count(0)
        self._board_mem_editor.set_regions(list())

        if board is None:
            return

        self._ui.label_model.setText(board.model)
        self._ui.label_vendor.setText(board.vendor)

        cpu: ResourceCPU = board.parent().cpu()

        dev_names = sorted(map(lambda x: x.name(), cpu.devices()))
        for dev in dev_names:
            w = SelectButton(dev, self)
            self._device_layout.addWidget(w)
            if dev in board.devices:
                w.setChecked(True)

        self._cpu_editor.set_cpu_count( cpu.cpu_count() )
        self._cpu_editor.set_cpus(board.cpus())
        self._board_mem_editor.set_regions(board.ram_regions())

    def _on_rsc_modified(self, sender, **kwargs):
        if sender is not self._board:
            return
        self._update()

    def _on_update_from_plt(self):
        if self._board is None:
            return

        board: PlatformMgr.Board = PlatformMgr.get_instance().find_board(self._board.name())
        if board is None:
            self.logger.error(f"can not find board {self._board.name()} from platform")
            return

        if not self._board.from_dict(board.value):
            self.logger.error(f"update board failed.")
            return

        self._board.set_modified()

    def _on_cpus_changed(self):
        if self._board is None:
            return
        self._board.set_cpus(self._cpu_editor.get_cpus())

    def _on_board_mems_changed(self):
        if self._board is None:
            return
        self._board.set_ram_regions(self._board_mem_editor.get_value())
