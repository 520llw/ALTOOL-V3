#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功率器件参数提取系统 - Windows 便携版打包脚本

在 Windows 上运行此脚本，将生成一个无需安装任何环境的便携包。
用户解压后双击 启动.bat 即可使用。

使用方法（需在 Windows 上执行）:
    python build_portable.py

或双击 build.bat
"""

import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess
import fnmatch
from pathlib import Path

# Windows 控制台默认 cp1252，无法打印中文，强制使用 UTF-8 避免 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============ 配置 ============
PYTHON_VERSION = "3.10.11"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
OUTPUT_NAME = "功率器件参数提取系统_便携版"
OUTPUT_ZIP = f"{OUTPUT_NAME}.zip"

# 项目根目录（build 的上一级）
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 需要包含的文件/目录
INCLUDE_PATTERNS = [
    "main.py",
    "launcher_desktop.py",
    "config.yaml",
    "requirements.txt",
    "backend",
    "frontend",
    ".streamlit",
    "README.md",
]

# 需要排除的文件/目录（在 INCLUDE 范围内的）
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".gitignore",
    "*.log",
    "*.pdf",
    "test_*.py",
    "*_accuracy*.py",
    "evaluate_*.py",
    "complete_evaluation.py",
    "debug_*.py",
    "verify_*.py",
    "self_optimize.py",
    "enhance_db.py",
    "test_extraction*.py",
    "test_parallel*.py",
    "test_fast_mode.py",
    "test_refactored.py",
    "test_shanyangtong*.py",
    "test_sanrise*.py",
    "test_excel*.py",
    "test_extraction_performance.py",
    "extraction_performance_report*.json",
    "optimize_report*.json",
    "optimized_pdfs.log",
    "ground_truth.json",
    "shanyangtong_ground_truth.json",
    "raw_pdf_content.json",
    "test_results*.json",
    "test_kjx*.json",
    "evaluation_report.json",
    "params.db",  # 用户数据，不打包
]

# 需要创建的空目录
EMPTY_DIRS = ["data", "logs", "output", "cache", "backup"]


def log(msg: str):
    print(f"[打包] {msg}")


def download_file(url: str, dest: Path, retries: int = 3) -> bool:
    """下载文件，带重试（适用于 CI 网络波动）"""
    import time
    req = urllib.request.Request(url, headers={"User-Agent": "Python-build"})
    for attempt in range(1, retries + 1):
        try:
            log(f"下载: {url} (尝试 {attempt}/{retries})")
            with urllib.request.urlopen(req, timeout=120) as resp:
                dest.write_bytes(resp.read())
            if dest.exists() and dest.stat().st_size > 0:
                return True
        except Exception as e:
            log(f"下载失败: {e}")
            if attempt < retries:
                time.sleep(5)
    return False


def extract_zip(zip_path: Path, dest: Path):
    """解压 zip"""
    log(f"解压: {zip_path.name}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)


def should_exclude(file_path: Path, relative_to: Path) -> bool:
    """检查文件是否应排除"""
    try:
        rel = file_path.relative_to(relative_to)
    except ValueError:
        return True
    rel_str = str(rel).replace("\\", "/")
    name = file_path.name

    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            if rel_str.endswith(pattern[1:]) or name.endswith(pattern[1:]):
                return True
        elif "*" in pattern:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_str, pattern):
                return True
        elif pattern in rel_str or pattern == name:
            return True
    return False


def copy_project_files(dest: Path):
    """复制项目文件到目标目录"""
    log("复制项目文件...")

    for item in INCLUDE_PATTERNS:
        src = PROJECT_ROOT / item
        if not src.exists():
            log(f"  跳过（不存在）: {item}")
            continue

        if src.is_file():
            if not should_exclude(src, PROJECT_ROOT):
                shutil.copy2(src, dest / item)
                log(f"  复制: {item}")
        else:
            # 目录
            for root, dirs, files in os.walk(src):
                # 过滤 __pycache__
                dirs[:] = [d for d in dirs if d != "__pycache__" and d != ".git"]

                rel_root = Path(root).relative_to(PROJECT_ROOT)
                dest_root = dest / rel_root
                dest_root.mkdir(parents=True, exist_ok=True)

                for f in files:
                    src_file = Path(root) / f
                    if not should_exclude(src_file, PROJECT_ROOT):
                        shutil.copy2(src_file, dest_root / f)
                        log(f"  复制: {rel_root / f}")


def fix_embed_pth(python_dir: Path):
    """修改嵌入式 Python 的 ._pth 文件以启用 site-packages"""
    pth_files = list(python_dir.glob("python*._pth"))
    if not pth_files:
        log("警告: 未找到 ._pth 文件")
        return

    for pth_file in pth_files:
        content = pth_file.read_text(encoding="utf-8")
        if "#import site" in content:
            content = content.replace("#import site", "import site")
            pth_file.write_text(content, encoding="utf-8")
            log(f"已启用 site-packages: {pth_file.name}")


def create_launcher_bat(dest: Path, python_exe: Path):
    """创建便携版启动脚本（桌面窗口 + 浏览器备用）"""
    # 主启动：桌面窗口（选项 C）
    desktop_bat = f'''@echo off
chcp 65001 >nul
title 功率器件参数提取系统

cd /d "%~dp0"

echo ==========================================
echo   ⚡ 功率器件参数提取系统（桌面版）
echo ==========================================
echo.
echo 正在启动，请稍候...
echo.

if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "output" mkdir output
if not exist "cache" mkdir cache

"{python_exe}" launcher_desktop.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 启动失败，请检查错误信息。
    pause
)
'''
    (dest / "启动.bat").write_text(desktop_bat, encoding="utf-8")
    log("已创建: 启动.bat（桌面窗口）")

    # 备用：浏览器版
    browser_bat = f'''@echo off
chcp 65001 >nul
title 功率器件参数提取系统 - 浏览器版

cd /d "%~dp0"

echo ==========================================
echo   ⚡ 功率器件参数提取系统（浏览器版）
echo ==========================================
echo.
echo 正在启动，浏览器将自动打开...
echo.

if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "output" mkdir output
if not exist "cache" mkdir cache

"{python_exe}" -m streamlit run main.py ^
    --server.port 8501 ^
    --server.headless false ^
    --browser.gatherUsageStats false ^
    --theme.base light

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 启动失败，请检查错误信息。
    pause
)
'''
    (dest / "启动-浏览器版.bat").write_text(browser_bat, encoding="utf-8")
    log("已创建: 启动-浏览器版.bat")


def create_readme(dest: Path):
    """创建使用说明"""
    readme = dest / "使用说明.txt"
    content = """功率器件参数提取系统 - 便携版使用说明
========================================

【使用方法】
1. 双击 启动.bat（推荐：在桌面窗口中打开，无需浏览器）
2. 等待程序窗口出现（约 10-30 秒）
3. 默认账号: admin  密码: admin123
4. 若桌面版无法使用，可双击 启动-浏览器版.bat 用浏览器打开

【注意事项】
- 首次启动可能较慢，请耐心等待
- 需要联网（用于 AI 参数提取）
- 请勿删除或移动本文件夹内的任何文件
- 数据保存在 data 目录，可定期备份
- Windows 10/11 会使用系统自带的 Edge WebView2 显示窗口

【如遇问题】
- 若杀毒软件拦截，请添加信任
- 若端口 8501 被占用，可修改启动脚本中的端口号
- 关闭时直接关闭程序窗口即可（桌面版会同时退出后台服务）
"""
    readme.write_text(content, encoding="utf-8")
    log("已创建: 使用说明.txt")


def main():
    if sys.platform != "win32":
        log("=" * 50)
        log("此脚本需在 Windows 上运行才能打包 Windows 便携版。")
        log("请将项目复制到 Windows 电脑，或在 Windows 虚拟机中运行。")
        log("=" * 50)
        return 1

    log("=" * 50)
    log("功率器件参数提取系统 - Windows 便携版打包")
    log("=" * 50)

    build_dir = SCRIPT_DIR / "portable_build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    try:
        # 1. 下载 Python 嵌入式包
        python_zip = build_dir / "python_embed.zip"
        if not download_file(PYTHON_EMBED_URL, python_zip):
            return 1

        # 2. 解压 Python
        python_dir = build_dir / "python"
        extract_zip(python_zip, python_dir)
        python_exe = python_dir / "python.exe"
        if not python_exe.exists():
            log("错误: 解压后未找到 python.exe")
            return 1

        # 3. 修改 ._pth 启用 site-packages
        fix_embed_pth(python_dir)

        # 4. 安装 pip
        get_pip = build_dir / "get-pip.py"
        if not download_file(GET_PIP_URL, get_pip):
            return 1

        log("安装 pip...")
        subprocess.run(
            [str(python_exe), str(get_pip), "--no-warn-script-location"],
            cwd=str(build_dir),
            check=True,
            capture_output=True,
        )

        # 5. 安装依赖
        log("安装 Python 依赖（可能需要几分钟）...")
        req_file = PROJECT_ROOT / "requirements.txt"
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(req_file), "--quiet", "--no-warn-script-location"],
            cwd=str(PROJECT_ROOT),
            check=True,
        )

        # 6. 复制项目文件到 build 目录（与 python 同级）
        copy_project_files(build_dir)

        # 7. 创建空目录
        for d in EMPTY_DIRS:
            (build_dir / d).mkdir(exist_ok=True)

        # 8. 创建启动脚本（使用相对路径）
        create_launcher_bat(build_dir, Path("python") / "python.exe")
        create_readme(build_dir)

        # 9. 打包成 zip
        output_zip = PROJECT_ROOT / OUTPUT_ZIP
        log(f"正在压缩: {output_zip.name}")
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(build_dir):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for f in files:
                    fp = Path(root) / f
                    arcname = fp.relative_to(build_dir)
                    zf.write(fp, arcname)

        # 10. 清理
        shutil.rmtree(build_dir)

        log("=" * 50)
        log(f"打包完成！")
        log(f"输出文件: {output_zip}")
        log(f"大小约: {output_zip.stat().st_size / 1024 / 1024:.1f} MB")
        log("=" * 50)
        log("将 zip 发给用户，解压后双击 启动.bat 即可使用。")
        return 0

    except subprocess.CalledProcessError as e:
        log(f"命令执行失败: {e}")
        return 1
    except Exception as e:
        log(f"打包失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
