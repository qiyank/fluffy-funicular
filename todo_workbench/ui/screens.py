# -*- coding: utf-8 -*-
"""四个页面：工作台 / 任务 / 搜索 / 归档后台。"""
from __future__ import annotations

from datetime import datetime

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from core import models as M
from core import responsive
from core import theme as T
from ui import widgets as W


# ------------------------------------------------------------------ 栅格
class CardGrid(BoxLayout):
    """响应式卡片栅格：根据窗口宽度自动 1 / 2 / 3 列。"""

    def __init__(self, gap=10, vgap=10, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         spacing=dp(vgap), **kwargs)
        self.gap = gap
        self.bind(minimum_height=self.setter("height"))

    def set_cards(self, cards):
        self.clear_widgets()
        if not cards:
            return
        cols = responsive.grid_columns()
        for i in range(0, len(cards), cols):
            chunk = cards[i:i + cols]
            row = BoxLayout(size_hint_y=None, spacing=dp(self.gap))
            row.height = max(c.height for c in chunk)
            for card in chunk:
                row.add_widget(card)
            for _ in range(cols - len(chunk)):
                row.add_widget(Widget())
            self.add_widget(row)


def chip_line(names, handler, color=T.PRIMARY, spacing=8):
    """横向可滚动的胶囊行；返回 (容器, 胶囊列表)。"""
    scroll = ScrollView(size_hint_y=None, height=dp(36), do_scroll_y=False,
                        bar_width=0, bar_color=(0, 0, 0, 0))
    box = BoxLayout(size_hint=(None, 1), spacing=dp(spacing))
    box.bind(minimum_width=box.setter("width"))
    holder = BoxLayout(size_hint_y=None, height=dp(36))
    holder.add_widget(box)
    holder.add_widget(Widget())
    chips = []
    for name in names:
        chip = W.Chip(name, color=color)
        chip.bind(on_release=lambda w, n=name: handler(n))
        box.add_widget(chip)
        chips.append(chip)
    scroll.add_widget(holder)
    return scroll, chips


# ------------------------------------------------------------------ 页面基类
class BaseScreen(Screen):
    """带滚动内容 + 右下角悬浮按钮的页面骨架，尺寸变化时自动重排。"""

    def __init__(self, controller, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self._cols = responsive.grid_columns()
        self.build()
        self.bind(size=self._on_size, pos=self._on_pos)

    # ---- 子类实现 ----
    def build(self):
        raise NotImplementedError

    def reload(self):
        pass

    # ---- 骨架 ----
    def make_scroll(self, bottom_pad=96):
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3),
                                 bar_color=(0.6, 0.65, 0.75, 0.5),
                                 bar_inactive_color=(0, 0, 0, 0))
        self.content = BoxLayout(orientation="vertical", size_hint_y=None,
                                 padding=[dp(T.PAGE_PAD), dp(12), dp(T.PAGE_PAD),
                                          dp(bottom_pad)],
                                 spacing=dp(12))
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        self.add_widget(self.scroll)
        return self.content

    def make_fab(self, text="+", on_tap=None):
        self.fab = W.RoundButton(text, fill=T.PRIMARY, size_dp=56, font_size=26,
                                 on_tap=lambda *_: on_tap and on_tap())
        self.add_widget(self.fab)
        self._place_fab()
        return self.fab

    def _place_fab(self, *args):
        if getattr(self, "fab", None) is not None:
            self.fab.pos = (self.right - self.fab.width - dp(18), self.y + dp(18))

    def _on_size(self, *args):
        self._place_fab()
        cols = responsive.grid_columns()
        if cols != self._cols:
            self._cols = cols
            self.reload()

    def _on_pos(self, *args):
        self._place_fab()


# ------------------------------------------------------------------ 工作台
class HomeScreen(BaseScreen):
    """工作台：今日概览 + 数据一览 + 近 7 天完成情况 + 今日与逾期清单。"""

    def build(self):
        self.make_scroll()
        c = self.content

        # 顶部问候
        self.header = W.Panel(orientation="horizontal", padding=[16, 14, 16, 14],
                              size_hint_y=None, height=dp(112), shadow=True,
                              border=T.LINE, accent=T.PRIMARY, spacing=dp(10))
        left = BoxLayout(orientation="vertical", spacing=0)
        self.greet_label = W.txt("你好", size=T.FONT_H1, bold=True)
        self.date_label = W.txt("", size=T.FONT_SMALL, color=T.TEXT_SUB)
        self.hint_label = W.txt("", size=T.FONT_SMALL, color=T.PRIMARY, bold=True)
        for w in (Widget(), self.greet_label, self.date_label, self.hint_label, Widget()):
            left.add_widget(w)
        self.header.add_widget(left)

        holder = FloatLayout(size_hint=(None, None), size=(dp(84), dp(84)))
        self.ring = W.RingStat(value=0, color=T.PRIMARY, thickness=8)
        self.ring.size = (dp(84), dp(84))
        self.ring.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.ring_text = W.fill_label(
            holder, W.txt("0%", size=T.FONT_TITLE, bold=True,
                          halign="center", valign="middle"))
        holder.add_widget(self.ring)
        self.header.add_widget(holder)
        c.add_widget(self.header)

        # 数据一览
        c.add_widget(W.SectionTitle("数据一览", color=T.PRIMARY))
        self.stats_box = BoxLayout(orientation="vertical", size_hint_y=None,
                                   spacing=dp(10))
        self.stats_box.bind(minimum_height=self.stats_box.setter("height"))
        c.add_widget(self.stats_box)

        # 近 7 天
        c.add_widget(W.SectionTitle("近 7 天完成情况", color=T.ACCENT))
        self.week_panel = W.Panel(orientation="horizontal", padding=[14, 12, 14, 12],
                                  size_hint_y=None, height=dp(118), shadow=True,
                                  border=T.LINE, spacing=dp(12))
        self.bars = W.MiniBars(data=[], height_dp=94)
        self.week_panel.add_widget(self.bars)
        avg_holder = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(76))
        ring_holder = FloatLayout(size_hint_y=None, height=dp(62))
        self.avg_ring = W.RingStat(value=0, color=T.ACCENT, thickness=7)
        self.avg_ring.size = (dp(62), dp(62))
        self.avg_ring.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        ring_holder.add_widget(self.avg_ring)
        self.avg_text = W.fill_label(
            ring_holder, W.txt("0%", size=T.FONT_SMALL + 1, bold=True,
                               halign="center", valign="middle"))
        cap = W.txt("平均进度", size=T.FONT_SMALL, color=T.TEXT_HINT, halign="center")
        cap.size_hint_y = None
        cap.height = dp(18)
        avg_holder.add_widget(Widget())
        avg_holder.add_widget(ring_holder)
        avg_holder.add_widget(cap)
        avg_holder.add_widget(Widget())
        self.week_panel.add_widget(avg_holder)
        c.add_widget(self.week_panel)

        # 今日与逾期
        self.due_title = W.SectionTitle("今日与逾期", color=T.WARN)
        c.add_widget(self.due_title)
        self.due_list = BoxLayout(orientation="vertical", size_hint_y=None,
                                  spacing=dp(8))
        self.due_list.bind(minimum_height=self.due_list.setter("height"))
        c.add_widget(self.due_list)
        self.due_empty = W.EmptyState(icon="○", title="没有临近的任务",
                                      caption="所有待办都还有充裕时间", height_dp=150)
        c.add_widget(self.due_empty)

        self.make_fab("+", on_tap=lambda: self.controller.open_editor())

    def reload(self):
        db = self.controller.db
        data = db.stats()
        now = datetime.now()
        hour = now.hour
        greet = ("早上好" if hour < 11 else "中午好" if hour < 14
                 else "下午好" if hour < 18 else "晚上好")
        self.greet_label.text = f"{greet}，今天也要加油"
        self.date_label.text = (f"{now.year}年{now.month}月{now.day}日 · "
                                f"{M.WEEKDAY_CN[now.weekday()]}")
        active = data["todo"] + data["doing"]
        self.hint_label.text = (f"待处理 {active} 条 · 今日到期 {data['today']} 条"
                                if active else "太棒了，当前没有待办任务")
        self.ring.set_value(data["done_rate"])
        self.ring_text.text = f"{data['done_rate']}%"
        self.avg_ring.set_value(data["avg_progress"])
        self.avg_text.text = f"{data['avg_progress']}%"
        self.bars.set_data(data["week"])

        # 数据卡片
        self.stats_box.clear_widgets()
        tiles = [
            W.StatTile("待办中", str(active), color=T.PRIMARY,
                       caption=f"进行中 {data['doing']} 条"),
            W.StatTile("今日 / 逾期", str(data["today"]), color=T.WARN,
                       caption=f"逾期 {data['overdue']} 条"),
            W.StatTile("已完成", str(data["done"]), color=T.OK,
                       caption=f"累计 {data['done_all']} 条"),
            W.StatTile("后台归档", str(data["archive"]), color=T.MUTED,
                       caption="可随时搜索调出"),
        ]
        cols = responsive.grid_columns(2, 4, 4)
        for i in range(0, len(tiles), cols):
            chunk = tiles[i:i + cols]
            row = BoxLayout(size_hint_y=None, spacing=dp(10))
            row.height = max(t.height for t in chunk)
            for tile in chunk:
                row.add_widget(tile)
            for _ in range(cols - len(chunk)):
                row.add_widget(Widget())
            self.stats_box.add_widget(row)

        # 今日与逾期
        self.due_list.clear_widgets()
        items = db.recent_due(5)
        for task in items:
            self.due_list.add_widget(W.TaskRow(
                task, on_open=self.controller.open_detail_task,
                on_complete=self.controller.quick_complete))
        self.due_empty.opacity = 0 if items else 1
        self.due_empty.height = 0 if items else dp(150)
        self.due_title.set_caption(f"{len(items)} 条" if items else "全部完成")


# ------------------------------------------------------------------ 任务列表
class TasksScreen(BaseScreen):
    """全部任务：多维度筛选 + 排序 + 响应式卡片。"""

    FILTERS = [("all", "全部"), ("todo", "待办"), ("doing", "进行中"),
               ("done", "已完成"), ("today", "今日截止"), ("overdue", "已逾期")]
    ORDERS = [("due", "按时间"), ("created", "按创建"), ("priority", "按优先级"),
              ("progress", "按进度")]

    def build(self):
        self.filter_key = "all"
        self.order_key = "due"
        self.make_scroll()
        c = self.content

        head = BoxLayout(size_hint_y=None, height=dp(38))
        head.add_widget(W.txt("全部待办", size=T.FONT_H1, bold=True))
        head.add_widget(Widget())
        self.count_label = W.txt("", size=T.FONT_SMALL, color=T.TEXT_SUB,
                                 halign="right")
        self.count_label.size_hint_x = None
        self.count_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(2)))
        head.add_widget(self.count_label)
        c.add_widget(head)

        f_map = {name: key for key, name in self.FILTERS}
        o_map = {name: key for key, name in self.ORDERS}
        self.filter_scroll, self.filter_chips = chip_line(
            [n for _, n in self.FILTERS],
            lambda name: self._pick(f_map[name], "filter"))
        self.order_scroll, self.order_chips = chip_line(
            [n for _, n in self.ORDERS],
            lambda name: self._pick(o_map[name], "order"), color=T.TEXT_SUB)
        c.add_widget(self.filter_scroll)
        c.add_widget(self.order_scroll)

        self.grid = CardGrid()
        c.add_widget(self.grid)
        self.empty = W.EmptyState(icon="○", title="还没有待办",
                                  caption="点右下角 + 新建第一条任务")
        c.add_widget(self.empty)
        self.make_fab("+", on_tap=lambda: self.controller.open_editor())
        self._sync_chips()

    def _pick(self, key, kind):
        if kind == "filter":
            self.filter_key = key
        else:
            self.order_key = key
        self._sync_chips()
        self.reload()

    def _sync_chips(self):
        for value, chip in zip([k for k, _ in self.FILTERS], self.filter_chips):
            chip.set_selected(value == self.filter_key)
        for value, chip in zip([k for k, _ in self.ORDERS], self.order_chips):
            chip.set_selected(value == self.order_key)

    def reload(self):
        tasks = self.controller.db.list_tasks(self.filter_key, self.order_key)
        self.count_label.text = f"共 {len(tasks)} 条"
        cards = [W.TaskCard(t, on_open=self.controller.open_detail_task,
                            on_complete=self.controller.quick_complete,
                            on_progress=self.controller.open_progress)
                 for t in tasks]
        self.grid.set_cards(cards)
        self.empty.opacity = 0 if tasks else 1
        self.empty.height = 0 if tasks else dp(190)


# ------------------------------------------------------------------ 搜索
class SearchScreen(BaseScreen):
    """关键词搜索：标题 / 备注 / 分类，可勾选包含后台归档。"""

    def build(self):
        self.include_archive = True
        self.order_key = "due"
        self._pending = None
        self.make_scroll(bottom_pad=40)
        c = self.content

        c.add_widget(W.txt("搜索任务", size=T.FONT_H1, bold=True,
                           size_hint_y=None, height=dp(34)))

        self.input_panel = W.Panel(orientation="vertical", color=T.CARD,
                                   radius=T.RADIUS_SMALL, border=T.LINE,
                                   size_hint_y=None, height=dp(48),
                                   padding=[dp(4), dp(2), dp(4), dp(2)])
        self.search_input = TextInput(
            hint_text="输入关键词，例如：周报 / 客户 / 报销",
            multiline=False, background_color=(0, 0, 0, 0), background_normal="",
            background_active="", foreground_color=T.TEXT,
            hint_text_color=T.TEXT_HINT, cursor_color=T.PRIMARY,
            font_size=sp(14), padding=[dp(10), dp(12), dp(10), dp(10)],
            write_tab=False)
        self.search_input.bind(text=lambda *_: self._on_text())
        self.search_input.bind(on_text_validate=lambda *_: self.reload())
        self.input_panel.add_widget(self.search_input)
        c.add_widget(self.input_panel)

        opts = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        self.archive_chip = W.Chip("包含后台归档", selected=True, color=T.ACCENT,
                                   on_tap=lambda *_: self._toggle_archive())
        opts.add_widget(self.archive_chip)
        self.order_chip = W.Chip("排序：时间", selected=True, color=T.TEXT_SUB,
                                 on_tap=lambda *_: self._toggle_order())
        opts.add_widget(self.order_chip)
        opts.add_widget(Widget())
        opts.add_widget(W.TextButton("清空", color=T.TEXT_HINT, height_dp=34,
                                     width_dp=56, size=T.FONT_SMALL,
                                     on_tap=lambda *_: self._clear()))
        c.add_widget(opts)

        self.result_label = W.txt("", size=T.FONT_SMALL, color=T.TEXT_SUB)
        self.result_label.size_hint_y = None
        self.result_label.height = dp(22)
        c.add_widget(self.result_label)

        self.grid = CardGrid()
        c.add_widget(self.grid)
        self.empty = W.EmptyState(icon="○", title="输入关键词开始搜索",
                                  caption="可搜索标题、备注、分类；后台归档的任务也能搜到")
        c.add_widget(self.empty)
        self.tip_panel = W.Panel(orientation="vertical", color=T.PRIMARY_SOFT,
                                 radius=T.RADIUS_SMALL, padding=12,
                                 size_hint_y=None, height=dp(84))
        tips = W.txt("小提示\n· 输入「逾期」「进行中」等状态词也能搜到\n"
                     "· 搜到的任务可直接查看进度、创建时间与完成时间",
                     size=T.FONT_SMALL, color=T.PRIMARY_DARK)
        tips.bind(width=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        self.tip_panel.add_widget(tips)
        c.add_widget(self.tip_panel)

    # ---- 交互 ----
    def _on_text(self):
        if self._pending:
            self._pending.cancel()
        self._pending = Clock.schedule_once(lambda *_: self.reload(), 0.25)

    def _toggle_archive(self):
        self.include_archive = not self.include_archive
        self.archive_chip.set_selected(self.include_archive)
        self.reload()

    def _toggle_order(self):
        self.order_key = "created" if self.order_key == "due" else "due"
        self.order_chip.set_text("排序：时间" if self.order_key == "due"
                                 else "排序：创建")
        self.reload()

    def _clear(self):
        self.search_input.text = ""
        self.reload()

    def reload(self):
        keyword = self.search_input.text.strip()
        db = self.controller.db
        if not keyword:
            self.grid.clear_widgets()
            self.result_label.text = ""
            self.empty.set_text("输入关键词开始搜索",
                                "可搜索标题、备注、分类；后台归档的任务也能搜到")
            self.empty.opacity = 1
            self.empty.height = dp(190)
            self.tip_panel.opacity = 1
            self.tip_panel.height = dp(84)
            return
        tasks = db.search(keyword, include_archive=self.include_archive,
                          order=self.order_key)
        archive_hit = sum(1 for t in tasks if t.is_archived)
        self.result_label.text = (f"找到 {len(tasks)} 条" +
                                  (f"（含后台归档 {archive_hit} 条）" if archive_hit else ""))
        cards = [W.TaskCard(t, on_open=self.controller.open_detail_task,
                            on_complete=self.controller.quick_complete,
                            on_progress=self.controller.open_progress)
                 for t in tasks]
        self.grid.set_cards(cards)
        self.empty.set_text("没有匹配的任务", "换个关键词试试，或勾选「包含后台归档」")
        self.empty.opacity = 0 if tasks else 1
        self.empty.height = 0 if tasks else dp(190)
        self.tip_panel.opacity = 0
        self.tip_panel.height = 0


# ------------------------------------------------------------------ 归档后台
class ArchiveScreen(BaseScreen):
    """后台归档：已完成任务存放处，可搜索调出、取回或删除。"""

    def build(self):
        self.make_scroll()
        c = self.content

        head = BoxLayout(size_hint_y=None, height=dp(38))
        head.add_widget(W.txt("后台归档", size=T.FONT_H1, bold=True))
        head.add_widget(Widget())
        self.count_label = W.txt("", size=T.FONT_SMALL, color=T.TEXT_SUB,
                                 halign="right")
        self.count_label.size_hint_x = None
        self.count_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(2)))
        head.add_widget(self.count_label)
        c.add_widget(head)

        note = W.Panel(orientation="vertical", color=T.PRIMARY_SOFT, padding=12,
                       size_hint_y=None, height=dp(66), radius=T.RADIUS_SMALL)
        note.add_widget(W.txt("完成任务后点「存入后台」，任务及其进度、创建时间、完成时间"
                              "都会被完整保存；在「搜索」页输入关键词随时调出。",
                              size=T.FONT_SMALL, color=T.PRIMARY_DARK,
                              short=True, max_lines=3))
        c.add_widget(note)

        self.section = W.SectionTitle("已归档任务", color=T.MUTED)
        c.add_widget(self.section)
        self.grid = CardGrid()
        c.add_widget(self.grid)
        self.empty = W.EmptyState(icon="○", title="后台还没有任务",
                                  caption="在任务详情里点「存入后台」即可归档")
        c.add_widget(self.empty)
        self.clear_btn = W.SoftButton("清空后台归档", color=T.DANGER, bg=T.DANGER_SOFT,
                                      height_dp=44, size_hint_y=None,
                                      on_tap=lambda *_: self._clear_all())
        c.add_widget(self.clear_btn)

    def _clear_all(self):
        from ui.sheets import ConfirmModal
        tasks = self.controller.db.list_tasks("archive")
        if not tasks:
            self.controller.toast("后台没有可清理的任务")
            return
        total = len(tasks)

        def _do():
            for task in self.controller.db.list_tasks("archive"):
                self.controller.db.delete_task(task.id)
            self.controller.toast(f"已清空 {total} 条归档任务")
            self.controller.refresh()

        ConfirmModal(title="清空后台归档？",
                     message=f"将永久删除 {total} 条归档任务及其进度记录，无法恢复。",
                     confirm_text="确认清空", on_confirm=_do).open()

    def reload(self):
        tasks = self.controller.db.list_tasks("archive", "created")
        self.count_label.text = f"共 {len(tasks)} 条"
        cards = [W.TaskCard(t, on_open=self.controller.open_detail_task,
                            on_complete=self.controller.quick_complete,
                            on_progress=self.controller.open_progress)
                 for t in tasks]
        self.grid.set_cards(cards)
        self.empty.opacity = 0 if tasks else 1
        self.empty.height = 0 if tasks else dp(190)
        self.section.set_caption(f"{len(tasks)} 条")
        self.clear_btn.opacity = 1 if tasks else 0
        self.clear_btn.height = dp(44) if tasks else 0
