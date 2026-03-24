# -*- coding: utf-8 -*-
"""
功率器件参数提取系统 - 桌面窗口启动器（选项 C）
在独立窗口中运行 Streamlit 应用，无需打开浏览器。
"""
import os
import sys
import time
import signal
import subprocess
import urllib.request
from pathlib import Path

# 便携式：以本脚本所在目录为工作目录
APP_ROOT = Path(__file__).resolve().parent
os.chdir(APP_ROOT)
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# 创建必要目录
for d in ("data", "logs", "output", "cache"):
    (APP_ROOT / d).mkdir(exist_ok=True)

PORT = 8501
URL = f"http://127.0.0.1:{PORT}"
MAX_WAIT = 60
POLL_INTERVAL = 0.5


def wait_for_server():
    """等待 Streamlit 服务就绪"""
    for _ in range(int(MAX_WAIT / POLL_INTERVAL)):
        try:
            urllib.request.urlopen(URL, timeout=2)
            return True
        except Exception:
            time.sleep(POLL_INTERVAL)
    return False


def main():
    python_exe = sys.executable
    # 嵌入式 Python 便携版：若在 python 子目录下存在 python.exe，则用其路径
    if (APP_ROOT / "python" / "python.exe").exists():
        python_exe = str(APP_ROOT / "python" / "python.exe")

    cmd = [
        python_exe, "-m", "streamlit", "run", "main.py",
        "--server.port", str(PORT),
        "--server.headless", "true",
        "--server.address", "127.0.0.1",
        "--browser.gatherUsageStats", "false",
    ]
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    kwargs = {"cwd": str(APP_ROOT), "env": env}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(cmd, **kwargs)

    try:
        if not wait_for_server():
            print("启动超时，请检查端口是否被占用。")
            proc.terminate()
            proc.wait(timeout=5)
            return 1
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait(timeout=5)
        return 0

    try:
        import webview
        webview.create_window("功率器件参数提取系统", URL, width=1280, height=800)
        webview.start()
    except ImportError:
        print("未安装 pywebview，请运行: pip install pywebview")
        print("将使用默认浏览器打开...")
        if sys.platform == "win32":
            os.startfile(URL)
        else:
            import webbrowser
            webbrowser.open(URL)
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
        return 0

    # 窗口关闭后结束 Streamlit
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
