from PySide2 import QtWidgets, QtCore, QtGui
from forms.ui_check_widget import Ui_CheckWidget
from checklist import Checklist, CheckResult
from jh_resource import ResourceMgr

class CheckWidget(QtWidgets.QWidget):
    """
    配置检查结果显示部件
    
    提供配置文件检查功能的用户界面，包含检查按钮、结果清理按钮和结果显示区域。
    通过调用Checklist工具类执行检查，并将结果以不同颜色显示在文本浏览器中。
    
    Attributes:
        _ui: 由UI设计器生成的用户界面对象，包含界面元素的引用
    """
    def __init__(self, parent=None):
        """
        初始化检查结果显示部件
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._ui = Ui_CheckWidget()
        self._ui.setupUi(self)

        self._ui.btn_clean.clicked.connect(self._on_clean)
        self._ui.btn_check.clicked.connect(self._on_check)

    def _on_clean(self):
        """处理清理按钮点击事件：清空文本浏览器中的检查结果"""
        self._ui.textbrowser.clear()
        pass

    def _on_check(self):
        """处理检查按钮点击事件：执行配置检查并在文本浏览器中显示结果"""
        # 设置默认文本颜色为白色
        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        self._ui.textbrowser.append("")
        self._ui.textbrowser.append("开始检查")
        self._ui.textbrowser.append("")

        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        # 从资源管理器获取当前打开的配置文件
        rsc = ResourceMgr.get_instance().get_current()
        if rsc is None:
            # 处理未打开配置文件的情况
            self._ui.textbrowser.append("当前没有打开配置文件")
        else:
            # 执行配置检查并获取结果列表
            results = Checklist.check(rsc)
            for result in results:
                # 根据检查结果状态设置文本颜色
                if result:
                    self._ui.textbrowser.setTextColor(QtCore.Qt.white)
                    self._ui.textbrowser.append(f'{result.name}: 成功')# 成功信息后续文本设为灰色
                    self._ui.textbrowser.setTextColor(QtCore.Qt.gray)
                else:
                    self._ui.textbrowser.setTextColor(QtCore.Qt.red)
                    self._ui.textbrowser.append(f'{result.name}: 失败')# 失败信息用红色显示
                    self._ui.textbrowser.setTextColor(QtGui.QColor(243,104,109))# 错误消息颜色
                 # 追加失败消息和警告消息（带缩进）
                for msg in result.failed_messages:
                    self._ui.textbrowser.append(f'    {msg}')
                for msg in result.warning_messages:
                    self._ui.textbrowser.append(f'    {msg}')

        # 检查完成后显示结束提示
        self._ui.textbrowser.setTextColor(QtCore.Qt.white)
        self._ui.textbrowser.append("")
        self._ui.textbrowser.append("检查完成")
        self._ui.textbrowser.append("")
