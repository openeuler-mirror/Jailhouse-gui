import logging
import os
import sys
import json
import logging
from PySide2 import QtWidgets, QtCore
from forms.ui_create_widget import Ui_CreateWidget
from jh_resource import PlatformMgr, ResourceMgr


class CreateDialog(QtWidgets.QDialog):
    logger = logging.getLogger('CreateWidget')

    def __init__(self, parent=None):
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

        self._demo_path = "demos"
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self._demo_path = os.path.join(getattr(sys, '_MEIPASS'), "demos")
            self.logger.info(f"demos path {self._demo_path}")

        for name in os.listdir(self._demo_path):
            if name.endswith('.jhr'):
                self._ui.combobox_demo.addItem(name)

        names = pltmgr.board_names()
        self._ui.combobox_platform.addItems(names)

        self._ui.radiobtn_new.setChecked(True)
        self._ui.stackedwidget_params.setCurrentIndex(0)

        self._ui.btn_close.clicked.connect(self._on_close)
        self._ui.radiobtn_new.clicked.connect(self._on_mode_select)
        self._ui.radiobtn_demo.clicked.connect(self._on_mode_select)
        self._ui.btn_cancel.clicked.connect(self._on_close)
        self._ui.btn_create.clicked.connect(self._on_create)

    def _on_close(self):
        self.setResult(0)
        self.close()

    def _on_mode_select(self):
        if self.sender() is self._ui.radiobtn_new:
            self._ui.stackedwidget_params.setCurrentIndex(0)
        elif self.sender() is self._ui.radiobtn_demo:
            self._ui.stackedwidget_params.setCurrentIndex(1)

    def _on_create(self):
        if self._ui.radiobtn_new.isChecked():
            plt = self._ui.combobox_platform.currentText()
            if len(plt) == 0:
                return
            name = self._ui.lineedit_name.text().strip()
            if len(name) == 0:
                return

            rsc = ResourceMgr().get_instance().create(name, plt)
            if rsc is None:
                return
            ResourceMgr().get_instance().set_current(rsc)
            self.close()
        elif self._ui.radiobtn_demo.isChecked():
            name = self._ui.lineedit_name.text().strip()
            if len(name) == 0:
                return

            demo = self._ui.combobox_demo.currentText()
            demo_fn = os.path.join(self._demo_path, demo)

            try:
                with open(demo_fn, "rt", encoding='utf8') as f:
                    value = json.load(f)
            except Exception as e:
                self.logger.error(f"open {demo_fn} failed: {e}")
                return None

            rsc = ResourceMgr().get_instance().load(value)
            if rsc is None:
                self.logger.error("load resource file failed.")
                return

            rsc.set_name(name)
            ResourceMgr().get_instance().set_current(rsc)
            self.setResult(1)
            self.close()
