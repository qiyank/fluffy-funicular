# -*- coding: utf-8 -*-
"""
主题：配色、尺寸令牌与中文字体注册。

中文字体处理（很关键，Kivy 默认字体没有汉字，会显示成方框）：
1. 优先使用项目内 assets/fonts 下的思源黑体（打包进 APK，一定生效）；
2. 否则在系统字体目录里找可用中文字体（荣耀/华为 MagicOS 自带 HarmonyOS Sans，
   安卓通用机器一般有 DroidSansFallback / NotoSansCJK）；
3. 找到后注册成 Kivy 的默认字体名 'Roboto'，这样界面上所有 Label 自动使用中文字体。
"""
from __future__ import annotations

import os

from kivy.core.text import LabelBase
from kivy.metrics import dp, sp

# ------------------------------------------------------------------ 配色
BG            = (0.960, 0.965, 0.976, 1)   # 页面底色 #F5F6F9
BG_SOFT       = (0.925, 0.933, 0.949, 1)   # 分区底色
CARD          = (1.000, 1.000, 1.000, 1)   # 卡片
CARD_ALT      = (0.976, 0.980, 0.992, 1)   # 次级卡片
LINE          = (0.886, 0.898, 0.925, 1)   # 分割线

PRIMARY       = (0.235, 0.353, 0.937, 1)   # 主色 蓝紫 #3C5AEF
PRIMARY_DARK  = (0.161, 0.251, 0.741, 1)
PRIMARY_SOFT  = (0.902, 0.918, 1.000, 1)
ACCENT        = (0.000, 0.702, 0.647, 1)   # 青绿 #00B3A5
ACCENT_SOFT   = (0.878, 0.969, 0.957, 1)

TEXT          = (0.106, 0.129, 0.176, 1)   # 主要文字
TEXT_SUB      = (0.427, 0.463, 0.545, 1)   # 次要文字
TEXT_HINT     = (0.639, 0.671, 0.741, 1)   # 提示文字
ON_PRIMARY    = (1, 1, 1, 1)

DANGER        = (0.902, 0.278, 0.278, 1)   # 逾期 / 删除
DANGER_SOFT   = (0.996, 0.910, 0.910, 1)
WARN          = (0.949, 0.671, 0.086, 1)   # 即将到期
WARN_SOFT     = (0.996, 0.953, 0.847, 1)
OK            = (0.145, 0.678, 0.400, 1)   # 完成
OK_SOFT       = (0.894, 0.969, 0.925, 1)
MUTED         = (0.600, 0.635, 0.702, 1)   # 归档

#: 优先级 -> (主色, 浅底色, 文案)
PRIORITY_COLORS = {
    0: ((0.235, 0.635, 0.616, 1), (0.886, 0.965, 0.957, 1), "低"),
    1: ((0.949, 0.671, 0.086, 1), (0.996, 0.953, 0.847, 1), "中"),
    2: ((0.882, 0.263, 0.310, 1), (0.992, 0.902, 0.910, 1), "高"),
}

#: 状态 -> (主色, 浅底色, 文案)
STATUS_COLORS = {
    "todo":  ((0.427, 0.463, 0.545, 1), (0.925, 0.937, 0.957, 1), "待办"),
    "doing": (PRIMARY, PRIMARY_SOFT, "进行中"),
    "done":  (OK, OK_SOFT, "已完成"),
}

#: 分类色板（按分类名哈希取色，视觉上更好区分）
CATEGORY_PALETTE = [
    ((0.235, 0.353, 0.937, 1), (0.902, 0.918, 1.000, 1)),
    ((0.000, 0.702, 0.647, 1), (0.878, 0.969, 0.957, 1)),
    ((0.949, 0.671, 0.086, 1), (0.996, 0.953, 0.847, 1)),
    ((0.729, 0.361, 0.878, 1), (0.957, 0.906, 0.984, 1)),
    ((0.882, 0.263, 0.310, 1), (0.992, 0.902, 0.910, 1)),
    ((0.180, 0.545, 0.878, 1), (0.886, 0.941, 0.992, 1)),
]

# ------------------------------------------------------------------ 尺寸
RADIUS_CARD   = 18
RADIUS_SMALL  = 12
RADIUS_PILL   = 999
PAGE_PAD      = 14
GAP           = 10

NAV_HEIGHT    = 62   # 折叠（竖屏）时底部导航高度
RAIL_WIDTH    = 92   # 展开（宽屏）时左侧导航宽度

FONT_SMALL    = 11
FONT_BODY     = 13
FONT_TITLE    = 15
FONT_H1       = 21


def category_color(name: str):
    """同一个分类名总是拿到同一个颜色。"""
    name = name or "默认"
    idx = sum(ord(c) for c in name) % len(CATEGORY_PALETTE)
    return CATEGORY_PALETTE[idx]


# ------------------------------------------------------------------ 字体
FONT_NAME = "Roboto"          # 覆盖 Kivy 默认字体名，全局生效
_REGISTERED = {"path": None}


def _bundled_fonts() -> list[tuple[str, str]]:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = os.path.join(root, "assets", "fonts")
    return [
        (os.path.join(folder, "NotoSansSC-Regular.otf"),
         os.path.join(folder, "NotoSansSC-Bold.otf")),
        (os.path.join(folder, "NotoSansSC-Regular.ttf"),
         os.path.join(folder, "NotoSansSC-Bold.ttf")),
        # 安卓设备上常见的中文字体（Magicos / HarmonyOS / 通用 Android）
        ("/system/fonts/HarmonyOS_Sans_SC_Regular.ttf",
         "/system/fonts/HarmonyOS_Sans_SC_Bold.ttf"),
        ("/system/fonts/HarmonyOS_SansSC_Regular.ttf",
         "/system/fonts/HarmonyOS_SansSC_Bold.ttf"),
        ("/system/fonts/HarmonyOS_Sans_Regular.ttf",
         "/system/fonts/HarmonyOS_Sans_Bold.ttf"),
        ("/system/fonts/NotoSansCJK-Regular.ttc",
         "/system/fonts/NotoSansCJK-Bold.ttc"),
        ("/system/fonts/NotoSansSC-Regular.otf",
         "/system/fonts/NotoSansSC-Bold.otf"),
        ("/system/fonts/DroidSansFallback.ttf",
         "/system/fonts/DroidSansFallback.ttf"),
        ("/system/fonts/DroidSansChinese.ttf", None),
        # Windows / macOS 开发机上的中文字体
        ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
        ("C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simhei.ttf"),
        ("C:/Windows/Fonts/Deng.ttf", "C:/Windows/Fonts/Dengb.ttf"),
        ("/System/Library/Fonts/PingFang.ttc", None),
    ]


def register_cjk_font(verbose: bool = True) -> str | None:
    """注册中文字体为默认字体，返回实际使用的字体路径。"""
    if _REGISTERED["path"]:
        return _REGISTERED["path"]
    for regular, bold in _bundled_fonts():
        if not regular or not os.path.exists(regular):
            continue
        bold_path = bold if (bold and os.path.exists(bold)) else regular
        try:
            LabelBase.register(
                name=FONT_NAME,
                fn_regular=regular,
                fn_bold=bold_path,
                fn_italic=regular,
                fn_bolditalic=bold_path,
            )
        except Exception as exc:      # 字体损坏时继续尝试下一个
            if verbose:
                print(f"[font] 注册失败 {regular}: {exc}")
            continue
        _REGISTERED["path"] = regular
        if verbose:
            print(f"[font] 已启用中文字体: {regular}")
        return regular
    if verbose:
        print("[font] 未找到中文字体，界面文字可能显示为方框；"
              "请把 NotoSansSC-Regular.otf 放到 assets/fonts/ 目录。")
    return None


def font_path() -> str | None:
    return _REGISTERED["path"]
