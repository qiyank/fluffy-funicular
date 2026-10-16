# -*- coding: utf-8 -*-
"""
通用 UI 组件库：圆角卡片、按钮、胶囊、进度条、环形进度、迷你柱状图、任务卡片等。
全部基于 Kivy 原生 canvas 绘制，不依赖 kivymd 等第三方包，打包最省心。
"""
from __future__ import annotations

from kivy.animation import Animation
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from core import theme as T


# ------------------------------------------------------------------ 小工具
def shade(color, factor: float):
    """把颜色调亮(factor>1)或调暗(factor<1)。"""
    r, g, b, a = (list(color) + [1])[:4]
    return (min(1, r * factor), min(1, g * factor), min(1, b * factor), a)


def txt(text, size=T.FONT_BODY, color=T.TEXT, bold=False, halign="left",
        valign="middle", short=False, max_lines=1, **kwargs) -> Label:
    """创建统一风格的文字标签。short=True 时超长自动省略号。"""
    label = Label(
        text=text, font_size=sp(size), color=color, bold=bold,
        halign=halign, valign=valign, markup=True, **kwargs
    )
    if short:
        label.shorten = True
        label.shorten_from = "right"
        label.max_lines = max_lines
        label.bind(width=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        label.text_size = (label.width, None)
    return label


def text_glyph(text, size, color, anchor="lb"):
    """
    用 CoreLabel 生成一段文字纹理，返回 (texture, pos_size 计算函数)。
    必须在外层 `with canvas:` 上下文里使用返回的纹理绘制。
    """
    lab = CoreLabel(text=str(text), font_size=sp(size), color=color,
                    font_name=T.FONT_NAME)
    lab.refresh()
    tex = lab.texture
    if tex is None:
        return None

    def place(x, y):
        w, h = tex.size
        if anchor[0] == "c":
            x -= w / 2
        elif anchor[0] == "r":
            x -= w
        if anchor[1] == "t":
            y -= h
        elif anchor[1] == "m":
            y -= h / 2
        return (x, y), (w, h)

    return tex, place


def fill_label(container, label):
    """让 label 填满一个 FloatLayout 容器，并按 halign/valign 居中绘制。

    注意：FloatLayout 只会给带 pos_hint 的子组件定位，缺少 pos_hint 时
    子组件的 pos 保持 (0,0)，而画布坐标又是相对最近的 RelativeLayout
    （即 Screen），文字就会被画到屏幕左下角、看起来"消失"。
    所以这里必须显式指定 pos_hint，并把 text_size 绑定为自身尺寸，
    halign/valign 才会生效。
    """
    label.size_hint = (1, 1)
    label.pos_hint = {"x": 0, "y": 0}
    label.bind(size=lambda w, s: setattr(w, "text_size", s))
    container.add_widget(label)
    return label


def stack_top(widget, min_width=dp(24)):
    """把固定高度的小组件放到一行/一格的最上方（BoxLayout 默认是底部对齐）。"""
    widget.size_hint_x = None
    holder = BoxLayout(orientation="vertical", size_hint_x=None,
                       width=max(widget.width or 0, min_width))
    holder.add_widget(widget)
    holder.add_widget(Widget())

    def _sync(w, value):
        holder.width = max(value, min_width)

    widget.bind(width=_sync)
    _sync(widget, widget.width or min_width)
    return holder


# ------------------------------------------------------------------ 背景混入
class RoundedBG:
    """给 Widget/布局加上圆角背景、描边、左侧强调条、柔和阴影。"""

    def init_bg(self, color=T.CARD, radius=T.RADIUS_CARD, border=None,
                border_width=1, shadow=False, accent=None, accent_width=4):
        self._bg_color = list(color)
        self._radius_px = dp(radius)
        self._border = list(border) if border else None
        self._border_w = dp(border_width)
        self._has_shadow = shadow
        self._accent_color = list(accent) if accent else None
        self._accent_w = dp(accent_width)
        with self.canvas.before:
            if shadow:
                self._sh_col = Color(0.24, 0.28, 0.42, 0.10)
                self._sh_rect = RoundedRectangle(pos=self.pos, size=self.size,
                                                 radius=[self._radius_px])
            self._bg_col = Color(*self._bg_color)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size,
                                             radius=[self._radius_px])
            self._accent_rect = None
            if self._accent_color:
                self._accent_col = Color(*self._accent_color)
                self._accent_rect = RoundedRectangle(pos=self.pos, size=self.size,
                                                     radius=[self._accent_w / 2])
            self._line = None
            if self._border:
                self._border_col = Color(*self._border)
                self._line = Line(width=self._border_w)
        self.bind(pos=self.sync_bg, size=self.sync_bg)
        self.sync_bg()

    def sync_bg(self, *args):
        r = self._radius_px
        if getattr(self, "_has_shadow", False):
            self._sh_rect.pos = (self.x, self.y - dp(3))
            self._sh_rect.size = (self.width, self.height)
            self._sh_rect.radius = [r]
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = [r]
        if getattr(self, "_accent_rect", None) is not None:
            inset = dp(10)
            self._accent_rect.pos = (self.x + dp(5), self.y + inset)
            self._accent_rect.size = (self._accent_w, max(dp(6), self.height - inset * 2))
            self._accent_rect.radius = [self._accent_w / 2]
        if getattr(self, "_line", None) is not None:
            self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, r)

    def set_bg_color(self, color):
        self._bg_color = list(color)
        self._bg_col.rgba = self._bg_color

    def set_accent_color(self, color):
        if getattr(self, "_accent_rect", None) is not None:
            self._accent_col.rgba = list(color)


# ------------------------------------------------------------------ 基础卡片
class Panel(BoxLayout, RoundedBG):
    """圆角面板，最常用的容器。"""

    def __init__(self, color=T.CARD, radius=T.RADIUS_CARD, border=None,
                 shadow=False, accent=None, padding=None, spacing=0, **kwargs):
        super().__init__(spacing=dp(spacing), **kwargs)
        if padding is not None:
            if isinstance(padding, (int, float)):
                self.padding = [dp(padding)] * 4
            else:
                self.padding = [dp(v) for v in padding]
        self.init_bg(color=color, radius=radius, border=border, shadow=shadow,
                     accent=accent)


# ------------------------------------------------------------------ 胶囊标签
class Pill(BoxLayout, RoundedBG):
    """小圆角标签（优先级、状态、分类、时间节点都用它）。"""

    def __init__(self, text="", color=None, bg=None, size=T.FONT_SMALL,
                 bold=False, width_dp=None, height_dp=22, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        color = color or T.TEXT_SUB
        bg = bg or T.BG_SOFT
        self._auto_width = width_dp is None
        self.label = txt(text, size=size, color=color, bold=bold,
                         halign="center", valign="middle")
        self.add_widget(self.label)
        self.height = dp(height_dp)
        self.width = dp(width_dp) if width_dp else dp(44)
        self.label.width = self.width
        self.init_bg(color=bg, radius=T.RADIUS_SMALL)
        self.label.bind(texture_size=self._fit)
        self._fit()

    def _fit(self, *args):
        if self._auto_width:
            tex = self.label.texture_size
            self.width = (tex[0] if tex else dp(24)) + dp(18)

    def set_text(self, value):
        self.label.text = str(value)
        self._fit()


class Dot(Widget):
    """状态小圆点。"""

    def __init__(self, color=T.PRIMARY, size=dp(8), **kwargs):
        super().__init__(size_hint=(None, None), size=(size, size), **kwargs)
        with self.canvas:
            self._col = Color(*color)
            self._dot = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *args):
        self._dot.pos = self.pos
        self._dot.size = self.size

    def set_color(self, color):
        self._col.rgba = list(color)


# ------------------------------------------------------------------ 按钮
class BaseButton(ButtonBehavior, BoxLayout, RoundedBG):
    """带圆角背景的可点击按钮。"""

    def __init__(self, text="", fill=T.PRIMARY, text_color=T.ON_PRIMARY,
                 border=None, radius=T.RADIUS_SMALL, size=T.FONT_BODY,
                 bold=False, height_dp=38, width_dp=None, on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None if width_dp else 1, None)
        self.height = dp(height_dp)
        if width_dp:
            self.width = dp(width_dp)
        self._fill = list(fill)
        self._text_color = list(text_color)
        self._enabled = True
        self.label = txt(text, size=size, color=text_color, bold=bold,
                         halign="center", valign="middle", short=True)
        self.add_widget(self.label)
        self.init_bg(color=fill, radius=radius, border=border)
        self.bind(state=self._on_state)
        if on_tap:
            self.bind(on_release=lambda *_: on_tap(self))

    def _on_state(self, *args):
        if self._enabled:
            self.set_bg_color(shade(self._fill, 0.86) if self.state == "down"
                              else self._fill)

    def set_text(self, value):
        self.label.text = value

    def set_enabled(self, flag: bool):
        self._enabled = bool(flag)
        self.disabled = not flag
        self.set_bg_color(self._fill if flag else T.BG_SOFT)
        self.label.color = self._text_color if flag else T.TEXT_HINT

    def set_colors(self, fill=None, text_color=None):
        if fill is not None:
            self._fill = list(fill)
            self.set_bg_color(self._fill)
        if text_color is not None:
            self._text_color = list(text_color)
            self.label.color = self._text_color


class TextButton(BaseButton):
    """纯文字按钮。"""

    def __init__(self, text="", color=T.PRIMARY, **kwargs):
        kwargs.setdefault("height_dp", 32)
        super().__init__(text=text, fill=(0, 0, 0, 0), text_color=color, **kwargs)


class SoftButton(BaseButton):
    """浅底按钮（用于次要操作）。"""

    def __init__(self, text="", color=T.PRIMARY, bg=T.PRIMARY_SOFT, **kwargs):
        super().__init__(text=text, fill=bg, text_color=color, **kwargs)


class RoundButton(ButtonBehavior, FloatLayout, RoundedBG):
    """圆形按钮（一键完成、新增等）。"""

    def __init__(self, glyph="✓", fill=T.PRIMARY, text_color=T.ON_PRIMARY,
                 size_dp=42, font_size=T.FONT_TITLE, on_tap=None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self.size = (dp(size_dp), dp(size_dp))
        self._fill = list(fill)
        self.label = fill_label(self, txt(glyph, size=font_size, color=text_color,
                                          halign="center", valign="middle"))
        self.init_bg(color=fill, radius=int(size_dp / 2))
        self.bind(state=lambda *_: self.set_bg_color(
            shade(self._fill, 0.85) if self.state == "down" else self._fill))
        if on_tap:
            self.bind(on_release=lambda *_: on_tap(self))

    def set_colors(self, fill=None, text_color=None):
        if fill:
            self._fill = list(fill)
            self.set_bg_color(self._fill)
        if text_color:
            self.label.color = text_color


class Chip(ButtonBehavior, BoxLayout, RoundedBG):
    """可切换的筛选胶囊。"""

    def __init__(self, text="", selected=False, color=T.PRIMARY, on_tap=None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self.height = dp(32)
        self._color = list(color)
        self._selected = bool(selected)
        self.label = txt(text, size=T.FONT_SMALL + 1, halign="center", valign="middle")
        self.add_widget(self.label)
        self.width = dp(60)
        self.init_bg(color=T.CARD, radius=T.RADIUS_PILL, border=T.LINE)
        self.label.bind(texture_size=self._fit)
        self._apply()
        if on_tap:
            self.bind(on_release=lambda *_: on_tap(self))

    def _fit(self, *args):
        tex = self.label.texture_size
        self.width = (tex[0] if tex else dp(30)) + dp(26)

    def _apply(self):
        if self._selected:
            self.set_bg_color(self._color)
            self.label.color = (1, 1, 1, 1)
            self.label.bold = True
            self._border_col.rgba = [0, 0, 0, 0]
        else:
            self.set_bg_color(T.CARD)
            self.label.color = T.TEXT_SUB
            self.label.bold = False
            self._border_col.rgba = list(T.LINE)
        self._fit()

    def set_selected(self, flag):
        self._selected = bool(flag)
        self._apply()

    @property
    def selected(self):
        return self._selected


# ------------------------------------------------------------------ 进度
class BarProgress(Widget):
    """圆角进度条，支持数值动画。"""

    value = NumericProperty(0)

    def __init__(self, value=0, thickness=8, color=T.PRIMARY, track=T.BG_SOFT, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.thickness = dp(thickness)
        self.height = dp(thickness)
        with self.canvas:
            self._track_col = Color(*track)
            self._track = RoundedRectangle(pos=self.pos, size=self.size,
                                           radius=[self.thickness / 2])
            self._fill_col = Color(*color)
            self._fill = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[self.thickness / 2])
        self.bind(pos=self._sync, size=self._sync, value=self._sync)
        self.value = value
        self._sync()

    def _sync(self, *args):
        r = self.height / 2
        self._track.pos = self.pos
        self._track.size = self.size
        self._track.radius = [r]
        w = max(0.0, self.width * (float(self.value) / 100.0))
        self._fill.pos = self.pos
        self._fill.size = (w, self.height)
        self._fill.radius = [r]

    def set_value(self, value, animate=True):
        value = max(0, min(100, int(value)))
        if animate:
            Animation(value=value, d=0.28, t="out_quad").start(self)
        else:
            self.value = value

    def set_color(self, color):
        self._fill_col.rgba = list(color)


class RingStat(Widget):
    """环形进度（工作台统计）。"""

    value = NumericProperty(0)

    def __init__(self, value=0, color=T.PRIMARY, track=T.BG_SOFT, thickness=7, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        super().__init__(**kwargs)
        self.thickness = dp(thickness)
        with self.canvas:
            Color(*track)
            self._track = Line(width=self.thickness, cap="round")
            self._arc_col = Color(*color)
            self._arc = Line(width=self.thickness, cap="round")
        self.bind(pos=self._sync, size=self._sync, value=self._sync)
        self.value = value
        self._sync()

    def _sync(self, *args):
        # 注意：不要在这里使用 self.center —— Kivy 在 pos 属性的观察者里
        # center_x/center_y 的缓存可能尚未失效，会拿到过期坐标导致圆环画错位置。
        # 直接用 x/y/width/height 计算，保证拿到的是本次派发的最新值。
        radius = max(1.0, min(self.width, self.height) / 2 - self.thickness / 2)
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        self._track.circle = (cx, cy, radius, 0, 360)
        angle = max(1.0, 360.0 * (float(self.value) / 100.0))
        self._arc.circle = (cx, cy, radius, 90 - angle, 90)

    def set_value(self, value, animate=True):
        value = max(0, min(100, int(value)))
        if animate:
            Animation(value=value, d=0.45, t="out_quad").start(self)
        else:
            self.value = value

    def set_color(self, color):
        self._arc_col.rgba = list(color)


class DragSlider(Widget):
    """可拖动的进度滑杆（自绘，样式统一、触屏手感好）。"""

    value = NumericProperty(0)

    def __init__(self, value=0, step=5, thickness=8, color=T.PRIMARY,
                 height_dp=40, on_change=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.height = dp(height_dp)
        self.step = step
        self._grabbed = False
        self.on_change = on_change
        self.thickness = dp(thickness)
        knob = dp(22)
        with self.canvas:
            self._track_col = Color(*T.BG_SOFT)
            self._track = RoundedRectangle(pos=self.pos, size=self.size,
                                           radius=[self.thickness / 2])
            self._fill_col = Color(*color)
            self._fill = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[self.thickness / 2])
            self._ring_col = Color(*T.CARD)
            self._ring = Ellipse(pos=self.pos, size=(knob, knob))
            self._knob_col = Color(*color)
            self._knob = Ellipse(pos=self.pos, size=(knob - dp(5), knob - dp(5)))
        self.knob_size = knob
        self.bind(pos=self._sync, size=self._sync, value=self._sync)
        self.value = max(0, min(100, value))
        self._sync()

    def _sync(self, *args):
        r = self.thickness / 2
        # 同 RingStat：pos 观察者里 center_y 可能是过期缓存，直接用 x/y 计算
        cy = self.y + self.height / 2
        self._track.pos = (self.x, cy - r)
        self._track.size = (self.width, self.thickness)
        self._track.radius = [r]
        w = max(0.0, self.width * (float(self.value) / 100.0))
        self._fill.pos = (self.x, cy - r)
        self._fill.size = (w, self.thickness)
        self._fill.radius = [r]
        k = self.knob_size
        cx = self.x + w
        self._ring.pos = (cx - k / 2, cy - k / 2)
        self._ring.size = (k, k)
        inner = k - dp(5)
        self._knob.pos = (cx - inner / 2, cy - inner / 2)
        self._knob.size = (inner, inner)

    def set_value(self, value):
        self.value = max(0, min(100, int(value)))
        self._sync()
        if self.on_change:
            self.on_change(self.value)

    def _from_touch(self, x):
        raw = (x - self.x) / max(1.0, self.width) * 100.0
        value = max(0.0, min(100.0, raw))
        if self.step:
            value = round(value / self.step) * self.step
        value = int(max(0, min(100, value)))
        if value != self.value:
            self.value = value
            if self.on_change:
                self.on_change(value)

    def on_touch_down(self, touch):
        if self.disabled:
            return False
        if self.collide_point(*touch.pos):
            self._grabbed = True
            touch.grab(self)
            self._from_touch(touch.x)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._grabbed and touch.grab_current is self:
            self._from_touch(touch.x)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._grabbed and touch.grab_current is self:
            self._grabbed = False
            touch.ungrab(self)
            if self.on_change:
                self.on_change(self.value)
            return True
        return super().on_touch_up(touch)

    def set_color(self, color):
        self._fill_col.rgba = list(color)
        self._knob_col.rgba = list(color)


class MiniBars(Widget):
    """近 7 天完成数柱状图。"""

    def __init__(self, data=None, color=T.PRIMARY, height_dp=76, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.height = dp(height_dp)
        self.color = list(color)
        self._data = list(data or [])
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def set_data(self, data):
        self._data = list(data or [])
        self._redraw()

    def _redraw(self, *args):
        if self.width <= 1:
            return
        self.canvas.clear()
        data = self._data or [("", 0)]
        n = len(data)
        top_pad, bottom_pad = dp(18), dp(18)
        chart_h = max(dp(6), self.height - top_pad - bottom_pad)
        slot = self.width / n
        bar_w = min(dp(24), slot * 0.46)
        peak = max([d[1] for d in data] + [1])
        with self.canvas:
            for i, (label, count) in enumerate(data):
                cx = self.x + slot * (i + 0.5)
                h = chart_h * (count / peak) if count else dp(3)
                y = self.y + bottom_pad
                Color(*(self.color if count else T.BG_SOFT))
                RoundedRectangle(pos=(cx - bar_w / 2, y), size=(bar_w, h),
                                 radius=[bar_w / 2])
                glyph = text_glyph(label, T.FONT_SMALL, T.TEXT_HINT, anchor="cb")
                if glyph:
                    tex, place = glyph
                    pos, size = place(cx, self.y + dp(3))
                    Rectangle(texture=tex, size=size, pos=pos)
                if count:
                    Color(*self.color)
                    glyph = text_glyph(count, T.FONT_SMALL, self.color, anchor="cb")
                    if glyph:
                        tex, place = glyph
                        pos, size = place(cx, y + h + dp(3))
                        Rectangle(texture=tex, size=size, pos=pos)


class Divider(Widget):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", 1)
        super().__init__(**kwargs)
        with self.canvas:
            Color(*T.LINE)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class SectionTitle(BoxLayout):
    """小节标题：色点 + 标题 + 右侧统计。"""

    def __init__(self, title="", caption="", color=T.PRIMARY, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(30))
        super().__init__(spacing=dp(8), **kwargs)
        self.add_widget(Dot(color=color, size=dp(9)))
        self.add_widget(txt(title, size=T.FONT_TITLE, color=T.TEXT, bold=True))
        self.add_widget(Widget())
        self.caption_label = txt(caption, size=T.FONT_SMALL, color=T.TEXT_HINT,
                                 halign="right")
        self.caption_label.size_hint_x = None
        self.caption_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(2)))
        self.add_widget(self.caption_label)

    def set_caption(self, value):
        self.caption_label.text = value


# ------------------------------------------------------------------ 任务卡片
class TaskCard(ButtonBehavior, BoxLayout, RoundedBG):
    """
    待办任务卡片。
    点卡片 -> 打开详情；右侧圆钮 -> 一键完成；「记录进度」-> 快速填写进度。
    """

    def __init__(self, task, on_open=None, on_complete=None, on_progress=None,
                 title_lines=2, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.task = task
        self.on_open = on_open
        self.on_complete = on_complete
        self.on_progress = on_progress
        self.padding = [dp(16), dp(10), dp(14), dp(10)]
        self.spacing = dp(6)

        p_color, p_bg, p_text = T.PRIORITY_COLORS.get(task.priority, T.PRIORITY_COLORS[1])
        s_color, s_bg, s_text = T.STATUS_COLORS.get(task.status, T.STATUS_COLORS["todo"])
        cat_color, cat_bg = T.category_color(task.category)

        title_h = dp(20 * title_lines + 2)
        self.height = (dp(20) + title_h + dp(22) + dp(18) + dp(22) + dp(36)
                       + self.spacing * 4)

        # 第一行：标题 + 状态
        row1 = BoxLayout(size_hint_y=None, height=title_h, spacing=dp(8))
        self.title_label = txt(task.title or "（无标题）", size=14.5, bold=True,
                               valign="top", short=True, max_lines=title_lines)
        row1.add_widget(self.title_label)
        status_pill = Pill(s_text, color=s_color, bg=s_bg, bold=True, height_dp=22)
        row1.add_widget(stack_top(status_pill))
        self.add_widget(row1)

        # 第二行：分类 + 时间节点
        row2 = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
        row2.add_widget(Pill(task.category or "默认", color=cat_color, bg=cat_bg,
                             height_dp=21))
        if task.due_at:
            if task.is_done:
                d_color, d_bg = T.MUTED, T.BG_SOFT
            elif task.is_overdue:
                d_color, d_bg = T.DANGER, T.DANGER_SOFT
            elif task.is_today_due:
                d_color, d_bg = T.WARN, T.WARN_SOFT
            else:
                d_color, d_bg = T.PRIMARY, T.PRIMARY_SOFT
            row2.add_widget(Pill(f"⏱ {task.due_text}", color=d_color, bg=d_bg,
                                 height_dp=21))
        row2.add_widget(Widget())
        self.add_widget(row2)

        # 第三行：倒计时
        remain_color = T.DANGER if task.is_overdue else (
            T.OK if task.is_done else T.TEXT_SUB)
        self.remain_label = txt(task.remain_text, size=T.FONT_SMALL,
                                color=remain_color, short=True)
        self.remain_label.size_hint_y = None
        self.remain_label.height = dp(18)
        self.add_widget(self.remain_label)

        # 第四行：进度条
        row4 = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(8))
        self.bar = BarProgress(value=task.progress, thickness=8,
                               color=T.OK if task.is_done else T.PRIMARY)
        row4.add_widget(self.bar)
        self.percent = txt(task.progress_text, size=T.FONT_SMALL, color=T.TEXT_SUB,
                           halign="right", bold=True)
        self.percent.size_hint_x = None
        self.percent.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(2)))
        row4.add_widget(self.percent)
        self.add_widget(row4)

        # 第五行：操作
        row5 = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        row5.add_widget(Widget())
        self.progress_btn = SoftButton("记录进度", color=T.PRIMARY,
                                       bg=T.PRIMARY_SOFT, height_dp=34,
                                       width_dp=88, size=T.FONT_SMALL + 1,
                                       on_tap=lambda *_: self.on_progress and
                                       self.on_progress(self.task))
        row5.add_widget(self.progress_btn)
        if task.is_done:
            self.done_btn = RoundButton("↻", fill=T.PRIMARY_SOFT, text_color=T.PRIMARY,
                                        size_dp=34, on_tap=lambda *_: self.on_open and
                                        self.on_open(self.task))
        else:
            self.done_btn = RoundButton("✓", fill=T.OK, size_dp=34,
                                        on_tap=lambda *_: self.on_complete and
                                        self.on_complete(self.task))
        row5.add_widget(self.done_btn)
        self.add_widget(row5)

        accent = s_color if task.is_done else p_color
        self.init_bg(color=T.CARD_ALT if task.is_archived else T.CARD,
                     radius=T.RADIUS_CARD, shadow=True, border=T.LINE, accent=accent)
        self.bind(on_release=self._tapped)

    def _tapped(self, *args):
        if self.on_open:
            self.on_open(self.task)


class EmptyState(BoxLayout):
    """空状态占位。"""

    def __init__(self, icon="◌", title="这里还很空", caption="点右下角 + 新建第一条待办",
                 height_dp=190, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.height = dp(height_dp)
        self.add_widget(Widget())
        self.icon_label = txt(icon, size=34, color=T.TEXT_HINT, halign="center")
        self.icon_label.size_hint_y = None
        self.icon_label.height = dp(46)
        self.add_widget(self.icon_label)
        self.title_label = txt(title, size=T.FONT_TITLE, color=T.TEXT_SUB,
                               halign="center", bold=True)
        self.title_label.size_hint_y = None
        self.title_label.height = dp(28)
        self.add_widget(self.title_label)
        self.caption_label = txt(caption, size=T.FONT_SMALL, color=T.TEXT_HINT,
                                 halign="center")
        self.caption_label.size_hint_y = None
        self.caption_label.height = dp(22)
        self.add_widget(self.caption_label)
        self.add_widget(Widget())

    def set_text(self, title=None, caption=None, icon=None):
        if title is not None:
            self.title_label.text = title
        if caption is not None:
            self.caption_label.text = caption
        if icon is not None:
            self.icon_label.text = icon


class StatTile(Panel):
    """工作台统计卡：数字型 / 环形进度型。"""

    def __init__(self, title="", value="0", color=T.PRIMARY, caption="",
                 kind="text", ring_value=0, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        super().__init__(padding=12, spacing=2, shadow=True, border=T.LINE, **kwargs)
        self.height = dp(104) if kind == "ring" else dp(92)
        if kind == "ring":
            top = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(10))
            holder = FloatLayout(size_hint=(None, None), size=(dp(62), dp(62)))
            self.ring = RingStat(value=ring_value, color=color, thickness=6)
            self.ring.size = (dp(62), dp(62))
            self.ring.pos_hint = {"center_x": 0.5, "center_y": 0.5}
            holder.add_widget(self.ring)
            self.ring_value = fill_label(
                holder, txt(f"{int(ring_value)}%", size=T.FONT_BODY,
                            color=T.TEXT, bold=True, halign="center",
                            valign="middle"))
            top.add_widget(holder)
            right = BoxLayout(orientation="vertical", spacing=0)
            right.add_widget(Widget())
            right.add_widget(txt(title, size=T.FONT_SMALL, color=T.TEXT_SUB, short=True))
            self.value_label = txt(value, size=T.FONT_TITLE, color=color, bold=True)
            self.value_label.size_hint_y = None
            self.value_label.height = dp(22)
            right.add_widget(self.value_label)
            if caption:
                self.cap_label = txt(caption, size=T.FONT_SMALL, color=T.TEXT_HINT,
                                     short=True)
                self.cap_label.size_hint_y = None
                self.cap_label.height = dp(16)
                right.add_widget(self.cap_label)
            right.add_widget(Widget())
            top.add_widget(right)
            self.add_widget(top)
        else:
            self.add_widget(txt(title, size=T.FONT_SMALL, color=T.TEXT_SUB, short=True))
            self.value_label = txt(value, size=T.FONT_H1, color=color, bold=True)
            self.value_label.size_hint_y = None
            self.value_label.height = dp(32)
            self.add_widget(self.value_label)
            if caption:
                self.cap_label = txt(caption, size=T.FONT_SMALL, color=T.TEXT_HINT,
                                     short=True)
                self.cap_label.size_hint_y = None
                self.cap_label.height = dp(18)
                self.add_widget(self.cap_label)
            self.add_widget(Widget())

    def set_value(self, value, caption=None):
        self.value_label.text = str(value)
        if caption is not None and hasattr(self, "cap_label"):
            self.cap_label.text = caption


class TaskRow(ButtonBehavior, BoxLayout, RoundedBG):
    """紧凑任务行（工作台「今日与逾期」用）。"""

    def __init__(self, task, on_open=None, on_complete=None, height_dp=68, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.task = task
        self.height = dp(height_dp)
        self.padding = [dp(16), dp(8), dp(12), dp(8)]
        self.spacing = dp(10)
        p_color, _, _ = T.PRIORITY_COLORS.get(task.priority, T.PRIORITY_COLORS[1])
        s_color, _, _ = T.STATUS_COLORS.get(task.status, T.STATUS_COLORS["todo"])

        left = BoxLayout(orientation="vertical", spacing=0)
        left.add_widget(Widget())
        left.add_widget(txt(task.title or "（无标题）", size=13.5, bold=True, short=True))
        left.add_widget(txt(f"{task.category} · {task.remain_text}", size=T.FONT_SMALL,
                            color=T.DANGER if task.is_overdue else T.TEXT_SUB,
                            short=True))
        left.add_widget(Widget())
        self.add_widget(left)

        right = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(72),
                          spacing=dp(3))
        right.add_widget(Widget())
        right.add_widget(txt(task.progress_text, size=T.FONT_SMALL, bold=True,
                             color=T.OK if task.is_done else T.PRIMARY,
                             halign="right"))
        bar = BarProgress(value=task.progress, thickness=6,
                          color=T.OK if task.is_done else T.PRIMARY)
        right.add_widget(bar)
        right.add_widget(Widget())
        self.add_widget(right)

        if task.is_done:
            btn = RoundButton("√", fill=T.OK_SOFT, text_color=T.OK, size_dp=32,
                              on_tap=lambda *_: on_open and on_open(task))
        else:
            btn = RoundButton("√", fill=T.OK, size_dp=32,
                              on_tap=lambda *_: on_complete and on_complete(task))
        btn.size_hint_y = None
        holder = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(34))
        holder.add_widget(Widget())
        holder.add_widget(btn)
        holder.add_widget(Widget())
        self.add_widget(holder)

        self.init_bg(color=T.CARD, radius=T.RADIUS_SMALL, border=T.LINE,
                     accent=p_color if not task.is_done else s_color)
        self.bind(on_release=lambda *_: on_open and on_open(task))


class Toast(BoxLayout, RoundedBG):
    """轻提示（保存成功、已归档……）。"""

    def __init__(self, text="", **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("padding", [dp(18), dp(10)])
        super().__init__(**kwargs)
        self.label = txt(text, size=T.FONT_BODY, color=(1, 1, 1, 1), halign="center")
        self.add_widget(self.label)
        self.init_bg(color=(0.13, 0.15, 0.22, 0.94), radius=T.RADIUS_SMALL)
        self.opacity = 0
        self.label.bind(texture_size=self._fit)
        self._fit()

    def _fit(self, *args):
        ts = self.label.texture_size
        self.size = (ts[0] + dp(36), ts[1] + dp(20))
