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
    """十六进制转储工具类
    
    将字节数据格式化为十六进制字符串，支持按16字节块迭代输出
    
    Attributes:
        buf: 待转储的字节数据
        off: 数据偏移量（用于地址计算）
    """
    def __init__(self, buf, off=0):
        self.buf = buf
        self.off = off

    def __iter__(self):
        """迭代器方法：按16字节块生成转储行"""
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
        """返回完整的十六进制转储字符串"""
        return "\n".join(self)

    def __repr__(self):
        """返回对象的字符串表示"""
        return "\n".join(self)

class GeneratorBase(metaclass=abc.ABCMeta):
    """生成器基类（抽象类）
    
    定义生成器接口，所有具体生成器需实现以下抽象方法
    """
    def __init__(self) -> None:
        self._userdata = None

    @abc.abstractclassmethod
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        """判断是否支持该细胞类型"""
        pass

    @abc.abstractclassmethod
    def get_name(self) -> str:
        """获取生成器名称（用于UI显示）"""
        pass

    def get_text(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """获取用于显示的文本内容（默认实现）"""
        data = self.get_save_data(cell)
        if isinstance(data, str):
            return data
        if isinstance(data, bytes):
            return str(hexdump(data, 0))
        return ""

    @abc.abstractclassmethod
    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """获取保存文件名"""
        pass

    @abc.abstractclassmethod
    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> Union[str,bytes]:
        """获取保存数据（字符串或字节）"""
        pass

    def set_userdata(self, data):
        """设置用户数据"""
        self._userdata =  data

    def get_userdata(self):
        """获取用户数据"""
        return self._userdata

class CellConfigSrcGenerator(GeneratorBase):
    """细胞配置源码生成器"""
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        """支持所有细胞类型"""
        return True

    def get_name(self) -> str:
        """返回生成器名称"""
        return "Cell配置源码"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成保存文件名（.c后缀）"""
        if isinstance(cell, ResourceGuestCell):
            return f'{cell.name()}.c'
        elif isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.c'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> Union[str,bytes]:
        """生成细胞配置C源码"""
        if isinstance(cell, ResourceGuestCell):
            return GuestCellGenerator.gen_config_source(cell)
        elif isinstance(cell, ResourceRootCell):
            return RootCellGenerator.gen_config_source(cell.find(Resource))
        return None

class CellConfigBinGenerator(GeneratorBase):
    """细胞配置二进制生成器"""
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        """支持所有细胞类型"""
        return True

    def get_name(self) -> str:
        """返回生成器名称"""
        return "Cell配置二进制"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成保存文件名（.cell后缀）"""
        if isinstance(cell, ResourceGuestCell):
            return f'{cell.name()}.cell'
        elif isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.cell'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bytes:
        """生成细胞配置二进制数据"""
        if isinstance(cell, ResourceGuestCell):
            return GuestCellGenerator.gen_config_bin(cell)
        elif isinstance(cell, ResourceRootCell):
            return RootCellGenerator.gen_config_bin(cell.find(Resource))
        return None

class GuestLinuxDtsGenerator(GeneratorBase):
    """Linux设备树源码生成器"""
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        """仅支持Guest Cell且操作系统为Linux"""
        if not isinstance(cell, ResourceGuestCell):
            return False
        if not isinstance(cell.runinfo().os_runinfo(), LinuxRunInfo):
            return False
        return True

    def get_name(self) -> str:
        """返回生成器名称"""
        return "linux设备树源码"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成保存文件名（.dts后缀）"""
        if isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.dts'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成Linux设备树源码"""
        if not isinstance(cell, ResourceGuestCell):
            return None
        return GuestCellGenerator.gen_guestlinux_dts(cell)

class GuestLinuxDtbGenerator(GeneratorBase):
    """Linux设备树二进制生成器"""
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        """仅支持Guest Cell且操作系统为Linux"""
        if not isinstance(cell, ResourceGuestCell):
            return False
        if not isinstance(cell.runinfo().os_runinfo(), LinuxRunInfo):
            return False
        return True

    def get_name(self) -> str:
        """返回生成器名称"""
        return "linux设备树二进制"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成保存文件名（.dtb后缀）"""
        if isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.dtb'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成Linux设备树二进制"""
        if not isinstance(cell, ResourceGuestCell):
            return None
        return GuestCellGenerator.gen_guestlinux_dtb(cell)

class ResourceTableSrcGenerator(GeneratorBase):
    """资源表源码生成器"""
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        """仅支持非Linux的Guest Cell"""
        if not isinstance(cell, ResourceGuestCell):
            return False
        if isinstance(cell.runinfo().os_runinfo(), LinuxRunInfo):
            return False
        return True

    def get_name(self) -> str:
        """返回生成器名称"""
        return "资源表源码"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成保存文件名（.rsctable后缀）"""
        if isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.rsctable'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成资源表源码"""
        if not isinstance(cell, ResourceGuestCell):
            return None
        return GuestCellGenerator.gen_resource_table_src(cell)

class ResourceTableBinGenerator(GeneratorBase):
    """资源表二进制生成器"""
    def is_support(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> bool:
        """仅支持非Linux的Guest Cell"""
        if not isinstance(cell, ResourceGuestCell):
            return False
        if isinstance(cell.runinfo().os_runinfo(), LinuxRunInfo):
            return False
        return True

    def get_name(self) -> str:
        """返回生成器名称"""
        return "资源表二进制"

    def get_save_name(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成保存文件名（.rsctable.bin后缀）"""
        if isinstance(cell, ResourceRootCell):
            return f'{cell.name()}.rsctable.bin'
        return ""

    def get_save_data(self, cell: Union[ResourceGuestCell, ResourceRootCell]) -> str:
        """生成资源表二进制数据"""
        if not isinstance(cell, ResourceGuestCell):
            return None
        return GuestCellGenerator.gen_resource_table_bin(cell)

class ExportDialog(QtWidgets.QDialog):
    """配置导出对话框
    
    提供将Jailhouse配置导出为不同格式的功能，支持细胞配置源码/二进制、Linux设备树、资源表等格式
    
    Attributes:
        logger: 日志记录器
        _ui: UI设计器生成的界面元素
        _generators: 支持的生成器列表
        _rootcell_name: 根细胞显示名称
    """

    logger = logging.getLogger("ExportDialog")
    def __init__(self, parent=None):
        """初始化导出对话框"""
        super().__init__(parent)

        self._ui = Ui_ExportWidget()
        self._ui.setupUi(self)
        self._ui.frame_title.hide() # 隐藏标题框架
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)    # 移除帮助按钮
        self._ui.combobox_cell.setView(QtWidgets.QListView())   # 设置下拉列表样式
        self._rootcell_name = "root cell"

        rscmgr = ResourceMgr.get_instance()
        rsc = rscmgr.get_current()

        if rsc is None:
            self.setWindowTitle("当前无可导出资源")
        else:
            self.setWindowTitle(f"导出 {rsc.name()}")

        # 初始化生成器列表
        self._generators: list[GeneratorBase] = [
            CellConfigSrcGenerator(),
            CellConfigBinGenerator(),
            GuestLinuxDtsGenerator(),
            GuestLinuxDtbGenerator(),
            ResourceTableSrcGenerator(),
            ResourceTableBinGenerator(),
        ]

        # 在UI中添加生成器按钮
        clean_layout(self._ui.frame_gens.layout())
        for gen in self._generators:
            btn = QtWidgets.QPushButton(gen.get_name(), parent=self)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setFlat(True)
            btn.clicked.connect(self._on_generator_click)
            self._ui.frame_gens.layout().addWidget(btn)
            gen.set_userdata(btn)   # 将按钮绑定到生成器

        self._update_cell_list(rsc) # 更新细胞列表
        self._ui.combobox_cell.currentIndexChanged.connect(self._on_cell_changed)   # 细胞切换事件
        self._ui.btn_save.clicked.connect(self._on_save)    # 保存按钮事件
        self._ui.btn_close.clicked.connect(self._on_close)  # 关闭按钮事件

    def _current_cell(self):
        """获取当前选择的细胞对象"""
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return
        cellname = self._ui.combobox_cell.currentText()
        if cellname == self._rootcell_name:
            return rsc.jailhouse().rootcell()
        else:
            return rsc.jailhouse().guestcells().find_cell(cellname)

    def _current_generator(self) -> GeneratorBase:
        """获取当前选中的生成器"""
        for gen in self._generators:
            btn: QtWidgets.QPushButton = gen.get_userdata()
            if btn.isVisible() and btn.isChecked():
                return gen
        return None

    def _on_generator_click(self):
        """处理生成器按钮点击事件：显示对应细胞的生成内容"""
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
            self._show_source(txt)  # 显示语法高亮后的源码

    def _on_cell_changed(self):
        """处理细胞选择变化事件：更新生成器可见性"""
        cell = self._current_cell()
        if cell is None:
            return
        for gen in self._generators:
            btn = gen.get_userdata()
            btn.setVisible(gen.is_support(cell))    # 根据支持情况显示按钮

    def _update_cell_list(self, rsc: Resource):
        """更新细胞列表下拉框"""
        if rsc is None:
            return
        self._ui.combobox_cell.clear()
        self._ui.combobox_cell.addItem(self._rootcell_name)
        cell_list: ResourceGuestCellList = rsc.find(ResourceGuestCellList)
        for i in range(cell_list.cell_count()):
            cell: ResourceGuestCell = cell_list.cell_at(i)
            self._ui.combobox_cell.addItem(cell.name())
        self._on_cell_changed() # 触发细胞变化处理

    def _show_source(self, source):
        """显示语法高亮的源码（HTML格式）"""
        formatter = HtmlFormatter(full=True, noclasses=True, style="github-dark", linenos=False, nobackground=True)
        src_html = highlight(source, get_lexer_by_name("C"), formatter)
        self._ui.textbrowser.setHtml(src_html)

    def _on_save(self):
        """处理保存按钮事件：导出配置数据到文件"""
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

         # 打开文件保存对话框
        filename = QtWidgets.QFileDialog.getSaveFileName(self, f"保存 {generator.get_name()}: {cellname}",
                                                         name)[0]
        if len(filename) == 0:
            return
        
         # 写入文件（支持文本和二进制模式）
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
        """处理关闭按钮事件"""
        self.close()