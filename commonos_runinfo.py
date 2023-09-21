import os
import copy
import logging
from typing import List
from hashlib import md5
from PySide2 import QtWidgets, QtCore
from jh_resource import ResourceGuestCell, ResourceBase, Resource
from jh_resource import ImageInfo
from jh_resource import OSRunInfoBase, CommonOSRunInfo
from jh_resource import MemRegionList, MemRegion
from generator import GuestCellGenerator
from forms.ui_image_info import Ui_ImageInfoWidget
from forms.ui_common_runinfo import Ui_CommonRunInfoWidget
from common_widget import clean_layout
from utils import from_human_num, to_human_addr
from rpc_server.rpc_client import RPCClient


class ImageInfoWidget(QtWidgets.QWidget):
    remove = QtCore.Signal()
    changed = QtCore.Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ImageInfoWidget()
        self._ui.setupUi(self)
        self._imageinfo = ImageInfo()

        self._ui.btn_file.clicked.connect(self._on_file)
        self._ui.btn_remove.clicked.connect(self._on_remove)
        self._ui.lineedit_name.editingFinished.connect(self._on_name_changed)
        self._ui.lineedit_load_addr.editingFinished.connect(self._on_addr_changed)
        self._ui.lineedit_filename.editingFinished.connect(self._on_file_changed)
        self._ui.checkbox_enable.clicked.connect(self._on_enable)

    def get_imageinfo(self) -> ImageInfo:
        return self._imageinfo

    def set_imageinfo(self, image_info: ImageInfo):
        self._imageinfo = copy.deepcopy(image_info)
        self._ui.lineedit_name.setText(image_info.name)
        self._ui.lineedit_load_addr.setText(to_human_addr(image_info.addr))
        self._ui.lineedit_filename.setText(image_info.filename)
        self._ui.checkbox_enable.setChecked(image_info.enable)

    def _on_file(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "选择文件", "")[0]
        if len(filename) == 0:
            return
        self._ui.lineedit_filename.setText(filename)
        if self._imageinfo.filename != filename:
            self._imageinfo.filename = filename
            self.changed.emit()

    def _on_remove(self):
        self.remove.emit()

    def _on_enable(self):
        en = self._ui.checkbox_enable.isChecked()
        if self._imageinfo.enable != en:
            self._imageinfo.enable = en
            self.changed.emit()

    def _on_name_changed(self):
        name = self._ui.lineedit_name.text().strip()
        if name != self._imageinfo.name:
            self._imageinfo.name = name
            self.changed.emit()

    def _on_addr_changed(self):
        addr = from_human_num(self._ui.lineedit_load_addr.text())
        if addr is None:
            return

        if addr != self._imageinfo.addr:
            self._imageinfo.addr = addr
            self.changed.emit()

    def _on_file_changed(self):
        filename = self._ui.lineedit_filename.text().strip()
        if filename != self._imageinfo.filename:
            self._imageinfo.filename = filename
            self.changed.emit()


class OSRunInfoWidget(QtWidgets.QWidget):
    logger = logging.getLogger("RunInfoWidget")
    value_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runinfo = CommonOSRunInfo()

    def runinfo(self) -> OSRunInfoBase:
        return copy.deepcopy(self._runinfo)

    def load_resource_table(self, cell: ResourceGuestCell) -> bool:
        client = RPCClient.get_instance()
        cellname = cell.name()
        rsc_table_mmap = cell.system_mem_resource_table()

        if rsc_table_mmap is not None:
            self.logger.info(f"load resource table 0x{rsc_table_mmap.virt():x}@{rsc_table_mmap.size()}")
            rsc_table_bin = GuestCellGenerator.gen_resource_table_bin(cell)
            if rsc_table_bin is None:
                self.logger.error(f'generate resource table dtb failed.')
                return False

            self.logger.info(f"resource table size: {len(rsc_table_bin)} sum: {sum(rsc_table_bin)}")
            if len(rsc_table_bin) > rsc_table_mmap.size():
                self.logger.error(f'resource table size {rsc_table_mmap.size()}, need {len(rsc_table_bin)}')
                return False
            result = client.load_cell(cellname, rsc_table_mmap.virt(), rsc_table_bin )
            if result is None or not result.status:
                self.logger.error(f"load failed")
                return False
            return True
        return True

    def abspath(self, rsc_any: ResourceBase, path) -> str:
        if os.path.isabs(path):
            return path
        rsc: Resource = rsc_any.ancestor(Resource)
        if rsc is None:
            return ""
        return rsc.abs_path(path)

    # 抽象方法
    def reset(self):
        pass

    # 抽象方法
    def set_runinfo(self, runinfo: OSRunInfoBase):
        pass

    # 抽象方法
    def run(self, cell: ResourceGuestCell) -> bool:
        """
        运行系统
        """
        return False


class CommonOSRunInfoWidget(OSRunInfoWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._runinfo = CommonOSRunInfo()

        self._ui = Ui_CommonRunInfoWidget()
        self._ui.setupUi(self)

        self._images: List[ImageInfoWidget] = list()
        self._ui.btn_add_image.clicked.connect(self._on_add_image)
        self._ui.lineedit_reset_addr.editingFinished.connect(self._on_reset_addr_changed)

    def reset(self):
        self._images.clear()
        clean_layout(self._ui.frame_images.layout())

    def set_runinfo(self, runinfo: CommonOSRunInfo):
        self.reset()
        for image in runinfo.images():
            w = ImageInfoWidget(self)
            w.set_imageinfo(image)
            self._ui.frame_images.layout().addWidget(w)
            self._images.append(w)
            w.remove.connect(self._on_remove_image)
            w.changed.connect(self._on_image_changed)
        self._ui.lineedit_reset_addr.setText(to_human_addr(runinfo.reset_addr()))

        self._runinfo = copy.deepcopy(runinfo)

        # 处理事件后，外面才能获取正确的sizeHint
        QtWidgets.QApplication.instance().processEvents()

    def _update_runinfo(self):
        self._runinfo.clear_image()
        for w in self._images:
            self._runinfo.add_image(w.get_imageinfo())

    def _on_image_changed(self):
        self._update_runinfo()
        self.value_changed.emit()

    def _on_add_image(self):
        image_info = ImageInfoWidget(self)
        self._ui.frame_images.layout().addWidget(image_info)
        self._images.append(image_info)
        image_info.remove.connect(self._on_remove_image)
        image_info.changed.connect(self._on_image_changed)
        self._update_runinfo()
        QtWidgets.QApplication.instance().processEvents()
        self.value_changed.emit()

    def _on_remove_image(self):
        image_info: ImageInfoWidget = self.sender()
        image_info.hide()
        image_info.deleteLater()
        self._images.remove(image_info)
        self._update_runinfo()
        QtWidgets.QApplication.instance().processEvents()
        self.value_changed.emit()

    def _on_reset_addr_changed(self):
        value = from_human_num(self._ui.lineedit_reset_addr.text())
        if value is None:
            self._ui.lineedit_reset_addr.setText(to_human_addr(self._runinfo.reset_addr()))
            return

        self._runinfo.set_reset_addr(value)
        self.value_changed.emit()

    def run(self, cell: ResourceGuestCell) -> bool:
        client = RPCClient.get_instance()
        if cell is None:
            return False
        if not client.is_connected():
            return False

        regions = MemRegionList()
        cellname = cell.name()
        os_runinfo: CommonOSRunInfo = self.runinfo()
        self.logger.info(f"start run cell {cellname}")

        reset_addr = from_human_num(self._ui.lineedit_reset_addr.text())
        if reset_addr is None:
            self.logger.error(f"invalid entry addr {self._ui.lineedit_reset_addr.text()}")
            return False
        self.logger.info(f"set reset addr {hex(reset_addr)}")
        cell.set_reset_addr(reset_addr)

        for image in os_runinfo.images():
            if not image.enable:
                continue

            if image.addr is None:
                self.logger.error(f"image ({image.name}) invalid.")
                return
            if not os.path.isfile(self.abspath(cell, image.filename)):
                self.logger.error(f"image ({image.name}) not found: {image.filename}")
                return

            size = os.path.getsize(self.abspath(cell, image.filename))
            if regions.is_overlap(image.addr, size):
                self.logger.error(f"image ({image.name}) overlap")
                return
            regions.add(image.addr, size)

        # 生成当前guest cell的代码
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

        for image in os_runinfo.images():
            if not image.enable:
                continue
            name = image.name
            addr = image.addr
            file = self.abspath(cell, image.filename)

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
