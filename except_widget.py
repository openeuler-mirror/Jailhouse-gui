from PySide2 import QtWidgets
from forms.ui_except_widget import Ui_ExceptWidget

class ExceptDialog(QtWidgets.QDialog):
    """
    异常处理对话框
    
    用于显示程序运行时发生的异常信息，提供复制异常信息、忽略异常继续运行或终止程序的选项。
    
    Attributes:
        _ui: 由UI设计器生成的用户界面对象
    """
    def __init__(self, parent=None):
        """
        初始化异常处理对话框
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__(parent)
        self._ui = Ui_ExceptWidget()
        self._ui.setupUi(self)

        # 连接按钮点击事件到对应的处理函数
        self._ui.btn_copy.clicked.connect(self._on_copy)     # 复制异常信息到剪贴板
        self._ui.btn_ignore.clicked.connect(self._on_ignore)    # 忽略异常，关闭对话框
        self._ui.btn_terminate.clicked.connect(self._on_terminate)  # 终止程序运行


    def set_text(self, text: str):
        """
        设置对话框中显示的异常信息文本
        
        Args:
            text: 要显示的异常信息文本
        """
        self._ui.textbrowser.clear()    # 清空现有内容
        self._ui.textbrowser.setText(text)  # 设置新的异常信息文本

    def _on_copy(self):
        """处理复制按钮点击事件：将异常信息复制到系统剪贴板"""
        QtWidgets.QApplication.clipboard().setText(self._ui.textbrowser.toPlainText())

    def _on_ignore(self):
        """处理忽略按钮点击事件：关闭对话框，程序继续运行"""
        self.close()

    def _on_terminate(self):
        """处理终止按钮点击事件：退出整个应用程序"""
        QtWidgets.QApplication.quit()
