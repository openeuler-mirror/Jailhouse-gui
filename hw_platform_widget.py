from typing import Optional
from forms.ui_hw_platform_widget import Ui_HwPlatformWidget
from PySide2 import QtWidgets
from jh_resource import ResourcePlatform
from cpu_widget import CPUWidget
from board_widget import BoardWidget


class HwPlatformWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_HwPlatformWidget()
        self._ui.setupUi(self)

        self._platform: Optional[ResourcePlatform] = None

        self._blank_page = QtWidgets.QWidget(self)
        self._cpu_page = CPUWidget(self)
        self._board_page = BoardWidget()
        self._ui.stacked_widget.addWidget(self._blank_page)
        self._ui.stacked_widget.addWidget(self._cpu_page)
        self._ui.stacked_widget.addWidget(self._board_page)
        self._ui.stacked_widget.setCurrentWidget(self._blank_page)

        self._ui.btn_cpu.clicked.connect(self._on_submenu)
        self._ui.btn_board.clicked.connect(self._on_submenu)

    def set_platform(self, platform: ResourcePlatform):
        self._cpu_page.set_cpu(None)
        self._board_page.set_board(None)

        if platform is None:
            self._platform = platform
            return
        self._platform = None

        self._cpu_page.set_cpu(platform.cpu())
        self._board_page.set_board(platform.board())

        self._platform = platform
        self._ui.btn_cpu.setChecked(True)
        self._ui.stacked_widget.setCurrentWidget(self._cpu_page)

    def _on_submenu(self):
        if self._platform is None:
            return
        if self._ui.btn_cpu.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._cpu_page)
        if self._ui.btn_board.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._board_page)
