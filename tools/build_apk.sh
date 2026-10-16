#!/usr/bin/env bash
# =====================================================================
# 一键打包脚本（在 Linux / WSL / macOS 终端里运行）
#   1) 安装系统依赖与 buildozer（已装会自动跳过）
#   2) 打包出 bin/*.apk
# 用法：
#   bash tools/build_apk.sh            # 常规打包
#   bash tools/build_apk.sh clean      # 清理后从头打包（很慢，仅在改配置后异常时用）
# =====================================================================
set -e

echo "==> [1/3] 安装系统依赖（需要 sudo 密码）"
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf libtool \
        pkg-config zlib1g-dev libffi-dev libssl-dev cmake build-essential \
        ccache python3-pip python3-venv
fi

echo "==> [2/3] 安装 buildozer 与 cython"
python3 -m pip install --user --upgrade pip
python3 -m pip install --user --upgrade "cython==3.0.11" buildozer virtualenv
export PATH="$HOME/.local/bin:$PATH"

if [ "$1" = "clean" ]; then
    echo "==> 清理旧的构建缓存"
    rm -rf .buildozer bin
fi

echo "==> [3/3] 开始打包（首次会下载 Android SDK/NDK，约 2~3GB，耐心等待）"
buildozer android debug

echo ""
echo "✅ 打包完成！APK 位于 bin/ 目录："
ls -lh bin/*.apk 2>/dev/null || echo "（未找到 APK，请往上翻看报错信息）"
echo ""
echo "安装到手机（手机开启 USB 调试并连接电脑后）："
echo "  adb install -r bin/*.apk"
