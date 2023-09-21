import os
import logging
from hashlib import md5

from PySide2 import QtWidgets, QtCore
from forms.ui_remote_widget import Ui_RemoteWidget
from forms.ui_acoreOs_source_config import Ui_Form_acoreOS
from forms.ui_root_cell_config import Ui_Form_root

from rpc_server.rpc_client import RPCClient
from generator import RootCellGenerator, GuestCellGenerator
from jh_resource import Resource, ResourceGuestCellList, ResourceGuestCell
from jh_resource import ResourceMgr, ResourceSignals
from utils import from_human_num, Profile

class RemoteACoreWidget(QtWidgets.QWidget):
    profile_msl_run_addr = Profile.Item('acore_msl_run_addr', 0)
    profile_os_run_addr = Profile.Item('acore_os_run_addr', 0x80000000)
    profile_app_run_addr = Profile.Item('acore_run_app_addr', 0x82000000)
    profile_msl_enable = Profile.Item('acore_msl_enable', False)
    profile_os_enable = Profile.Item('acore_os_enable', False)
    profile_app_enable = Profile.Item('acore_run_enable', False)
    profile_msl_fn = Profile.Item('acore_msl_fn', "")
    profile_os_fn = Profile.Item('acore_os_fn', "")
    profile_app_fn = Profile.Item('acore_run_fn', "")

    logger = logging.getLogger("RemoteACoreWidget")
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_Form_acoreOS()
        self._ui.setupUi(self)

        self._client: RPCClient = RPCClient.get_instance()

        ResourceSignals.current_rsc.connect(self._on_current_rsc_changed)
        self._ui.comboBox_cell_name.installEventFilter(self)

        self._ui.pushButton_start.clicked.connect(self._on_guest_cell_start_connect)
        self._ui.pushButton_stop.clicked.connect(self._on_guest_cell_stop_connect)

        self._ui.btn_select_file_1.clicked.connect(self.select_msl_file)
        self._ui.btn_select_file_2.clicked.connect(self.select_os_file)
        self._ui.btn_select_file_3.clicked.connect(self.select_app_file)

        self._ui.checkBox_msl.clicked.connect(self._on_checkbox_msl_connect)
        self._ui.checkBox_os.clicked.connect(self._on_checkbox_os_connect)
        self._ui.checkBox_app.clicked.connect(self._on_checkbox_app_connect)

        self._ui.lineEdit_msl_run_addr.setText(hex(self.profile_msl_run_addr.get()))
        self._ui.lineEdit_os_run_addr.setText(hex(self.profile_os_run_addr.get()))
        self._ui.lineEdit_app_run_addr.setText(hex(self.profile_app_run_addr.get()))
        self._ui.lineEdit_select_msl_file.setText(self.profile_msl_fn.get())
        self._ui.lineEdit_select_os_file.setText(self.profile_os_fn.get())
        self._ui.lineEdit_select_app_file.setText(self.profile_app_fn.get())
        self._ui.checkBox_msl.setChecked(self.profile_msl_enable.get())
        self._ui.checkBox_os.setChecked(self.profile_os_enable.get())
        self._ui.checkBox_app.setChecked(self.profile_app_enable.get())

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.MouseButtonPress:
            rsc = ResourceMgr.get_instance().get_current()
            if rsc is None:
                return False
            self._update_cell_list(rsc)
        return False

    def _on_checkbox_msl_connect(self):
        self.profile_msl_enable.set(self._ui.checkBox_msl.isChecked())

    def _on_checkbox_os_connect(self):
        self.profile_os_enable.set(self._ui.checkBox_os.isChecked())

    def _on_checkbox_app_connect(self):
        self.profile_app_enable.set(self._ui.checkBox_app.isChecked())

    def select_msl_file(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(None, "打开文件", "", "*.bin")[0]
        self._ui.lineEdit_select_msl_file.setText(file_name)
        self.profile_msl_fn.set(file_name)

    def select_os_file(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(None, "打开文件", "", "*.bin")[0]
        self._ui.lineEdit_select_os_file.setText(file_name)
        self.profile_os_fn.set(file_name)

    def select_app_file(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(None, "打开文件", "", "*.bin")[0]
        self._ui.lineEdit_select_app_file.setText(file_name)
        self.profile_app_fn.set(file_name)

    def _on_guest_cell_start_connect(self):
        self.logger.debug("start guest cell ")
        rscmgr = ResourceMgr.get_instance()
        rsc = rscmgr.get_current()
        if rsc is None:
            return

        celllist: ResourceGuestCellList = rsc.find(ResourceGuestCellList)
        cellname = self._ui.comboBox_cell_name.currentText()
        cell = celllist.find_cell(cellname)
        if cell is None:
            self.logger.error(f"cell {cellname} not found")
            return

        firmwares = {
            "msl": {
                "enable": self._ui.checkBox_msl.isCheckable(),
                "addr"  : from_human_num(self._ui.lineEdit_msl_run_addr.text().strip()),
                "file"  : self._ui.lineEdit_select_msl_file.text().strip(),
            },
            "os": {
                "enable": self._ui.checkBox_os.isCheckable(),
                "addr"  : from_human_num(self._ui.lineEdit_os_run_addr.text().strip()),
                "file"  : self._ui.lineEdit_select_os_file.text().strip(),
            },
            "app":{
                "enable": self._ui.checkBox_app.isCheckable(),
                "addr"  : from_human_num(self._ui.lineEdit_app_run_addr.text().strip()),
                "file"  : self._ui.lineEdit_select_app_file.text().strip(),
            }
        }

        for name, fw in firmwares.items():
            if fw['enable'] and (fw['addr'] is None or not os.path.exists(fw['file'])):
                self.logger.error(f"[{name}] invalid addr or filename")
                return

        # 生成当前guest cell的代码
        self.logger.info(f"generate cell({cellname}) config")
        guest_cell_bin = GuestCellGenerator.gen_config_bin(cell)
        if guest_cell_bin is None:
            self.logger.error(f"generate cell config failed")
            return

        # 创建之前先查询列表，有无此cell,若有就destroy
        cell_exist = False
        result = self._client.list_cell()
        if result is None or not result.result:
            self.logger.error("get cell list failed")
            return
        self.logger.debug("jailhouse cll list: " + str(result.result))
        for cell in result.result:
            if cell['name'] == cellname:
                cell_exist = True
                break
        if cell_exist:
            self.logger.info(f"destroy cell({cellname})")
            if not self._client.destroy_cell(cellname):
                self.logger.debug(f"destroy cell({cellname}) failed")
                return

        #  创建guest cell
        self.logger.info(f'create cell({cellname})')
        result = self._client.create_cell(guest_cell_bin)
        if not result.status:
            self.logger.error(f"create guest cell failed {result.message}")
            return

        for name, fw in firmwares.items():
            if not fw['enable']:
                continue

            self.logger.info(f"load firmware {name} for cell({cellname}) @{hex(fw['addr'])}")
            try:
                with open(fw['file'], 'rb') as f:
                    fw_bin = f.read()
            except:
                self.logger.error(f"read {fw['file']} failed.")
                return

            self.logger.info(f"md5: {md5(fw_bin).hexdigest()}")
            result = self._client.load_cell(cellname, fw['addr'], fw_bin )
            if result is None or not result.status:
                self.logger.error(f"load failed")
                return

        self.logger.info(f"start cell({cellname})")
        result = self._client.start_cell(cellname)
        if result is None or not result.status:
            self.logger.error(f"start cell({cellname}) failed")
            return

        self.logger.info(f"run cell{cellname} success.")

    def _on_guest_cell_stop_connect(self):
        # 获取当前的comboBox选中的值
        current_text = self._ui.comboBox_cell_name.currentText()
        # 查询列表
        result = self._client.list_cell()
        if result is None:
            self.logger.debug("get guest cell list failed")
            return
        if not result.status:
            self.logger.debug("get guest cell list failed")
            return
        # 查找guest cell
        for cell in result.result:
            if cell['name'] == current_text:
                self.logger.debug(f"destroy {current_text}...")
                if not self._client.destroy_cell(current_text):
                    self.logger.debug(f"destroy {current_text} failed")
                    return
        # destroy
        self._client.destroy_cell(current_text)
        self.logger.debug(f"destroy {current_text} success")

    def _on_current_rsc_changed(self, sender, **kwargs):
        rsc = kwargs.get('rsc')
        self._update_cell_list(rsc)

    def _update_cell_list(self, rsc: Resource):
        if rsc is None:
            return

        current = self._ui.comboBox_cell_name.currentText()
        self._ui.comboBox_cell_name.clear()
        cell_list: ResourceGuestCellList = rsc.find(ResourceGuestCellList)
        for i in range(cell_list.cell_count()):
            cell: ResourceGuestCell = cell_list.cell_at(i)
            cell_name = cell.name()
            self._ui.comboBox_cell_name.addItem(cell_name)
            if current == cell_name:
                self._ui.comboBox_cell_name.setCurrentIndex(i)


class RemoteRootWidget(QtWidgets.QWidget):
    logger = logging.getLogger("RemoteRootWidget")
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_Form_root()
        self._ui.setupUi(self)

        self._client: RPCClient = RPCClient.get_instance()

        self._ui.pushButton_start.clicked.connect(self._on_root_cell_start_connect)
        self._ui.pushButton_stop.clicked.connect(self._on_root_cell_destory_connect)

    def _on_root_cell_start_connect(self):
        # 把root cell的资源获取出来
        rscmgr = ResourceMgr.get_instance()
        rsc = rscmgr.get_current()
        if rsc is None:
            self.logger.error("ResourceMgr failed")
            return

        # 生成源码
        root_cell_bin = RootCellGenerator.gen_config_bin(rsc)
        if root_cell_bin is None:
            self.logger.error("root_cell_bin is None")
            return

        # 每次创建, 前先destroy
        result = self._client.list_cell()
        if result is None or not result.status:
            self.logger.error("get root cell list failed")
            return
        for cell in result.result:
            if cell['id'] == 0:
                self.logger.debug(f"jailhouse disable")
                result = self._client.jailhouse_disable()
                if not result.status:
                    self.logger.debug("disable failed")
                    return
                break

        # 开始创建root cell
        result = self._client.jailhouse_enable(root_cell_bin)
        if not result.status:
            self.logger.error("jailhouse_enable failed")
            self.logger.error(f"{result.message}")
            return
        self.logger.info("jailhouse root cell enable success")

    def _on_root_cell_destory_connect(self):
        # 先获取列表
        result = self._client.list_cell()
        if not result.status or result is None:
            self.logger.error("get root cell list failed")
            return
        result = self._client.jailhouse_disable()
        if not result.status:
            self.logger.error("get root cell list failed")
            return
        self.logger.debug("root cell disable success")

class RemoteWidget(QtWidgets.QWidget):
    logger = logging.getLogger("RemoteWidget")

    profile_addr = Profile.Item('remote_addr', 'tcp://127.0.0.1:4240')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_RemoteWidget()
        self._ui.setupUi(self)

        self._ui.lineedit_addr.setText(self.profile_addr.get())

        self._client: RPCClient = RPCClient.get_instance()

        self.table_root = RemoteRootWidget(self)
        self.table_acoreos = RemoteACoreWidget(self)

        self._ui.tabWidget.addTab(self.table_root, "Root Cell")
        self._ui.tabWidget.addTab(self.table_acoreos, "AcoreOs")

        self._client.state_changed.connect(self._on_state_changed)

        self._ui.lineedit_addr.editingFinished.connect(self._on_addr_edit_finished)
        self._ui.btn_connect.clicked.connect(self._on_connect)

    def _on_addr_edit_finished(self):
        self.profile_addr.set(self._ui.lineedit_addr.text().strip())

    def _on_state_changed(self, sender):
        if sender is not self._client:
            return

        if self._client.is_connected():
            self._ui.btn_connect.setChecked(True)
            self._ui.btn_connect.setText("断开")
        else:
            self._ui.btn_connect.setChecked(False)
            self._ui.btn_connect.setText("连接")

    def _on_connect(self):
        if not self._client.is_connected():
            if not self._client.connect(self._ui.lineedit_addr.text().strip()):
                self.logger.error("连接失败")
        else:
            self._client.close()

