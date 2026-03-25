# -*- coding: utf-8 -*-
"""
ALTOOL V3 - main.py 集成补丁

集成前端组件到新系统
使用方法：在main.py中导入此模块
"""

import streamlit as st
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入前端组件
try:
    from frontend.dashboard import Dashboard, render_dashboard_page
    from frontend.progress import ProgressWidget, BatchProgressTracker
    from frontend.guide import UserGuide, check_and_show_guide, render_guide_button
    FRONTEND_AVAILABLE = True
except ImportError as e:
    print(f"前端组件导入失败: {e}")
    FRONTEND_AVAILABLE = False


def render_dashboard_page_wrapper():
    """
    渲染仪表盘页面（包装函数）
    在main.py中添加页面路由时调用
    """
    if not FRONTEND_AVAILABLE:
        st.error("仪表盘组件未加载")
        return
    
    # 获取数据库管理器
    try:
        from backend.db_manager import DatabaseManager
        db_manager = DatabaseManager()
    except:
        db_manager = None
    
    # 渲染仪表盘
    render_dashboard_page(db_manager)


def show_user_guide(user_id: str = None):
    """
    显示用户引导
    在main.py的适当位置调用（如首次登录）
    
    Args:
        user_id: 用户ID，默认使用session_state中的user_id
    """
    if not FRONTEND_AVAILABLE:
        return
    
    if user_id is None:
        user_id = st.session_state.get('user_id', 'default')
    
    if check_and_show_guide(user_id):
        st.info("👆 请查看上方的新手引导")


def render_batch_progress(files: list, title: str = "批量处理"):
    """
    渲染批量处理进度（简化版）
    在解析任务中使用
    
    Args:
        files: 文件列表
        title: 任务标题
    """
    if not FRONTEND_AVAILABLE:
        # 使用原生Streamlit进度条
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        for i, file in enumerate(files):
            progress_text.text(f"处理: {file}")
            progress_bar.progress((i + 1) / len(files))
        
        progress_text.success(f"完成: {len(files)} 个文件")
        return
    
    # 使用高级进度组件
    tracker = BatchProgressTracker(files, title)
    return tracker


# ==================== 菜单配置 ====================

def get_updated_pages():
    """
    获取更新后的页面列表
    在main.py中替换原有的pages列表
    """
    pages = [
        '仪表盘',      # 新增
        '解析任务',
        '数据中心',
        '参数管理',
        '生成表格',
        '系统设置',
        '个人中心',
    ]
    return pages


def get_page_icons():
    """
    获取页面图标
    """
    return {
        '仪表盘': '📊',
        '解析任务': '🔍',
        '数据中心': '💾',
        '参数管理': '⚙️',
        '生成表格': '📋',
        '系统设置': '🔧',
        '个人中心': '👤',
    }


# ==================== 集成说明 ====================
"""
在main.py中添加以下内容：

1. 导入集成模块（在文件顶部）:
   from main_integration import (
       render_dashboard_page_wrapper,
       show_user_guide,
       get_updated_pages,
       get_page_icons
   )

2. 更新页面列表（找到pages定义的地方）:
   pages = get_updated_pages()

3. 添加仪表盘页面路由（在页面路由部分）:
   elif st.session_state.current_page == '仪表盘':
       render_dashboard_page_wrapper()

4. 显示新手引导（在登录成功后的地方）:
   show_user_guide()

5. 在侧边栏菜单添加仪表盘（如果还没有）:
   在get_page_icons中添加 '仪表盘': '📊'
"""


if __name__ == "__main__":
    print("=== main.py 集成补丁 ===")
    print()
    print("此模块提供以下功能:")
    print("  1. render_dashboard_page_wrapper() - 仪表盘页面")
    print("  2. show_user_guide() - 新手引导")
    print("  3. render_batch_progress() - 批量进度")
    print("  4. get_updated_pages() - 更新页面列表")
    print()
    print("前端组件可用:", FRONTEND_AVAILABLE)
    print()
    print("使用方法: 在main.py中导入并调用相应函数")
