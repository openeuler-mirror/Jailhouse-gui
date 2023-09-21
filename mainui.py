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
    def __init__(self, widget: QtWidgets.QWidget, name, title=None, parent=None):
        super().__init__(parent)
        self.setWidget(widget)
        self.setWindowTitle(name)
        if title is not None:
            self.setTitleBarWidget(title)


class MainUI(QtWidgets.QMainWindow):
    logger = logging.getLogger("MainUI")

    def __init__(self):
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
        x = CreateDialog()
        x.exec_()
        self._resource_tree.expand_all()

    def _on_open(self):
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
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return

        self._save(rsc)

    def _on_saveas(self):
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
        x = ExportDialog()
        x.exec_()

    def _on_generate(self):
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
        # 选择当前激活的Resource
        if isinstance(rsc, Resource):
            if rsc is not ResourceMgr.get_instance().get_current():
                self.logger.info(f"set current resource {rsc.name()}")
                ResourceMgr.get_instance().set_current(rsc)


class HomePageWidget(QtWidgets.QWidget):
    logger = logging.getLogger("homepage")
    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_HomePageWidget()
        self._ui.setupUi(self)

        self._ui.btn_new.clicked.connect(self._on_create)
        self._ui.btn_open.clicked.connect(self._on_open)

    def _on_create(self):
        x = CreateDialog()
        x.exec_()

    def _on_open(self):
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
    logger = logging.getLogger('MainPage')
    signal_close = QtCore.Signal()

    def __init__(self, parent):
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
        if not isinstance(sender, ResourceBase):
            return
        self._ui.label_state.setText("已修改")

    def _save(self, rsc):
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
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            return
        self._save(rsc)

    def _on_export(self):
        x = ExportDialog()
        x.exec_()

    def _on_save_and_exit(self):
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is not None:
            self._save(rsc)
        self.signal_close.emit()

    def _on_menu(self):
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
    def __init__(self, parent=None) -> None:
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
        super().showEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
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
        QtWidgets.QApplication.instance().quit()

    def _on_minimize(self):
        self.window().showMinimized()

    def _on_maximize(self):
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

    def _on_status_btn(self):
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
        if isinstance(sender, ResourceMgr):
            rsc = kwargs['rsc']
            self._ui.stacked_widget.setCurrentWidget(self._main_page)
            self._main_page.set_resource(rsc)

    def _on_main_page_close(self):
        self._ui.stacked_widget.setCurrentWidget(self._home_page)
        self._main_page.set_resource(None)


def load_stylesheet(name: str) -> Optional[str]:
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
        s = io.StringIO()
        traceback.print_exception(etype, value, tb, file=s)

        x = ExceptDialog()
        x.set_text(s.getvalue())
        x.exec_()

    sys.excepthook = on_exception
    app.exec_()
