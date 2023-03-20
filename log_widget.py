import time
import logging
from PySide2 import QtWidgets, QtCore, QtGui

from forms.ui_log import Ui_LogWidget
from forms.ui_log_title import Ui_LogTitleWidget


class LogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def emit(self, record):
        if self._callback:
            self._callback(record)


class LogWidget(QtWidgets.QWidget):
    sig_new_log = QtCore.Signal(object)

    colors = {
        logging.DEBUG: QtGui.QColor(116, 185, 255),
        logging.INFO: QtCore.Qt.green,
        logging.WARNING: QtCore.Qt.yellow,
        logging.ERROR: QtCore.Qt.red,
        logging.CRITICAL: QtCore.Qt.red
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_LogWidget()
        self._ui.setupUi(self)
        self._ui.combobox_level.setView(QtWidgets.QListView())

        self._handler = LogHandler(
            lambda record: self.new_log(record)
        )

        logger = logging.getLogger()
        logger.addHandler(self._handler)

        self._levels = {
            logging.getLevelName(logging.NOTSET) : logging.NOTSET,
            logging.getLevelName(logging.DEBUG)  : logging.DEBUG,
            logging.getLevelName(logging.INFO)   : logging.INFO,
            logging.getLevelName(logging.WARNING): logging.WARNING,
            logging.getLevelName(logging.ERROR)  : logging.ERROR
        }
        self._ui.combobox_level.addItems(self._levels.keys())
        self._ui.combobox_level.setCurrentText(logging.getLevelName(self.get_loglevel()))
        self._ui.combobox_level.currentIndexChanged.connect(self._on_loglevel_changed)
        self._ui.btn_clean.clicked.connect(self._on_log_clean)

        self.sig_new_log.connect(self._on_log)

    def set_loglevel(self, level):
        self._handler.setLevel(level)

    def get_loglevel(self):
        return self._handler.level

    def log_clean(self):
        self._ui.textbrowser.clear()

    def new_log(self, record: logging.LogRecord):
        self.sig_new_log.emit(record)

    def _on_log(self, record: logging.LogRecord):
        if record.name == "zerorpc.gevent_zmq":
            return

        sec = time.strftime(f"%H:%M:%S", time.gmtime(record.created))
        msec = f'{int(record.msecs):03d}'
        timestamp = f"  {sec}.{msec}"
        color = self.colors.get(record.levelno, QtCore.Qt.white)
        self._ui.textbrowser.setTextColor(color)
        self._ui.textbrowser.insertPlainText(record.levelname.ljust(8))
        self._ui.textbrowser.insertPlainText(timestamp)
        self._ui.textbrowser.insertPlainText("  " + record.name)

        if record.levelno >= logging.ERROR:
            self._ui.textbrowser.insertPlainText(f"  {record.funcName}:{record.lineno}")

        self._ui.textbrowser.insertPlainText(": ")
        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        self._ui.textbrowser.insertPlainText(record.msg)
        self._ui.textbrowser.insertPlainText('\n')
        self._ui.textbrowser.moveCursor(self._ui.textbrowser.textCursor().End)

        QtWidgets.QApplication.instance().processEvents()

    def _on_loglevel_changed(self):
        name = self._ui.combobox_level.currentText()
        if name not in self._levels:
            return
        self.set_loglevel(self._levels[name])

    def _on_log_clean(self):
        self.log_clean()
