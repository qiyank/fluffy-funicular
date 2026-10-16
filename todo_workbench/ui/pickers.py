# -*- coding: utf-8 -*-
"""日期 / 时间选择器（自绘日历，无需第三方依赖）。"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from core import models as M
from core import theme as T
from ui import widgets as W


class BaseModal(ModalView):
    """统一风格的弹层：深色遮罩 + 白色圆角卡片，宽度自适应（窄屏铺满，宽屏限宽）。"""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (1, 1))
        kwargs.setdefault("auto_dismiss", True)
        kwargs.setdefault("background_color", (0.05, 0.06, 0.12, 0.55))
        super().__init__(**kwargs)
        self._scroll = None
        self._inner = None
        self._natural = 0
        self._max_width = 560
        self.holder = AnchorLayout(anchor_x="center", anchor_y="center")
        self.add_widget(self.holder)
        Window.bind(size=self._on_window)

    def _on_window(self, *args):
        if self._scroll is not None:
            self._place()

    def show_card(self, inner, natural_height, max_width=560, padding=16):
        """把内容装进卡片并居中显示。inner 需要有确定的自然高度。"""
        self._inner = inner
        self._natural = dp(natural_height)
        self._max_width = max_width
        self._card = W.Panel(orientation="vertical", color=T.CARD,
                             radius=T.RADIUS_CARD, shadow=True, padding=0)
        self._card.add_widget(inner)
        self._scroll = ScrollView(size_hint=(None, None), do_scroll_x=False,
                                  bar_width=dp(3), bar_color=(0.6, 0.65, 0.75, 0.7),
                                  bar_inactive_color=(0, 0, 0, 0))
        self._scroll.add_widget(self._card)
        self.holder.add_widget(self._scroll)
        inner.bind(height=lambda *_: self._place())
        self._place()

    def _place(self, *args):
        if self._scroll is None:
            return
        width = max(dp(240), min(dp(self._max_width), Window.width - dp(24)))
        avail_h = max(dp(200), Window.height - dp(40))
        content_h = self._inner.height if self._inner and self._inner.height > 1 \
            else self._natural
        height = min(max(content_h, dp(120)), avail_h)
        self._scroll.width = width
        self._scroll.height = height
        self._card.width = width
        self._card.height = content_h

    def close(self, *args):
        self.dismiss()


class DayCell(ButtonBehavior, BoxLayout, W.RoundedBG):
    """日历里的一天。"""

    def __init__(self, day=None, in_month=True, selected=False, is_today=False,
                 on_tap=None, **kwargs):
        super().__init__(size_hint=(1, 1), **kwargs)
        self.day = day
        self._in_month = in_month
        self.label = W.txt(str(day) if day else "", size=T.FONT_BODY,
                           halign="center", valign="middle")
        self.add_widget(self.label)
        color = T.PRIMARY if is_today and in_month else (
            T.TEXT if in_month else T.TEXT_HINT)
        self._base_color = color
        self.label.color = color
        self.init_bg(color=(0, 0, 0, 0), radius=T.RADIUS_SMALL)
        self._today = is_today
        self._selected = False
        self.set_selected(selected)

    def set_selected(self, flag):
        self._selected = bool(flag)
        if self._selected:
            self.set_bg_color(T.PRIMARY)
            self.label.color = (1, 1, 1, 1)
            self.label.bold = True
        else:
            if self._today:
                self.set_bg_color(T.PRIMARY_SOFT)
            else:
                self.set_bg_color((0, 0, 0, 0))
            self.label.color = self._base_color
            self.label.bold = False


class Stepper(BoxLayout):
    """数值步进器： [-] 09 [+] 。"""

    def __init__(self, value=0, step=1, low=0, high=59, fmt="%02d",
                 on_change=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(38))
        kwargs.setdefault("spacing", dp(6))
        super().__init__(**kwargs)
        self.step = step
        self.low = low
        self.high = high
        self.fmt = fmt
        self.value = value
        self._on_change = on_change
        minus = W.TextButton("-", color=T.PRIMARY, height_dp=34, width_dp=40,
                             size=T.FONT_TITLE, on_tap=lambda *_: self.bump(-1))
        plus = W.TextButton("+", color=T.PRIMARY, height_dp=34, width_dp=40,
                            size=T.FONT_TITLE, on_tap=lambda *_: self.bump(1))
        self.value_label = W.txt(self._text(), size=T.FONT_TITLE, color=T.TEXT,
                                 bold=True, halign="center")
        self.add_widget(minus)
        self.add_widget(self.value_label)
        self.add_widget(plus)

    def _text(self):
        return self.fmt % self.value

    def bump(self, direction):
        self.set_value(self.value + direction * self.step)

    def set_value(self, value):
        span = self.high - self.low + 1
        self.value = self.low + (int(value) - self.low) % span
        self.value_label.text = self._text()
        if self._on_change:
            self._on_change(self.value)


class DatePickerModal(BaseModal):
    """
    时间节点选择器：日历 + 时分步进 + 常用快捷项。
    on_pick(datetime | None) 回调，返回 None 表示清空时间节点。
    """

    WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]

    def __init__(self, initial=None, on_pick=None, title="选择时间节点", **kwargs):
        super().__init__(**kwargs)
        self.on_pick = on_pick
        self.title_text = title
        start = M.parse(initial) if initial else None
        now = datetime.now()
        self.selected = start or now.replace(second=0, microsecond=0)
        if not start:
            self.selected = now.replace(hour=18, minute=0, second=0, microsecond=0)
        self.view_year = self.selected.year
        self.view_month = self.selected.month
        self.hour = self.selected.hour
        self.minute = (self.selected.minute // 5) * 5
        self._build()
        self.show_card(self.content, natural_height=self._natural_height(),
                       max_width=430)

    # ------------------------------------------------------------- 构建
    def _natural_height(self):
        return 552

    def _build(self):
        self.content = BoxLayout(orientation="vertical", size_hint_y=None,
                                 spacing=dp(6), padding=[dp(14), dp(12), dp(14), dp(4)])
        self.content.bind(minimum_height=self.content.setter("height"))

        # 标题
        head = BoxLayout(size_hint_y=None, height=dp(30))
        head.add_widget(W.txt(self.title_text, size=T.FONT_TITLE, bold=True))
        head.add_widget(Widget())
        head.add_widget(W.TextButton("关闭", color=T.TEXT_HINT, height_dp=30,
                                     width_dp=56, size=T.FONT_SMALL,
                                     on_tap=lambda *_: self.dismiss()))
        self.content.add_widget(head)

        # 月份切换
        nav = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        prev_btn = W.TextButton("<", color=T.PRIMARY, height_dp=36, width_dp=44,
                                size=T.FONT_H1, on_tap=lambda *_: self.shift_month(-1))
        next_btn = W.TextButton(">", color=T.PRIMARY, height_dp=36, width_dp=44,
                                size=T.FONT_H1, on_tap=lambda *_: self.shift_month(1))
        self.month_label = W.txt("", size=T.FONT_TITLE, bold=True, halign="center")
        self.year_label = W.txt("", size=T.FONT_SMALL, color=T.TEXT_SUB, halign="center")
        mid = BoxLayout(orientation="vertical", spacing=0)
        mid.add_widget(self.month_label)
        mid.add_widget(self.year_label)
        nav.add_widget(prev_btn)
        nav.add_widget(mid)
        nav.add_widget(next_btn)
        self.content.add_widget(nav)

        # 星期表头
        week = GridLayout(cols=7, size_hint_y=None, height=dp(24))
        for name in self.WEEKDAYS:
            week.add_widget(W.txt(name, size=T.FONT_SMALL, color=T.TEXT_HINT,
                                  halign="center"))
        self.content.add_widget(week)

        # 日期网格
        self.grid = GridLayout(cols=7, size_hint_y=None, spacing=dp(3))
        self.content.add_widget(self.grid)

        # 快捷按钮
        quick = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        for label, days in (("今天", 0), ("明天", 1), ("后天", 2), ("下周一", "__mon"),
                            ("+1周", 7)):
            quick.add_widget(W.Chip(label, color=T.PRIMARY,
                                    on_tap=lambda w, d=days: self.quick_pick(d)))
        quick.add_widget(Widget())
        self.content.add_widget(quick)

        self.content.add_widget(W.Divider())

        # 时间
        time_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        time_row.add_widget(W.txt("时间", size=T.FONT_BODY, color=T.TEXT_SUB))
        self.hour_stepper = Stepper(self.hour, 1, 0, 23, on_change=self._set_hour)
        self.minute_stepper = Stepper(self.minute, 5, 0, 55, on_change=self._set_minute)
        time_row.add_widget(Widget())
        time_row.add_widget(self.hour_stepper)
        time_row.add_widget(W.txt(":", size=T.FONT_TITLE, color=T.TEXT_SUB,
                                  halign="center"))
        time_row.add_widget(self.minute_stepper)
        self.content.add_widget(time_row)

        # 目前选择
        self.summary = W.txt("", size=T.FONT_BODY, color=T.PRIMARY, bold=True)
        self.summary.size_hint_y = None
        self.summary.height = dp(22)
        self.content.add_widget(self.summary)

        # 底部按钮
        footer = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        footer.add_widget(W.SoftButton("清空时间节点", color=T.TEXT_SUB, bg=T.BG_SOFT,
                                       height_dp=42, on_tap=lambda *_: self._finish(None)))
        footer.add_widget(W.BaseButton("确定", height_dp=42,
                                       on_tap=lambda *_: self._finish(self.selected)))
        self.content.add_widget(footer)

        self.refresh()

    # ------------------------------------------------------------- 交互
    def shift_month(self, delta):
        month = self.view_month + delta
        year = self.view_year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        self.view_year, self.view_month = year, month
        self.refresh()

    def quick_pick(self, spec):
        today = date.today()
        if spec == "__mon":
            target = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        else:
            target = today + timedelta(days=int(spec))
        self.selected = datetime.combine(target, self.selected.time())
        self.view_year, self.view_month = target.year, target.month
        self.refresh()

    def _set_hour(self, value):
        self.hour = value
        self._sync_selected()

    def _set_minute(self, value):
        self.minute = value
        self._sync_selected()

    def _sync_selected(self):
        self.selected = self.selected.replace(hour=self.hour, minute=self.minute,
                                              second=0, microsecond=0)
        self._update_summary()

    def _update_summary(self):
        self.summary.text = ("已选：" + M.pretty_date_cn(
            self.selected.strftime(M.DT_FMT)))

    def refresh(self):
        self.month_label.text = f"{self.view_month} 月"
        self.year_label.text = f"{self.view_year} 年"
        self.grid.clear_widgets()
        first = date(self.view_year, self.view_month, 1)
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self.view_year, self.view_month)
        today = date.today()
        for week in weeks[:6]:
            for d in week:
                cell = DayCell(d.day, in_month=(d.month == self.view_month),
                               selected=(d == self.selected.date()),
                               is_today=(d == today))
                cell.bind(on_release=lambda w, day=d: self.pick_day(day))
                self.grid.add_widget(cell)
        self.grid.height = dp(6 * 36 + 5 * 3)
        for child in self.grid.children:
            child.height = dp(36)
        self.hour_stepper.set_value(self.selected.hour)
        self.minute_stepper.set_value((self.selected.minute // 5) * 5)
        self._update_summary()

    def pick_day(self, day):
        self.selected = datetime.combine(day, self.selected.time())
        self.refresh()

    def _finish(self, value):
        if self.on_pick:
            self.on_pick(value)
        self.dismiss()
