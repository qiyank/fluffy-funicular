# -*- coding: utf-8 -*-
"""底部 / 侧边导航栏。折叠时是底部标签栏，展开成大屏时自动变成左侧导航条。"""
from __future__ import annotations

from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from core import theme as T
from ui import widgets as W


class NavIcon(Widget):
    """纯 canvas 绘制的导航图标（不依赖字体图标，避免中文环境下显示成方框）。"""

    def __init__(self, kind="grid", color=T.TEXT_HINT, size=dp(22), **kwargs):
        super().__init__(size_hint=(None, None), size=(size, size), **kwargs)
        self.kind = kind
        self.color = list(color)
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def set_color(self, color):
        self.color = list(color)
        self._redraw()

    def _redraw(self, *args):
        if self.width <= 1:
            return
        self.canvas.clear()
        u = min(self.width, self.height) / 22.0     # 以 22dp 为设计基准
        x, y = self.x, self.y
        c = self.color
        with self.canvas:
            Color(*c)
            if self.kind == "grid":
                s = 8 * u
                for ox, oy in ((1, 12), (13, 12), (1, 2), (13, 2)):
                    RoundedRectangle(pos=(x + ox * u, y + oy * u), size=(s, s),
                                     radius=[2.2 * u])
            elif self.kind == "task":
                for i, oy in enumerate((15, 9.5, 4)):
                    Color(*c)
                    Ellipse(pos=(x + 1 * u, y + oy * u), size=(2.6 * u, 2.6 * u))
                    RoundedRectangle(pos=(x + 6 * u, y + (oy + 0.9) * u),
                                     size=((15 - i * 2) * u, 2.4 * u),
                                     radius=[1.2 * u])
            elif self.kind == "search":
                r = 6.2 * u
                center = (x + 9.5 * u, y + 12.5 * u)
                Line(circle=(center[0], center[1], r, 0, 360), width=max(1.4, 2 * u))
                Line(points=[x + 14 * u, y + 8 * u, x + 19.5 * u, y + 2.5 * u],
                     width=max(1.4, 2 * u), cap="round")
            elif self.kind == "box":
                Line(rounded_rectangle=(x + 2 * u, y + 2 * u, 18 * u, 13 * u, 4 * u),
                     width=max(1.4, 2 * u))
                Line(points=[x + 2 * u, y + 15 * u, x + 20 * u, y + 15 * u],
                     width=max(1.4, 2 * u))
                Line(points=[x + 8 * u, y + 19 * u, x + 14 * u, y + 19 * u],
                     width=max(1.4, 2 * u), cap="round")


class NavItem(ButtonBehavior, BoxLayout, W.RoundedBG):
    """一个导航项：图标 + 文字。"""

    def __init__(self, key, label, icon, on_tap=None, **kwargs):
        super().__init__(orientation="vertical", padding=[0, dp(7), 0, dp(7)],
                         spacing=dp(3), **kwargs)
        self.key = key
        self.icon = NavIcon(icon, color=T.TEXT_HINT, size=dp(22))
        icon_holder = BoxLayout(size_hint_y=None, height=dp(24))
        icon_holder.add_widget(Widget())
        icon_holder.add_widget(self.icon)
        icon_holder.add_widget(Widget())
        self.add_widget(icon_holder)
        self.label = W.txt(label, size=T.FONT_SMALL, color=T.TEXT_HINT,
                           halign="center")
        self.label.size_hint_y = None
        self.label.height = dp(16)
        self.add_widget(self.label)
        self.init_bg(color=(0, 0, 0, 0), radius=T.RADIUS_SMALL)
        self._active = False
        if on_tap:
            self.bind(on_release=lambda *_: on_tap(key))

    def set_active(self, flag):
        flag = bool(flag)
        if flag == self._active:
            return
        self._active = flag
        if flag:
            self.set_bg_color(T.PRIMARY_SOFT)
            self.icon.set_color(T.PRIMARY)
            self.label.color = T.PRIMARY
            self.label.bold = True
        else:
            self.set_bg_color((0, 0, 0, 0))
            self.icon.set_color(T.TEXT_HINT)
            self.label.color = T.TEXT_HINT
            self.label.bold = False


class NavBar(BoxLayout):
    """导航栏容器，支持 bottom（折叠态）/ rail（展开态）两种形态。"""

    def __init__(self, items, on_select=None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self._items = list(items)
        self.on_select = on_select
        self.buttons = {}
        self.current = self._items[0][0] if self._items else None
        self._mode = None
        with self.canvas.before:
            self._bg_col = Color(*T.CARD)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            self._line_col = Color(*T.LINE)
            self._line_rect = Rectangle(pos=self.pos, size=(1, 1))
        self.bind(pos=self._sync, size=self._sync)
        self.set_mode("bottom")

    def _sync(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        if self._mode == "bottom":
            self._line_rect.pos = (self.x, self.top - 1)
            self._line_rect.size = (self.width, 1)
        else:
            self._line_rect.pos = (self.right - 1, self.y)
            self._line_rect.size = (1, self.height)

    def set_mode(self, mode):
        if mode == self._mode:
            return
        self._mode = mode
        self.clear_widgets()
        self.buttons.clear()
        if mode == "bottom":
            self.orientation = "horizontal"
            self.padding = [dp(6), dp(4), dp(6), dp(4)]
        else:
            self.orientation = "vertical"
            self.padding = [dp(8), dp(14), dp(8), dp(8)]
        for key, label, icon in self._items:
            item = NavItem(key, label, icon, on_tap=self.select)
            self.buttons[key] = item
            self.add_widget(item)
            if mode == "bottom":
                item.size_hint = (1, 1)
            else:
                item.size_hint = (1, None)
                item.height = dp(62)
                item.padding = [0, dp(6), 0, dp(6)]
        if mode == "rail":
            self.add_widget(Widget())
        self.highlight(self.current)
        self._sync()

    def select(self, key, force=False):
        """用户点击导航项时调用。"""
        if key not in self.buttons:
            return
        self.highlight(key)
        if self.on_select:
            self.on_select(key)

    def highlight(self, key):
        """只更新高亮状态，不触发回调（供外部切页时同步界面）。"""
        if key not in self.buttons:
            return
        self.current = key
        for k, item in self.buttons.items():
            item.set_active(k == key)
        self._sync()
