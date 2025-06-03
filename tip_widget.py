"""
提示信息管理模块。

本模块提供了基于鼠标悬停和焦点事件的提示信息显示功能，包括：
- 提示信息的注册与管理
- 鼠标悬停时的提示信息显示
- 控件获得焦点时的提示信息显示
- 提示信息的层级处理（优先显示子控件提示）

主要类:
- TipItem: 提示信息项
- TipMgr: 提示信息管理器
- TipWidget: 提示信息显示界面组件
"""

from typing import List, Optional
from PySide2 import QtWidgets, QtCore, QtGui
from forms.ui_tip_widget import Ui_TipWidget
import enum
import weakref


class TipItem(object):
    """
    提示信息项。
    
    存储控件与对应提示文本的关联关系。
    
    属性:
        obj: 弱引用指向的控件对象
        doc: 提示文本内容
    """
    def __init__(self, obj, doc: str) -> None:
        """
        初始化提示信息项。
        
        Args:
            obj: 关联的控件对象
            doc: 提示文本
        """
        self.obj = weakref.ref(obj)
        self.doc = doc


class TipMgr(object):
    """
    提示信息管理器。
    
    提供提示信息的注册、查找等静态方法，支持：
    - 按控件查找提示信息
    - 按坐标位置查找提示信息
    - 提示信息类型管理（悬停/焦点）
    
    属性:
        Type: 提示信息类型枚举
        _tips: 存储所有提示信息项的列表
    """
    class Type(enum.Enum):
        """提示信息类型枚举"""
        HOVER_TIP = 0   # 鼠标悬停提示
        FOCUS_TIP = 1   # 控件焦点提示
        ANY_TIP   = 2   # 任意类型提示

    _tips: List[TipItem] = list()   # 存储所有提示信息项

    @classmethod
    def add(cls, obj, doc: str):
        """
        添加提示信息项。
        
        Args:
            obj: 关联的控件对象
            doc: 提示文本
        """
        tip = TipItem(obj, doc)
        cls._tips.append(tip)

    @classmethod
    def find_obj(cls, obj) -> Optional[TipItem]:
        """
        查找控件及其父控件链上的提示信息。
        
        逐级向上查找，直到找到第一个有提示信息的控件。
        
        Args:
            obj: 要查找的控件对象
        Returns:
            找到的提示信息项，若未找到则返回None
        """
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
            w = w.parentWidget()     # 逐级向上查找父控件
        return None

    @classmethod
    def find_pos(cls, pos: QtCore.QPoint) -> Optional[TipItem]:
        """
        查找指定坐标位置的提示信息。
        
        优先选择面积最小的可见控件的提示信息。
        
        Args:
            pos: 全局坐标点
        Returns:
            找到的提示信息项，若未找到则返回None
        """
        found_w: QtWidgets.QWidget = None
        found_tip: Optional[TipItem] = None
        for tip in cls._tips:
            w: QtWidgets.QWidget = tip.obj()
            if w is None:
                continue
            if not w.isVisible():
                continue

            # 检查坐标是否在控件范围内
            if w.rect().contains(w.mapFromGlobal(pos)):
                # 优先选择面积更小的控件（更具体的子控件）
                if found_tip is None:
                    found_w = w
                    found_tip = tip
                else:
                    if w.width()*w.height() < found_w.width()*found_w.height():
                        found_w = w
                        found_tip = tip
        return found_tip


class TipWidget(QtWidgets.QWidget):
    """
    提示信息显示界面组件。
    
    处理全局鼠标和焦点事件，显示对应的提示信息，支持：
    - 鼠标悬停提示
    - 控件焦点提示
    - 提示信息的切换与显示
    
    属性:
        _ui: 自动生成的UI组件对象
        _focus_tip: 当前焦点控件的提示信息项
    """
    def __init__(self, parent=None):
        """
        初始化提示信息显示界面。
        
        设置UI组件、连接事件并安装全局事件过滤器。
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super().__init__()
        self._ui = Ui_TipWidget()
        self._ui.setupUi(self)
        self._ui.textbrowser.setTextColor(QtCore.Qt.white)  # 设置提示文本颜色为白色

        self._focus_tip: Optional[TipItem] = None   # 当前焦点提示信息

        # 获取应用实例并连接焦点变更事件
        qapp = QtWidgets.QApplication.instance()
        qapp.focusChanged.connect(self._on_focus_changed)
        qapp.installEventFilter(self)    # 安装全局事件过滤器

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """
        全局事件过滤器。
        
        捕获鼠标移动事件并处理悬停提示。
        
        Args:
            watched: 被监视的对象
            event: 事件对象
        Returns:
            bool: 是否过滤该事件
        """
        if event.type() == QtCore.QEvent.MouseMove:
            self._do_hover_tip(event.globalPos())   # 处理鼠标悬停提示
        return False    # 不过滤事件，继续传递

    def _on_focus_changed(self, old, new):
        """
        处理焦点变更事件。
        
        Args:
            old: 失去焦点的控件
            new: 获得焦点的控件
        """
        if new is self._ui.textbrowser: # 避免自身获得焦点时触发
            return
        self._do_focus_tip(new) # 处理焦点提示


    def _do_focus_tip(self, obj):
        """
        处理焦点提示信息显示。
        
        Args:
            obj: 当前获得焦点的控件
        """
        tip = TipMgr.find_obj(obj)  # 查找控件的提示信息
        if tip is not None:
            self._focus_tip = tip
            self._ui.textbrowser.setText(tip.doc)   # 显示提示文本
        else:
            self._focus_tip = None
            self._ui.textbrowser.clear()    # 清除提示文本

    def _do_hover_tip(self, pos):
        """
        处理鼠标悬停提示信息显示。
        
        Args:
            pos: 鼠标全局坐标
        """
        tip = TipMgr.find_pos(pos)  # 查找坐标位置的提示信息
        if tip is not None:
            self._ui.textbrowser.setText(tip.doc)   # 显示悬停提示
            return

        # 若无悬停提示，显示焦点提示（如果有）
        if self._focus_tip:
            self._ui.textbrowser.setText(self._focus_tip.doc)
        else:
            self._ui.textbrowser.clear()    # 清除提示文本
