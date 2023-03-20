import logging
from PySide2 import QtWidgets
from forms.ui_jailhouse_widget import Ui_JailhouseWidget
from jh_resource import ResourceJailhouse, ResourceMgr


class JailhouseWidget(QtWidgets.QWidget):
    logger = logging.getLogger("JailhouseWidget")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_JailhouseWidget()
        self._ui.setupUi(self)

    def set_jailhosue(self, rsc: ResourceJailhouse):
        pass

