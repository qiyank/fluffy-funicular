# -*- coding: utf-8 -*-
"""
响应式布局工具：折叠屏/平板适配。

荣耀 Magic V6 外屏约 4xx dp 宽（折叠），内屏展开后约 7xx~9xx dp 宽。
本模块把屏幕宽度换算成 dp，并给出断点判断：
    - is_compact()  : 折叠态（窄屏，单列 + 底部导航）
    - is_medium()   : 展开态（双列 + 左侧导航）
    - is_expanded() : 大屏/横屏（双列或三列）
所有界面通过监听 Window.size 变化重新排布，因此展开/折叠时可以无缝切换。
"""
from __future__ import annotations

from kivy.core.window import Window
from kivy.metrics import Metrics

#: dp 断点
BP_MEDIUM = 560     # >= 该宽度视为「展开态」
BP_EXPANDED = 900   # >= 该宽度视为「大屏平铺态」


def width_dp() -> float:
    """当前窗口宽度（dp）。"""
    density = Metrics.density or 1.0
    return Window.width / density


def height_dp() -> float:
    density = Metrics.density or 1.0
    return Window.height / density


def is_landscape() -> bool:
    return Window.width >= Window.height


def is_compact() -> bool:
    """折叠态：窄屏。"""
    return width_dp() < BP_MEDIUM


def is_medium() -> bool:
    """展开态：可以放两栏。"""
    return BP_MEDIUM <= width_dp() < BP_EXPANDED


def is_expanded() -> bool:
    """大屏：可以放三栏。"""
    return width_dp() >= BP_EXPANDED


def is_unfolded() -> bool:
    """是否处于「展开/大屏」状态——用于切换侧边导航。"""
    return width_dp() >= BP_MEDIUM


def grid_columns(compact: int = 1, medium: int = 2, expanded: int = 3) -> int:
    """按当前宽度返回卡片列数。"""
    if is_expanded():
        return expanded
    if is_medium():
        return medium
    return compact


def max_content_width() -> float:
    """内容区最大宽度，防止在大屏上被拉得过宽。"""
    w = width_dp()
    if w >= 1280:
        return 1180.0
    return w
