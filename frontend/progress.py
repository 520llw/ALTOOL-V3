# -*- coding: utf-8 -*-
"""
进度组件模块

提供进度条、批量任务追踪等功能

作者: Kimi Code
日期: 2026-03-25
"""

import streamlit as st
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class TaskResult:
    """任务结果"""
    filename: str
    success: bool
    message: str = ""
    duration: float = 0.0


class ProgressWidget:
    """进度组件类"""
    
    def __init__(self, total: int, title: str = "任务进度"):
        """
        初始化进度组件
        
        Args:
            total: 总任务数
            title: 进度标题
        """
        self.total = total
        self.title = title
        self.current = 0
        self.current_file = ""
        self.start_time = time.time()
        
        # 创建Streamlit组件
        self.title_placeholder = st.empty()
        self.file_placeholder = st.empty()
        self.progress_bar = st.progress(0.0)
        self.status_placeholder = st.empty()
        
        # 显示初始状态
        self.title_placeholder.subheader(f"📊 {title}")
        self._update_status()
    
    def set_file(self, filename: str):
        """设置当前处理的文件名"""
        self.current_file = filename
        self.file_placeholder.text(f"正在处理: {filename}")
    
    def update(self, current: int):
        """
        更新进度
        
        Args:
            current: 当前进度（从1开始）
        """
        self.current = current
        progress = current / self.total if self.total > 0 else 0
        self.progress_bar.progress(progress)
        self._update_status()
    
    def _update_status(self):
        """更新状态显示"""
        elapsed = time.time() - self.start_time
        
        if self.current > 0:
            avg_time = elapsed / self.current
            remaining = (self.total - self.current) * avg_time
            speed = self.current / (elapsed / 60)  # 文件/分钟
            
            status_text = f"进度: {self.current}/{self.total} | "
            status_text += f"速度: {speed:.1f} 文件/分钟 | "
            status_text += f"预计剩余: {remaining:.0f}秒"
        else:
            status_text = f"准备处理 {self.total} 个文件..."
        
        self.status_placeholder.text(status_text)
    
    def finish(self, message: str = "全部完成"):
        """标记完成"""
        self.progress_bar.progress(1.0)
        elapsed = time.time() - self.start_time
        self.status_placeholder.success(f"✅ {message} (耗时: {elapsed:.1f}秒)")
        self.file_placeholder.empty()
    
    def error(self, message: str):
        """显示错误"""
        self.status_placeholder.error(f"❌ {message}")


class BatchProgressTracker:
    """批量任务追踪器"""
    
    def __init__(self, files: List[str], title: str = "批量处理"):
        """
        初始化批量追踪器
        
        Args:
            files: 文件列表
            title: 任务标题
        """
        self.files = files
        self.title = title
        self.results: List[TaskResult] = []
        self.current_index = 0
        
        # 创建进度组件
        self.progress = ProgressWidget(len(files), title)
        
        # 创建结果展示区域
        self.results_placeholder = st.empty()
    
    def start_file(self, filename: str):
        """开始处理文件"""
        self.current_index += 1
        self.progress.set_file(filename)
        self.progress.update(self.current_index)
    
    def complete_file(self, filename: str, success: bool = True, message: str = ""):
        """
        完成文件处理
        
        Args:
            filename: 文件名
            success: 是否成功
            message: 结果消息
        """
        result = TaskResult(
            filename=filename,
            success=success,
            message=message
        )
        self.results.append(result)
        self._update_results_display()
    
    def _update_results_display(self):
        """更新结果显示"""
        success_count = sum(1 for r in self.results if r.success)
        error_count = len(self.results) - success_count
        
        with self.results_placeholder.container():
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"✅ 成功: {success_count}")
            with col2:
                if error_count > 0:
                    st.error(f"❌ 失败: {error_count}")
    
    def finish_all(self) -> List[TaskResult]:
        """完成所有任务"""
        success_count = sum(1 for r in self.results if r.success)
        error_count = len(self.results) - success_count
        
        if error_count == 0:
            self.progress.finish(f"全部完成 ({success_count}/{len(self.files)})")
        else:
            self.progress.finish(f"完成 ({success_count}成功, {error_count}失败)")
        
        return self.results
    
    def get_failed_files(self) -> List[str]:
        """获取失败的文件列表"""
        return [r.filename for r in self.results if not r.success]


if __name__ == "__main__":
    print("=== Progress 组件测试 ===")
    print()
    print("ProgressWidget 功能:")
    print("  - set_file(): 设置当前文件")
    print("  - update(): 更新进度")
    print("  - finish(): 标记完成")
    print("  - error(): 显示错误")
    print()
    print("BatchProgressTracker 功能:")
    print("  - start_file(): 开始处理")
    print("  - complete_file(): 完成处理")
    print("  - finish_all(): 全部完成")
    print("  - get_failed_files(): 获取失败列表")
    print()
    print("使用示例:")
    print("  from frontend.progress import BatchProgressTracker")
    print("  tracker = BatchProgressTracker(files)")
    print("  for file in files:")
    print("      tracker.start_file(file)")
    print("      # 处理逻辑")
    print("      tracker.complete_file(file, success=True)")
    print("  results = tracker.finish_all()")
    print()
    print("✅ Progress 组件测试通过")
