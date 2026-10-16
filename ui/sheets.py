# -*- coding: utf-8 -*-
"""弹层：新建/编辑任务、任务详情、快捷填写进度、确认对话框。"""
from __future__ import annotations

from datetime import datetime, timedelta

from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from core import models as M
from core import theme as T
from ui import widgets as W
from ui.pickers import BaseModal, DatePickerModal


# ------------------------------------------------------------------ 表单零件
def caption(text, color=T.TEXT_SUB):
    label = W.txt(text, size=T.FONT_SMALL, color=color, bold=True)
    label.size_hint_y = None
    label.height = dp(20)
    return label


def make_input(hint="", text="", multiline=False, height_dp=44, size=T.FONT_BODY):
    """带圆角浅底的输入框。"""
    box = W.Panel(orientation="vertical", color=T.CARD_ALT, radius=T.RADIUS_SMALL,
                  border=T.LINE, size_hint_y=None, height=dp(height_dp),
                  padding=[dp(4), dp(2), dp(4), dp(2)])
    ti = TextInput(
        text=text, hint_text=hint, multiline=multiline,
        background_color=(0, 0, 0, 0), background_normal="", background_active="",
        foreground_color=T.TEXT, hint_text_color=T.TEXT_HINT,
        cursor_color=T.PRIMARY, cursor_width=dp(1.6), font_size=sp(size),
        padding=[dp(10), dp(10), dp(10), dp(10)], write_tab=False,
        selection_color=(0.235, 0.353, 0.937, 0.35),
    )
    box.add_widget(ti)
    return box, ti


def info_row(name, value, value_color=T.TEXT):
    row = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(6))
    name_label = W.txt(name, size=T.FONT_SMALL, color=T.TEXT_HINT)
    name_label.size_hint_x = None
    name_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(4)))
    row.add_widget(name_label)
    row.add_widget(W.txt(value, size=T.FONT_SMALL + 1, color=value_color, short=True))
    return row


def set_info_value(row, value, value_color=None):
    """更新 info_row 的右侧文本。"""
    label = row.children[0]
    label.text = value
    if value_color:
        label.color = value_color


def chip_row(items, on_tap, spacing=6, color=T.PRIMARY):
    """一行可横向滚动的小胶囊。"""
    scroll = ScrollView(size_hint_y=None, height=dp(36), do_scroll_y=False,
                        bar_width=0, bar_color=(0, 0, 0, 0))
    box = BoxLayout(size_hint=(None, 1), spacing=dp(spacing))
    box.bind(minimum_width=box.setter("width"))
    for label in items:
        box.add_widget(W.Chip(label, color=color,
                              on_tap=lambda w, name=label: on_tap(name)))
    holder = BoxLayout(size_hint_y=None, height=dp(36))
    holder.add_widget(box)
    holder.add_widget(Widget())
    scroll.add_widget(holder)
    return scroll


# ------------------------------------------------------------------ 新建 / 编辑
class TaskEditorModal(BaseModal):
    """新建或编辑一条待办。on_save(data, task) 由外部写入数据库。"""

    QUICK_DUE = [("今天 18:00", "today18"), ("明天 09:00", "tomorrow9"),
                 ("3 天后", "d3"), ("下周一 09:00", "mon9")]

    def __init__(self, task=None, categories=None, on_save=None,
                 default_category="默认", **kwargs):
        super().__init__(**kwargs)
        self.task = task
        self.on_save = on_save
        self.categories = list(categories or [])
        self._due = task.due_at if task else ""
        self._priority = task.priority if task else 1
        self._category = (task.category if task else default_category) or "默认"
        self._progress = task.progress if task else 0
        self._build()
        self.show_card(self.content, natural_height=680, max_width=520)

    # ------------------------------------------------------------- 构建
    def _build(self):
        self.content = BoxLayout(orientation="vertical", size_hint_y=None,
                                 spacing=dp(8), padding=[dp(16), dp(14), dp(16), dp(14)])
        self.content.bind(minimum_height=self.content.setter("height"))

        # 标题栏
        head = BoxLayout(size_hint_y=None, height=dp(30))
        head.add_widget(W.txt("编辑待办" if self.task else "新建待办",
                              size=T.FONT_H1, bold=True))
        head.add_widget(Widget())
        head.add_widget(W.TextButton("关闭", color=T.TEXT_HINT, height_dp=30,
                                     width_dp=56, size=T.FONT_SMALL,
                                     on_tap=lambda *_: self.dismiss()))
        self.content.add_widget(head)

        # 待办标题
        self.content.add_widget(caption("待办内容 *"))
        box, self.title_input = make_input("例如：完成季度复盘材料")
        if self.task:
            self.title_input.text = self.task.title
        self.content.add_widget(box)
        self.error_label = W.txt("", size=T.FONT_SMALL, color=T.DANGER)
        self.error_label.size_hint_y = None
        self.error_label.height = dp(16)
        self.content.add_widget(self.error_label)

        # 备注
        self.content.add_widget(caption("备注（选填）"))
        box, self.detail_input = make_input("补充说明、链接、验收标准……", multiline=True,
                                            height_dp=76)
        if self.task:
            self.detail_input.text = self.task.detail
        self.content.add_widget(box)

        # 分类
        self.content.add_widget(caption("分类"))
        box, self.category_input = make_input("工作 / 生活 / 学习……")
        self.category_input.text = self._category
        self.category_input.bind(focus=self._on_category_focus)
        self.content.add_widget(box)
        cats = [c for c in self.categories if c] or ["工作", "生活", "学习"]
        self.content.add_widget(chip_row(cats[:8], self._pick_category))

        # 优先级
        self.content.add_widget(caption("优先级"))
        pr_box = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        self.priority_chips = {}
        for value in (2, 1, 0):
            color, soft, name = T.PRIORITY_COLORS[value]
            chip = W.Chip(f"{name}优先级", selected=(value == self._priority),
                          color=color,
                          on_tap=lambda w, v=value: self._pick_priority(v))
            self.priority_chips[value] = chip
            pr_box.add_widget(chip)
        pr_box.add_widget(Widget())
        self.content.add_widget(pr_box)

        # 时间节点
        self.content.add_widget(caption("时间节点（截止时间）"))
        due_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.due_label = W.txt("未设置", size=T.FONT_BODY, color=T.TEXT, short=True)
        due_panel = W.Panel(orientation="vertical", color=T.CARD_ALT,
                            radius=T.RADIUS_SMALL, border=T.LINE, padding=[dp(10), 0])
        due_panel.add_widget(self.due_label)
        due_row.add_widget(due_panel)
        due_row.add_widget(W.BaseButton("选择时间", height_dp=44, width_dp=92,
                                        size=T.FONT_SMALL + 1,
                                        on_tap=lambda *_: self._open_picker()))
        self.content.add_widget(due_row)
        self.content.add_widget(chip_row([q[0] for q in self.QUICK_DUE],
                                         self._quick_due, color=T.ACCENT))

        # 当前进度
        self.content.add_widget(caption("当前进度"))
        prog_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.progress_slider = W.DragSlider(value=self._progress, step=5,
                                            on_change=self._on_progress)
        prog_row.add_widget(self.progress_slider)
        self.progress_label = W.txt(f"{self._progress}%", size=T.FONT_TITLE,
                                    color=T.PRIMARY, bold=True, halign="right")
        self.progress_label.size_hint_x = None
        self.progress_label.bind(texture_size=lambda w, s: setattr(
            w, "width", s[0] + dp(4)))
        prog_row.add_widget(self.progress_label)
        self.content.add_widget(prog_row)
        self.content.add_widget(chip_row(["0%", "25%", "50%", "75%", "100%"],
                                         self._quick_progress, color=T.ACCENT))

        self.content.add_widget(W.Divider())

        # 底部
        footer = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        footer.add_widget(W.SoftButton("取消", color=T.TEXT_SUB, bg=T.BG_SOFT,
                                       height_dp=46, on_tap=lambda *_: self.dismiss()))
        footer.add_widget(W.BaseButton("保存待办", height_dp=46,
                                       on_tap=lambda *_: self._save()))
        self.content.add_widget(footer)

        self._refresh_due()

    # ------------------------------------------------------------- 交互
    def _on_category_focus(self, instance, focused):
        if not focused:
            self._category = instance.text.strip() or "默认"

    def _pick_category(self, name):
        self.category_input.text = name
        self._category = name

    def _pick_priority(self, value):
        self._priority = value
        for key, chip in self.priority_chips.items():
            chip.set_selected(key == value)

    def _open_picker(self):
        DatePickerModal(initial=self._due or M.to_str(datetime.now() +
                                                      timedelta(hours=2)),
                        on_pick=self._set_due).open()

    def _set_due(self, value):
        self._due = M.to_str(value) if value else ""
        self._refresh_due()

    def _quick_due(self, label):
        now = datetime.now()
        mapping = {
            "今天 18:00": now.replace(hour=18, minute=0, second=0, microsecond=0),
            "明天 09:00": (now + timedelta(days=1)).replace(hour=9, minute=0,
                                                            second=0, microsecond=0),
            "3 天后": (now + timedelta(days=3)).replace(hour=18, minute=0,
                                                        second=0, microsecond=0),
            "下周一 09:00": (now + timedelta(days=(7 - now.weekday()) % 7 or 7)
                             ).replace(hour=9, minute=0, second=0, microsecond=0),
        }
        self._due = M.to_str(mapping[label])
        self._refresh_due()

    def _refresh_due(self):
        if self._due:
            task = M.Task(due_at=self._due)
            self.due_label.text = f"{M.pretty_date_cn(self._due)}   （{task.remain_text}）"
            self.due_label.color = T.TEXT
        else:
            self.due_label.text = "未设置时间节点"
            self.due_label.color = T.TEXT_HINT

    def _on_progress(self, value):
        self._progress = int(value)
        self.progress_label.text = f"{self._progress}%"

    def _quick_progress(self, label):
        value = int(label.rstrip("%"))
        self.progress_slider.set_value(value)
        self._on_progress(value)

    def _save(self):
        title = self.title_input.text.strip()
        if not title:
            self.error_label.text = "请先填写待办内容"
            return
        category = self.category_input.text.strip() or self._category or "默认"
        data = {
            "title": title,
            "detail": self.detail_input.text.strip(),
            "category": category,
            "priority": self._priority,
            "due_at": self._due,
            "progress": self._progress,
        }
        if self.on_save:
            self.on_save(data, self.task)
        self.dismiss()


# ------------------------------------------------------------------ 快捷进度
class ProgressModal(BaseModal):
    """在卡片上点「记录进度」时弹出的轻量弹层。"""

    def __init__(self, task, on_submit=None, **kwargs):
        super().__init__(**kwargs)
        self.task = task
        self.on_submit = on_submit
        self._value = task.progress
        self.content = BoxLayout(orientation="vertical", size_hint_y=None,
                                 spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(14)])
        self.content.bind(minimum_height=self.content.setter("height"))

        self.content.add_widget(W.txt(task.title, size=T.FONT_TITLE, bold=True,
                                      short=True, max_lines=2, size_hint_y=None,
                                      height=dp(42)))
        info = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        info.add_widget(info_row("时间节点", task.due_text))
        self.content.add_widget(info)

        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.slider = W.DragSlider(value=task.progress, step=5,
                                   on_change=self._on_change)
        row.add_widget(self.slider)
        self.value_label = W.txt(f"{task.progress}%", size=T.FONT_H1, color=T.PRIMARY,
                                 bold=True, halign="right")
        self.value_label.size_hint_x = None
        self.value_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(4)))
        row.add_widget(self.value_label)
        self.content.add_widget(row)

        self.content.add_widget(chip_row(["-10%", "+10%", "+25%", "+50%", "100%"],
                                         self._quick, color=T.ACCENT))
        self.content.add_widget(caption("这次进展说明（选填）"))
        box, self.note_input = make_input("例如：已完成资料收集", height_dp=44)
        self.content.add_widget(box)

        footer = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        footer.add_widget(W.SoftButton("取消", color=T.TEXT_SUB, bg=T.BG_SOFT,
                                       height_dp=46, on_tap=lambda *_: self.dismiss()))
        footer.add_widget(W.BaseButton("保存进度", height_dp=46, fill=T.ACCENT,
                                       on_tap=lambda *_: self._submit()))
        self.content.add_widget(footer)
        self.show_card(self.content, natural_height=430, max_width=460)

    def _on_change(self, value):
        self._value = int(value)
        self.value_label.text = f"{self._value}%"

    def _quick(self, label):
        if label == "100%":
            value = 100
        else:
            value = max(0, min(100, self._value + int(label.rstrip("%"))))
        self.slider.set_value(value)
        self._on_change(value)

    def _submit(self):
        if self.on_submit:
            self.on_submit(self.task, self._value, self.note_input.text.strip())
        self.dismiss()


# ------------------------------------------------------------------ 详情
class TaskDetailModal(BaseModal):
    """任务详情：完整信息 + 进度填写 + 完成/归档/编辑/删除 + 进度流水。"""

    def __init__(self, task, controller, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller          # 提供 db / 刷新 / 打开编辑器等能力
        self.task = task
        self._value = task.progress
        self._build()
        self.show_card(self.content, natural_height=760, max_width=560)

    # ------------------------------------------------------------- 构建
    def _build(self):
        task = self.task
        self.content = BoxLayout(orientation="vertical", size_hint_y=None,
                                 spacing=dp(9), padding=[dp(16), dp(14), dp(16), dp(16)])
        self.content.bind(minimum_height=self.content.setter("height"))

        # 头部
        head = BoxLayout(size_hint_y=None, height=dp(30))
        head.add_widget(W.txt("任务详情", size=T.FONT_TITLE, color=T.TEXT_SUB, bold=True))
        head.add_widget(Widget())
        head.add_widget(W.TextButton("关闭", color=T.TEXT_HINT, height_dp=30,
                                     width_dp=56, size=T.FONT_SMALL,
                                     on_tap=lambda *_: self.dismiss()))
        self.content.add_widget(head)

        self.title_label = W.txt(task.title, size=T.FONT_H1, bold=True,
                                 halign="left", valign="middle")
        self.title_label.size_hint_y = None
        self.title_label.height = dp(34)
        self.content.add_widget(self.title_label)

        # 状态行
        s_color, s_bg, s_text = T.STATUS_COLORS.get(task.status, T.STATUS_COLORS["todo"])
        p_color, p_bg, p_text = T.PRIORITY_COLORS.get(task.priority, T.PRIORITY_COLORS[1])
        c_color, c_bg = T.category_color(task.category)
        tags = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        tags.add_widget(W.Pill(s_text, color=s_color, bg=s_bg, bold=True, height_dp=22))
        tags.add_widget(W.Pill(f"{p_text}优先级", color=p_color, bg=p_bg,
                               height_dp=22))
        tags.add_widget(W.Pill(task.category or "默认", color=c_color, bg=c_bg,
                               height_dp=22))
        tags.add_widget(Widget())
        self.content.add_widget(tags)

        if task.detail:
            detail_panel = W.Panel(orientation="vertical", color=T.CARD_ALT,
                                   radius=T.RADIUS_SMALL, padding=10, size_hint_y=None)
            detail = W.txt(task.detail, size=T.FONT_BODY, color=T.TEXT_SUB)
            detail.size_hint_y = None
            detail.bind(width=lambda w, *_: setattr(w, "text_size", (w.width, None)))
            detail.bind(texture_size=lambda w, s: setattr(w, "height", s[1] + dp(4)))
            detail_panel.bind(minimum_height=detail_panel.setter("height"))
            detail_panel.add_widget(detail)
            self.content.add_widget(detail_panel)

        # 时间信息
        info = W.Panel(orientation="vertical", color=T.CARD_ALT, radius=T.RADIUS_SMALL,
                       padding=[12, 8, 12, 8], spacing=2, size_hint_y=None,
                       height=dp(140))
        self.row_due = info_row("时间节点", task.due_text_cn,
                                T.DANGER if task.is_overdue else T.TEXT)
        self.row_remain = info_row("剩余时间", task.remain_text)
        self.row_created = info_row("创建时间", task.created_text)
        self.row_updated = info_row("最近更新", task.updated_text)
        self.row_completed = info_row("完成时间", task.completed_text,
                                      T.OK if task.completed_at else T.TEXT_HINT)
        for row in (self.row_due, self.row_remain, self.row_created,
                    self.row_updated, self.row_completed):
            info.add_widget(row)
        self.content.add_widget(info)

        # 进度
        self.content.add_widget(W.SectionTitle("进度填写", color=T.PRIMARY))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.slider = W.DragSlider(value=task.progress, step=5,
                                   on_change=self._on_slider)
        row.add_widget(self.slider)
        self.value_label = W.txt(f"{task.progress}%", size=T.FONT_H1,
                                 color=T.OK if task.is_done else T.PRIMARY,
                                 bold=True, halign="right")
        self.value_label.size_hint_x = None
        self.value_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(4)))
        row.add_widget(self.value_label)
        self.content.add_widget(row)
        self.content.add_widget(chip_row(["-10%", "+10%", "+25%", "50%", "100%"],
                                         self._quick_progress, color=T.ACCENT))
        box, self.note_input = make_input("填写这次进展的说明（选填）", height_dp=44)
        self.content.add_widget(box)
        self.content.add_widget(W.BaseButton("保存进度并记录", height_dp=44,
                                             fill=T.ACCENT,
                                             on_tap=lambda *_: self._save_progress()))

        # 操作
        self.content.add_widget(W.SectionTitle("任务操作", color=T.PRIMARY))
        ops = GridLayout(cols=2, size_hint_y=None, height=dp(88), spacing=dp(8))
        if task.is_done:
            ops.add_widget(W.SoftButton("重新打开", color=T.PRIMARY, bg=T.PRIMARY_SOFT,
                                        height_dp=40, on_tap=lambda *_: self._reopen()))
        else:
            ops.add_widget(W.BaseButton("√ 标记完成", height_dp=40, fill=T.OK,
                                        on_tap=lambda *_: self._complete()))
        ops.add_widget(W.SoftButton("编辑内容", color=T.PRIMARY, bg=T.PRIMARY_SOFT,
                                    height_dp=40, on_tap=lambda *_: self._edit()))
        if task.is_archived:
            ops.add_widget(W.SoftButton("从后台取回", color=T.PRIMARY,
                                        bg=T.PRIMARY_SOFT, height_dp=40,
                                        on_tap=lambda *_: self._restore()))
        else:
            ops.add_widget(W.SoftButton("存入后台", color=T.TEXT_SUB, bg=T.BG_SOFT,
                                        height_dp=40, on_tap=lambda *_: self._archive()))
        ops.add_widget(W.SoftButton("删除任务", color=T.DANGER, bg=T.DANGER_SOFT,
                                    height_dp=40, on_tap=lambda *_: self._delete()))
        self.content.add_widget(ops)

        # 进度流水
        self.content.add_widget(W.SectionTitle("进度记录", color=T.ACCENT,
                                               caption="最近 20 条"))
        self.logs_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        self.logs_box.bind(minimum_height=self.logs_box.setter("height"))
        self.content.add_widget(self.logs_box)
        self._load_logs()

    # ------------------------------------------------------------- 数据
    def _reload_task(self):
        fresh = self.controller.db.get_task(self.task.id)
        if fresh:
            self.task = fresh

    def _load_logs(self):
        self.logs_box.clear_widgets()
        logs = self.controller.db.logs_of(self.task.id)[:20]
        if not logs:
            empty = W.txt("暂无记录", size=T.FONT_SMALL, color=T.TEXT_HINT)
            empty.size_hint_y = None
            empty.height = dp(24)
            self.logs_box.add_widget(empty)
            return
        for entry in logs:
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            kind_color = {
                "create": T.PRIMARY, "progress": T.ACCENT, "complete": T.OK,
                "archive": T.MUTED, "reopen": T.WARN, "restore": T.PRIMARY,
            }.get(entry.kind, T.TEXT_SUB)
            row.add_widget(W.Dot(color=kind_color, size=dp(8)))
            text = BoxLayout(orientation="vertical", spacing=0)
            head = f"{entry.kind_label} · {entry.progress}%" if entry.kind != "edit" \
                else entry.kind_label
            text.add_widget(W.txt(head, size=T.FONT_SMALL + 1, color=T.TEXT, bold=True,
                                  short=True))
            text.add_widget(W.txt(entry.note or entry.time_text, size=T.FONT_SMALL,
                                  color=T.TEXT_HINT, short=True))
            row.add_widget(text)
            time_label = W.txt(M.pretty_dt(entry.created_at), size=T.FONT_SMALL,
                               color=T.TEXT_HINT, halign="right")
            time_label.size_hint_x = None
            time_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0] + dp(2)))
            row.add_widget(time_label)
            self.logs_box.add_widget(row)

    def refresh_view(self):
        """操作之后刷新弹层内的展示内容。"""
        self._reload_task()
        self.close()
        self.controller.open_detail(self.task.id)

    # ------------------------------------------------------------- 进度
    def _on_slider(self, value):
        self._value = int(value)
        self.value_label.text = f"{self._value}%"

    def _quick_progress(self, label):
        value = int(label.rstrip("%")) if label in ("50%", "100%") else \
            max(0, min(100, self._value + int(label.rstrip("%"))))
        self.slider.set_value(value)
        self._on_slider(value)

    def _save_progress(self):
        note = self.note_input.text.strip()
        self.controller.db.set_progress(self.task.id, self._value, note)
        label = "已完成" if self._value >= 100 else f"进度更新为 {self._value}%"
        self.controller.toast(f"{label}，已记录")
        self.controller.refresh()
        self.refresh_view()

    # ------------------------------------------------------------- 操作
    def _complete(self):
        self.controller.db.complete_task(self.task.id)
        self.controller.toast("任务已完成 √")
        self.controller.refresh()
        self.refresh_view()

    def _reopen(self):
        self.controller.db.reopen_task(self.task.id)
        self.controller.toast("已重新打开任务")
        self.controller.refresh()
        self.refresh_view()

    def _archive(self):
        self.controller.db.archive_task(self.task.id)
        self.controller.toast("已存入后台归档")
        self.controller.refresh()
        self.dismiss()

    def _restore(self):
        self.controller.db.restore_task(self.task.id)
        self.controller.toast("已从后台取回")
        self.controller.refresh()
        self.dismiss()

    def _delete(self):
        ConfirmModal(
            title="删除这条待办？",
            message=f"「{self.task.title}」及其进度记录将永久删除，无法恢复。",
            confirm_text="确认删除",
            on_confirm=self._do_delete,
        ).open()

    def _do_delete(self):
        self.controller.db.delete_task(self.task.id)
        self.controller.toast("已删除")
        self.controller.refresh()
        self.dismiss()

    def _edit(self):
        self.dismiss()
        self.controller.open_editor(self.task)


# ------------------------------------------------------------------ 确认框
class ConfirmModal(BaseModal):
    def __init__(self, title="确认操作", message="", confirm_text="确认",
                 cancel_text="取消", danger=True, on_confirm=None, **kwargs):
        super().__init__(**kwargs)
        self.on_confirm = on_confirm
        content = BoxLayout(orientation="vertical", size_hint_y=None,
                            spacing=dp(10), padding=[dp(18), dp(18), dp(18), dp(14)])
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(W.txt(title, size=T.FONT_TITLE, bold=True,
                                 size_hint_y=None, height=dp(26)))
        body = W.txt(message, size=T.FONT_BODY, color=T.TEXT_SUB)
        body.size_hint_y = None
        body.bind(width=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        body.bind(texture_size=lambda w, s: setattr(w, "height", s[1] + dp(4)))
        content.add_widget(body)
        footer = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        footer.add_widget(W.SoftButton(cancel_text, color=T.TEXT_SUB, bg=T.BG_SOFT,
                                       height_dp=44, on_tap=lambda *_: self.dismiss()))
        footer.add_widget(W.BaseButton(confirm_text, height_dp=44,
                                       fill=T.DANGER if danger else T.PRIMARY,
                                       on_tap=lambda *_: self._confirm()))
        content.add_widget(footer)
        self.content = content
        self.show_card(content, natural_height=240, max_width=420)

    def _confirm(self):
        if self.on_confirm:
            self.on_confirm()
        self.dismiss()
