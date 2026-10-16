# -*- coding: utf-8 -*-
# ============================================================================
# 打包配置文件（buildozer）。在 Linux / WSL / Docker / GitHub Actions 里使用：
#     buildozer android debug          # 打包调试 APK（可直接安装）
#     buildozer android release        # 打包正式签名包（aab/apk）
# ============================================================================

[app]

# 应用名称（手机桌面图标下显示的名字）
title = 待办工作台

# 包名（反域名格式，只能小写字母/数字/点/下划线）
package.name = todoworkbench
package.domain = com.example

# 应用源码入口与目录
source.dir = .
source.include_exts = py,png,otf,ttf,kv,txt,md,json

# 版本号：每次更新给手机重新安装前，建议递增
version = 1.0.0

# 运行时依赖（不要随意加包，每加一个都会显著增加打包时间与体积）
requirements = python3,kivy==2.3.0

# 图标与启动画面
icon.filename = assets/icon.png
# presplash.filename = assets/icon.png

# 屏幕方向：all 表示跟随系统旋转（折叠屏展开/合上都会自适应）
orientation = all

fullscreen = 0
android.allow_backup = True

# Android 平台配置 -----------------------------------------------------------
# 目标架构：荣耀 Magic V6 是骁龙 8 Elite（arm64），只编 arm64 速度快、包小
android.archs = arm64-v8a
android.api = 34
android.minapi = 26
android.ndk_api = 26
android.accept_sdk_license = True

# 本应用完全离线、不需要任何危险权限
# android.permissions =

# Gradle 构建参数（内存不足时把 Xmx 调大）
#android.gradle_options = -Xmx4g

# iOS 相关（用不到，保持默认）
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

[buildozer]
# 日志等级：首次打包想看详细过程改成 2
log_level = 1
warn_on_root = 1
# buildozer 会把 SDK/NDK 缓存在 ~/.buildozer，删除后下次要重新下载
