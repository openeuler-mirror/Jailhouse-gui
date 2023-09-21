import logging
from typing import Optional
import time
import json
import math

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCharts import QtCharts
from forms.ui_vm_manager import Ui_VMManageWidget
from forms.ui_vm_state_item import Ui_VMStateItemWidget
from forms.ui_meminfo import Ui_MemInfoWidget
from forms.ui_cpuload import Ui_CPULoadWidget

from rpc_server.rpc_client import RPCClient
from generator import RootCellGenerator
from jh_resource import Resource, ResourceGuestCellList, ResourceGuestCell, ResourceCPU
from jh_resource import LinuxRunInfo, ACoreRunInfo, CommonOSRunInfo
from utils import Profile

from commonos_runinfo import OSRunInfoWidget, CommonOSRunInfoWidget
from linux_runinfo import LinuxRunInfoWidget
from acore_runinfo import ACoreRunInfoWidget


class CellStateItemWidget(QtWidgets.QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)

        self.setFixedHeight(40)
        self._ui = Ui_VMStateItemWidget()
        self._ui.setupUi(self)
        self._ui.label_name.setText(name)
        self._ui.label_state.setText('未知状态')

    def name(self):
        return self._ui.label_name.text()

    def set_status(self, status: str):
        self._ui.label_state.setText(status)


class CPULoadWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_CPULoadWidget()
        self._ui.setupUi(self)

        self._layout = self._ui.frame_chart.layout()
        if self._layout is None:
            self._layout = QtWidgets.QHBoxLayout(self._ui.frame_chart)

        self._axis_time = QtCharts.QDateTimeAxis()
        self._axis_time.setFormat("mm:ss")
        self._axis_time.setTitleText("Time")
        self._axis_time.setRange(QtCore.QDateTime.currentDateTime(), QtCore.QDateTime().currentDateTime().addSecs(10))
        self._axis_load = QtCharts.QValueAxis()
        self._axis_load.setTitleText("Load")
        self._axis_load.setRange(0, 1)

        self._chart = QtCharts.QChart()
        self._chart.addAxis(self._axis_time, QtCore.Qt.AlignBottom)
        self._chart.addAxis(self._axis_load, QtCore.Qt.AlignLeft)
        self._chart.setTitle("CPU负载")
        # self._chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        self._series = QtCharts.QSplineSeries()
        self._chart.addSeries(self._series)
        self._series.setPointsVisible(True)
        a = self._series.attachAxis(self._axis_time)
        b = self._series.attachAxis(self._axis_load)

        self._chartview = QtCharts.QChartView(self._chart)
        self._chartview.setRenderHint(QtGui.QPainter.Antialiasing)
        self._layout.addWidget(self._chartview)

        self.setMinimumHeight(400)
        self._chart.setTheme(QtCharts.QChart.ChartTheme.ChartThemeBlueCerulean)

    def add_data(self, now_sec, load):
        now = QtCore.QDateTime.fromMSecsSinceEpoch(int(now_sec*1000))
        self._ui.label_load.setText(f"{load*100:.1f} %")
        self._series.append(now_sec*1000, load)
        if self._series.count() > 200:
            print(self._series.count())
            self._series.removePoints(0, self._series.count()-40)
        self._axis_time.setRange(now.addSecs(-30), now)
        self._chartview.update()

    def set_cpucount(self, count):
        self._ui.label_count.setText(f"{count}")

    def reset(self):
        self._series.clear()


class MemInfoWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._ui = Ui_MemInfoWidget()
        self._ui.setupUi(self)

        self._layout = self._ui.frame_chart.layout()
        if self._layout is None:
            self._layout = QtWidgets.QHBoxLayout(self._ui.frame_chart)

        self._axis_time = QtCharts.QDateTimeAxis()
        self._axis_time.setFormat("mm:ss")
        self._axis_time.setTitleText("Time")
        self._axis_load = QtCharts.QValueAxis()
        self._axis_load.setTitleText("Memory")
        self._axis_load.setRange(0, 1)

        self._chart = QtCharts.QChart()
        self._chart.addAxis(self._axis_time, QtCore.Qt.AlignBottom)
        self._chart.addAxis(self._axis_load, QtCore.Qt.AlignLeft)
        self._chart.setTitle("内存负载")
        # self._chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        self._series = QtCharts.QSplineSeries()
        self._chart.addSeries(self._series)
        self._series.setPointsVisible(True)
        a = self._series.attachAxis(self._axis_time)
        b = self._series.attachAxis(self._axis_load)

        self._chartview = QtCharts.QChartView(self._chart)
        self._chartview.setRenderHint(QtGui.QPainter.Antialiasing)
        self._layout.addWidget(self._chartview)

        self.setMinimumHeight(400)
        self._chart.setTheme(QtCharts.QChart.ChartTheme.ChartThemeBlueCerulean)

    def add_data(self, now_sec, total, free):
        def size_to_str(size):
            if size < 1024*1024:
                return f'{size/1024:.03f} KB'
            if size < 1024*1024*1024:
                return f'{size/1024/1024:.02f} MB'
            return f'{size/1024/1024/1024:.02f} GB'

        self._ui.label_total.setText(size_to_str(total))
        self._ui.label_free.setText(size_to_str(free))
        self._ui.label_load.setText(f'{(total-free)/total*100:.0f}%')

        now = QtCore.QDateTime.fromMSecsSinceEpoch(int(now_sec*1000))
        self._series.append(now_sec*1000, (total-free)/total)
        if self._series.count() > 200:
            print(self._series.count())
            self._series.removePoints(0, self._series.count()-40)
        self._axis_time.setRange(now.addSecs(-30), now)
        self._chartview.update()


class VMManageWidget(QtWidgets.QWidget):
    logger = logging.getLogger("VMManage")

    profile_addr = Profile.Item('remote_addr', 'tcp://127.0.0.1:4240')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_VMManageWidget()
        self._ui.setupUi(self)
        self._ui.combobox_os_type.setView(QtWidgets.QListView())
        self._ui.frame_sd_img_content.hide()
        self._ui.frame_sd_img_title.hide()

        self._root_cpuload = CPULoadWidget()
        self._root_meminfo = MemInfoWidget()
        self._root_layout = QtWidgets.QVBoxLayout(self._ui.frame_rootcell_content)
        self._root_layout.addWidget(self._root_cpuload)
        self._root_layout.addWidget(self._root_meminfo)
        self._ui.frame_runcell.hide()

        self._timer = QtCore.QTimer()
        self._timer.setInterval(1000)
        self._timer.setSingleShot(False)

        self._ui.lineedit_addr.setText(self.profile_addr.get())
        self._commonos_runinfo = CommonOSRunInfoWidget(self)
        self._linux_runinfo = LinuxRunInfoWidget(self)
        self._acore_runinfo = ACoreRunInfoWidget(self)

        self._os_runinfo_desc = [
            {
                'name'   : 'CommonOS',
                'display': '通用系统',
                'class'  : CommonOSRunInfo,
                'widget' : self._commonos_runinfo,
            },
            {
                'name'   : 'Linux',
                'display': 'Linux',
                'class'  : LinuxRunInfo,
                'widget' : self._linux_runinfo,
            },
            {
                'name'   : 'Acore',
                'display': '天脉(单分区)',
                'class'  : ACoreRunInfo,
                'widget' : self._acore_runinfo,
            },
        ]

        for item in self._os_runinfo_desc:
            self._ui.stackedwidget_os_runinfo.addWidget(item['widget'])
            self._ui.combobox_os_type.addItem(item['display'])
            item['widget'].value_changed.connect(self._on_runinfo_value_changed)

        self._ui.stackedwidget_os_runinfo.setFixedHeight(0)

        self._resource: Optional[Resource] = None
        self._current_cell: Optional[ResourceGuestCell] = None
        self._client: RPCClient = RPCClient.get_instance()
        self._last_status = None

        self._client.state_changed.connect(self._on_state_changed)
        self._ui.lineedit_addr.editingFinished.connect(self._on_addr_edit_finished)
        self._ui.btn_connect.clicked.connect(self._on_connect)
        self._ui.combobox_os_type.currentIndexChanged.connect(self._on_os_type_changed)
        self._ui.listwidget_cells.currentRowChanged.connect(self._on_current_cell_changed)
        self._ui.btn_cell_run.clicked.connect(self._on_cell_run)
        self._ui.btn_cell_stop.clicked.connect(self._on_cell_stop)
        self._ui.btn_hyp_start.clicked.connect(self._on_hyp_start)
        self._ui.btn_hyp_stop.clicked.connect(self._on_hyp_stop)
        self._ui.btn_cell_flush.clicked.connect(self._on_cell_flush)

        self._timer.timeout.connect(self._on_timeout)

    def set_resource(self, rsc: Resource):
        if self._resource is rsc:
            return
        self._resource = None
        self._current_cell = None

        self._ui.listwidget_cells.setCurrentRow(-1)
        self._update_vm_list(rsc)
        self._resource = rsc

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._ui.stackedwidget_os_runinfo.setFixedHeight(self._ui.stackedwidget_os_runinfo.currentWidget().sizeHint().height())

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        return super().showEvent(event)

    def hideEvent(self, event: QtGui.QHideEvent) -> None:
        return super().hideEvent(event)

    def _on_hyp_start(self):
        if self._resource is None:
            return

        # 生成源码
        root_cell_bin = RootCellGenerator.gen_config_bin(self._resource)
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
                self.logger.info(f"jailhouse disable")
                result = self._client.jailhouse_disable()
                if not result.status:
                    self.logger.error("disable failed")
                    return
                break

        # 开始创建root cell
        self.logger.info(f"jailhouse enable")
        result = self._client.jailhouse_enable(root_cell_bin)
        if not result.status:
            self.logger.error("jailhouse_enable failed")
            self.logger.error(f"{result.message}")
            return
        self.logger.info("jailhouse root cell enable success")

        jhr_obj = self._resource.to_dict()
        jhr_json = None
        if jhr_obj is not None:
            jhr_json = json.dumps(jhr_obj)
        if jhr_json is not None:
            result = self._client.start_uart_server(jhr_json)
            if not result:
                self.logger.warning(f"start uart server failed, {result.message}")
            else:
                self.logger.info("start uart server succes.")
        else:
            self.logger.warning(f"generate jhr json failed.")

    def _on_cell_flush(self):
        if self._resource is None:
            return
        self._update_vm_list(self._resource)

    def _on_hyp_stop(self):
        if self._resource is None:
            return

        result = self._client.list_cell()
        if not result.status or result is None:
            self.logger.error("get root cell list failed")
            return
        result = self._client.jailhouse_disable()
        if not result.status:
            self.logger.error("get root cell list failed")
            return
        self.logger.info("root cell disable success")

        result = self._client.stop_uart_server()
        if not result:
            self.logger.warning("stop uart server failed.")

    def _on_timeout(self):
        if self._resource is None:
            return
        if not self._client.is_connected():
            return

        result = self._client.get_status()
        if not result:
            return
        status = result.result
        rootcell: dict = status.get('rootcell')
        guestcells = status.get('guestcells')
        timestamp = status.get('timestamp', time.time())

        if guestcells:
            for i in range(self._ui.listwidget_cells.count()):
                item = self._ui.listwidget_cells.item(i)
                item_widget: CellStateItemWidget = self._ui.listwidget_cells.itemWidget(item)
                cell = guestcells.get(item_widget.name())
                if cell is not None:
                    item_widget.set_status(cell['status'])
                else:
                    item_widget.set_status("未创建")

        if rootcell:
            meminfo = rootcell.get('meminfo')
            cputimes = rootcell.get('cputimes')
            if meminfo is None:
                return
            if cputimes is None:
                return

            self._root_cpuload.set_cpucount(rootcell.get('cpucount', "?"))

            if self._last_status is not None:
                last_cputimes = self._last_status['rootcell']['cputimes']
                _user = last_cputimes['user'] - cputimes['user']
                _sys = last_cputimes['system'] - cputimes['system']
                _idle = last_cputimes['idle'] - cputimes['idle']
                cpuload = (_user+_sys)/(_user+_sys+_idle)
                self._root_cpuload.add_data(timestamp, cpuload)

            self._root_meminfo.add_data(timestamp, meminfo['total'], meminfo['available'])

        self._last_status = status

    def _on_cell_run(self):
        if self._current_cell is None:
            return
        self._ui.btn_cell_run.setEnabled(False)
        os_runinfo = self._current_cell.runinfo().os_runinfo()
        if isinstance(os_runinfo, ACoreRunInfo):
            self._acore_runinfo.run(self._current_cell)
        elif isinstance(os_runinfo, LinuxRunInfo):
            self._linux_runinfo.run(self._current_cell)
        elif isinstance(os_runinfo, CommonOSRunInfo):
            self._commonos_runinfo.run(self._current_cell)
        else:
            self.logger.error(f'Unknown OS runinfo {type(os_runinfo)}')
        self._ui.btn_cell_run.setEnabled(True)

    def _on_cell_stop(self):
        if self._current_cell is None:
            return

        name = self._current_cell.name()
        self.logger.info("destroy cell {name}")
        self._client.destroy_cell(name)

    def _update_vm_list(self, rsc: Resource):
        if rsc is None:
            self._ui.listwidget_cells.clear()
            return

        self._ui.listwidget_cells.clear()
        guestcells: ResourceGuestCellList = rsc.find(ResourceGuestCellList)
        for i in range(guestcells.cell_count()):
            cell = guestcells.cell_at(i)
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, cell.name())
            item_widget = CellStateItemWidget(cell.name())
            item.setSizeHint(item_widget.minimumSize())
            self._ui.listwidget_cells.addItem(item)
            self._ui.listwidget_cells.setItemWidget(item, item_widget)

        fixed_height = self._ui.listwidget_cells.sizeHintForRow(0) * self._ui.listwidget_cells.count()
        self._ui.listwidget_cells.setFixedHeight(fixed_height)

    def _update_current_cell(self, cell: ResourceGuestCell):
        self._current_cell = None
        if cell is None:
            self._ui.frame_runcell.hide()
            return

        runinfo = cell.runinfo()
        os_runinfo = runinfo.os_runinfo()
        self._ui.frame_runcell.show()

        self._ui.combobox_os_type.setCurrentIndex(-1)
        for idx, item in enumerate(self._os_runinfo_desc):
            if isinstance(os_runinfo, item['class']):
                item['widget'].set_runinfo(os_runinfo)
                self._ui.combobox_os_type.setCurrentIndex(idx)

        self._ui.label_cellname.setText(cell.name())
        self._current_cell = cell

    def _on_runinfo_value_changed(self):
        if self._current_cell is None:
            return
        widget: OSRunInfoWidget = self._ui.stackedwidget_os_runinfo.currentWidget()
        self._current_cell.runinfo().set_os_runinfo(widget.runinfo())
        self._ui.stackedwidget_os_runinfo.setFixedHeight(self._ui.stackedwidget_os_runinfo.currentWidget().sizeHint().height())

    def _on_current_cell_changed(self, arg):
        item = self._ui.listwidget_cells.currentItem()
        if item is None:
            self._update_current_cell(None)
            return
        name = item.data(QtCore.Qt.UserRole)
        guestcells: ResourceGuestCellList = self._resource.find(ResourceGuestCellList)
        cell = guestcells.find_cell(name)
        if cell is None:
            self._update_current_cell(None)
            return
        self._update_current_cell(cell)

    def _on_os_type_changed(self, index):
        display  = self._ui.combobox_os_type.currentText()
        if display is None or len(display)==0:
            return

        found_item = None
        for item in self._os_runinfo_desc:
            if item['display'] == display:
                found_item = item
                break

        widget = found_item['widget']
        self._ui.stackedwidget_os_runinfo.setCurrentWidget(widget)
        fixed_height = self._ui.stackedwidget_os_runinfo.currentWidget().sizeHint().height()
        if fixed_height < 0:
            fixed_height = 0
        self._ui.stackedwidget_os_runinfo.setFixedHeight(fixed_height)

        if self._current_cell is not None:
            widget.reset()
            runinfo = self._current_cell.runinfo()
            runinfo.set_os_runinfo(widget.runinfo())

    def _on_addr_edit_finished(self):
        self.profile_addr.set(self._ui.lineedit_addr.text().strip())

    def _on_state_changed(self, sender):
        if sender is not self._client:
            return

        is_connected = self._client.is_connected()
        if is_connected:
            self._ui.btn_connect.setText("断开")
            self._timer.start()
        else:
            self._ui.btn_connect.setText("连接")
            self._ui.listwidget_cells.clearSelection()
            self._timer.stop()
            self._root_cpuload.reset()

        self._ui.btn_connect.setChecked(is_connected)
        self._ui.btn_hyp_start.setEnabled(is_connected)
        self._ui.btn_hyp_stop.setEnabled(is_connected)
        self._ui.frame_runcell.setVisible(is_connected)

    def _on_connect(self):
        if not self._client.is_connected():
            if not self._client.connect(self._ui.lineedit_addr.text().strip(), timeout=10):
                self.logger.error("连接失败")
        else:
            self._client.close()
