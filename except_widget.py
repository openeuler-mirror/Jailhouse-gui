from PySide2 import QtWidgets
from forms.ui_except_widget import Ui_ExceptWidget

class ExceptDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_ExceptWidget()
        self._ui.setupUi(self)

        self._ui.btn_copy.clicked.connect(self._on_copy)
        self._ui.btn_ignore.clicked.connect(self._on_ignore)
        self._ui.btn_terminate.clicked.connect(self._on_terminate)

    def set_text(self, text: str):
        self._ui.textbrowser.clear()
        self._ui.textbrowser.setText(text)

    def _on_copy(self):
        QtWidgets.QApplication.clipboard().setText(self._ui.textbrowser.toPlainText())

    def _on_ignore(self):
        self.close()

    def _on_terminate(self):
        QtWidgets.QApplication.quit()
