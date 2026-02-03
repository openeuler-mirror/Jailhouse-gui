"""
日志显示界面模块。

本模块提供了用于显示和管理系统日志的图形界面组件，包括：
- 实时日志滚动显示
- 日志级别过滤（DEBUG/INFO/WARNING/ERROR）
- 日志颜色标记（不同级别不同颜色）
- 日志清除功能
- 日志级别动态调整

主要类:
- LogHandler: 自定义日志处理器，用于将日志记录传递到UI
- LogWidget: 日志显示界面主组件
"""

import time
import logging
from PySide2 import QtWidgets, QtCore, QtGui

from forms.ui_log import Ui_LogWidget
from forms.ui_log_title import Ui_LogTitleWidget


class LogHandler(logging.Handler):
    """
    自定义日志处理器。
    
    将日志记录通过回调函数传递给UI组件进行显示。
    
    属性:
        _callback: 日志记录回调函数
    """
    def __init__(self, callback):
        """
        初始化日志处理器。
        
        Args:
            callback: 处理日志记录的回调函数
        """
        super().__init__()
        self._callback = callback

    def emit(self, record):
        """
        处理日志记录事件。
        
        将日志记录传递给回调函数。
        
        Args:
            record: 日志记录对象
        """
        if self._callback:
            self._callback(record)


class LogWidget(QtWidgets.QWidget):
    """
    日志显示界面主组件。
    
    提供实时日志显示功能，支持：
    - 不同日志级别（DEBUG/INFO/WARNING/ERROR）的颜色标记
    - 日志级别动态过滤
    - 日志内容清除
    - 时间戳和来源信息显示
    
    属性:
        sig_new_log: 新日志记录信号
        colors: 日志级别对应的文本颜色映射
        _ui: 自动生成的UI组件对象
        _handler: 日志处理器实例
        _levels: 日志级别名称与值的映射
    """
    sig_new_log = QtCore.Signal(object)

    colors = {
        logging.DEBUG: QtGui.QColor(116, 185, 255), # 调试级别颜色（蓝色）
        logging.INFO: QtCore.Qt.green,  # 信息级别颜色（绿色）
        logging.WARNING: QtCore.Qt.yellow,  # 警告级别颜色（黄色）
        logging.ERROR: QtCore.Qt.red,   # 错误级别颜色（红色）
        logging.CRITICAL: QtCore.Qt.red # 严重错误颜色（红色）
    }

    def __init__(self, parent=None):
        """
        初始化日志显示界面。
        
        设置UI组件、日志处理器及信号槽连接。
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._ui = Ui_LogWidget()
        self._ui.setupUi(self)
        self._ui.combobox_level.setView(QtWidgets.QListView())  # 设置组合框显示为列表视图

        # 创建日志处理器并绑定回调
        self._handler = LogHandler(
            lambda record: self.new_log(record) # 接收到日志记录时触发new_log方法
        )

        # 将处理器添加到根日志记录器
        logger = logging.getLogger()
        logger.addHandler(self._handler)

        # 初始化日志级别映射
        self._levels = {
            logging.getLevelName(logging.NOTSET) : logging.NOTSET,
            logging.getLevelName(logging.DEBUG)  : logging.DEBUG,
            logging.getLevelName(logging.INFO)   : logging.INFO,
            logging.getLevelName(logging.WARNING): logging.WARNING,
            logging.getLevelName(logging.ERROR)  : logging.ERROR
        }
        self._ui.combobox_level.addItems(self._levels.keys())   # 添加日志级别选项
        self._ui.combobox_level.setCurrentText(logging.getLevelName(self.get_loglevel()))   # 设置初始级别
        self._ui.combobox_level.currentIndexChanged.connect(self._on_loglevel_changed)      # 级别变更事件
        self._ui.btn_clean.clicked.connect(self._on_log_clean)  # 清除日志事件

        self.sig_new_log.connect(self._on_log)  # 信号连接到日志显示处理函数

    def set_loglevel(self, level):
        """设置日志处理器的过滤级别"""
        self._handler.setLevel(level)

    def get_loglevel(self):
        """获取当前日志处理器的过滤级别"""
        return self._handler.level

    def log_clean(self):
        """清除日志显示内容"""
        self._ui.textbrowser.clear()

    def new_log(self, record: logging.LogRecord):
        """接收新日志记录并发送信号"""
        self.sig_new_log.emit(record)

    def _on_log(self, record: logging.LogRecord):
        """处理新日志记录的显示"""
        # 过滤特定来源的日志（如zerorpc框架日志）
        if record.name == "zerorpc.gevent_zmq":
            return

        # 格式化时间戳（秒.毫秒）
        sec = time.strftime(f"%H:%M:%S", time.gmtime(record.created))
        msec = f'{int(record.msecs):03d}'
        timestamp = f"  {sec}.{msec}"

        # 设置日志级别对应的文本颜色
        color = self.colors.get(record.levelno, QtCore.Qt.white)
        self._ui.textbrowser.setTextColor(color)
        # 插入日志级别（左对齐8字符宽度）
        self._ui.textbrowser.insertPlainText(record.levelname.ljust(8))
        # 插入时间戳
        self._ui.textbrowser.insertPlainText(timestamp)
        # 插入日志来源名称
        self._ui.textbrowser.insertPlainText("  " + record.name)

        # 错误级别以上显示函数名和行号
        if record.levelno >= logging.ERROR:
            self._ui.textbrowser.insertPlainText(f"  {record.funcName}:{record.lineno}")

        # 插入日志内容分隔符
        self._ui.textbrowser.insertPlainText(": ")
        # 恢复默认文本颜色
        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        # 插入日志具体内容
        self._ui.textbrowser.insertPlainText(record.msg)
        self._ui.textbrowser.insertPlainText('\n')
        # 滚动到日志末尾
        self._ui.textbrowser.moveCursor(self._ui.textbrowser.textCursor().End)
        # 处理事件确保界面及时更新
        QtWidgets.QApplication.instance().processEvents()

    def _on_loglevel_changed(self):
        """处理日志级别选择变更事件"""
        name = self._ui.combobox_level.currentText()
        if name not in self._levels:
            return
        self.set_loglevel(self._levels[name])   # 根据选择设置日志级别

    def _on_log_clean(self):
        """处理日志清除按钮点击事件"""
        self.log_clean()    # 调用清除日志方法
