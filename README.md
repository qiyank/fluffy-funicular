# 待办工作台（Todo Workbench）

用 Python + Kivy 写的本地待办 App，针对荣耀 Magic V6 折叠屏自动适配
（折叠：单列 + 底部导航；展开：双/三列 + 侧边导航）。

**功能**：手动添加待办（标题/备注/分类/优先级/时间节点/进度）· 可拖动滑杆更新进度并留痕 ·
一键完成并记录完成时间 · 完成任务「存入后台」归档 · 关键词搜索任意调出 ·
工作台数据看板（完成率、今日与逾期、近 7 天完成柱状图）。

数据存在手机本地 SQLite，完全离线，不需要任何权限。

## 快速开始

```bash
# 电脑预览
pip install kivy
python main.py

# 打包 APK（Linux / WSL2 / Docker）
bash tools/build_apk.sh          # 产物在 bin/*.apk
```

详细的使用说明、三种打包方式（WSL / Docker / GitHub Actions 云打包）、
安装到荣耀 Magic V6 的步骤与常见问题，见 **[操作说明.md](操作说明.md)**。
