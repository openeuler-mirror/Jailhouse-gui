from PySide2 import QtWidgets, QtCore
from typing import Set, List
from forms.ui_cpu_edit_widget import Ui_CPUEditWidget
from flowlayout import FlowLayout
from common_widget import SelectButton, clean_layout


class CPUEditWidget(QtWidgets.QWidget):
    cpus_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_CPUEditWidget()
        self._ui.setupUi(self)
        self._ui.frame_ops.hide()
        self._layout = FlowLayout(self._ui.frame_cpus)

        self._editable = True
        self._items: List[SelectButton] = list()
        self._cpu_count = 0

    def set_cpu_count(self, count):
        self._cpu_count = count
        clean_layout(self._layout)
        self._items.clear()

        for i in range(count):
            item = SelectButton(str(i), self._ui.frame_cpus)
            self._layout.addWidget(item)
            item.clicked.connect(self._on_item_changed)
            self._items.append(item)

    def set_editable(self, editable: bool):
        for item in self._items:
            item.setEnabled(editable)

    def set_cpus(self, cpus: Set[int]):
        for idx, item in enumerate(self._items):
            item.setChecked(idx in cpus)

    def get_cpus(self) -> Set[int]:
        cpus = set()
        for idx, item in enumerate(self._items):
            if item.isChecked():
                cpus.add(idx)
        return cpus

    def _on_item_changed(self):
        cpus = list()
        for idx, item in enumerate(self._items):
            if item.isChecked():
                cpus.append(idx)

        self.cpus_changed.emit()


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = CPUEditWidget()
    w.set_cpu_count(4)
    w.show()
    app.exec_()
    pass