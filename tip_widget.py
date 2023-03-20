from typing import List, Optional
from PySide2 import QtWidgets, QtCore, QtGui
from forms.ui_tip_widget import Ui_TipWidget
import enum
import weakref


class TipItem(object):
    def __init__(self, obj, doc: str) -> None:
        self.obj = weakref.ref(obj)
        self.doc = doc


class TipMgr(object):
    class Type(enum.Enum):
        HOVER_TIP = 0
        FOCUS_TIP = 1
        ANY_TIP   = 2

    _tips: List[TipItem] = list()

    @classmethod
    def add(cls, obj, doc: str):
        tip = TipItem(obj, doc)
        cls._tips.append(tip)

    @classmethod
    def find_obj(cls, obj) -> Optional[TipItem]:
        def _find(obj):
            tips = cls._tips
            for tip in tips:
                if tip.obj() == obj:
                    return tip

        w: QtWidgets.QWidget = obj
        while w is not None:
            tip = _find(w)
            if tip is not None:
                return tip
            w = w.parentWidget()
        return None

    @classmethod
    def find_pos(cls, pos: QtCore.QPoint) -> Optional[TipItem]:
        found_w: QtWidgets.QWidget = None
        found_tip: Optional[TipItem] = None
        for tip in cls._tips:
            w: QtWidgets.QWidget = tip.obj()
            if w is None:
                continue
            if not w.isVisible():
                continue

            if w.rect().contains(w.mapFromGlobal(pos)):
                if found_tip is None:
                    found_w = w
                    found_tip = tip
                else:
                    if w.width()*w.height() < found_w.width()*found_w.height():
                        found_w = w
                        found_tip = tip
        return found_tip


class TipWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self._ui = Ui_TipWidget()
        self._ui.setupUi(self)
        self._ui.textbrowser.setTextColor(QtCore.Qt.white)

        self._focus_tip: Optional[TipItem] = None

        qapp = QtWidgets.QApplication.instance()
        qapp.focusChanged.connect(self._on_focus_changed)
        qapp.installEventFilter(self)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.MouseMove:
            self._do_hover_tip(event.globalPos())
        return False

    def _on_focus_changed(self, old, new):
        if new is self._ui.textbrowser:
            return
        self._do_focus_tip(new)


    def _do_focus_tip(self, obj):
        tip = TipMgr.find_obj(obj)
        if tip is not None:
            self._focus_tip = tip
            self._ui.textbrowser.setText(tip.doc)
        else:
            self._focus_tip = None
            self._ui.textbrowser.clear()

    def _do_hover_tip(self, pos):
        tip = TipMgr.find_pos(pos)
        if tip is not None:
            self._ui.textbrowser.setText(tip.doc)
            return

        if self._focus_tip:
            self._ui.textbrowser.setText(self._focus_tip.doc)
        else:
            self._ui.textbrowser.clear()
