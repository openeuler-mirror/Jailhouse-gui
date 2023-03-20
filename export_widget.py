import logging
import abc
from typing import Optional, Union
from PySide2 import QtWidgets, QtCore
from mako.template import Template
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from forms.ui_export_widget import Ui_ExportWidget
from jh_resource import ResourceMgr, ResourceSignals
from jh_resource import ResourceGuestCellList, ResourceRootCell
from jh_resource import ResourceGuestCell, Resource, LinuxRunInfo
from generator import GuestCellGenerator, RootCellGenerator
from rpc_server.rpc_client import RPCClient
from frameless_window import FramelessWindow
from common_widget import clean_layout

class hexdump:
    def __init__(self, buf, off=0):
        self.buf = buf
        self.off = off

    def __iter__(self):
        last_bs, last_line = None, None
        for i in range(0, len(self.buf), 16):
            bs = bytearray(self.buf[i : i + 16])
            line = "{:08x}  {:23}  {:23}  |{:16}|".format(
                self.off + i,
                " ".join(("{:02x}".format(x) for x in bs[:8])),
                " ".join(("{:02x}".format(x) for x in bs[8:])),
                "".join((chr(x) if 32 <= x < 127 else "." for x in bs)),
            )
            if bs == last_bs:
                line = "*"
            if bs != last_bs or line != last_line:
                yield line
            last_bs, last_line = bs, line
        yield "{:08x}".format(self.off + len(self.buf))

    def __str__(self):
        return "\n".join(self)

    def __repr__(self):
        return "\n".join(self)

class GeneratorBase(metaclass=abc.ABCMeta):
    def __init__(self) -> None:
        self._userdata = None

    @abc.abstractclassmethod
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        pass

    @abc.abstractclassmethod
    def get_name(self) -> str:
        pass

    def get_text(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        data = self.get_save_data(cell)
        if isinstance(data, str):
            return data
        if isinstance(data, bytes):
            return str(hexdump(data, 0))
        return ""

    @abc.abstractclassmethod
    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        pass

    @abc.abstractclassmethod
    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> Union[str,bytes]:
        pass

    def set_userdata(self, data):
        self._userdata =  data

    def get_userdata(self):
        return self._userdata

class CellConfigSrcGenerator(GeneratorBase):
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        return True

    def get_name(self) -> str:
        return "Cell配置源码"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if isinstance(cell, ResourceGuestCell):
            return f'{cell.name()}.c'
        elif isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.c'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> Union[str,bytes]:
        if isinstance(cell, ResourceGuestCell):
            return GuestCellGenerator.gen_config_source(cell)
        elif isinstance(cell, ResourceRootCell):
            return RootCellGenerator.gen_config_source(cell.find(Resource))
        return None

class CellConfigBinGenerator(GeneratorBase):
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        return True

    def get_name(self) -> str:
        return "Cell配置二进制"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if isinstance(cell, ResourceGuestCell):
            return f'{cell.name()}.cell'
        elif isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.cell'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bytes:
        if isinstance(cell, ResourceGuestCell):
            return GuestCellGenerator.gen_config_bin(cell)
        elif isinstance(cell, ResourceRootCell):
            return RootCellGenerator.gen_config_bin(cell.find(Resource))
        return None

class GuestLinuxDtsGenerator(GeneratorBase):
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        if not isinstance(cell, ResourceGuestCell):
            return False
        if not isinstance(cell.runinfo().os_runinfo(), LinuxRunInfo):
            return False
        return True

    def get_name(self) -> str:
        return "linux设备树源码"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.dts'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if not isinstance(cell, ResourceGuestCell):
            return None
        return GuestCellGenerator.gen_guestlinux_dts(cell)

class GuestLinuxDtbGenerator(GeneratorBase):
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        if not isinstance(cell, ResourceGuestCell):
            return False
        if not isinstance(cell.runinfo().os_runinfo(), LinuxRunInfo):
            return False
        return True

    def get_name(self) -> str:
        return "linux设备树二进制"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.dtb'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if not isinstance(cell, ResourceGuestCell):
            return None
        return GuestCellGenerator.gen_guestlinux_dtb(cell)

class ResourceTableGenerator(GeneratorBase):
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        if not isinstance(cell, ResourceGuestCell):
            return False
        if isinstance(cell.runinfo().os_runinfo(), LinuxRunInfo):
            return False
        return True

    def get_name(self) -> str:
        return "guestcell资源表"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.rsctable'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        if not isinstance(cell, ResourceGuestCell):
            return None
        return GuestCellGenerator.gen_resource_table(cell)

class ExportDialog(QtWidgets.QDialog):

    logger = logging.getLogger("ExportDialog")
    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_ExportWidget()
        self._ui.setupUi(self)
        self._ui.frame_title.hide()
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self._ui.combobox_cell.setView(QtWidgets.QListView())
        self._rootcell_name = "root cell"

        rscmgr = ResourceMgr.get_instance()
        rsc = rscmgr.get_current()

        if rsc is None:
            self.setWindowTitle("当前无可导出资源")
        else:
            self.setWindowTitle(f"导出 {rsc.name()}")

        self._generators: list[GeneratorBase] = [
            CellConfigSrcGenerator(),
            CellConfigBinGenerator(),
            GuestLinuxDtsGenerator(),
            GuestLinuxDtbGenerator(),
            ResourceTableGenerator(),
        ]

        clean_layout(self._ui.frame_gens.layout())
        for gen in self._generators:
            btn = QtWidgets.QPushButton(gen.get_name(), parent=self)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setFlat(True)
            btn.clicked.connect(self._on_generator_click)
            self._ui.frame_gens.layout().addWidget(btn)
            gen.set_userdata(btn)

        self._update_cell_list(rsc)
        self._ui.combobox_cell.currentIndexChanged.connect(self._on_cell_changed)
        self._ui.btn_save.clicked.connect(self._on_save)
        self._ui.btn_close.clicked.connect(self._on_close)

    def _current_cell(self):
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return
        cellname = self._ui.combobox_cell.currentText()
        if cellname == self._rootcell_name:
            return rsc.jailhouse().rootcell()
        else:
            return rsc.jailhouse().guestcells().find_cell(cellname)

    def _current_generator(self) -> GeneratorBase:
        for gen in self._generators:
            btn: QtWidgets.QPushButton = gen.get_userdata()
            if btn.isVisible() and btn.isChecked():
                return gen
        return None

    def _on_generator_click(self):
        cell = self._current_cell()
        if cell is None:
            return
        btn = self.sender()
        generator = None
        for gen in self._generators:
            if gen.get_userdata() is btn:
                generator = gen
        if generator is None:
            return

        self._ui.textbrowser.clear()
        txt = generator.get_text(cell)
        if isinstance(txt, str):
            self._show_source(txt)

    def _on_cell_changed(self):
        cell = self._current_cell()
        if cell is None:
            return
        for gen in self._generators:
            btn = gen.get_userdata()
            btn.setVisible(gen.is_support(cell))

    def _update_cell_list(self, rsc: Resource):
        if rsc is None:
            return
        self._ui.combobox_cell.clear()
        self._ui.combobox_cell.addItem(self._rootcell_name)
        cell_list: ResourceGuestCellList = rsc.find(ResourceGuestCellList)
        for i in range(cell_list.cell_count()):
            cell: ResourceGuestCell = cell_list.cell_at(i)
            self._ui.combobox_cell.addItem(cell.name())
        self._on_cell_changed()

    def _show_source(self, source):
        formatter = HtmlFormatter(full=True, noclasses=True, style="github-dark", linenos=False, nobackground=True)
        src_html = highlight(source, get_lexer_by_name("C"), formatter)
        self._ui.textbrowser.setHtml(src_html)

    def _on_save(self):
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return None

        cellname = self._ui.combobox_cell.currentText()
        cell = self._current_cell()
        generator = self._current_generator()
        if cell is None or generator is None:
            return

        data = generator.get_save_data(cell)
        name = generator.get_save_name(cell)
        if data is None:
            return

        filename = QtWidgets.QFileDialog.getSaveFileName(self, f"保存 {generator.get_name()}: {cellname}",
                                                         name)[0]
        if len(filename) == 0:
            return
        
        if isinstance(data, str):
            try:
                with open(filename, "wt") as f:
                    f.write(data)
                self.logger.info(f"save {cellname} source to {filename}")
            except:
                self.logger.error(f"save file {filename} failed.")
                return
        if isinstance(data, bytes):
            try:
                with open(filename, "wb") as f:
                    f.write(data)
                self.logger.info(f"save {cellname} source to {filename}")
            except:
                self.logger.error(f"save file {filename} failed.")
                return

    def _on_close(self):
        self.close()