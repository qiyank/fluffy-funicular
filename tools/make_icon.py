# -*- coding: utf-8 -*-
"""
生成应用图标 assets/icon.png（512x512）。
纯标准库实现（zlib + struct），不依赖 Pillow，方便随时重新生成：
    python tools/make_icon.py
换配色/图形只需要改下面的参数。
"""
from __future__ import annotations

import math
import os
import struct
import zlib

SIZE = 512
TOP = (0x4C, 0x6B, 0xFF)        # 顶部渐变色
BOTTOM = (0x23, 0x31, 0xB8)     # 底部渐变色
ACCENT = (0x00, 0xD1, 0xC0)     # 右下角点缀光
STROKE = 23.0                   # 对勾线条半宽

# 对勾的三个折点（相对 512 的画布）
CHECK = [(146.0, 262.0), (218.0, 336.0), (372.0, 166.0)]


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def _seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    denom = vx * vx + vy * vy
    t = 0.0 if denom == 0 else _clamp((wx * vx + wy * vy) / denom)
    return math.hypot(wx - t * vx, wy - t * vy)


def build_pixels():
    rows = []
    for y in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            # 1) 垂直渐变 + 右下角青色光晕
            t = y / (SIZE - 1)
            r = TOP[0] + (BOTTOM[0] - TOP[0]) * t
            g = TOP[1] + (BOTTOM[1] - TOP[1]) * t
            b = TOP[2] + (BOTTOM[2] - TOP[2]) * t
            glow = _clamp(1.0 - math.hypot(x - SIZE * 0.82, y - SIZE * 0.86) / (SIZE * 0.62))
            glow = glow ** 2 * 0.85
            r += (ACCENT[0] - r) * glow
            g += (ACCENT[1] - g) * glow
            b += (ACCENT[2] - b) * glow

            # 2) 左上角提亮，让图标更有层次
            hi = _clamp(1.0 - math.hypot(x, y) / (SIZE * 0.95)) ** 2 * 0.16
            r += (255 - r) * hi
            g += (255 - g) * hi
            b += (255 - b) * hi

            # 3) 白色对勾（两条线段取最小距离，做 1.2px 抗锯齿）
            dist = min(_seg_dist(x + 0.5, y + 0.5, *CHECK[0], *CHECK[1]),
                       _seg_dist(x + 0.5, y + 0.5, *CHECK[1], *CHECK[2]))
            cover = _clamp(0.5 + (STROKE - dist) / 1.4)
            r += (255 - r) * cover
            g += (255 - g) * cover
            b += (255 - b) * cover

            row += bytes((int(_clamp(r / 255) * 255), int(_clamp(g / 255) * 255),
                          int(_clamp(b / 255) * 255), 255))
        rows.append(bytes(row))
    return rows


def write_png(path, rows, width, height):
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    return path


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "assets", "icon.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_png(out, build_pixels(), SIZE, SIZE)
    print("图标已生成:", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
