import itertools
import logging
import enum
from typing import Optional, List, Union
from PySide2 import QtWidgets, QtGui, QtCore
from forms.ui_mem_region_item import Ui_MemRegionItem
from forms.ui_mem_map_item import Ui_MemMapItem
from forms.ui_mem_edit_widget import Ui_MemEditWidget
import utils
from common_widget import clean_layout, set_lineedit_status
from jh_resource import MemMap, MemRegion, MemRegionList

logger = logging.getLogger("MemRegion")


class MemReginItem(QtWidgets.QWidget): ...
class MemEditWidget(QtWidgets.QWidget): ...


class MemRegionItem(QtWidgets.QWidget):
    def __init__(self, on_remove, on_changed, region: Optional[MemRegion]=None, parent=None):
        super().__init__(parent)

        self._on_remove = on_remove
        self._on_changed = on_changed
        self._region = MemRegion()

        self._ui = Ui_MemRegionItem()
        self._ui.setupUi(self)

        if region is None:
            region = MemRegion()
        self.set_value(region)

        self._ui.lineedit_addr.setText(utils.to_human_addr(region.addr()))
        self._ui.lineedit_size.setText(utils.to_human_size(region.size()))

        self._ui.btn_remove.clicked.connect(self._on_btn_remove)
        self._ui.lineedit_addr.textChanged.connect(self._on_value_changed)
        self._ui.lineedit_size.textChanged.connect(self._on_value_changed)
        self._ui.lineedit_addr.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_size.editingFinished.connect(self._on_edit_finished)

    def set_value(self, region: MemRegion):
        self._region = region
        self._ui.lineedit_addr.setText(utils.to_human_addr(region.addr()))
        self._ui.lineedit_size.setText(utils.to_human_size(region.size()))

    def value(self) -> Optional[MemRegion]:
        addr_txt = self._ui.lineedit_addr.text()
        size_txt = self._ui.lineedit_size.text()

        addr = utils.from_human_num(addr_txt)
        if addr is None:
            logger.error(f"invalid addr {addr_txt}.")
            return None
        size = utils.from_human_num(size_txt)
        if size is None:
            logger.error(f"invalid size {size_txt}")
            return None

        return MemRegion(addr, size)

    def _on_btn_remove(self):
        self._on_remove(self)

    def _on_value_changed(self, text):
        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(text)
        set_lineedit_status( w, value is not None)

    def _on_edit_finished(self):
        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(w.text())
        # 如果值无效,修改为默认值
        if w is self._ui.lineedit_addr:
            if value is None:
                self._ui.lineedit_addr.setText(utils.to_human_addr(self._region.addr()))
            else:
                self._ui.lineedit_addr.setText(utils.to_human_addr(value))
                if self._region.addr() != value:
                    self._region.set_addr(value)
                    self._on_changed(self)
        if w is self._ui.lineedit_size:
            if value is None:
                self._ui.lineedit_size.setText(utils.to_human_size(self._region.size()))
            else:
                self._ui.lineedit_size.setText(utils.to_human_size(value))
                if self._region.size() != value:
                    self._region.set_size(value)
                    self._on_changed(self)

class MemMapItem(QtWidgets.QWidget):
    def __init__(self, on_remove, on_changed, mmap: Optional[MemMap]=None, parent=None):
        super().__init__(parent)
        self._on_remove = on_remove
        self._on_changed = on_changed
        self._mmap = MemMap(0, 0, 0)

        self._ui = Ui_MemMapItem()
        self._ui.setupUi(self)
        self._ui.combobox_type.addItems(MemMap.Type.names())

        if mmap is None:
            mmap = MemMap(0, 0, 0)
        self.set_value(mmap)

        self._ui.btn_remove.clicked.connect(self._on_btn_remove)
        self._ui.lineedit_phys.textChanged.connect(self._on_value_changed)
        self._ui.lineedit_virt.textChanged.connect(self._on_value_changed)
        self._ui.lineedit_size.textChanged.connect(self._on_value_changed)
        self._ui.lineedit_phys.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_virt.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_size.editingFinished.connect(self._on_edit_finished)
        self._ui.lineedit_comment.editingFinished.connect(self._on_comment_edit_finished)
        self._ui.combobox_type.currentIndexChanged.connect(self._on_type_changed)

    def set_value(self, mmap: MemMap):
        self._mmap = mmap
        self._ui.lineedit_phys.setText(utils.to_human_addr(mmap.phys()))
        self._ui.lineedit_virt.setText(utils.to_human_addr(mmap.virt()))
        self._ui.lineedit_size.setText(utils.to_human_size(mmap.size()))
        self._ui.lineedit_comment.setText(mmap.comment())
        self._ui.combobox_type.setCurrentText(mmap.type().value)

    def value(self) -> Optional[MemMap]:
        phys_txt = self._ui.lineedit_phys.text()
        virt_txt = self._ui.lineedit_virt.text()
        size_txt = self._ui.lineedit_size.text()

        phys = utils.from_human_num(phys_txt)
        if phys is None:
            logger.error(f"invalid phys {phys_txt}.")
            return None
        virt = utils.from_human_num(virt_txt)
        if virt is None:
            logger.error(f"invalid virt {virt_txt}.")
            return None
        size = utils.from_human_num(size_txt)
        if size is None:
            logger.error(f"invalid size {size_txt}")
            return None
        comment = self._ui.lineedit_comment.text().strip()

        _type = MemMap.Type.from_name(self._ui.combobox_type.currentText())
        if _type is None:
            _type = MemMap.Type.NORMAL

        return MemMap(phys, virt, size, _type, comment)

    def _on_btn_remove(self):
        self._on_remove(self)

    def _on_value_changed(self, text):
        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(text)
        set_lineedit_status(w, value is not None)

    def _on_edit_finished(self):
        w: QtWidgets.QLineEdit = self.sender()
        value = utils.from_human_num(w.text())
        # 如果输入有误, 使用默认值
        if w is self._ui.lineedit_phys:
            if value is None:
                w.setText(utils.to_human_addr(self._mmap.phys()))
            else:
                w.setText(utils.to_human_addr(value))
                self._on_changed(self)
        if w is self._ui.lineedit_virt:
            if value is None:
                w.setText(utils.to_human_addr(self._mmap.virt()))
            else:
                w.setText(utils.to_human_addr(value))
                self._on_changed(self)
        if w is self._ui.lineedit_size:
            if value is None:
                w.setText(utils.to_human_size(self._mmap.size()))
            else:
                w.setText(utils.to_human_size(value))
                self._on_changed(self)

    def _on_comment_edit_finished(self):
        self._on_changed(self)

    def _on_type_changed(self, index):
        name = self._ui.combobox_type.currentText()
        self._on_changed(self)

class MemEditWidget(QtWidgets.QWidget):
    signal_changed = QtCore.Signal()

    class Mode(enum.Enum):
        UNKNOWN = "unknown"
        MEM_REGION = "mem region"
        MEM_MAP = "mem map"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui = Ui_MemEditWidget()
        self._ui.setupUi(self)
        self._ui.label_total.setText("总大小: 0")
        self._ui.label_msg.setText("")

        self._items = list()
        self._mode = self.Mode.UNKNOWN

        self._ui.btn_add.clicked.connect(self._on_add)

    def set_regions(self, regions: List[MemRegion]):
        self._clear()
        self._mode = self.Mode.MEM_REGION
        for region in regions:
            self._add(region)
        self._update(False)

    def set_mmaps(self, mmaps: List[MemMap]):
        self._clear()
        self._mode = self.Mode.MEM_MAP
        for mmap in mmaps:
            self._add(mmap)
        self._update(False)

    def get_value(self) -> Union[List[MemMap], List[MemRegion]]:
        values = list()
        for item in self._items:
            value = item.value()
            if value is None:
                return list()
            values.append(value)
        return values

    def _clear(self):
        self._items.clear()
        clean_layout(self._ui.frame_regions.layout())

    def _add(self, m: Union[MemRegion, MemMap]) -> bool:
        if self._mode is self.Mode.MEM_REGION:
            if not isinstance(m, MemRegion):
                return False
            item = MemRegionItem(self._on_item_remove, self._on_item_changed, m, self)
            self._items.append(item)
            self._ui.frame_regions.layout().addWidget(item)
        elif self._mode is self.Mode.MEM_MAP:
            if not isinstance(m, MemMap):
                return False
            item = MemMapItem(self._on_item_remove, self._on_item_changed, m, self)
            self._items.append(item)
            self._ui.frame_regions.layout().addWidget(item)
        return True

    def _check(self) -> bool:
        """
        检查输入是否有效
        """
        # 所有item大小不为0
        for item in self._items:
            v = item.value()
            if v is None or v.size()==0:
                return False

        # 检查是否重叠
        self._ui.label_msg.clear()
        for index_pair in itertools.combinations(range(len(self._items)), 2):
            i1 = index_pair[0]
            i2 = index_pair[1]
            m1 = self._items[i1].value()
            m2 = self._items[i2].value()
            if m1.is_overlap(m2):
                self._ui.label_msg.setText(f"索引{i1}和{i2}重叠")
                return False

        return True

    def _update(self, emit=True):
        total = 0
        self._ui.label_total.clear()

        if not self._check():
            return

        if self._mode is self.Mode.MEM_REGION:
            for item in self._items:
                if item.value():
                    total = total + item.value().size()
        elif self._mode is self.Mode.MEM_MAP:
            for item in self._items:
                if item.value():
                    total = total + item.value().size()

        txt = f'总大小 {utils.to_human_size(total)}'
        self._ui.label_total.setText(txt)
        if emit:
            self.signal_changed.emit()

    def _on_add(self) -> bool:
        if not self._check():
            return False

        if self._mode == self.Mode.MEM_REGION:
            self._add(MemRegion(0,0))
        elif self._mode is self.Mode.MEM_MAP:
            self._add(MemMap(0,0,0))
        return True

    def _on_item_remove(self, item: MemReginItem):
        if item in self._items:
            self._ui.frame_regions.layout().removeWidget(item)
            self._items.remove(item)
        item.deleteLater()
        self._update()

    def _on_item_changed(self, item: MemReginItem):
        if item in self._items:
            self._update()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w1 = MemEditWidget()
    w1.set_regions(list())
    w1.show()
    w2 = MemEditWidget()
    w2.set_mmaps(list())
    w2.show()
    app.exec_()
