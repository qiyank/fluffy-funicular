# -*- coding: utf-8 -*-
"""
数据模型与时间展示辅助。

本模块只依赖 Python 标准库，不导入 Kivy，因此可以脱离界面单独运行/测试：
    python -m core.models
"""
from __future__ import annotations

from datetime import datetime, timedelta

DT_FMT = "%Y-%m-%d %H:%M:%S"      # 数据库内统一使用的时间格式
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"

# ---------------------------------------------------------------- 枚举与文案
STATUS_TODO = "todo"
STATUS_DOING = "doing"
STATUS_DONE = "done"

STATUS_LABEL = {
    STATUS_TODO: "待办",
    STATUS_DOING: "进行中",
    STATUS_DONE: "已完成",
}

PRIORITY_LABEL = {0: "低", 1: "中", 2: "高"}

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


# ---------------------------------------------------------------- 时间工具
def now() -> datetime:
    """当前本地时间。"""
    return datetime.now()


def now_str() -> str:
    """当前本地时间字符串（写入数据库用）。"""
    return now().strftime(DT_FMT)


def to_str(dt: datetime | None) -> str:
    return dt.strftime(DT_FMT) if dt else ""


def parse(text: str | None) -> datetime | None:
    """把数据库里的时间字符串解析成 datetime，失败返回 None。"""
    if not text:
        return None
    text = str(text).strip()
    for fmt in (DT_FMT, "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def human_span(delta: timedelta) -> str:
    """把时间差转成「3天2小时」这种中文短文案。"""
    total = int(delta.total_seconds())
    if total < 0:
        total = -total
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}天{hours}小时" if hours else f"{days}天"
    if hours:
        return f"{hours}小时{minutes}分" if minutes else f"{hours}小时"
    if minutes:
        return f"{minutes}分钟"
    return "不到1分钟"


def pretty_dt(text: str | None, with_year: bool = False) -> str:
    """把时间字符串格式化成「10-18 18:00」这样的展示文案。"""
    dt = parse(text)
    if not dt:
        return "—"
    fmt = "%Y-%m-%d %H:%M" if with_year else "%m-%d %H:%M"
    return dt.strftime(fmt)


def pretty_date_cn(text: str | None) -> str:
    dt = parse(text)
    if not dt:
        return "—"
    today = now().date()
    d = dt.date()
    if d == today:
        head = "今天"
    elif d == today + timedelta(days=1):
        head = "明天"
    elif d == today - timedelta(days=1):
        head = "昨天"
    else:
        head = f"{dt.month}月{dt.day}日"
    return f"{head} {dt.strftime(TIME_FMT)} · {WEEKDAY_CN[dt.weekday()]}"


# ---------------------------------------------------------------- 任务对象
class Task:
    """一条待办任务。底层是一行 dict，附带若干只读展示属性。"""

    FIELDS = (
        "id", "title", "detail", "category", "priority", "due_at",
        "progress", "status", "archived",
        "created_at", "updated_at", "completed_at", "archived_at",
    )

    def __init__(self, row=None, **kwargs):
        self.id = None
        self.title = ""
        self.detail = ""
        self.category = "默认"
        self.priority = 1
        self.due_at = ""
        self.progress = 0
        self.status = STATUS_TODO
        self.archived = 0
        self.created_at = ""
        self.updated_at = ""
        self.completed_at = ""
        self.archived_at = ""
        if row is not None:
            for key in self.FIELDS:
                try:
                    value = row[key]
                except (KeyError, IndexError, TypeError):
                    continue
                if value is not None:
                    setattr(self, key, value)
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)
        # 数据库里可能存的是 str，统一成 int
        self.priority = int(self.priority or 0)
        self.progress = max(0, min(100, int(self.progress or 0)))
        self.archived = int(self.archived or 0)

    # ---------------- 展示属性 ----------------
    @property
    def status_label(self) -> str:
        return STATUS_LABEL.get(self.status, "待办")

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABEL.get(self.priority, "中")

    @property
    def is_done(self) -> bool:
        return self.status == STATUS_DONE

    @property
    def is_archived(self) -> bool:
        return bool(self.archived)

    @property
    def due_dt(self) -> datetime | None:
        return parse(self.due_at)

    @property
    def is_overdue(self) -> bool:
        if self.is_done or not self.due_at:
            return False
        due = self.due_dt
        return bool(due and due < now())

    @property
    def is_today_due(self) -> bool:
        due = self.due_dt
        if not due or self.is_done:
            return False
        return due.date() <= now().date()

    @property
    def progress_text(self) -> str:
        return f"{self.progress}%"

    @property
    def due_text(self) -> str:
        if not self.due_at:
            return "未设置时间节点"
        return pretty_dt(self.due_at)

    @property
    def due_text_cn(self) -> str:
        if not self.due_at:
            return "未设置时间节点"
        return pretty_date_cn(self.due_at)

    @property
    def remain_text(self) -> str:
        """倒计时文案：还剩 / 已逾期 / 已完成。"""
        if self.is_done:
            return "已完成" + (f" · {pretty_dt(self.completed_at)}" if self.completed_at else "")
        due = self.due_dt
        if not due:
            return "未设置时间节点"
        delta = due - now()
        if delta.total_seconds() < 0:
            return f"已逾期 {human_span(delta)}"
        return f"还剩 {human_span(delta)}"

    @property
    def created_text(self) -> str:
        return pretty_dt(self.created_at, with_year=True)

    @property
    def completed_text(self) -> str:
        return pretty_dt(self.completed_at, with_year=True) if self.completed_at else "—"

    @property
    def updated_text(self) -> str:
        return pretty_dt(self.updated_at, with_year=True)

    def matches(self, keyword: str) -> bool:
        """关键词匹配（标题 / 备注 / 分类 / 状态）。"""
        if not keyword:
            return True
        kw = keyword.strip().lower()
        haystack = " ".join([
            str(self.title or ""), str(self.detail or ""),
            str(self.category or ""), self.status_label,
        ]).lower()
        return kw in haystack

    def as_dict(self) -> dict:
        return {key: getattr(self, key) for key in self.FIELDS}

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Task #{self.id} {self.title!r} {self.status} {self.progress}%>"


class LogEntry:
    """一条进度/操作记录。"""

    KIND_LABEL = {
        "create": "创建任务",
        "progress": "更新进度",
        "complete": "标记完成",
        "reopen": "重新打开",
        "archive": "存入后台",
        "restore": "从后台取回",
        "edit": "编辑任务",
    }

    def __init__(self, row=None, **kwargs):
        data = dict(row) if row is not None else {}
        data.update(kwargs)
        self.id = data.get("id")
        self.task_id = data.get("task_id")
        self.progress = int(data.get("progress") or 0)
        self.note = data.get("note") or ""
        self.kind = data.get("kind") or "progress"
        self.created_at = data.get("created_at") or ""

    @property
    def kind_label(self) -> str:
        return self.KIND_LABEL.get(self.kind, "记录")

    @property
    def time_text(self) -> str:
        return pretty_dt(self.created_at, with_year=True)


if __name__ == "__main__":  # pragma: no cover - 自测
    t = Task(title="测试任务", due_at="2026-10-20 18:00:00", progress=40)
    print(t, t.remain_text, t.due_text_cn, t.created_text)
    d = parse("2026-10-20 18:00:00")
    print(pretty_date_cn("2026-10-20 18:00:00"), human_span(d - now()))
