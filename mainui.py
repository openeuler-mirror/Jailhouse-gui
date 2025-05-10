import sys

# 打包后，不执行build操作
if not (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')):
    from build import build
    build()

import os
import traceback
import logging
import io
import time
import json
from typing import Optional

from PySide2 import QtWidgets, QtCore, QtGui
from assets import qr_resource

from forms.ui_mainui import Ui_MainWindow
from forms.ui_main_window import Ui_MainWindow as Ui_NewMainWindow
from forms.ui_main_page import Ui_MainPageWidget
from forms.ui_home_page import Ui_HomePageWidget

from jh_resource import ResourceSignals, ResourceMgr, ResourceBase
from jh_resource import PlatformMgr, ResourceGuestCell, ResourceGuestCellList, ResourceMgr, Resource
from jh_resource import ResourceCPU, ResourceBoard
from jh_resource import ResourceJailhouse, ResourceRootCell, ResourceComm
from jh_resource import ResourcePCIDevice, ResourcePCIDeviceList

from frameless_window import FramelessWindow
from log_widget import LogWidget
from resource_tree_widget import ResourceTreeWidget
from create_widget import CreateDialog
from hw_platform_widget import HwPlatformWidget
from cpu_widget import CPUWidget
from board_widget import BoardWidget
from vm_config_widget import VMConfigWidget
from export_widget import ExportDialog
from rootcell_widget import RootCellWidget
from ivshmem_widget import IVShMemWidget
from jailhouse_widget import JailhouseWidget
from pci_device_widget import PCIDeviceWidget, PCIDeviceListWidget
from guestcell_widget import GuestCellWidget, GuestCellsWidget
from vm_manage_widget import VMManageWidget

from remote_widget import RemoteWidget
from except_widget import ExceptDialog
from tip_widget import TipWidget
from check_widget import CheckWidget

from version import VERSION, BUILD_TIME


PROP_FILENAME = "filename"


class DockWidget(QtWidgets.QDockWidget):
    """
    自定义可停靠窗口部件。
    
    用于创建带有指定标题和内容部件的可停靠窗口。
    
    Attributes:
        widget: 要显示的内容部件。
    """
    def __init__(self, widget: QtWidgets.QWidget, name, title=None, parent=None):
        """
        初始化停靠窗口部件。
        
        Args:
            widget: 要在停靠窗口中显示的部件。
            name: 停靠窗口的名称。
            title: 自定义标题栏部件，默认为None使用标准标题栏。
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self.setWidget(widget)
        self.setWindowTitle(name)
        if title is not None:
            self.setTitleBarWidget(title)


class MainUI(QtWidgets.QMainWindow):
    """
    主界面类(旧版)。
    
    实现Jailhouse资源配置工具的主界面，包含资源树、配置编辑区和日志显示等功能。
    
    Attributes:
        _ui: 用户界面对象。
        _log_widget: 日志显示部件。
        _resource_tree: 资源树部件。
        _remote_widget: 远程管理部件。
        _tip_widget: 提示信息部件。
        logger: 日志记录器。
    """
    logger = logging.getLogger("MainUI")

    def __init__(self):
        """
        初始化主界面。
        
        设置界面布局，创建和添加各个子部件，连接信号和槽。
        """
        super().__init__()

        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)

        self.setWindowTitle(f"Jailhouse资源配置工具  {VERSION}")
        self._ui.tabWidget.removeTab(1)
        self._ui.tabWidget.removeTab(1)

        self._log_widget = LogWidget()
        self._resource_tree = ResourceTreeWidget()
        self._remote_widget = RemoteWidget()
        self._tip_widget = TipWidget()
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, DockWidget(self._tip_widget, "提示"))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, DockWidget(self._resource_tree, "资源树"))
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, DockWidget(self._remote_widget, "远程管理"))

        self._black_widget = QtWidgets.QWidget()
        self._cpu_widget = CPUWidget()
        self._board_widget = BoardWidget()
        self._rootcell_widget = RootCellWidget()
        self._comm_widget = IVShMemWidget()
        self._jh_widget = JailhouseWidget()
        self._pci_device_widget = PCIDeviceWidget()
        self._pci_devices_widget = PCIDeviceListWidget()
        self._guestcell_widget = GuestCellWidget()
        self._guestcells_widget = GuestCellsWidget()

        self._ui.stackedwidget_resource.addWidget(self._black_widget)
        self._ui.stackedwidget_resource.addWidget(self._cpu_widget)
        self._ui.stackedwidget_resource.addWidget(self._board_widget)
        self._ui.stackedwidget_resource.addWidget(self._rootcell_widget)
        self._ui.stackedwidget_resource.addWidget(self._comm_widget)
        self._ui.stackedwidget_resource.addWidget(self._jh_widget)
        self._ui.stackedwidget_resource.addWidget(self._pci_device_widget)
        self._ui.stackedwidget_resource.addWidget(self._pci_devices_widget)
        self._ui.stackedwidget_resource.addWidget(self._guestcell_widget)
        self._ui.stackedwidget_resource.addWidget(self._guestcells_widget)

        self._ui.action_new.triggered.connect(self._on_create)
        self._ui.action_open.triggered.connect(self._on_open)
        self._ui.action_save.triggered.connect(self._on_save)
        self._ui.action_saveas.triggered.connect(self._on_saveas)
        self._ui.action_export.triggered.connect(self._on_export)

        self._resource_tree.item_clicked.connect(self._on_item_clicked)
        self._resource_tree.item_double_clicked.connect(self._on_item_double_clicked)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        处理窗口关闭事件。
        
        在关闭窗口前检查是否有未保存的修改，提示用户保存。
        
        Args:
            event: 关闭事件对象。
        """
        rsc_mgr = ResourceMgr.get_instance()
        modified = list()
        for i in range(len(rsc_mgr)):
            rsc = rsc_mgr[i]
            if rsc.is_modified(True):
                modified.append(rsc)
        if len(modified) == 0:
            return super().closeEvent(event)

        names = ', '.join(map(lambda x: x.name(), modified))
        text = f"修改但未保存 {names}, 是否保存文件"
        btns = QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        result = QtWidgets.QMessageBox.question(self, "关闭程序", text, btns)
        if result == QtWidgets.QMessageBox.Cancel:
            event.ignore()
            return
        if result == QtWidgets.QMessageBox.Yes:
            for rsc in modified:
                self._save(rsc)
        return super().closeEvent(event)


    def _on_create(self):
        """
        处理创建新资源事件。
        
        打开创建对话框，用于创建新的资源。
        """
        x = CreateDialog()
        x.exec_()
        self._resource_tree.expand_all()

    def _on_open(self):
        """
        处理打开资源文件事件。
        
        显示文件选择对话框，打开并加载选中的资源文件。
        """
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "打开文件", "", "Jailhouse resource(*.jhr)")[0]
        if len(filename) == 0:
            return

        rsc = ResourceMgr.get_instance().open(filename)
        if rsc is None:
            self.logger.error(f"open {filename} failed")
            return
        rsc.set_prop(PROP_FILENAME, filename)
        ResourceMgr.get_instance().set_current(rsc)
        self._resource_tree.expand_all()

    def _save(self, rsc):
        """
        保存资源到文件。
        
        如果资源没有关联文件名，则显示文件保存对话框。
        
        Args:
            rsc: 要保存的资源对象。
        """
        filename = rsc.get_prop(PROP_FILENAME)
        if filename is None:
            fn = os.path.join(os.getcwd(), "untitled.jhr")
            filename = QtWidgets.QFileDialog.getSaveFileName(self, f"保存文件 {rsc.name()}", fn, "Jailhouse resource(*.jhr)")[0]
            if len(filename) == 0:
                return

        if ResourceMgr.save(rsc, filename):
            self.logger.info(f"save resource to {filename}")
        else:
            self.logger.error("save failed.")

        rsc.set_prop(PROP_FILENAME, filename)

    def _on_save(self):
        """
        处理保存当前资源事件。
        
        保存当前选中的资源到文件。
        """
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return

        self._save(rsc)

    def _on_saveas(self):
        """
        处理另存为事件。
        
        将当前资源保存到新文件。
        """
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return

        fn = os.path.join(os.getcwd(), f"saveas_{int(time.time())}.jhr")
        filename = QtWidgets.QFileDialog.getSaveFileName(self, "保存文件", fn, "Jailhouse resource(*.jhr)")[0]
        if len(filename) == 0:
            return

        if ResourceMgr.save(rsc, filename):
            self.logger.info(f"save resource to {filename}")
        else:
            self.logger.error("save failed.")

    def _on_export(self):
        """
        处理导出事件。
        
        显示导出对话框，将资源导出为其他格式。
        """
        x = ExportDialog()
        x.exec_()

    def _on_generate(self):
        """
        处理生成源码事件。
        
        生成当前资源的root cell配置源码并显示。
        """
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            self.logger.info("当前无可用资源")
            return
        src_rootcell = generate_root_cell(rsc)
        if src_rootcell is None:
            self.logger.error("生成root cell配置源码失败")
            return

        formatter = HtmlFormatter(full=True, noclasses=True, style="igor", linenos=True)
        src_html = highlight(src_rootcell, get_lexer_by_name("C"), formatter)
        self._ui.textbrowser_source.setHtml(src_html)

    def _on_item_clicked(self, rsc):
        """
        处理资源项点击事件。
        
        根据点击的资源类型，显示相应的配置界面。
        
        Args:
            rsc: 被点击的资源对象。
        """
        if isinstance(rsc, ResourceCPU):
            self._cpu_widget.set_cpu(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._cpu_widget)
        elif isinstance(rsc, ResourceBoard):
            self._board_widget.set_board(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._board_widget)
        elif isinstance(rsc, ResourceRootCell):
            self._rootcell_widget.set_rootcell(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._rootcell_widget)
        elif isinstance(rsc, ResourceComm):
            self._comm_widget.set_comm(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._comm_widget)
        elif isinstance(rsc, ResourceJailhouse):
            self._jh_widget.set_jailhosue(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._jh_widget)
        elif isinstance(rsc, ResourcePCIDeviceList):
            self._pci_devices_widget.set_resource(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._pci_devices_widget)
        elif isinstance(rsc, ResourcePCIDevice):
            self._pci_device_widget.set_resource(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._pci_device_widget)
        elif isinstance(rsc, ResourceGuestCell):
            self._guestcell_widget.set_resource(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._guestcell_widget)
        elif isinstance(rsc, ResourceGuestCellList):
            self._guestcells_widget.set_guestcells(rsc)
            self._ui.stackedwidget_resource.setCurrentWidget(self._guestcells_widget)
        else:
            self._ui.stackedwidget_resource.setCurrentWidget(self._black_widget)

    def _on_item_double_clicked(self, rsc):
        """
        处理资源项双击事件。
        
        设置双击的资源为当前激活资源。
        
        Args:
            rsc: 被双击的资源对象。
        """
        # 选择当前激活的Resource
        if isinstance(rsc, Resource):
            if rsc is not ResourceMgr.get_instance().get_current():
                self.logger.info(f"set current resource {rsc.name()}")
                ResourceMgr.get_instance().set_current(rsc)


class HomePageWidget(QtWidgets.QWidget):
    """
    首页部件。
    
    显示欢迎界面，提供创建新资源和打开现有资源的功能。
    
    Attributes:
        _ui: 用户界面对象。
        logger: 日志记录器。
    """
    logger = logging.getLogger("homepage")
    def __init__(self, parent):
        """
        初始化首页部件。
        
        Args:
            parent: 父窗口部件。
        """
        super().__init__(parent)
        self._ui = Ui_HomePageWidget()
        self._ui.setupUi(self)

        self._ui.btn_new.clicked.connect(self._on_create)
        self._ui.btn_open.clicked.connect(self._on_open)

    def _on_create(self):
        """
        处理创建新资源事件。
        
        打开创建对话框，用于创建新的资源。
        """
        x = CreateDialog()
        x.exec_()

    def _on_open(self):
        """
        处理打开资源文件事件。
        
        显示文件选择对话框，打开并加载选中的资源文件。
        """
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "打开文件", "", "Jailhouse resource(*.jhr)")[0]
        if len(filename) == 0:
            return

        rsc = ResourceMgr.get_instance().open(filename)
        if rsc is None:
            self.logger.error(f"open {filename} failed")
            return
        rsc.set_prop(PROP_FILENAME, filename)
        ResourceMgr.get_instance().set_current(rsc)


class MainPageWidget(QtWidgets.QWidget):
    """
    主页面部件。
    
    显示资源编辑界面，包含硬件平台、虚拟机配置和虚拟机管理等功能页面。
    
    Attributes:
        _ui: 用户界面对象。
        _blank_page: 空白页面。
        _hw_plt_page: 硬件平台配置页面。
        _vm_config_page: 虚拟机配置页面。
        _vm_manage_page: 虚拟机管理页面。
        signal_close: 关闭信号。
        logger: 日志记录器。
    """
    logger = logging.getLogger('MainPage')
    signal_close = QtCore.Signal()

    def __init__(self, parent):
        """
        初始化主页面部件。
        
        Args:
            parent: 父窗口部件。
        """
        super().__init__(parent)
        self._ui = Ui_MainPageWidget()
        self._ui.setupUi(self)

        self._blank_page = QtWidgets.QWidget(self._ui.stacked_widget)
        self._hw_plt_page = HwPlatformWidget(self._ui.stacked_widget)
        self._vm_config_page = VMConfigWidget(self._ui.stacked_widget)
        self._vm_manage_page = VMManageWidget(self._ui.stacked_widget)

        self._ui.stacked_widget.addWidget(self._blank_page)
        self._ui.stacked_widget.addWidget(self._hw_plt_page)
        self._ui.stacked_widget.addWidget(self._vm_config_page)
        self._ui.stacked_widget.addWidget(self._vm_manage_page)
        self._ui.stacked_widget.setCurrentWidget(self._blank_page)

        self._ui.btn_save.clicked.connect(self._on_save)
        self._ui.btn_export.clicked.connect(self._on_export)
        self._ui.btn_save_and_exit.clicked.connect(self._on_save_and_exit)
        self._ui.btn_hw_platform.clicked.connect(self._on_menu)
        self._ui.btn_vm_config.clicked.connect(self._on_menu)
        self._ui.btn_vm_manage.clicked.connect(self._on_menu)

        ResourceSignals.modified.connect(self._on_rsc_modified)

    def set_resource(self, rsc: Resource):
        """
        设置要显示的资源。
        
        Args:
            rsc: 资源对象，如果为None则清空显示。
        """
        self._ui.label_name.clear()
        self._ui.label_state.clear()
        self._hw_plt_page.set_platform(None)
        self._vm_config_page.set_vm_config(None)
        self._vm_manage_page.set_resource(None)

        if rsc is None:
            return
        self._ui.label_name.setText(rsc.name())
        self._hw_plt_page.set_platform(rsc.platform())
        self._vm_config_page.set_vm_config(rsc.jailhouse())
        self._vm_manage_page.set_resource(rsc)
        if rsc.is_modified():
            self._ui.label_state.setText("已修改")

    def _on_rsc_modified(self, sender, **kwargs):
        """
        处理资源修改事件。
        
        当资源被修改时，更新界面显示状态。
        
        Args:
            sender: 信号发送者。
            **kwargs: 关键字参数。
        """
        if not isinstance(sender, ResourceBase):
            return
        self._ui.label_state.setText("已修改")

    def _save(self, rsc):
        """
        保存资源到文件。
        
        如果资源没有关联文件名，则显示文件保存对话框。
        
        Args:
            rsc: 要保存的资源对象。
        """
        filename = rsc.get_prop(PROP_FILENAME)
        if filename is None:
            fn = os.path.join(os.getcwd(), "untitled.jhr")
            filename = QtWidgets.QFileDialog.getSaveFileName(self, f"保存文件 {rsc.name()}", fn, "Jailhouse resource(*.jhr)")[0]
            if len(filename) == 0:
                return

        if ResourceMgr.save(rsc, filename):
            self.logger.info(f"save resource to {filename}")
        else:
            self.logger.error("save failed.")

        rsc.set_prop(PROP_FILENAME, filename)
        self._ui.label_state.clear()

    def _on_save(self):
        """
        处理保存按钮点击事件。
        
        保存当前资源到文件。
        """
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return
        self._save(rsc)

    def _on_export(self):
        """
        处理导出按钮点击事件。
        
        显示导出对话框，将资源导出为其他格式。
        """
        x = ExportDialog()
        x.exec_()

    def _on_save_and_exit(self):
        """
        处理保存并退出按钮点击事件。
        
        保存当前资源并发出关闭信号。
        """
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is not None:
            self._save(rsc)
        self.signal_close.emit()

    def _on_menu(self):
        """
        处理菜单按钮点击事件。
        
        根据点击的菜单按钮，切换显示相应的功能页面。
        """
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return

        if self._ui.btn_hw_platform.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._hw_plt_page)
        if self._ui.btn_vm_config.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._vm_config_page)
        if self._ui.btn_vm_manage.isChecked():
            self._ui.stacked_widget.setCurrentWidget(self._vm_manage_page)


class MainWindow(QtWidgets.QWidget):
    """
    主窗口类(新版)。
    
    实现Jailhouse资源配置工具的无边框主窗口，提供资源创建、编辑和管理功能。
    
    Attributes:
        _ui: 用户界面对象。
        _home_page: 首页部件。
        _main_page: 主页面部件。
        _log_widget: 日志显示部件。
        _tip_widget: 提示信息部件。
        _check_widget: 检查信息部件。
        _tools_spliter: 工具区域分割器。
    """
    def __init__(self, parent=None) -> None:
        """
        初始化主窗口。
        
        Args:
            parent: 父窗口部件，默认为None。
        """
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)

        self._ui = Ui_NewMainWindow()
        self._ui.setupUi(self)
        self._ui.label_version.setText(VERSION)

        self._home_page = HomePageWidget(self)
        self._main_page = MainPageWidget(self)
        self._ui.stacked_widget.addWidget(self._home_page)
        self._ui.stacked_widget.addWidget(self._main_page)
        self._ui.stacked_widget.setCurrentWidget(self._home_page)

        self._ui.frame_tools.hide()
        self._log_widget = LogWidget()
        self._tip_widget = TipWidget()
        self._check_widget = CheckWidget()
        self._tools_spliter = QtWidgets.QSplitter()
        self._ui.frame_tools.layout().addWidget(self._tools_spliter)
        self._tools_spliter.addWidget(self._log_widget)
        self._tools_spliter.addWidget(self._tip_widget)
        self._tools_spliter.addWidget(self._check_widget)

        self._tools_spliter.setOpaqueResize(True)
        self._tools_spliter.setMidLineWidth(0)
        self._tools_spliter.setLineWidth(0)
        self._tools_spliter.setHandleWidth(7)

        self._ui.btn_close.clicked.connect(self._on_close)
        self._ui.btn_minimize.clicked.connect(self._on_minimize)
        self._ui.btn_maximize.clicked.connect(self._on_maximize)
        self._ui.btn_log.clicked.connect(self._on_status_btn)
        self._ui.btn_tip.clicked.connect(self._on_status_btn)
        self._ui.btn_check.clicked.connect(self._on_status_btn)

        self._main_page.signal_close.connect(self._on_main_page_close)
        ResourceSignals.add.connect(self._on_rsc_add)

        self._ui.btn_log.setChecked(True)
        self._ui.btn_tip.setChecked(True)
        self._on_status_btn()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """
        处理窗口显示事件。
        
        Args:
            event: 显示事件对象。
        """
        super().showEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        处理窗口关闭事件。
        
        在关闭窗口前检查是否有未保存的修改，提示用户保存。
        
        Args:
            event: 关闭事件对象。
        """
        rsc_mgr = ResourceMgr.get_instance()
        modified = list()
        for i in range(len(rsc_mgr)):
            rsc = rsc_mgr[i]
            if rsc.is_modified(True):
                modified.append(rsc)
        if len(modified) == 0:
            return super().closeEvent(event)

        names = ', '.join(map(lambda x: x.name(), modified))
        text = f"修改但未保存 {names}, 是否保存文件"
        btns = QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        result = QtWidgets.QMessageBox.question(self, "关闭程序", text, btns)
        if result == QtWidgets.QMessageBox.Cancel:
            event.ignore()
            return
        if result == QtWidgets.QMessageBox.Yes:
            for rsc in modified:
                self._save(rsc)
        return super().closeEvent(event)

    def _on_close(self):
        """
        处理关闭按钮点击事件。
        
        退出应用程序。
        """
        QtWidgets.QApplication.instance().quit()

    def _on_minimize(self):
        """
        处理最小化按钮点击事件。
        
        最小化窗口。
        """
        self.window().showMinimized()

    def _on_maximize(self):
        """
        处理最大化/还原按钮点击事件。
        
        在最大化和正常大小之间切换窗口状态。
        """
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

    def _on_status_btn(self):
        """
        处理状态按钮点击事件。
        
        根据按钮状态，显示或隐藏相应的工具部件。
        """
        show_log = self._ui.btn_log.isChecked()
        show_tip = self._ui.btn_tip.isChecked()
        show_check = self._ui.btn_check.isChecked()

        self._log_widget.setVisible(show_log)
        self._tip_widget.setVisible(show_tip)
        self._check_widget.setVisible(show_check)
        if show_log or show_tip or show_check:
            self._ui.frame_tools.show()
        else:
            self._ui.frame_tools.hide()

    def _on_rsc_add(self, sender, **kwargs):
        """
        处理资源添加事件。
        
        当新资源被添加时，切换到主页面并显示该资源。
        
        Args:
            sender: 信号发送者。
            **kwargs: 关键字参数，包含添加的资源。
        """
        if isinstance(sender, ResourceMgr):
            rsc = kwargs['rsc']
            self._ui.stacked_widget.setCurrentWidget(self._main_page)
            self._main_page.set_resource(rsc)

    def _on_main_page_close(self):
        """
        处理主页面关闭事件。
        
        切换回首页并清空资源显示。
        """
        self._ui.stacked_widget.setCurrentWidget(self._home_page)
        self._main_page.set_resource(None)


def load_stylesheet(name: str) -> Optional[str]:
    """
    加载样式表。
    
    从QSS文件或JSON配置文件加载样式表。
    
    Args:
        name: 样式表文件名，可以是QSS文件或JSON配置文件。
        
    Returns:
        加载的样式表文本，如果加载失败则返回None。
    """
    qss_list = list()
    if name.endswith('.qss'):
        qss_list.append(name)
    elif name.endswith('.json'):
        qss_json = QtCore.QFile(name)
        if not qss_json.open(QtCore.QFile.ReadOnly|QtCore.QFile.Text):
            return None
        json_txt = str(qss_json.readAll(), 'utf-8')
        try:
            qss_obj = json.loads(json_txt)
            qss_list.extend(qss_obj['qss_files'])
        except:
            qss_json.close()
            return None
        qss_json.close()

    qss_txt = io.StringIO()
    for fn in qss_list:
        if not fn.endswith('.qss'):
            continue
        qss_file = QtCore.QFile(fn)
        if qss_file.open(QtCore.QFile.ReadOnly|QtCore.QFile.Text):
            qss_txt.write(str(qss_file.readAll(), 'utf-8'))
            qss_txt.write("\n")
            qss_file.close()

    return qss_txt.getvalue()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)


    app = QtWidgets.QApplication(sys.argv)

    qss_txt = load_stylesheet(":/style/new_style.json")
    if qss_txt:
        app.setStyleSheet(qss_txt)
    else:
        logging.error("load qss failed.")

    #mainui = MainUI()
    #mainui.show()

    mainui = MainWindow()
    window = FramelessWindow(mainui)
    window.show()

    size = QtWidgets.QApplication.primaryScreen().geometry().size()
    scale = 0.75
    w = int(size.width() * scale)
    h = int(size.height() * scale)
    window.setGeometry((size.width()-w)//2, (size.height()-h)//2, w, h)

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        logging.info(f'running in a PyInstaller bundle {getattr(sys,"_MEIPASS")}')
        meipass = getattr(sys, '_MEIPASS')
        PlatformMgr.get_instance().load(os.path.join(meipass, "platform"))
    else:
        logging.info('running in a normal Python process')
        PlatformMgr.get_instance().load("platform")


    def on_exception(etype, value, tb):
        """
        全局异常处理函数。
        
        捕获未处理的异常并显示异常对话框。
        
        Args:
            etype: 异常类型。
            value: 异常值。
            tb: 异常追踪信息。
        """
        s = io.StringIO()
        traceback.print_exception(etype, value, tb, file=s)

        x = ExceptDialog()
        x.set_text(s.getvalue())
        x.exec_()

    sys.excepthook = on_exception
    app.exec_()
