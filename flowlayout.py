
############################################################################
##
## Copyright (C) 2013 Riverbank Computing Limited.
## Copyright (C) 2020 The Qt Company Ltd.
## Contact: http://www.qt.io/licensing/
##
## This file is part of the Qt for Python examples of the Qt Toolkit.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of The Qt Company Ltd nor the names of its
##     contributors may be used to endorse or promote products derived
##     from this software without specific prior written permission.
##
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
## $QT_END_LICENSE$
##
#############################################################################

"""PySide2 port of the widgets/layouts/flowlayout example from Qt v5.x"""

import sys
from PySide2.QtCore import Qt, QMargins, QPoint, QRect, QSize
from PySide2.QtWidgets import (QApplication, QLayout, QPushButton,
                               QSizePolicy, QWidget)


class Window(QWidget):
    """流布局演示窗口
    
    创建一个包含FlowLayout的窗口，添加多个按钮用于展示流布局效果
    """
    def __init__(self):
        """初始化流布局演示窗口"""
        super(Window, self).__init__()

        # 创建流布局并添加多个按钮进行演示
        flowLayout = FlowLayout(self)
        flowLayout.addWidget(QPushButton("Short"))
        flowLayout.addWidget(QPushButton("Longer"))
        flowLayout.addWidget(QPushButton("Different text"))
        flowLayout.addWidget(QPushButton("More text"))
        flowLayout.addWidget(QPushButton("Even longer button text"))

        self.setWindowTitle("Flow Layout")


class FlowLayout(QLayout):
    """流布局实现
    
    类似网页中的浮动布局效果，当水平空间不足时自动换行排列子控件
    """
    def __init__(self, parent=None):
        """初始化流布局
        
        Args:
            parent: 父窗口部件，默认为None
        """
        super(FlowLayout, self).__init__(parent)

         # 设置内容边距
        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        """析构函数：清理所有布局项"""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        """添加布局项到列表"""
        self._item_list.append(item)

    def count(self):
        """返回布局项数量"""
        return len(self._item_list)

    def itemAt(self, index):
        """获取指定索引的布局项"""
        if index >= 0 and index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
         """移除并返回指定索引的布局项"""
        if index >= 0 and index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        """返回布局的扩展方向（水平和垂直均不扩展）"""
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        """指示布局的高度依赖于宽度（流布局的特性）"""
        return True

    def heightForWidth(self, width):
        """计算给定宽度下所需的高度"""
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        """设置布局的几何区域并执行布局操作"""
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        """返回布局的建议大小（等于最小大小）"""
        return self.minimumSize()

    def minimumSize(self):
        """计算布局的最小尺寸"""
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(),
                      2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        """执行布局计算
        
        Args:
            rect: 布局区域
            test_only: 是否仅进行测试计算（不实际设置几何位置）
            
        Returns:
            布局所需的总高度
        """
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()    # 获取布局项之间的间距

        for item in self._item_list:
            # 获取样式表中的间距信息
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(QSizePolicy.PushButton,
                                                   QSizePolicy.PushButton,
                                                   Qt.Horizontal)
            layout_spacing_y = style.layoutSpacing(QSizePolicy.PushButton,
                                                   QSizePolicy.PushButton,
                                                   Qt.Vertical)
            space_x = spacing + layout_spacing_x    # 水平间距
            space_y = spacing + layout_spacing_y    # 垂直间距

            # 计算下一个控件的x坐标
            next_x = x + item.sizeHint().width() + space_x
            # 如果超出当前行宽度，则换行
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            # 如果不是测试模式，则实际设置控件位置
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()   # 返回总高度


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = Window()
    mainWin.show()
    sys.exit(app.exec_())
