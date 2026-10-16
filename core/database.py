# -*- coding: utf-8 -*-
"""
SQLite 数据层：任务增删改查、进度流水、后台归档、搜索与统计。

只依赖标准库。自测（不需要 Kivy）：
    python -m core.database
"""
from __future__ import annotations

import os
import sqlite3
from datetime import timedelta

from core import models as M

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    detail      TEXT    NOT NULL DEFAULT '',
    category    TEXT    NOT NULL DEFAULT '默认',
    priority    INTEGER NOT NULL DEFAULT 1,
    due_at      TEXT    NOT NULL DEFAULT '',
    progress    INTEGER NOT NULL DEFAULT 0,
    status      TEXT    NOT NULL DEFAULT 'todo',
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT    NOT NULL DEFAULT '',
    completed_at TEXT   NOT NULL DEFAULT '',
    archived_at TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS progress_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL,
    progress    INTEGER NOT NULL DEFAULT 0,
    note        TEXT    NOT NULL DEFAULT '',
    kind        TEXT    NOT NULL DEFAULT 'progress',
    created_at  TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status, archived);
CREATE INDEX IF NOT EXISTS idx_tasks_due      ON tasks(due_at);
CREATE INDEX IF NOT EXISTS idx_logs_task      ON progress_logs(task_id, id DESC);
"""

#: 列表过滤器 -> SQL 片段
FILTER_SQL = {
    "all":      "1=1",
    "todo":     "status='todo' AND archived=0",
    "doing":    "status='doing' AND archived=0",
    "done":     "status='done' AND archived=0",
    "archive":  "archived=1",
    "overdue":  "status!='done' AND archived=0 AND due_at<>'' AND due_at<'{now}'",
    "today":    ("status!='done' AND archived=0 AND due_at<>'' "
                 "AND date(due_at)<=date('{now}')"),
}

ORDER_SQL = {
    "due":      "CASE WHEN due_at='' THEN 1 ELSE 0 END, due_at ASC, priority DESC, id DESC",
    "created":  "id DESC",
    "priority": "priority DESC, CASE WHEN due_at='' THEN 1 ELSE 0 END, due_at ASC",
    "progress": "progress DESC, id DESC",
}


class TaskDB:
    """任务数据库。默认存到 APP 私有目录，卸载应用才会清除。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        folder = os.path.dirname(os.path.abspath(db_path))
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._migrate()

    # ------------------------------------------------------------ 底层
    def _migrate(self):
        """老版本数据库缺列时自动补齐。"""
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(tasks)")}
        for name, ddl in (
            ("detail", "ALTER TABLE tasks ADD COLUMN detail TEXT NOT NULL DEFAULT ''"),
            ("category", "ALTER TABLE tasks ADD COLUMN category TEXT NOT NULL DEFAULT '默认'"),
            ("priority", "ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 1"),
            ("due_at", "ALTER TABLE tasks ADD COLUMN due_at TEXT NOT NULL DEFAULT ''"),
            ("progress", "ALTER TABLE tasks ADD COLUMN progress INTEGER NOT NULL DEFAULT 0"),
            ("archived", "ALTER TABLE tasks ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"),
            ("completed_at", "ALTER TABLE tasks ADD COLUMN completed_at TEXT NOT NULL DEFAULT ''"),
            ("archived_at", "ALTER TABLE tasks ADD COLUMN archived_at TEXT NOT NULL DEFAULT ''"),
        ):
            if name not in cols:
                self.conn.execute(ddl)
        self.conn.commit()

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass

    def backup_to(self, dest_path: str) -> str:
        """把数据库整体备份一份（用于导出/迁移）。"""
        dest = sqlite3.connect(dest_path)
        with dest:
            self.conn.backup(dest)
        dest.close()
        return dest_path

    # ------------------------------------------------------------ 日志
    def add_log(self, task_id: int, kind: str, note: str = "", progress: int = 0,
                created_at: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO progress_logs(task_id, progress, note, kind, created_at)"
            " VALUES(?,?,?,?,?)",
            (task_id, int(progress), note or "", kind, created_at or M.now_str()),
        )
        self.conn.commit()

    def logs_of(self, task_id: int) -> list[M.LogEntry]:
        rows = self.conn.execute(
            "SELECT * FROM progress_logs WHERE task_id=? ORDER BY id DESC", (task_id,)
        ).fetchall()
        return [M.LogEntry(r) for r in rows]

    # ------------------------------------------------------------ 写操作
    def add_task(self, title: str, detail: str = "", category: str = "默认",
                 priority: int = 1, due_at: str = "", progress: int = 0) -> M.Task:
        ts = M.now_str()
        progress = max(0, min(100, int(progress)))
        status = M.STATUS_DONE if progress >= 100 else (
            M.STATUS_DOING if progress > 0 else M.STATUS_TODO)
        cur = self.conn.execute(
            "INSERT INTO tasks(title, detail, category, priority, due_at, progress,"
            " status, archived, created_at, updated_at, completed_at, archived_at)"
            " VALUES(?,?,?,?,?,?,?,0,?,?,'','')",
            (title.strip(), detail.strip(), (category or "默认").strip(),
             int(priority), due_at or "", progress, status, ts, ts),
        )
        self.conn.commit()
        task_id = cur.lastrowid
        self.add_log(task_id, "create", f"创建任务（初始进度 {progress}%）", progress, ts)
        if status == M.STATUS_DONE:
            self.conn.execute("UPDATE tasks SET completed_at=? WHERE id=?", (ts, task_id))
            self.conn.commit()
            self.add_log(task_id, "complete", "创建时即已完成", 100, ts)
        return self.get_task(task_id)

    def update_task(self, task_id: int, **fields) -> M.Task | None:
        allowed = {"title", "detail", "category", "priority", "due_at", "progress",
                   "status", "completed_at"}
        data = {k: v for k, v in fields.items() if k in allowed}
        if not data:
            return self.get_task(task_id)
        old = self.get_task(task_id)
        if old is None:
            return None
        data["updated_at"] = M.now_str()
        # 进度改变时同步状态
        if "progress" in data:
            p = max(0, min(100, int(data["progress"])))
            data["progress"] = p
            if p >= 100:
                data["status"] = M.STATUS_DONE
                data.setdefault("completed_at", M.now_str())
            elif p > 0:
                data["status"] = M.STATUS_DOING if data.get("status") != M.STATUS_DONE \
                    else M.STATUS_DONE
            else:
                if data.get("status") != M.STATUS_DONE:
                    data["status"] = M.STATUS_TODO
        sets = ", ".join(f"{k}=?" for k in data)
        self.conn.execute(f"UPDATE tasks SET {sets} WHERE id=?",
                          (*data.values(), task_id))
        self.conn.commit()
        return self.get_task(task_id)

    def set_progress(self, task_id: int, progress: int, note: str = "") -> M.Task | None:
        """更新进度并写一条流水。"""
        task = self.get_task(task_id)
        if task is None:
            return None
        progress = max(0, min(100, int(progress)))
        ts = M.now_str()
        status = M.STATUS_DONE if progress >= 100 else (
            M.STATUS_DOING if progress > 0 else M.STATUS_TODO)
        completed_at = task.completed_at
        if status == M.STATUS_DONE and not completed_at:
            completed_at = ts
        elif status != M.STATUS_DONE:
            completed_at = ""
        self.conn.execute(
            "UPDATE tasks SET progress=?, status=?, completed_at=?, updated_at=? WHERE id=?",
            (progress, status, completed_at, ts, task_id),
        )
        self.conn.commit()
        if status == M.STATUS_DONE and task.status != M.STATUS_DONE:
            self.add_log(task_id, "complete", note or "任务完成", 100, ts)
        else:
            self.add_log(task_id, "progress",
                         note or f"进度 {task.progress}% → {progress}%", progress, ts)
        return self.get_task(task_id)

    def complete_task(self, task_id: int, note: str = "") -> M.Task | None:
        return self.set_progress(task_id, 100, note or "标记为已完成")

    def reopen_task(self, task_id: int) -> M.Task | None:
        """重新打开（回到进行中，进度保留为 90% 以便继续推进）。"""
        task = self.get_task(task_id)
        if task is None:
            return None
        progress = 90 if task.progress >= 100 else task.progress
        ts = M.now_str()
        status = M.STATUS_DOING if progress > 0 else M.STATUS_TODO
        self.conn.execute(
            "UPDATE tasks SET status=?, archived=0, archived_at='', completed_at='',"
            " progress=?, updated_at=? WHERE id=?",
            (status, progress, ts, task_id),
        )
        self.conn.commit()
        self.add_log(task_id, "reopen", "重新打开任务", progress, ts)
        return self.get_task(task_id)

    def archive_task(self, task_id: int) -> M.Task | None:
        """完成任务后「存入后台」。"""
        task = self.get_task(task_id)
        if task is None:
            return None
        ts = M.now_str()
        self.conn.execute(
            "UPDATE tasks SET archived=1, archived_at=?, updated_at=? WHERE id=?",
            (ts, ts, task_id),
        )
        self.conn.commit()
        self.add_log(task_id, "archive", "存入后台归档", task.progress, ts)
        return self.get_task(task_id)

    def restore_task(self, task_id: int) -> M.Task | None:
        ts = M.now_str()
        self.conn.execute(
            "UPDATE tasks SET archived=0, archived_at='', updated_at=? WHERE id=?",
            (ts, task_id),
        )
        self.conn.commit()
        self.add_log(task_id, "restore", "从后台取回", 0, ts)
        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> None:
        self.conn.execute("DELETE FROM progress_logs WHERE task_id=?", (task_id,))
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()

    # ------------------------------------------------------------ 读操作
    def get_task(self, task_id: int) -> M.Task | None:
        row = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return M.Task(row) if row else None

    def list_tasks(self, flt: str = "all", order: str = "due",
                   keyword: str = "", include_archive: bool = False,
                   limit: int | None = None) -> list[M.Task]:
        """按过滤器 + 排序取任务；keyword 非空时做关键词搜索。"""
        where = [FILTER_SQL.get(flt, "1=1").format(now=M.now_str())]
        if flt == "archive":
            pass
        elif include_archive:
            where = ["1=1"]
        params: list = []
        if keyword and keyword.strip():
            kw = f"%{keyword.strip()}%"
            where.append("(title LIKE ? OR detail LIKE ? OR category LIKE ?)")
            params += [kw, kw, kw]
        sql = "SELECT * FROM tasks WHERE " + " AND ".join(where)
        sql += " ORDER BY " + ORDER_SQL.get(order, ORDER_SQL["due"])
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [M.Task(r) for r in self.conn.execute(sql, params).fetchall()]

    def search(self, keyword: str, include_archive: bool = True,
               order: str = "due") -> list[M.Task]:
        return self.list_tasks("all", order, keyword, include_archive=include_archive)

    def all_categories(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT category, COUNT(*) c FROM tasks GROUP BY category ORDER BY c DESC"
        ).fetchall()
        return [r["category"] or "默认" for r in rows]

    # ------------------------------------------------------------ 统计
    def stats(self) -> dict:
        q = "SELECT COUNT(*) c FROM tasks WHERE {}"
        now_s = M.now_str()
        today = M.now().strftime("%Y-%m-%d")
        data = {
            "total":    self.conn.execute(q.format("1=1")).fetchone()["c"],
            "todo":     self.conn.execute(q.format("status='todo' AND archived=0")).fetchone()["c"],
            "doing":    self.conn.execute(q.format("status='doing' AND archived=0")).fetchone()["c"],
            "done":     self.conn.execute(q.format("status='done' AND archived=0")).fetchone()["c"],
            "archive":  self.conn.execute(q.format("archived=1")).fetchone()["c"],
            "overdue":  self.conn.execute(q.format(
                f"status!='done' AND archived=0 AND due_at<>'' AND due_at<'{now_s}'")).fetchone()["c"],
            "today":    self.conn.execute(q.format(
                f"status!='done' AND archived=0 AND due_at<>'' AND date(due_at)<=date('{today}')")).fetchone()["c"],
            "done_all": self.conn.execute(q.format("status='done'")).fetchone()["c"],
        }
        avg = self.conn.execute(
            "SELECT AVG(progress) a FROM tasks WHERE archived=0").fetchone()["a"]
        data["avg_progress"] = int(avg or 0)
        active = data["todo"] + data["doing"]
        data["active"] = active
        denom = data["done_all"] + data["todo"] + data["doing"]
        data["done_rate"] = int(round(data["done_all"] * 100 / denom)) if denom else 0
        # 近 7 天完成数（用于工作台柱状图）
        days = []
        for i in range(6, -1, -1):
            day = (M.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            c = self.conn.execute(
                "SELECT COUNT(*) c FROM tasks WHERE completed_at LIKE ?",
                (f"{day}%",)).fetchone()["c"]
            days.append((day[5:], c))
        data["week"] = days
        return data

    def recent_due(self, limit: int = 6) -> list[M.Task]:
        """工作台「今日与逾期」：未完成、按时间节点最近的若干条。"""
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE status!='done' AND archived=0 AND due_at<>''"
            " ORDER BY due_at ASC LIMIT ?", (limit,)).fetchall()
        return [M.Task(r) for r in rows]


def default_db_path(user_data_dir: str | None = None) -> str:
    """确定数据库位置：优先用应用私有目录。"""
    base = user_data_dir or os.path.expanduser("~/.todo_workbench")
    return os.path.join(base, "todo_workbench.db")


if __name__ == "__main__":  # pragma: no cover - 自测
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "self_test.db")
    db = TaskDB(tmp)
    a = db.add_task("写周报", "整理本周进展", "工作", 2, "2026-10-18 18:00:00", 30)
    b = db.add_task("买牛奶", priority=0, due_at="2026-10-16 21:00:00")
    print("新增:", a.id, b.id)
    db.set_progress(a.id, 60, "写完前半部分")
    db.complete_task(b.id)
    db.archive_task(b.id)
    print("搜索『周报』:", db.search("周报"))
    print("搜索『牛奶』(含归档):", db.search("牛奶"))
    print("归档列表:", db.list_tasks("archive"))
    print("统计:", db.stats()["done_rate"], db.stats()["avg_progress"], db.stats()["week"])
    print("流水:", [(x.kind_label, x.progress) for x in db.logs_of(a.id)])
    db.close()
    print("OK ->", tmp)
