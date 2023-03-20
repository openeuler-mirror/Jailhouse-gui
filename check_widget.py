from PySide2 import QtWidgets, QtCore, QtGui
from forms.ui_check_widget import Ui_CheckWidget
from checklist import Checklist, CheckResult
from jh_resource import ResourceMgr

class CheckWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_CheckWidget()
        self._ui.setupUi(self)

        self._ui.btn_clean.clicked.connect(self._on_clean)
        self._ui.btn_check.clicked.connect(self._on_check)

    def _on_clean(self):
        self._ui.textbrowser.clear()
        pass

    def _on_check(self):
        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        self._ui.textbrowser.append("")
        self._ui.textbrowser.append("开始检查")
        self._ui.textbrowser.append("")

        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            self._ui.textbrowser.append("当前没有打开配置文件")
        else:
            results = Checklist.check(rsc)
            for result in results:
                if result:
                    self._ui.textbrowser.setTextColor(QtCore.Qt.white)
                    self._ui.textbrowser.append(f'{result.name}: 成功')
                    self._ui.textbrowser.setTextColor(QtCore.Qt.gray)
                else:
                    self._ui.textbrowser.setTextColor(QtCore.Qt.red)
                    self._ui.textbrowser.append(f'{result.name}: 失败')
                    self._ui.textbrowser.setTextColor(QtGui.QColor(243,104,109))
                for msg in result.failed_messages:
                    self._ui.textbrowser.append(f'    {msg}')
                for msg in result.warning_messages:
                    self._ui.textbrowser.append(f'    {msg}')


        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        self._ui.textbrowser.append("")
        self._ui.textbrowser.append("检查完成")
        self._ui.textbrowser.append("")
