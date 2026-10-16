# -*- coding: utf-8 -*-
"""
待办工作台（Todo Workbench）
一个用 Python + Kivy 写的安卓待办 App，针对荣耀 Magic V6 这类
折叠屏做了适配：折叠时是单列 + 底部导航，展开后自动变成双列 / 三列 + 侧边导航。

运行（电脑上预览）：
    pip install kivy
    python main.py

打包成 APK 安装到手机：见同目录《操作说明.md》。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

from kivy.config import Config

# 桌面预览时的窗口尺寸（接近手机竖屏比例）；手机上这些设置无影响
Config.set("graphics", "width", "412")
Config.set("graphics", "height", "900")
Config.set("graphics", "resizable", "1")
Config.set("graphics", "minimum_width", "320")
Config.set("graphics", "minimum_height", "480")
Config.set("kivy", "exit_on_escape", "0")

from kivy.animation import Animation           # noqa: E402
from kivy.app import App                       # noqa: E402
from kivy.clock import Clock                   # noqa: E402
from kivy.core.window import Window            # noqa: E402
from kivy.metrics import dp                    # noqa: E402
from kivy.uix.modalview import ModalView       # noqa: E402
from kivy.uix.screenmanager import NoTransition, ScreenManager  # noqa: E402
from kivy.uix.widget import Widget                              # noqa: E402

from core import responsive                    # noqa: E402
from core import theme as T                    # noqa: E402
from core.database import TaskDB               # noqa: E402
from ui import widgets as W                    # noqa: E402
from ui.nav import NavBar                      # noqa: E402
from ui.screens import (ArchiveScreen, HomeScreen, SearchScreen,  # noqa: E402
                        TasksScreen)
from ui.sheets import ProgressModal, TaskDetailModal, TaskEditorModal  # noqa: E402


class Root(Widget):
    """根布局：负责「折叠 / 展开」两种形态的重新排布。

    刻意不使用布局容器（BoxLayout/FloatLayout），所有子部件的位置与尺寸
    都由本类手动计算，保证折叠屏形态切换时布局完全可控。
    """

    def __init__(self, app: "TodoApp", **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._reflow_ev = None
        self._toast = None

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.size_hint = (None, None)
        self.screens = {
            "home": HomeScreen(controller=app, name="home"),
            "tasks": TasksScreen(controller=app, name="tasks"),
            "search": SearchScreen(controller=app, name="search"),
            "archive": ArchiveScreen(controller=app, name="archive"),
        }
        for screen in self.screens.values():
            self.sm.add_widget(screen)

        self.nav = NavBar(
            items=[
                ("home", "工作台", "grid"),
                ("tasks", "任务", "task"),
                ("search", "搜索", "search"),
                ("archive", "后台", "box"),
            ],
            on_select=app.switch,
        )
        self.add_widget(self.sm)
        self.add_widget(self.nav)
        self.bind(pos=self._schedule_reflow, size=self._schedule_reflow)
        Clock.schedule_once(self._reflow, 0)

    # ---------------------------------------------------------- 形态切换
    def _schedule_reflow(self, *args):
        if self._reflow_ev:
            self._reflow_ev.cancel()
        self._reflow_ev = Clock.schedule_once(self._reflow, 0.04)

    def _reflow(self, *args):
        wide = responsive.is_unfolded()
        if wide:
            self.nav.set_mode("rail")
            nav_w = dp(T.RAIL_WIDTH)
            self.nav.pos = (self.x, self.y)
            self.nav.size = (nav_w, self.height)
            self.sm.pos = (self.x + nav_w, self.y)
            self.sm.size = (self.width - nav_w, self.height)
        else:
            self.nav.set_mode("bottom")
            nav_h = dp(T.NAV_HEIGHT)
            self.nav.pos = (self.x, self.y)
            self.nav.size = (self.width, nav_h)
            self.sm.pos = (self.x, self.y + nav_h)
            self.sm.size = (self.width, self.height - nav_h)
        if self._toast is not None and self._toast.parent:
            self._place_toast(self._toast)

    # ---------------------------------------------------------- 轻提示
    def _place_toast(self, toast):
        toast.pos = ((self.width - toast.width) / 2, self.y + dp(88))

    def toast(self, text):
        if self._toast is not None and self._toast.parent:
            self.remove_widget(self._toast)
        toast = W.Toast(text)
        self._toast = toast
        self.add_widget(toast)
        toast.bind(size=lambda w, s: self._place_toast(w))
        self._place_toast(toast)
        Animation(opacity=1, d=0.16).start(toast)
        Clock.schedule_once(lambda *_: self._hide_toast(toast), 1.7)

    def _hide_toast(self, toast):
        if toast.parent is None:
            return
        anim = Animation(opacity=0, d=0.3)
        anim.bind(on_complete=lambda *_: self.remove_widget(toast)
                  if toast.parent else None)
        anim.start(toast)


class TodoApp(App):
    """应用主体：持有数据库连接，统一对外提供界面动作。"""

    title = "待办工作台"

    def build(self):
        Window.clearcolor = T.BG
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass
        self.db = TaskDB(self._db_path())
        self.root_layout = Root(self)
        Window.bind(on_keyboard=self._on_keyboard)
        return self.root_layout

    # ---------------------------------------------------------- 基础设施
    def _db_path(self) -> str:
        base = None
        try:
            base = self.user_data_dir          # 安卓：应用私有目录
        except Exception:
            base = None
        if not base:
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "todo_workbench.db")

    @property
    def sm(self):
        return self.root_layout.sm

    def on_start(self):
        self.refresh()
        self.switch("home")
        if "--selftest" in sys.argv:
            Clock.schedule_once(self._selftest_step, 0.8)

    # ---------------------------------------------------------- 自检流程
    def _selftest_step(self, *args):
        """python main.py --selftest ：自动过一遍主要界面，用于快速验证环境。
        加 --shots 参数时会把每一步截图保存到 screenshots/ 目录。"""
        from datetime import timedelta

        from core import models as M

        shots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "screenshots")
        take_shots = "--shots" in sys.argv
        if take_shots:
            os.makedirs(shots_dir, exist_ok=True)

        def snap(name):
            if not take_shots:
                return
            try:
                Window.screenshot(name=os.path.join(shots_dir, name))
                print(f"[selftest] 截图 -> {name}")
            except Exception as exc:
                print(f"[selftest] 截图失败 {name}: {exc}")

        def log(msg):
            print(f"[selftest] {msg}")

        def warmup(*_):
            # 预热：本机首次 Window.screenshot 常拍到黑帧，先拍一张丢弃
            # （写到系统临时目录，不污染 screenshots/）
            if take_shots:
                import tempfile
                snap(os.path.join(tempfile.gettempdir(), "_kivy_warmup.png"))

        def make_task(*_):
            self._self_task = self.db.add_task(
                "自检任务", "由 --selftest 自动创建", "自检", 2,
                M.to_str(datetime.now() + timedelta(days=1)), 40)
            self.db.add_task("整理报销单据", "贴好发票并提交 OA", "工作", 1,
                             M.to_str(datetime.now() + timedelta(hours=3)), 70)
            self.db.add_task("每周健身三次", "已完成本周第二次", "生活", 0,
                             M.to_str(datetime.now() + timedelta(days=3)), 100)
            self.refresh()
            self.switch("home")
            log("新建任务 OK")

        def open_editor(*_):
            snap("01_home_narrow.png")
            self.open_editor()
            log("打开新建弹层 OK")

        def close_and_detail(*_):
            snap("02_editor.png")
            for child in list(Window.children):
                if isinstance(child, ModalView):
                    child.dismiss()
            self.open_detail(self._self_task.id)
            log("打开详情弹层 OK")

        def close_and_search(*_):
            snap("03_detail.png")
            for child in list(Window.children):
                if isinstance(child, ModalView):
                    child.dismiss()
            self.switch("search")
            self.root_layout.screens["search"].search_input.text = "自检"
            Clock.schedule_once(lambda *_: self.root_layout.screens["search"].reload(), 0.4)
            log("搜索页 OK")

        def go_tasks(*_):
            snap("04_search.png")
            self.switch("tasks")
            log("任务列表 OK")

        def go_wide(*_):
            snap("05_tasks_narrow.png")
            self.switch("home")
            Window.size = (880, 700)
            log("切换展开态布局 OK")

        def go_narrow(*_):
            snap("06_home_wide.png")
            Window.size = (412, 900)
            log("切换折叠态布局 OK")

        def finish(*_):
            snap("07_home_narrow_again.png")
            self.db.delete_task(self._self_task.id)
            self.refresh()
            log("自检全部通过 ✔  即将退出")
            Clock.schedule_once(lambda *_: self.stop(), 0.4)

        steps = [(0, warmup), (0.4, make_task), (1.2, open_editor),
                 (2.2, close_and_detail), (3.2, close_and_search),
                 (4.2, go_tasks), (5.2, go_wide), (6.1, go_narrow),
                 (7.0, finish)]
        for delay, fn in steps:
            Clock.schedule_once(fn, delay)

    def on_stop(self):
        try:
            self.db.close()
        except Exception:
            pass

    # ---------------------------------------------------------- 界面动作
    def switch(self, key):
        if key in self.root_layout.screens:
            self.sm.current = key
            self.root_layout.nav.highlight(key)

    def refresh(self):
        """数据变化后刷新当前所有页面。"""
        for screen in self.root_layout.screens.values():
            try:
                screen.reload()
            except Exception as exc:      # 单个页面出错不影响其他页面
                print(f"[refresh] {screen.name} 刷新失败: {exc}")

    def toast(self, text):
        self.root_layout.toast(text)

    # ---------------------------------------------------------- 任务操作
    def open_editor(self, task=None):
        categories = self.db.all_categories()
        TaskEditorModal(
            task=task, categories=categories, on_save=self._save_task).open()

    def _save_task(self, data, task=None):
        if task is None:
            self.db.add_task(
                data["title"], data.get("detail", ""), data.get("category", "默认"),
                data.get("priority", 1), data.get("due_at", ""),
                data.get("progress", 0))
            self.toast("已新建待办")
        else:
            self.db.update_task(
                task.id, title=data["title"], detail=data.get("detail", ""),
                category=data.get("category", "默认"),
                priority=data.get("priority", 1), due_at=data.get("due_at", ""))
            if data.get("progress", task.progress) != task.progress:
                self.db.set_progress(task.id, data["progress"], "编辑时更新进度")
            self.toast("已保存修改")
        self.refresh()

    def open_detail_task(self, task):
        self.open_detail(task.id)

    def open_detail(self, task_id):
        fresh = self.db.get_task(task_id)
        if fresh is None:
            self.toast("任务不存在")
            return
        TaskDetailModal(fresh, self).open()

    def open_progress(self, task):
        def _submit(t, value, note):
            self.db.set_progress(t.id, value, note)
            self.toast("进度已更新为 %d%%" % value)
            self.refresh()
        ProgressModal(task, on_submit=_submit).open()

    def quick_complete(self, task):
        if getattr(task, "is_done", False):
            self.open_detail(task.id)
            return
        self.db.complete_task(task.id)
        self.toast("任务已完成 √")
        self.refresh()

    # ---------------------------------------------------------- 安卓返回键
    def _on_keyboard(self, window, key, *args):
        if key == 27:                       # 返回键
            for child in list(Window.children):
                if isinstance(child, ModalView):
                    child.dismiss()
                    return True
            if self.sm.current != "home":
                self.switch("home")
                return True
        return False


if __name__ == "__main__":
    T.register_cjk_font()
    TodoApp().run()
