import os
import copy
from hashlib import md5
from PySide2 import QtWidgets
from jh_resource import ACoreRunInfo, CommonOSRunInfo
from jh_resource import ResourceGuestCell
from forms.ui_acore_runinfo import Ui_ACoreRunInfoWidget
from generator import GuestCellGenerator
from commonos_runinfo import OSRunInfoWidget
from common_widget import set_lineedit_status
from utils import from_human_num, to_human_addr
from rpc_server.rpc_client import RPCClient


class ACoreRunInfoWidget(OSRunInfoWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._runinfo = ACoreRunInfo()

        self._ui = Ui_ACoreRunInfoWidget()
        self._ui.setupUi(self)

        self._ui.lineedit_msl_addr.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_msl_path.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_os_addr.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_os_path.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_app_addr.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_app_path.editingFinished.connect(self._on_edit_finished)
        self._ui.groupbox_app.clicked.connect(self._on_group_app_clicked)
        self._ui.btn_select_msl.clicked.connect(self._on_select_file)
        self._ui.btn_select_os.clicked.connect(self._on_select_file)
        self._ui.btn_select_app.clicked.connect(self._on_select_file)

    def reset(self):
        self._ui.lineedit_msl_addr.clear()
        self._ui.lineedit_msl_path.clear()
        self._ui.lineedit_os_addr.clear()
        self._ui.lineedit_os_path.clear()
        self._ui.lineedit_app_addr.clear()
        self._ui.lineedit_app_path.clear()
        self._ui.groupbox_app.setChecked(False)

    def set_runinfo(self, runinfo: ACoreRunInfo):
        self._runinfo = None
        if runinfo is None:
            self.reset()
            return
        if not isinstance(runinfo, ACoreRunInfo):
            return

        self._ui.lineedit_msl_addr.setText(to_human_addr(runinfo.msl.addr))
        self._ui.lineedit_msl_path.setText(runinfo.msl.filename)
        self._ui.lineedit_os_addr.setText(to_human_addr(runinfo.os.addr))
        self._ui.lineedit_os_path.setText(runinfo.os.filename)
        self._ui.lineedit_app_addr.setText(to_human_addr(runinfo.app.addr))
        self._ui.lineedit_app_path.setText(runinfo.app.filename)
        self._ui.groupbox_app.setChecked(runinfo.app.enable)

        self._runinfo = copy.deepcopy(runinfo)

    def _on_edit_finished(self):
        if self._runinfo is None:
            return
        changed = False
        if self.sender() is self._ui.lineedit_msl_addr:
            msl_addr = from_human_num(self._ui.lineedit_msl_addr.text())
            if msl_addr is None:
                set_lineedit_status(self._ui.lineedit_msl_addr, False)
                return
            set_lineedit_status(self._ui.lineedit_msl_addr, True)
            changed = msl_addr != self._runinfo.msl.addr
            self._runinfo.msl.addr = msl_addr
        elif self.sender() is self._ui.lineedit_msl_path:
            msl_path = self._ui.lineedit_msl_path.text()
            changed = msl_path != self._runinfo.msl.filename
            self._runinfo.msl.filename = msl_path
        elif self.sender() is self._ui.lineedit_os_addr:
            os_addr = from_human_num(self._ui.lineedit_os_addr.text())
            if os_addr is None:
                set_lineedit_status(self._ui.lineedit_os_addr, False)
                return
            set_lineedit_status(self._ui.lineedit_os_addr, True)
            changed = os_addr != self._runinfo.os.addr
            self._runinfo.os.addr = os_addr
        elif self.sender() is self._ui.lineedit_os_path:
            os_path = self._ui.lineedit_os_path.text()
            changed = os_path != self._runinfo.os.filename
            self._runinfo.os.filename = os_path
        elif self.sender() is self._ui.lineedit_app_addr:
            app_addr = from_human_num(self._ui.lineedit_app_addr.text())
            if app_addr is None:
                set_lineedit_status(self._ui.lineedit_app_addr, False)
                return
            set_lineedit_status(self._ui.lineedit_app_addr, True)
            changed = app_addr != self._runinfo.app.addr
            self._runinfo.app.addr = app_addr
        elif self.sender() is self._ui.lineedit_app_path:
            app_path= self._ui.lineedit_app_path.text()
            changed = app_path != self._runinfo.app.filename
            self._runinfo.app.filename = app_path

        if changed:
            self.value_changed.emit()

    def _on_group_app_clicked(self):
        if self._runinfo is None:
            return
        self._runinfo.app.enable = self._ui.groupbox_app.isChecked()
        self.value_changed.emit()

    def _on_select_file(self):
        if self._runinfo is None:
            return
        caption = '选择文件'
        if self.sender() is self._ui.btn_select_msl:
            caption = '选择MSL固件'
        elif self.sender() is self._ui.btn_select_os:
            caption = '选择OS固件'
        elif self.sender() is self._ui.btn_select_app:
            caption = '选择APP固件'

        filename = QtWidgets.QFileDialog.getOpenFileName(None, caption, "", "firmware(*.bin);;*(*.*)")[0]
        if len(filename) == 0:
            return

        changed = False
        if self.sender() is self._ui.btn_select_msl:
            changed = (filename != self._runinfo.msl.filename)
            self._ui.lineedit_msl_path.setText(filename)
            self._runinfo.msl.filename = filename
        elif self.sender() is self._ui.btn_select_os:
            changed = (filename != self._runinfo.os.filename)
            self._ui.lineedit_os_path.setText(filename)
            self._runinfo.os.filename = filename
        elif self.sender() is self._ui.btn_select_app:
            changed = (filename != self._runinfo.app.filename)
            self._ui.lineedit_app_path.setText(filename)
            self._runinfo.app.filename = filename

        if changed:
            self.value_changed.emit()

    def run(self, cell: ResourceGuestCell) -> bool:
        client = RPCClient.get_instance()
        if cell is None:
            return False
        if not client.is_connected():
            return False

        cellname = cell.name()
        os_runinfo: ACoreRunInfo = self.runinfo()
        self.logger.info(f"start run acore cell {cellname}")

        # 天脉系统的入口地址为MSL的加载地址
        if cell.reset_addr() != os_runinfo.msl.addr:
            cell.set_reset_addr(os_runinfo.msl.addr)

        images = list()
        images.extend((
            {
                'name': "MSL",
                "enable": True,
                "addr": os_runinfo.msl.addr,
                "file": self.abspath(cell, os_runinfo.msl.filename)
            },
            {
                'name': "OS",
                "enable": True,
                "addr": os_runinfo.os.addr,
                "file": self.abspath(cell, os_runinfo.os.filename)
            },
            {
                'name': "APP",
                "enable": os_runinfo.app.enable,
                "addr": os_runinfo.app.addr,
                "file": self.abspath(cell, os_runinfo.app.filename)
            },
        ))

        for image in images:
            if not image['enable']:
                continue
            if image['addr'] is None:
                self.logger.error(f"image ({image['name']}) invalid.")
                return
            if not os.path.exists(image['file']):
                self.logger.error(f"image ({image['name']}) not found: {image['file']}")
                return

        # 生成当前guest cell的配置
        self.logger.info(f"generate cell({cellname}) config")
        guest_cell_bin = GuestCellGenerator.gen_config_bin(cell)
        if guest_cell_bin is None:
            self.logger.error(f"generate cell config failed")
            return

        # 创建之前先查询列表，有无此cell,若有就destroy
        cell_exist = False
        result = client.list_cell()
        if result is None or not result.result:
            self.logger.error("get cell list failed")
            return
        for _cell in result.result:
            if _cell['name'] == cellname:
                cell_exist = True
                break
        if cell_exist:
            self.logger.info(f"cell exist, destroy cell({cellname}) firstly.")
            if not client.destroy_cell(cellname):
                self.logger.debug(f"destroy cell({cellname}) failed")
                return

        #  创建guest cell
        self.logger.info(f'create cell({cellname})')
        result = client.create_cell(guest_cell_bin)
        if not result.status:
            self.logger.error(f"create guest cell failed {result.message}")
            return

        for image in images:
            if not image['enable']:
                continue
            name = image['name']
            addr = image['addr']
            file = image['file']

            self.logger.info(f"load firmware {name} for cell({cellname}) @{hex(addr)}")
            try:
                with open(file, 'rb') as f:
                    fw_bin = f.read()
            except:
                self.logger.error(f"read {file} failed.")
                return

            self.logger.info(f"md5: {md5(fw_bin).hexdigest()}")
            result = client.load_cell(cellname, addr, fw_bin )
            if result is None or not result.status:
                self.logger.error(f"load failed")
                return

        if not self.load_resource_table(cell):
            self.logger.error("load resource table failed.")
            return

        self.logger.info(f"start cell({cellname})")
        result = client.start_cell(cellname)
        if result is None or not result.status:
            self.logger.error(f"start cell({cellname}) failed")
            return

        self.logger.info(f"run cell{cellname} success.")