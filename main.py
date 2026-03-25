# -*- coding: utf-8 -*-
"""
功率器件参数提取系统 - 主程序入口
基于Streamlit构建的Web界面
包含登录认证、个人中心、权限控制功能
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import config, Config, OUTPUT_DIR, DATA_DIR
from backend.db_manager import DatabaseManager, User, UserLog
from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor
from backend.data_writer import DataWriter
from backend.user_manager import UserManager
from backend.cache_manager import get_cache_manager
from backend.backup_manager import get_backup_manager
from backend.security import get_security_manager

# 导入前端组件
try:
    from frontend.dashboard import Dashboard, render_dashboard_page
    from frontend.progress import ProgressWidget, BatchProgressTracker
    from frontend.guide import UserGuide, check_and_show_guide
    FRONTEND_AVAILABLE = True
except ImportError:
    FRONTEND_AVAILABLE = False

# 导入优化模块（简化版）
try:
    from backend.optimize_tools import (
        initialize_optimization, get_device_icon, get_device_color
    )
    OPTIMIZE_AVAILABLE = True
except ImportError:
    OPTIMIZE_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / 'logs' / 'app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="功率器件参数提取系统",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义提示组件 ====================
def show_toast(message: str, type: str = "info"):
    """
    显示提示消息 - 使用 Streamlit 原生 toast，更轻量、不阻塞渲染
    
    Args:
        message: 提示文字
        type: 类型 - info/success/warning/error
    """
    icons = {
        "info": "💡",
        "success": "✨",
        "warning": "⚠️",
        "error": "❌"
    }
    icon = icons.get(type, "💡")
    st.toast(f"{icon} {message}")


# ==================== 自定义CSS样式 ====================
@st.cache_data
def _get_custom_css() -> str:
    """构建并缓存CSS字符串，避免每次rerun重复拼接"""
    return """
    <style>
    /* ========== 全局流畅度优化 ========== */
    
    /* 平滑滚动 + 渲染优化 */
    html {
        scroll-behavior: smooth;
    }
    
    /* GPU 加速渲染 - 仅标记关键容器 */
    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"] {
        will-change: transform;
        contain: layout style;
    }
    
    /* 页面内容淡入动画 - 缩短到 150ms 提升感知速度 */
    @keyframes fadeInContent {
        from { opacity: 0.6; }
        to   { opacity: 1; }
    }
    .main .block-container {
        animation: fadeInContent 0.15s ease-out;
    }
    
    /* 主色调 */
    :root {
        --primary-color: #1E3A8A;
        --accent-color: #3B82F6;
        --warning-color: #F59E0B;
        --background-color: #F3F4F6;
        --text-color: #1F2937;
        --success-color: #10B981;
        --error-color: #EF4444;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #E5E7EB;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }
    
    /* 侧边栏标题 */
    .sidebar-title {
        font-size: 20px;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #E5E7EB;
        margin-bottom: 1rem;
    }
    
    /* 导航按钮样式 */
    .nav-button {
        display: block;
        width: 100%;
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        border: none;
        border-radius: 8px;
        background-color: #F3F4F6;
        color: #1F2937;
        font-size: 14px;
        text-align: left;
        cursor: pointer;
        transition: background-color 0.15s ease;
    }
    
    .nav-button:hover {
        background-color: #E5E7EB;
    }
    
    .nav-button.active {
        background-color: #3B82F6;
        color: white;
    }
    
    /* 版本信息 */
    .version-info {
        position: fixed;
        bottom: 1rem;
        left: 1rem;
        font-size: 12px;
        color: #9CA3AF;
    }
    
    /* 卡片样式 */
    .card {
        background-color: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* 统计数字 */
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
    }
    
    .stat-label {
        font-size: 0.875rem;
        color: #6B7280;
    }
    
    /* 进度条 - 使用 GPU 加速的 transform 代替 width */
    .stProgress > div > div > div > div {
        background-color: #3B82F6;
        transition: width 0.3s ease;
    }
    
    /* 成功消息 */
    .success-message {
        background-color: #DCFCE7;
        border-left: 4px solid #10B981;
        padding: 1rem;
        border-radius: 4px;
    }
    
    /* 错误消息 */
    .error-message {
        background-color: #FEE2E2;
        border-left: 4px solid #EF4444;
        padding: 1rem;
        border-radius: 4px;
    }
    
    /* 表格样式 */
    .dataframe {
        font-size: 13px;
    }
    
    /* 按钮样式 - 简化过渡属性 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: background-color 0.1s ease, box-shadow 0.1s ease;
    }
    
    .stButton > button:hover {
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    
    .stButton > button[kind="primary"] {
        background-color: #1E3A8A;
    }
    
    /* 选项卡切换过渡 - 缩短动画 */
    .stTabs [data-baseweb="tab-panel"] {
        animation: fadeInContent 0.1s ease-out;
    }
    
    /* 弹出框/对话框过渡 */
    [data-testid="stModal"] > div {
        animation: fadeInContent 0.15s ease-out;
    }
    
    /* Expander 展开过渡 */
    .streamlit-expanderContent {
        animation: fadeInContent 0.1s ease-out;
    }
    
    /* 输入框聚焦过渡 */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    
    /* 侧边栏收起按钮增强 */
    [data-testid="stSidebarCollapseButton"] button,
    button[aria-label="Close sidebar"] {
        background: #F3F4F6 !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 6px !important;
        width: 32px !important;
        height: 32px !important;
        transition: background-color 0.15s ease !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover,
    button[aria-label="Close sidebar"]:hover {
        background: #E5E7EB !important;
        border-color: #3B82F6 !important;
    }
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 隐藏顶部的 rerun 提示条，减少视觉干扰 */
    .stStatusWidget {
        visibility: hidden;
        height: 0;
        position: fixed;
    }
    
    /* 减少元素间布局抖动 */
    [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    </style>
    """


def load_custom_css():
    """加载自定义CSS样式（已缓存）"""
    st.markdown(_get_custom_css(), unsafe_allow_html=True)


# ==================== 初始化Session State ====================
def init_session_state():
    """初始化Session State"""
    defaults = {
        # 登录相关
        'logged_in': False,
        'user_id': None,
        'username': None,
        'user_role': None,
        'remember_me': False,
        
        # 页面导航
        'current_page': '解析任务',
        
        # 解析相关
        'pdf_folder': '',
        'device_types': ['Si MOSFET', 'SiC MOSFET', 'IGBT'],
        'parsing': False,
        'cancel_parsing': False,
        'parse_progress': 0,
        'parse_results': [],
        'parse_stats': {'success': 0, 'failed': 0, 'total': 0},
        'show_confirm_parse': False,
        'show_confirm_clear': False,
        'show_confirm_delete': False,
        'delete_param_id': None,
        'edit_param_id': None,
        'log_filters': {
            'start_date': datetime.now() - timedelta(days=7),
            'end_date': datetime.now(),
            'log_type': '全部',
            'search_text': ''
        },
        
        # AI配置
        'ai_provider': config.ai.provider,
        'ai_model': config.ai.model,
        'ai_api_key': config.ai.api_key,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # 安全重置：如果 parsing 卡在 True（后台线程已崩溃或不存在），强制恢复
    # 仅在确实处于 parsing 状态时才执行线程检查，降低正常 rerun 开销
    if st.session_state.get('parsing'):
        thread_id = st.session_state.get('_parsing_thread_id')
        shared = st.session_state.get('_bg_shared')
        
        if thread_id is None:
            # 没有记录线程ID（旧session残留），直接重置
            st.session_state.parsing = False
            st.session_state.parse_status = "⚠️ 上次解析异常中断，已自动恢复"
        elif thread_id == 'pending':
            # 线程即将创建（用户刚点击了开始按钮），不要重置
            pass
        else:
            # 先检查 shared 字典：后台线程是否已标记完成（快速路径，无需遍历线程）
            if shared and not shared.get('parsing', True):
                # 后台线程已正常完成，同步结果
                st.session_state.parsing = False
                st.session_state.parse_progress = shared.get('progress', 100)
                st.session_state.parse_status = shared.get('status', '✅ 完成')
                st.session_state.parse_results = shared.get('results', [])
                st.session_state.parse_stats = shared.get('stats', {})
                st.session_state._bg_shared = None
            else:
                # 只有 shared 仍显示 parsing 时，才遍历线程列表检查是否存活
                import threading
                alive = any(t.ident == thread_id and t.is_alive()
                             for t in threading.enumerate())
                if not alive:
                    st.session_state.parsing = False
                    if shared:
                        st.session_state.parse_status = shared.get('status', "⚠️ 上次解析异常中断，已自动恢复")
                        st.session_state.parse_results = shared.get('results', [])
                        st.session_state.parse_stats = shared.get('stats', {})
                        st.session_state._bg_shared = None
                    else:
                        st.session_state.parse_status = "⚠️ 上次解析异常中断，已自动恢复"
    
    # 初始化默认管理员账号（只执行一次）
    if not st.session_state.get('_admin_initialized'):
        user_manager = get_cached_user_manager()
        user_manager.init_default_admin()
        st.session_state._admin_initialized = True


# ==================== 缓存组件初始化 ====================
@st.cache_resource
def get_cached_pdf_parser():
    """缓存PDFParser实例，避免重复创建"""
    return PDFParser()

@st.cache_resource
def get_cached_ai_processor():
    """缓存AIProcessor实例，避免重复创建"""
    return AIProcessor()

@st.cache_resource
def get_cached_db_manager():
    """缓存DatabaseManager实例，避免重复创建"""
    return DatabaseManager()

@st.cache_resource
def get_cached_user_manager():
    """缓存UserManager实例，避免重复创建"""
    return UserManager()

@st.cache_data(ttl=600)  # 缓存10分钟，参数库变动不频繁
def get_cached_params_info():
    """缓存参数库信息，减少数据库查询"""
    db_manager = get_cached_db_manager()
    return db_manager.get_all_params_with_variants()

@st.cache_data(ttl=30)  # 缓存30秒，侧边栏统计不需要实时
def get_cached_parse_statistics(user_id: int = None):
    """缓存解析统计信息，减少侧边栏重复查询（按用户隔离）"""
    db_manager = get_cached_db_manager()
    return db_manager.get_parse_statistics(user_id=user_id)


# ==================== 工具函数 ====================
def get_folder_list(path: str) -> tuple:
    """获取文件夹列表和PDF文件列表"""
    folders = []
    pdf_files = []
    try:
        items = sorted(os.listdir(path))
        for item in items:
            if item.startswith('.'):
                continue
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                folders.append(item)
            elif item.lower().endswith('.pdf'):
                pdf_files.append(item)
    except PermissionError:
        pass
    return folders, pdf_files


def count_pdf_files(folder_path: str) -> int:
    """统计文件夹中的PDF文件数量"""
    if not folder_path or not os.path.exists(folder_path):
        return 0
    count = 0
    try:
        for f in os.listdir(folder_path):
            if f.lower().endswith('.pdf'):
                count += 1
    except:
        pass
    return count


@st.dialog("📂 选择文件夹", width="large")
def folder_browser_dialog(start_path: str = "/home/gjw"):
    """文件夹浏览器弹窗"""
    
    # 初始化当前路径
    if 'dialog_current_path' not in st.session_state:
        st.session_state.dialog_current_path = start_path
    
    current_path = st.session_state.dialog_current_path
    
    # 确保路径存在
    if not os.path.exists(current_path):
        current_path = "/home/gjw"
        st.session_state.dialog_current_path = current_path
    
    # 顶部导航栏
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("⬆️ 上级", use_container_width=True):
            parent = os.path.dirname(current_path)
            if parent:
                st.session_state.dialog_current_path = parent
                st.rerun()
    with col2:
        # 路径输入框
        new_path = st.text_input("路径", value=current_path, label_visibility="collapsed")
        if new_path != current_path and os.path.exists(new_path):
            st.session_state.dialog_current_path = new_path
            st.rerun()
    with col3:
        if st.button("🏠 主目录", use_container_width=True):
            st.session_state.dialog_current_path = "/home/gjw"
            st.rerun()
    
    st.divider()
    
    # 获取文件夹内容
    folders, pdf_files = get_folder_list(current_path)
    
    # 显示文件夹（使用容器模拟列表）
    st.markdown("**📁 文件夹**")
    
    if folders:
        # 创建一个滚动容器
        folder_container = st.container(height=250)
        with folder_container:
            for idx, folder in enumerate(folders):
                col1, col2 = st.columns([6, 1])
                with col1:
                    if st.button(f"📁  {folder}", key=f"folder_{idx}", use_container_width=True):
                        st.session_state.dialog_current_path = os.path.join(current_path, folder)
                        st.rerun()
                with col2:
                    st.caption("")
    else:
        st.caption("（空）")
    
    st.divider()
    
    # 显示当前文件夹的PDF文件数量
    if pdf_files:
        st.success(f"✅ 此文件夹包含 **{len(pdf_files)}** 个PDF文件: {', '.join(pdf_files[:5])}{'...' if len(pdf_files) > 5 else ''}")
    else:
        st.warning("⚠️ 此文件夹没有PDF文件")
    
    # 底部按钮
    st.divider()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**当前选择:** `{current_path}`")
    with col2:
        if st.button("❌ 取消", use_container_width=True):
            del st.session_state.dialog_current_path
            st.rerun()
    with col3:
        if st.button("✅ 确定选择", type="primary", use_container_width=True):
            st.session_state.pdf_folder = current_path
            st.session_state.dialog_current_path = start_path
            st.rerun()


# ==================== 登录页面 ====================
def render_login_page():
    """渲染登录页面 - 新增密码强度检测和登录锁定提示"""
    # 登录页面样式 - 简洁版
    st.markdown("""
    <style>
    .login-title {
        text-align: center;
        color: #1E3A8A;
        font-size: 26px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .login-subtitle {
        text-align: center;
        color: #6B7280;
        margin-bottom: 24px;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 初始化登录/注册切换状态
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    
    # 居中显示表单
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("")
        st.markdown("")
        
        # 标题
        st.markdown('<div class="login-title">⚡ 功率器件参数提取系统</div>', unsafe_allow_html=True)
        
        # 获取安全管理器
        security_manager = get_security_manager()
        user_manager = get_cached_user_manager()
        
        if st.session_state.show_register:
            # ========== 注册表单 ==========
            st.markdown('<div class="login-subtitle">创建新账号</div>', unsafe_allow_html=True)
            
            with st.form("register_form"):
                reg_username = st.text_input("👤 用户名", placeholder="3-20个字符")
                reg_password = st.text_input("🔒 密码", type="password", placeholder="至少6位")
                reg_password2 = st.text_input("🔒 确认密码", type="password", placeholder="再次输入密码")
                
                # 密码强度实时显示
                if reg_password:
                    feedback = security_manager.get_password_strength_feedback(reg_password)
                    color = feedback['color']
                    score = feedback['score']
                    
                    st.markdown(f"""
                    <div style="margin: 8px 0;">
                        <div style="font-size: 12px; color: #6B7280; margin-bottom: 4px;">
                            密码强度: <span style="color: {color}; font-weight: bold;">{feedback['level_name']}</span>
                        </div>
                        <div style="width: 100%; height: 6px; background: #E5E7EB; border-radius: 3px;">
                            <div style="width: {score}%; height: 100%; background: {color}; border-radius: 3px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if feedback['suggestions']:
                        with st.expander("💡 改进建议", expanded=False):
                            for suggestion in feedback['suggestions']:
                                st.caption(f"• {suggestion}")
                
                submitted = st.form_submit_button("📝 注 册", use_container_width=True, type="primary")
                
                if submitted:
                    if not reg_username or not reg_password or not reg_password2:
                        show_toast("请填写所有字段", "warning")
                    elif len(reg_username) < 3 or len(reg_username) > 20:
                        show_toast("用户名需要3-20个字符", "warning")
                    elif len(reg_password) < 6:
                        show_toast("密码至少需要6位", "warning")
                    elif reg_password != reg_password2:
                        show_toast("两次输入的密码不一致", "warning")
                    else:
                        # 检查密码强度
                        feedback = security_manager.get_password_strength_feedback(reg_password)
                        if not feedback['is_acceptable']:
                            show_toast(f"密码强度太弱，请加强密码", "warning")
                        else:
                            success, message = user_manager.create_user(reg_username, reg_password, "user")
                            
                            if success:
                                st.session_state.show_register = False
                                st.toast(f"{message}，请登录")
                                st.rerun()
                            else:
                                show_toast(message, "error")
            
            st.markdown("---")
            if st.button("⬅️ 返回登录", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()
        
        else:
            # ========== 登录表单 ==========
            st.markdown('<div class="login-subtitle">请登录以继续使用</div>', unsafe_allow_html=True)
            
            # 显示锁定提示（如果有）
            if 'login_username' in st.session_state and st.session_state.login_username:
                is_locked, remaining = security_manager.is_account_locked(st.session_state.login_username)
                if is_locked:
                    minutes = remaining // 60
                    seconds = remaining % 60
                    st.error(f"🔒 账号已被锁定，请等待 {minutes}分{seconds}秒 后重试")
            
            with st.form("login_form"):
                username = st.text_input("👤 用户名", placeholder="请输入用户名")
                password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
                
                # 保存用户名用于锁定检查
                if username:
                    st.session_state.login_username = username
                
                col_a, col_b = st.columns(2)
                with col_a:
                    remember_me = st.checkbox("记住我", value=False)
                
                submitted = st.form_submit_button("🔐 登 录", use_container_width=True, type="primary")
                
                if submitted:
                    if not username or not password:
                        show_toast("请填写用户名和密码后登录", "warning")
                    else:
                        # 检查账号是否被锁定
                        is_locked, remaining = security_manager.is_account_locked(username)
                        if is_locked:
                            minutes = remaining // 60
                            seconds = remaining % 60
                            show_toast(f"账号已被锁定，请{minutes}分{seconds}秒后重试", "error")
                        else:
                            success, message, user = user_manager.authenticate(username, password)
                            
                            # 记录登录尝试
                            security_manager.record_login_attempt(username, success)
                            
                            if success:
                                st.session_state.logged_in = True
                                st.session_state.user_id = user.id
                                st.session_state.username = user.username
                                st.session_state.user_role = user.role
                                st.session_state.remember_me = remember_me
                                # 加载用户专属API密钥（为空则使用系统默认）
                                user_key = user_manager.get_user_api_key(user.id)
                                st.session_state.ai_api_key = user_key if user_key else config.ai.api_key
                                st.rerun()
                            else:
                                # 检查锁定状态
                                is_now_locked, remaining = security_manager.is_account_locked(username)
                                if is_now_locked:
                                    show_toast(f"密码错误次数过多，账号已锁定", "error")
                                else:
                                    # 获取剩余尝试次数
                                    attempt_info = security_manager.get_login_attempts_info(username)
                                    remaining_attempts = 5 - attempt_info['failed_count']
                                    if remaining_attempts > 0:
                                        show_toast(f"{message}，还剩{remaining_attempts}次机会", "error")
                                    else:
                                        show_toast(message, "error")
            
            st.markdown("---")
            
            # 注册按钮
            if st.button("📝 没有账号？点击注册", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()


# ==================== 个人中心页面 ====================
def render_profile_page():
    """渲染个人中心页面 - 新增密码强度检测和数据备份恢复"""
    
    user_manager = get_cached_user_manager()
    backup_manager = get_backup_manager()
    security_manager = get_security_manager()
    user = user_manager.get_user_by_id(st.session_state.user_id)
    
    if not user:
        show_toast("用户信息获取失败", "error")
        return
    
    st.title("👤 个人中心")
    
    # 基本信息
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**用户名：** {user.username}")
        st.markdown(f"**角色：** {'🔑 管理员' if user.role == 'admin' else '👤 普通用户'}")
    with col2:
        st.markdown(f"**注册时间：** {user.created_at.strftime('%Y-%m-%d') if user.created_at else '-'}")
        st.markdown(f"**上次登录：** {user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '-'}")
    
    st.markdown("---")
    
    # 修改密码（带强度检测）
    st.subheader("🔐 修改密码")
    
    # 初始化密码强度状态
    if 'pwd_strength_feedback' not in st.session_state:
        st.session_state.pwd_strength_feedback = None
    
    with st.form("change_pwd_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            old_pwd = st.text_input("原密码", type="password")
        with col2:
            new_pwd = st.text_input("新密码", type="password", help="至少6位")
            
            # 实时显示密码强度
            if new_pwd:
                feedback = security_manager.get_password_strength_feedback(new_pwd)
                st.session_state.pwd_strength_feedback = feedback
                
                # 显示强度条
                color = feedback['color']
                score = feedback['score']
                st.markdown(f"""
                <div style="margin-top: 8px;">
                    <div style="font-size: 12px; color: #6B7280; margin-bottom: 4px;">
                        密码强度: <span style="color: {color}; font-weight: bold;">{feedback['level_name']}</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: #E5E7EB; border-radius: 3px;">
                        <div style="width: {score}%; height: 100%; background: {color}; border-radius: 3px; transition: all 0.3s;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 显示建议
                if feedback['suggestions']:
                    with st.expander("💡 改进建议"):
                        for suggestion in feedback['suggestions']:
                            st.caption(f"• {suggestion}")
        
        if st.form_submit_button("确认修改"):
            if old_pwd and new_pwd:
                # 检查密码强度
                feedback = security_manager.get_password_strength_feedback(new_pwd)
                if not feedback['is_acceptable']:
                    show_toast(f"密码强度太弱: {', '.join(feedback['suggestions'][:2])}", "warning")
                else:
                    success, msg = user_manager.change_password(st.session_state.user_id, old_pwd, new_pwd)
                    show_toast(msg, "success" if success else "error")
            else:
                show_toast("请填写完整", "warning")
    
    st.markdown("---")
    
    # 数据备份/恢复
    st.subheader("💾 数据备份与恢复")
    
    backup_tab1, backup_tab2 = st.tabs(["创建备份", "恢复备份"])
    
    with backup_tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            backup_name = st.text_input("备份名称（可选）", placeholder="留空自动生成时间戳名称")
        with col2:
            if st.button("📦 创建备份", type="primary", use_container_width=True):
                try:
                    with st.spinner("正在创建备份..."):
                        name = backup_name.strip() if backup_name else None
                        backup_path = backup_manager.create_backup(name)
                    show_toast(f"备份创建成功！", "success")
                    st.markdown(f"**备份路径：** `{backup_path}`")
                except Exception as e:
                    show_toast(f"备份失败: {e}", "error")
    
    with backup_tab2:
        backups = backup_manager.list_backups()
        
        if not backups:
            st.info("暂无备份文件")
        else:
            st.caption(f"共 {len(backups)} 个备份")
            
            for backup in backups:
                with st.expander(f"📦 {backup['name']} ({backup['size_mb']} MB)", expanded=False):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**创建时间：** {backup['created_at'][:19]}")
                        st.write(f"**文件大小：** {backup['size_mb']} MB")
                        st.write(f"**路径：** `{backup['path']}`")
                    with col2:
                        if st.button("🔄 恢复", key=f"restore_{backup['name']}", use_container_width=True):
                            confirm_key = f"confirm_restore_{backup['name']}"
                            st.session_state[confirm_key] = True
                            st.rerun()
                    with col3:
                        if st.button("🗑️ 删除", key=f"delete_{backup['name']}", use_container_width=True):
                            if backup_manager.delete_backup(backup['path']):
                                show_toast("备份已删除", "success")
                                st.rerun()
                            else:
                                show_toast("删除失败", "error")
                    
                    # 确认恢复
                    confirm_key = f"confirm_restore_{backup['name']}"
                    if st.session_state.get(confirm_key):
                        st.warning("⚠️ 恢复将覆盖当前数据，确定要继续吗？")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("确认恢复", key=f"yes_restore_{backup['name']}", type="primary", use_container_width=True):
                                with st.spinner("正在恢复数据..."):
                                    success = backup_manager.restore_backup(backup['path'])
                                    if success:
                                        st.session_state[confirm_key] = False
                                        show_toast("数据恢复成功！请刷新页面", "success")
                                    else:
                                        show_toast("恢复失败", "error")
                        with col_no:
                            if st.button("取消", key=f"no_restore_{backup['name']}", use_container_width=True):
                                st.session_state[confirm_key] = False
                                st.rerun()
    
    # 管理员功能
    if user.role == 'admin':
        st.markdown("---")
        st.subheader("🔑 用户管理")
        
        # 新增用户
        with st.form("add_user_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            with c1:
                new_username = st.text_input("用户名", placeholder="新用户名", label_visibility="collapsed")
            with c2:
                new_password = st.text_input("密码", type="password", placeholder="密码", label_visibility="collapsed")
            with c3:
                new_role = st.selectbox("角色", ["user", "admin"], label_visibility="collapsed")
            with c4:
                if st.form_submit_button("➕ 添加"):
                    if new_username and new_password:
                        success, msg = user_manager.create_user(new_username, new_password, new_role)
                        show_toast(msg, "success" if success else "error")
                        if success:
                            st.rerun()
        
        # 用户列表
        users = user_manager.get_all_users()
        for u in users:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                status = "🟢" if u.is_active else "🔴"
                role = "🔑" if u.role == 'admin' else "👤"
                st.markdown(f"{status} {role} **{u.username}**")
            with col2:
                if u.username != 'admin':
                    if st.button("禁用" if u.is_active else "启用", key=f"s_{u.id}"):
                        user_manager.update_user_status(u.id, not u.is_active)
                        st.rerun()
            with col3:
                if u.username != 'admin':
                    if st.button("设管理员" if u.role == 'user' else "设普通", key=f"r_{u.id}"):
                        user_manager.update_user_role(u.id, "admin" if u.role == "user" else "user")
                        st.rerun()


# ==================== 侧边栏 ====================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # 系统标题
        st.markdown('<div class="sidebar-title">⚡ 功率器件参数提取系统</div>', unsafe_allow_html=True)
        
        # 用户信息
        if st.session_state.logged_in:
            st.markdown(f"""
            <div style="text-align: center; padding: 12px; background: #F3F4F6; border-radius: 8px; margin-bottom: 10px;">
                <span style="font-size: 24px;">👤</span><br>
                <strong style="color: #1F2937; font-size: 15px;">{st.session_state.username}</strong><br>
                <small style="color: #6B7280;">{'🔑 管理员' if st.session_state.user_role == 'admin' else '普通用户'}</small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 导航菜单（优化后的6个页面）
        pages = ['仪表盘', '解析任务', '数据中心', '参数管理', '生成表格', '系统设置', '个人中心']
        icons = ['📊', '🔍', '💾', '⚙️', '📋', '🔧', '👤']
        
        # 解析中显示状态提示
        is_parsing = st.session_state.get('parsing', False)
        if is_parsing:
            st.info("🔄 后台解析中...")
        
        for page, icon in zip(pages, icons):
            is_active = st.session_state.current_page == page
            button_type = "primary" if is_active else "secondary"
            
            if st.button(f"{icon} {page}", key=f"nav_{page}", use_container_width=True, 
                        type=button_type, disabled=is_active):
                st.session_state.current_page = page
                st.rerun()
        
        st.markdown("---")
        
        # 退出登录按钮
        if st.button("🚪 退出登录", use_container_width=True):
            user_manager = get_cached_user_manager()
            user_manager.logout(st.session_state.user_id)
            
            # 清除登录状态
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.user_role = None
            
            # 清除用户数据缓存（数据隔离）
            st.session_state.parse_results = []
            st.session_state.parse_stats = {}
            st.session_state.pdf_folder = None
            st.session_state.dc_selected_pdf = None
            st.session_state.dc_pdf_search = ''
            st.session_state.dc_param_search = ''
            st.session_state.dc_active_search = False
            
            st.rerun()
        
        st.markdown("---")
        
        # 快速状态（使用缓存，30秒刷新一次，按用户过滤）
        stats = get_cached_parse_statistics(user_id=st.session_state.user_id)
        
        st.markdown(f"""
        <div style="display:flex; gap:12px; text-align:center;">
            <div style="flex:1; background:#F3F4F6; border-radius:8px; padding:8px 4px;">
                <div style="font-size:22px; font-weight:bold; color:#1E3A8A;">{stats['unique_pdfs']}</div>
                <div style="font-size:11px; color:#6B7280;">已解析PDF</div>
            </div>
            <div style="flex:1; background:#F3F4F6; border-radius:8px; padding:8px 4px;">
                <div style="font-size:22px; font-weight:bold; color:#1E3A8A;">{stats['total_params']}</div>
                <div style="font-size:11px; color:#6B7280;">提取参数</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 版本信息
        st.markdown("---")
        st.markdown(
            '<div style="font-size: 12px; color: #9CA3AF; text-align: center; margin-top: 8px;">'
            '版本 v1.0<br>支持 Si/SiC MOSFET、IGBT'
            '</div>',
            unsafe_allow_html=True
        )


# ==================== 解析进度片段（局部刷新，避免页面闪烁） ====================
@st.fragment(run_every=2)
def _render_parsing_progress():
    """
    解析进度片段 - 使用 @st.fragment 实现局部刷新
    只有这个片段每2秒自动刷新，文件上传组件、侧边栏等不会重新渲染
    """
    _is_startup = (st.session_state.get('_parsing_thread_id') == 'pending')
    
    # 从共享字典同步后台线程的状态到 session_state
    shared = st.session_state.get('_bg_shared')
    if shared and not _is_startup:
        st.session_state.parse_progress = shared.get('progress', 0)
        st.session_state.parse_status = shared.get('status', '准备中...')
        
        # 检查后台线程是否已完成
        if not shared.get('parsing', True):
            st.session_state.parsing = False
            st.session_state.parse_results = shared.get('results', [])
            st.session_state.parse_stats = shared.get('stats', {})
            st.session_state._bg_shared = None
            st.rerun(scope="app")  # 全页面刷新以切换到结果视图
            return
    
    # 检查后台线程是否还活着（防止线程崩溃后页面卡死）
    if not _is_startup:
        import threading as _th
        _tid = st.session_state.get('_parsing_thread_id')
        _thread_alive = _tid is not None and _tid != 'pending' and any(
            t.ident == _tid and t.is_alive() for t in _th.enumerate()
        )
        bg_still_parsing = shared.get('parsing', True) if shared else True
        if not _thread_alive and bg_still_parsing:
            st.session_state.parsing = False
            if '完成' not in st.session_state.get('parse_status', ''):
                st.session_state.parse_status = "⚠️ 解析异常中断，请重试"
            st.rerun(scope="app")
            return
    
    # 显示进度
    st.subheader("🔄 解析进行中...")
    
    progress = st.session_state.get('parse_progress', 0)
    status = st.session_state.get('parse_status', '准备中...')
    
    st.progress(progress / 100)
    st.info(f"**{status}**")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("⏹️ 取消解析", type="secondary", use_container_width=True):
            if shared:
                shared['cancel'] = True
            st.session_state.parsing = False
            st.rerun(scope="app")
    
    # 首次进入时启动后台任务
    if _is_startup:
        run_parsing()


# ==================== 解析任务页面 ====================
def render_parse_page():
    """渲染解析任务页面"""
    st.title("📋 解析任务")
    
    # 配置区域
    st.subheader("📤 上传PDF文件")
    st.caption("支持批量上传，可直接拖拽多个PDF文件到下方区域")
    
    uploaded_files = st.file_uploader(
        "拖拽PDF文件到此处，或点击 Browse files 选择文件",
        type=['pdf'],
        accept_multiple_files=True,
        key="pdf_uploader"
    )
    
    if uploaded_files:
        # 保存上传的文件到临时目录
        upload_dir = Path(DATA_DIR) / "uploads"
        upload_dir.mkdir(exist_ok=True)
        
        # 立即保存所有上传的文件
        saved_count = 0
        for uploaded_file in uploaded_files:
            file_path = upload_dir / uploaded_file.name
            # 检查是否需要保存（文件不存在或大小不同）
            if not file_path.exists() or file_path.stat().st_size != uploaded_file.size:
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                saved_count += 1
        
        # 删除不在上传列表中的旧文件
        current_names = {f.name for f in uploaded_files}
        for old_file in upload_dir.glob('*.pdf'):
            if old_file.name not in current_names:
                try:
                    old_file.unlink()
                except:
                    pass
        
        # 始终设置pdf_folder
        st.session_state.pdf_folder = str(upload_dir)
        st.session_state.uploaded_saved = [f.name for f in uploaded_files]
        
        # 显示文件列表
        with st.expander(f"📄 查看文件列表 ({len(uploaded_files)} 个)", expanded=False):
            for f in uploaded_files:
                st.write(f"• {f.name} ({f.size / 1024:.1f} KB)")
    else:
        # 清理之前的上传记录
        if 'uploaded_saved' in st.session_state:
            del st.session_state.uploaded_saved
        # 同时清空uploads目录
        upload_dir = Path(DATA_DIR) / "uploads"
        if upload_dir.exists():
            for old_file in upload_dir.glob('*.pdf'):
                try:
                    old_file.unlink()
                except:
                    pass
    
    st.markdown("---")
    
    # 操作按钮
    if st.button("🚀 开始批量解析", type="primary", use_container_width=True,
                disabled=st.session_state.parsing):
        if not st.session_state.pdf_folder:
            show_toast("请先上传PDF文件", "warning")
        else:
            st.session_state.parsing = True
            st.session_state.cancel_parsing = False  # 清除取消标志
            st.session_state._parsing_thread_id = 'pending'  # 标记线程即将创建，防止被 init_session_state 误重置
            st.session_state.parse_progress = 0
            st.session_state.parse_status = '准备中...'
            st.rerun()
    
    st.markdown("---")
    
    # 解析区域
    if st.session_state.parsing:
        _render_parsing_progress()
    else:
        # 显示解析结果
        results = st.session_state.parse_results
        stats = st.session_state.parse_stats
        
        if results:
            st.subheader("📊 解析结果")
            
            # 检查是否有API级别的致命错误（配额耗尽等），优先展示
            fatal_errors = set()
            for r in results:
                if r.error and ('配额' in r.error or '密钥' in r.error or 'Quota' in r.error 
                               or '免费额度' in r.error or 'exhausted' in r.error):
                    fatal_errors.add(r.error)
            
            if fatal_errors:
                for err in fatal_errors:
                    st.error(f"🚫 {err}")
                st.info("💡 **解决方法**：\n"
                       "1. 登录 [DeepSeek控制台](https://platform.deepseek.com/) 检查余额并充值\n"
                       "2. 或在「系统设置」页面更换为其他可用模型\n"
                       "3. 或更换一个新的API Key")
            
            # 构建表格数据
            table_data = []
            for r in results:
                error_display = ''
                if r.error:
                    # 截取错误信息前60字符显示
                    error_display = r.error[:60] + ('...' if len(r.error) > 60 else '')
                
                table_data.append({
                    '文件名': r.pdf_name,
                    '型号': r.opn or '-',
                    '厂家': r.manufacturer or '-',
                    '参数数': len(r.params) if not r.error else 0,
                    '状态': '✅ 成功' if not r.error else '❌ 失败',
                    '错误原因': error_display
                })
            
            st.dataframe(table_data, use_container_width=True, hide_index=True)
            
            # 底部摘要
            st.caption(f"共 {stats.get('total', 0)} 个文件 · 成功 {stats.get('success', 0)} 个 · 提取 {stats.get('total_params', 0)} 个参数 · 耗时 {stats.get('time', 0):.1f} 秒")


def run_parsing_background(pdf_folder, user_id, ai_config, max_concurrent, shared):
    """
    后台执行解析任务（在独立线程中运行）
    
    注意：后台线程不能直接访问 st.session_state（缺少 ScriptRunContext），
    所有状态更新都通过 shared 字典传递，由主线程同步到 session_state。
    """
    
    try:
        # 获取组件实例（在线程中创建新实例）
        from backend.pdf_parser import PDFParser
        from backend.ai_processor import AIProcessor
        from backend.db_manager import DatabaseManager
        from backend.data_writer import DataWriter
        from backend.cache_manager import get_cache_manager
        
        pdf_parser = PDFParser()
        ai_processor = AIProcessor()
        db_manager = DatabaseManager()
        data_writer = DataWriter(db_manager)
        cache_manager = get_cache_manager()
        
        # 更新AI配置
        ai_processor.update_config(
            provider=ai_config['provider'],
            model=ai_config['model'],
            api_key=ai_config['api_key'],
            api_base=ai_config.get('api_base')
        )
        
        # 获取参数库
        params_info = db_manager.get_all_params_with_variants()
        
        if not params_info:
            shared['status'] = "⚠️ 参数库为空，请先初始化参数库"
            shared['parsing'] = False
            return
        
        # 获取PDF文件列表
        pdf_list = pdf_parser.get_pdf_list(pdf_folder)
        
        if not pdf_list:
            shared['status'] = "⚠️ 未找到PDF文件"
            shared['parsing'] = False
            return
        
        total_files = len(pdf_list)
        start_time = time.time()
        
        # ===== 缓存系统：检查缓存并过滤已缓存文件 =====
        cached_results = []
        files_to_parse = []
        
        for pdf_file in pdf_list:
            file_path = os.path.join(pdf_folder, pdf_file)
            md5_hash = cache_manager.compute_md5(file_path)
            
            if cache_manager.is_cache_valid(md5_hash):
                # 缓存命中
                cached_result = cache_manager.get_cached_result(md5_hash)
                if cached_result:
                    cached_results.append((pdf_file, cached_result, md5_hash))
                else:
                    files_to_parse.append((pdf_file, md5_hash))
            else:
                files_to_parse.append((pdf_file, md5_hash))
        
        cache_hit_count = len(cached_results)
        cache_miss_count = len(files_to_parse)
        
        shared['cache_info'] = {
            'hit': cache_hit_count,
            'miss': cache_miss_count,
            'total': total_files
        }
        
        # 阶段1: 解析PDF（使用带缓存的批量解析：MD5 去重 + 缓存命中加速）
        shared['status'] = f"解析PDF中 (0/{total_files})"
        shared['progress'] = 0

        def pdf_progress_cb(idx, total, name, status):
            if shared.get('cancel'):
                return
            shared['progress'] = int((idx + 1) / total * 20) if total else 0
            shared['status'] = f"解析PDF ({idx + 1}/{total})"

        try:
            pdf_contents = pdf_parser.batch_parse(
                pdf_folder,
                progress_callback=pdf_progress_cb,
                use_cache=True
            )
        except Exception as e:
            logger.error(f"批量解析失败: {e}")
            shared['status'] = f"⚠️ 解析失败: {e}"
            shared['parsing'] = False
            return

        if shared.get('cancel'):
            shared['cancel'] = False
            shared['parsing'] = False
            shared['status'] = "已取消"
            return

        parse_failed = sum(1 for c in pdf_contents if c.error)
        pdf_contents_ok = [c for c in pdf_contents if not c.error]
        if not pdf_contents_ok:
            shared['status'] = "⚠️ 所有PDF解析失败"
            shared['parsing'] = False
            return
        
        # 阶段2: AI提取
        shared['status'] = f"AI提取中 (0/{len(pdf_contents_ok)})"
        
        def progress_callback(completed, total, pdf_name):
            shared['progress'] = 20 + int((completed / total) * 80)
            shared['status'] = f"AI提取中 ({completed}/{total})"
        
        results = []
        try:
            results = ai_processor.batch_extract(
                pdf_contents_ok,
                params_info,
                max_concurrent=max_concurrent,
                progress_callback=progress_callback
            )
            
            # ===== 缓存系统：保存解析结果到缓存 =====
            for i, result in enumerate(results):
                if not result.error:
                    # 找到对应的MD5
                    pdf_name = result.pdf_name
                    for pdf_file, md5_hash in files_to_parse:
                        if pdf_file == pdf_name:
                            cache_result = {
                                'pdf_name': result.pdf_name,
                                'opn': result.opn,
                                'manufacturer': result.manufacturer,
                                'device_type': result.device_type,
                                'params': result.params,
                                'tables': result.tables if hasattr(result, 'tables') else [],
                                'error': result.error
                            }
                            cache_manager.cache_result(md5_hash, cache_result, pdf_name)
                            break
            
            # ===== 缓存系统：合并缓存结果 =====
            for pdf_name, cached_result, md5_hash in cached_results:
                from backend.ai_processor import ExtractionResult
                result = ExtractionResult(
                    pdf_name=cached_result.get('pdf_name', pdf_name),
                    opn=cached_result.get('opn'),
                    manufacturer=cached_result.get('manufacturer'),
                    device_type=cached_result.get('device_type'),
                    params=cached_result.get('params', {}),
                    tables=cached_result.get('tables', []),
                    error=cached_result.get('error')
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"batch_extract 失败，降级为串行: {e}")
            results = []
            for idx, pdf_content in enumerate(pdf_contents_ok):
                try:
                    result = ai_processor.extract_params(pdf_content, params_info)
                    results.append(result)
                except Exception as ex:
                    logger.error(f"串行提取失败 {pdf_content.file_name}: {ex}")
                    from backend.ai_processor import ExtractionResult
                    results.append(ExtractionResult(pdf_name=pdf_content.file_name, error=str(ex)))
                shared['progress'] = 20 + int((idx + 1) / len(pdf_contents_ok) * 80)
        
        # 统计结果
        success_count = sum(1 for r in results if not r.error)
        failed_count = len(results) - success_count + parse_failed
        total_time = time.time() - start_time
        total_params = sum(len(r.params) for r in results if not r.error)
        
        # 检查是否有致命的API错误
        fatal_error = None
        for r in results:
            if r.error and ('余额' in r.error or '密钥' in r.error or '配额' in r.error or 'Quota' in r.error):
                fatal_error = r.error
                break
        
        # 写入数据库（只有成功结果才写入）
        if results and success_count > 0:
            try:
                data_writer.write_to_database(results, user_id=user_id)
            except Exception as e:
                logger.error(f"写入数据库失败: {e}")
        
        # 更新共享状态（主线程会同步到 session_state）
        shared['progress'] = 100
        if fatal_error:
            shared['status'] = f"❌ API错误 · {fatal_error[:80]}"
        elif failed_count > 0 and success_count == 0:
            shared['status'] = f"❌ 全部失败 ({failed_count}个文件) · 耗时{total_time:.1f}s"
        else:
            cache_info_str = f" | 缓存命中{cache_hit_count}/{total_files}" if cache_hit_count > 0 else ""
            shared['status'] = f"✅ 完成 · 成功{success_count} · 失败{failed_count}{cache_info_str} · 耗时{total_time:.1f}s"
        shared['results'] = results
        shared['stats'] = {
            'total': total_files,
            'success': success_count,
            'failed': failed_count,
            'total_params': total_params,
            'time': total_time,
            'cache_hit': cache_hit_count,
            'cache_miss': cache_miss_count
        }
    except Exception as e:
        # 兜底：无论什么异常都要让解析状态恢复
        logger.error(f"run_parsing_background 异常: {e}")
        shared['status'] = f"❌ 解析出错: {e}"
    finally:
        # 关键：无论如何都必须标记完成，否则页面会卡死在刷新循环里
        shared['parsing'] = False


def run_parsing():
    """启动后台解析任务"""
    import threading
    
    logger.info(f"run_parsing 被调用, pdf_folder={st.session_state.get('pdf_folder')}")
    
    # 检查参数库
    params_info = get_cached_params_info()
    if not params_info:
        logger.warning("run_parsing: 参数库为空")
        show_toast("参数库为空，请先在「参数管理」页面初始化参数库", "warning")
        st.session_state.parsing = False
        return
    
    logger.info(f"run_parsing: 参数库 {len(params_info)} 个参数")
    
    # 检查PDF
    pdf_parser = get_cached_pdf_parser()
    pdf_list = pdf_parser.get_pdf_list(st.session_state.pdf_folder)
    if not pdf_list:
        logger.warning(f"run_parsing: 未找到PDF文件, pdf_folder={st.session_state.pdf_folder}")
        show_toast("未找到PDF文件", "warning")
        st.session_state.parsing = False
        return
    
    logger.info(f"run_parsing: 找到 {len(pdf_list)} 个PDF文件，启动后台线程")
    
    # 准备配置
    ai_config = {
        'provider': st.session_state.ai_provider,
        'model': st.session_state.ai_model,
        'api_key': st.session_state.ai_api_key,
        'api_base': config.ai.api_base
    }
    max_concurrent = config.parser.max_workers
    user_id = st.session_state.user_id
    pdf_folder = st.session_state.pdf_folder
    
    # 创建共享状态字典（普通 Python dict，线程安全，不依赖 ScriptRunContext）
    shared = {
        'parsing': True,
        'progress': 0,
        'status': '启动中...',
        'results': [],
        'stats': {},
        'cancel': False,
    }
    st.session_state._bg_shared = shared  # 存入 session_state 供主线程读取
    
    # 初始化显示状态
    st.session_state.parse_status = "启动中..."
    st.session_state.parse_progress = 0
    
    # 启动后台线程
    thread = threading.Thread(
        target=run_parsing_background,
        args=(pdf_folder, user_id, ai_config, max_concurrent, shared),
        daemon=True
    )
    thread.start()
    # 记录线程ID，用于 init_session_state 检测线程是否已崩溃
    st.session_state._parsing_thread_id = thread.ident
    
    show_toast(f"后台解析已启动，共 {len(pdf_list)} 个文件", "success")


# ==================== 参数管理页面 ====================
def render_params_page():
    """渲染参数管理页面 - 简洁实用版"""
    st.title("📦 参数管理")
    
    db_manager = get_cached_db_manager()
    
    # 获取所有参数
    params = db_manager.get_all_params_with_variants()
    
    # 器件类型
    device_types = ['Si MOSFET', 'SiC MOSFET', 'IGBT']
    
    # 统计各类型参数
    def get_params_by_type(dtype):
        result = []
        for p in params:
            pt = p.get('param_type', '') or ''
            if dtype in pt:
                result.append(p)
        return result
    
    # 顶部操作栏
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕ 新增参数", use_container_width=True):
            st.session_state.edit_param_id = 'new'
    with col2:
        if st.button("🔄 重置参数库", use_container_width=True):
            init_count = initialize_params_from_excel()
            st.toast(f"已重置 {init_count} 个参数")
            st.rerun()
    
    st.markdown("---")
    
    # 新增参数表单（只在顶部新增时显示）
    if st.session_state.get('edit_param_id') == 'new':
        render_param_form_simple(db_manager, params)
        st.markdown("---")
    
    if not params:
        st.info("📭 参数库为空，请点击「重置参数库」初始化")
        return
    
    # 使用选项卡展示三种器件类型
    tab1, tab2, tab3 = st.tabs([
        f"🔷 Si MOSFET ({len(get_params_by_type('Si MOSFET'))})",
        f"🔶 SiC MOSFET ({len(get_params_by_type('SiC MOSFET'))})",
        f"🟢 IGBT ({len(get_params_by_type('IGBT'))})"
    ])
    
    with tab1:
        render_params_table(get_params_by_type('Si MOSFET'), db_manager, 'si')
    
    with tab2:
        render_params_table(get_params_by_type('SiC MOSFET'), db_manager, 'sic')
    
    with tab3:
        render_params_table(get_params_by_type('IGBT'), db_manager, 'igbt')


@st.fragment
def render_params_table(params_list: list, db_manager, prefix: str):
    """渲染参数表格"""
    if not params_list:
        st.info("暂无参数")
        return
    
    import pandas as pd
    
    # 搜索框
    search = st.text_input("🔍 搜索参数", key=f"search_{prefix}", placeholder="输入参数名或英文名...")
    
    # 过滤参数
    if search:
        search_lower = search.lower()
        filtered_list = [p for p in params_list if 
                        search_lower in p['param_name'].lower() or 
                        search_lower in (p.get('param_name_en', '') or '').lower()]
    else:
        filtered_list = params_list
    
    if not filtered_list:
        st.info(f"未找到包含「{search}」的参数")
        return
    
    # 构建表格数据
    data = []
    for p in filtered_list:
        variants = p.get('variants', [])
        data.append({
            '参数名': p['param_name'],
            '英文名': p.get('param_name_en', '-') or '-',
            '单位': p.get('unit', '-') or '-',
            '分类': p.get('category', '-') or '-',
            '变体': len(variants)
        })
    
    df = pd.DataFrame(data)
    
    # 使用可选择的表格
    event = st.dataframe(
        df,
        use_container_width=True,
        height=min(400, 35 * len(data) + 38),
        selection_mode="single-row",
        on_select="rerun",
        key=f"table_{prefix}"
    )
    
    # 获取选中的行
    selected_rows = event.selection.rows if event.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_param = filtered_list[selected_idx]
        
        # 检查是否正在编辑这个参数
        editing_this = st.session_state.get('edit_param_id') == selected_param['id']
        
        if not editing_this:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ 编辑选中参数", key=f"edit_{prefix}", use_container_width=True):
                    st.session_state.edit_param_id = selected_param['id']
                    st.rerun(scope="app")
            with col2:
                if st.button("🗑️ 删除选中参数", key=f"del_{prefix}", use_container_width=True):
                    db_manager.delete_standard_param(selected_param['id'])
                    st.rerun(scope="app")
        else:
            # 在表格下方显示编辑表单
            st.markdown("---")
            render_param_form_simple(db_manager, filtered_list)
    

def render_param_form_simple(db_manager, all_params):
    """简洁的参数表单"""
    is_new = st.session_state.edit_param_id == 'new'
    
    if is_new:
        st.subheader("➕ 新增参数")
        param_data = {}
    else:
        st.subheader("✏️ 编辑参数")
        param_data = next((p for p in all_params if p['id'] == st.session_state.edit_param_id), {})
    
    current_types = []
    if param_data.get('param_type'):
        current_types = [t.strip() for t in param_data['param_type'].split(',') if t.strip()]
    
    categories = ['基本信息', '电压', '电流', '电阻', '电容', '电荷', '时间', '热特性', '其他']
    current_category = param_data.get('category', '其他') or '其他'
    category_index = categories.index(current_category) if current_category in categories else 8
    
    with st.form("param_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            param_name = st.text_input("参数名 *", value=param_data.get('param_name', ''))
            unit = st.text_input("单位", value=param_data.get('unit', '') or '')
            category = st.selectbox("分类", options=categories, index=category_index)
        
        with col2:
            param_name_en = st.text_input("英文名", value=param_data.get('param_name_en', '') or '')
            st.markdown("**适用器件**")
            t1, t2, t3 = st.columns(3)
            with t1:
                si_mos = st.checkbox("Si", value='Si MOSFET' in current_types)
            with t2:
                sic_mos = st.checkbox("SiC", value='SiC MOSFET' in current_types)
            with t3:
                igbt = st.checkbox("IGBT", value='IGBT' in current_types)
        
        variants_text = st.text_area(
            "变体（每行一个）",
            value='\n'.join(param_data.get('variants', [])),
            height=80
        )
        
        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
        with c2:
            cancelled = st.form_submit_button("取消", use_container_width=True)
        
        if submitted and param_name:
            param_type_list = []
            if si_mos:
                param_type_list.append('Si MOSFET')
            if sic_mos:
                param_type_list.append('SiC MOSFET')
            if igbt:
                param_type_list.append('IGBT')
            
            variants = [v.strip() for v in variants_text.split('\n') if v.strip()]
            
            if is_new:
                db_manager.add_standard_param(
                    param_name=param_name,
                    param_name_en=param_name_en,
                    param_type=','.join(param_type_list),
                    unit=unit,
                    category=category,
                    variants=variants
                )
            else:
                db_manager.update_standard_param(
                    st.session_state.edit_param_id,
                    param_name=param_name,
                    param_name_en=param_name_en,
                    param_type=','.join(param_type_list),
                    unit=unit,
                    category=category
                )
            
            st.session_state.edit_param_id = None
            st.rerun(scope="app")
        
        if cancelled:
            st.session_state.edit_param_id = None
            st.rerun(scope="app")


# ==================== 生成表格页面（简化版） ====================
def render_table_generation_page():
    """渲染生成表格页面"""
    st.title("📤 生成参数表格")
    
    db_manager = get_cached_db_manager()
    
    # 使用选项卡分隔功能
    tab1, tab2 = st.tabs(["📊 生成表格", "📂 历史表格"])
    
    # ==================== 选项卡1：生成表格 ====================
    with tab1:
        st.subheader("📊 按条件生成参数表格")
        st.caption("选择器件类型和文件范围，生成「器件一行、参数一列」格式的Excel表格")
        
        # 初始化session state
        if 'table_selected_pdfs' not in st.session_state:
            st.session_state.table_selected_pdfs = []
        if 'table_gen_result' not in st.session_state:
            st.session_state.table_gen_result = None
        
        # 步骤1：选择器件类型（按用户过滤）
        st.markdown("### 1️⃣ 选择器件类型")
        current_user_id = st.session_state.user_id
        device_types = db_manager.get_device_types(user_id=current_user_id)
        
        if not device_types:
            st.warning("⚠️ 暂无解析记录，请先在「解析任务」页面进行PDF解析")
        else:
            selected_device_type = st.selectbox(
                "器件类型",
                options=["请选择..."] + device_types,
                key="table_device_type"
            )
            
            if selected_device_type and selected_device_type != "请选择...":
                # 步骤2：选择文件范围
                st.markdown("### 2️⃣ 选择文件范围")
                
                file_scope = st.radio(
                    "文件范围",
                    options=["该类型下所有已解析文件", "该类型下部分文件（手动选择）"],
                    key="table_file_scope",
                    horizontal=True
                )
                
                # 获取该类型的所有PDF文件（按用户过滤）
                all_pdfs = db_manager.get_pdf_list_by_device_type(selected_device_type, user_id=current_user_id)
                
                if file_scope == "该类型下所有已解析文件":
                    st.info(f"📄 将包含该类型下所有 {len(all_pdfs)} 个已解析的PDF文件")
                    selected_pdfs = all_pdfs
                else:
                    # 手动选择文件
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown("#### 选择要包含的PDF文件")
                    with col2:
                        if st.button("全选", key="select_all_pdfs", use_container_width=True):
                            st.session_state.table_selected_pdfs = all_pdfs
                            st.rerun()
                    
                    # 使用多选框
                    selected_pdfs = st.multiselect(
                        "选择PDF文件",
                        options=all_pdfs,
                        default=st.session_state.table_selected_pdfs,
                        key="table_pdf_multiselect",
                        label_visibility="collapsed"
                    )
                    st.session_state.table_selected_pdfs = selected_pdfs
                
                # 步骤3：生成表格
                st.markdown("### 3️⃣ 生成表格")
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    generate_clicked = st.button(
                        "📊 生成表格", 
                        type="primary", 
                        use_container_width=True,
                        key="generate_table_btn"
                    )
                
                if generate_clicked:
                    if selected_device_type == "请选择...":
                        show_toast("请先选择器件类型", "warning")
                    elif not selected_pdfs:
                        show_toast("请至少选择一个文件", "warning")
                    else:
                        with st.spinner("正在生成表格，请稍候..."):
                            from backend.data_writer import DataWriter
                            data_writer = DataWriter(db_manager)
                            
                            result = data_writer.generate_table_by_conditions(
                                device_type=selected_device_type,
                                pdf_list=selected_pdfs,
                                created_by=st.session_state.get('username', 'unknown'),
                                user_id=st.session_state.user_id
                            )
                            
                            st.session_state.table_gen_result = result
                
                # 显示生成结果
                if st.session_state.table_gen_result:
                    result = st.session_state.table_gen_result
                    
                    if result['success']:
                        # 检查文件是否存在
                        if not os.path.exists(result['file_path']):
                            st.session_state.table_gen_result = None
                            st.info("📭 表格文件已被删除，请重新生成")
                        else:
                            st.success("✅ 表格生成成功！")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"📂 **表格路径**: `{result['file_path']}`")
                                st.write(f"📄 **文件数量**: {result['pdf_count']} 个PDF")
                                st.write(f"📊 **参数列数**: {result['param_count']} 个参数")
                            
                            # 操作按钮
                            st.markdown("---")
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if st.button("🔍 预览表格", use_container_width=True, key="preview_gen_table"):
                                    st.session_state.preview_table_path = result['file_path']
                            
                            with col2:
                                # 提供下载
                                with open(result['file_path'], 'rb') as f:
                                    st.download_button(
                                        "📥 下载Excel",
                                        data=f,
                                        file_name=result['table_name'],
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True
                                    )
                            
                            # 表格预览
                            if st.session_state.get('preview_table_path') == result['file_path']:
                                st.markdown("---")
                                st.subheader("📋 表格预览")
                                
                                from backend.data_writer import DataWriter
                                data_writer = DataWriter(db_manager)
                                preview_data = data_writer.load_table_for_preview(result['file_path'])
                                
                                if preview_data['success']:
                                    import pandas as pd
                                    df = pd.DataFrame(preview_data['data'])
                                    
                                    # 高亮显示未提取的单元格
                                    def highlight_missing(val):
                                        if val == '-':
                                            return 'background-color: #FEF3C7; color: #D97706; font-style: italic;'
                                        return ''
                                    
                                    styled_df = df.style.applymap(highlight_missing)
                                    st.dataframe(styled_df, use_container_width=True, height=400)
                                    
                                    st.caption(f"共 {preview_data['row_count']} 行 × {preview_data['col_count']} 列")
                                else:
                                    show_toast(f"预览失败: {preview_data['error']}", "error")
                    else:
                        show_toast(f"生成失败: {result['error']}", "error")
    
    # ==================== 选项卡2：历史表格 ====================
    with tab2:
        st.subheader("📂 历史生成表格")
        
        # 获取历史记录
        table_records = db_manager.get_table_records(limit=50)
        
        if not table_records:
            st.info("📭 暂无历史表格记录")
        else:
            # 标题栏：显示数量和一键清空按钮
            header_col1, header_col2 = st.columns([4, 1])
            with header_col1:
                st.write(f"共 {len(table_records)} 个历史表格")
            with header_col2:
                if st.button("🗑️ 清空全部", key="clear_all_tables", type="secondary"):
                    # 删除所有表格记录和文件
                    for record in table_records:
                        if os.path.exists(record['file_path']):
                            try:
                                os.remove(record['file_path'])
                            except:
                                pass
                        db_manager.delete_table_record(record['id'])
                    st.rerun()
            
            # 显示表格列表
            for record in table_records:
                with st.expander(f"📄 {record['table_name']}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**器件类型**: {record['device_type']}")
                        st.write(f"**文件数量**: {record['pdf_count']} 个PDF")
                        st.write(f"**创建时间**: {record['create_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**创建用户**: {record['created_by']}")
                        st.write(f"**文件路径**: `{record['file_path']}`")
                    
                    with col2:
                        # 检查文件是否存在
                        file_exists = os.path.exists(record['file_path'])
                        
                        if file_exists:
                            # 预览按钮
                            if st.button("🔍 预览", key=f"preview_{record['id']}", use_container_width=True):
                                st.session_state.preview_history_table = record['id']
                            
                            # 下载按钮
                            with open(record['file_path'], 'rb') as f:
                                st.download_button(
                                    "📥 下载",
                                    data=f,
                                    file_name=record['table_name'],
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"download_{record['id']}",
                                    use_container_width=True
                                )
                        else:
                            st.warning("⚠️ 文件已被删除")
                        
                        # 删除按钮
                        if st.button("🗑️ 删除", key=f"delete_{record['id']}", use_container_width=True):
                            db_manager.delete_table_record(record['id'])
                            st.rerun()
                    
                    # 显示预览
                    if st.session_state.get('preview_history_table') == record['id'] and file_exists:
                        st.markdown("---")
                        st.subheader("📋 表格预览")
                        
                        from backend.data_writer import DataWriter
                        data_writer = DataWriter(db_manager)
                        preview_data = data_writer.load_table_for_preview(record['file_path'])
                        
                        if preview_data['success']:
                            import pandas as pd
                            df = pd.DataFrame(preview_data['data'])
                            
                            def highlight_missing(val):
                                if val == '-':
                                    return 'background-color: #FEF3C7; color: #D97706; font-style: italic;'
                                return ''
                            
                            styled_df = df.style.applymap(highlight_missing)
                            st.dataframe(styled_df, use_container_width=True, height=400)
                            
                            st.caption(f"共 {preview_data['row_count']} 行 × {preview_data['col_count']} 列")
                        else:
                            show_toast(f"预览失败: {preview_data['error']}", "error")


# ==================== 系统设置页面 ====================
def render_settings_page():
    """渲染系统设置页面 - 新增缓存清理和自动备份设置"""
    st.title("⚙️ 系统设置")
    
    # 获取管理器实例
    cache_manager = get_cache_manager()
    backup_manager = get_backup_manager()
    
    # ========== AI模型配置 ==========
    st.subheader("🤖 AI模型配置")
    
    with st.form("ai_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            provider = st.selectbox(
                "AI提供商",
                options=['deepseek', 'openai', 'local'],
                index=['deepseek', 'openai', 'local'].index(st.session_state.ai_provider) if st.session_state.ai_provider in ['deepseek', 'openai', 'local'] else 0,
                help="deepseek: DeepSeek, openai: OpenAI GPT, local: 本地模型"
            )
            
            model_options = {
                'deepseek': ['deepseek-chat', 'deepseek-reasoner'],
                'openai': ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                'local': ['llama3', 'qwen2']
            }
            
            model = st.selectbox(
                "模型",
                options=model_options.get(provider, ['deepseek-chat']),
                index=0
            )
        
        with col2:
            api_key = st.text_input(
                "API密钥",
                value=st.session_state.ai_api_key,
                type="password",
                help="留空则使用默认密钥"
            )
            
            api_base = st.text_input(
                "API基础URL（可选）",
                value=config.ai.api_base,
                placeholder="DeepSeek默认: https://api.deepseek.com/v1",
                help="API地址，DeepSeek默认为 https://api.deepseek.com/v1，本地模型如 http://localhost:8000/v1"
            )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.form_submit_button("💾 保存配置", type="primary", use_container_width=True):
                st.session_state.ai_provider = provider
                st.session_state.ai_model = model
                st.session_state.ai_api_key = api_key if api_key else config.ai.api_key
                
                # 保存用户专属API密钥（与系统默认不同时才存，相同则清除以跟随默认）
                user_manager = get_cached_user_manager()
                if api_key and api_key != config.ai.api_key:
                    user_manager.set_user_api_key(st.session_state.user_id, api_key)
                else:
                    user_manager.set_user_api_key(st.session_state.user_id, "")
                
                # 管理员可以同时更新系统默认配置
                if st.session_state.user_role == 'admin':
                    config.update_ai_config(
                        provider=provider,
                        model=model,
                        api_key=api_key if api_key else None,
                        api_base=api_base if api_base else None
                    )
                    show_toast("配置已保存（已同步更新系统默认配置）", "success")
                else:
                    show_toast("配置已保存（仅对当前账号生效）", "success")
    
    st.markdown("---")
    
    # ========== 缓存管理 ==========
    st.subheader("💾 缓存管理")
    
    # 获取缓存统计
    cache_stats = cache_manager.get_cache_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("缓存文件数", cache_stats['total_files'])
    with col2:
        st.metric("缓存大小", f"{cache_stats['total_size_mb']} MB")
    with col3:
        st.metric("命中率", f"{cache_stats['hit_rate']}%")
    with col4:
        st.metric("总访问", cache_stats['total_access'])
    
    st.caption(f"缓存保留时间：{cache_stats['max_age_days']}天 | 命中：{cache_stats['hits']}次 | 未命中：{cache_stats['misses']}次")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 清理过期缓存", use_container_width=True):
            count, msg = cache_manager.clear_expired_cache()
            show_toast(msg, "success" if count > 0 else "info")
            st.rerun()
    with col2:
        if st.button("🗑️ 清除全部缓存", type="secondary", use_container_width=True):
            confirm_key = "confirm_clear_cache"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = True
                st.warning("⚠️ 确定要清除所有缓存吗？")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("确认清除", key="yes_clear_cache", type="primary", use_container_width=True):
                        success, msg = cache_manager.clear_all_cache()
                        st.session_state[confirm_key] = False
                        show_toast(msg, "success" if success else "error")
                        st.rerun()
                with col_no:
                    if st.button("取消", key="no_clear_cache", use_container_width=True):
                        st.session_state[confirm_key] = False
                        st.rerun()
            else:
                st.session_state[confirm_key] = False
                st.rerun()
    
    st.markdown("---")
    
    # ========== 自动备份设置 ==========
    st.subheader("📦 自动备份设置")
    
    auto_config = backup_manager.get_auto_backup_config()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        auto_backup_enabled = st.toggle("启用自动备份", value=auto_config.get('enabled', False))
    with col2:
        interval_days = st.number_input(
            "备份间隔（天）",
            value=auto_config.get('interval_days', 7),
            min_value=1,
            max_value=30,
            help="每隔多少天自动创建一次备份"
        )
    with col3:
        max_backups = st.number_input(
            "保留备份数",
            value=auto_config.get('max_backups', 5),
            min_value=1,
            max_value=20,
            help="自动备份最多保留的数量"
        )
    
    # 显示上次备份时间
    last_backup = auto_config.get('last_backup')
    if last_backup:
        st.caption(f"上次自动备份：{last_backup[:19]}")
    else:
        st.caption("尚未进行过自动备份")
    
    if st.button("💾 保存自动备份设置", use_container_width=True):
        backup_manager.set_auto_backup_config(
            enabled=auto_backup_enabled,
            interval_days=int(interval_days),
            max_backups=int(max_backups)
        )
        show_toast("自动备份设置已保存", "success")
    
    # 手动触发自动备份检查
    if auto_backup_enabled and backup_manager.should_auto_backup():
        st.info("📦 已达到自动备份间隔，将在下次启动时自动创建备份")
    
    st.markdown("---")
    
    # ========== 测试连接 ==========
    st.subheader("🔗 连接测试")
    
    if st.button("🔗 测试API连接"):
        with st.spinner("正在测试连接..."):
            ai_processor = AIProcessor()
            ai_processor.update_config(
                provider=st.session_state.ai_provider,
                model=st.session_state.ai_model,
                api_key=st.session_state.ai_api_key
            )
            result = ai_processor.test_connection()
            
            if result['success']:
                show_toast(result['message'], "success")
                st.write(f"响应: {result['response']}")
            else:
                show_toast(result['message'], "error")
    
    st.markdown("---")
    
    # ========== AI性能配置 ==========
    st.subheader("⚡ AI性能配置")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ai_timeout = st.number_input(
            "AI超时时间（秒）",
            value=config.ai.timeout,
            min_value=30,
            max_value=300,
            help="单次AI调用的最长等待时间，建议60-120秒"
        )
    
    with col2:
        ai_max_retries = st.number_input(
            "AI最大重试次数",
            value=config.ai.max_retries,
            min_value=1,
            max_value=5,
            help="AI调用失败时的重试次数"
        )
    
    with col3:
        ai_concurrent = st.number_input(
            "AI并发数",
            value=config.parser.max_workers,
            min_value=1,
            max_value=8,
            help="同时处理多个PDF时的并发AI请求数"
        )
    
    if st.button("💾 保存AI配置"):
        config.ai.timeout = ai_timeout
        config.ai.max_retries = ai_max_retries
        config.parser.max_workers = ai_concurrent
        config.save_config()
        show_toast("AI配置已保存", "success")

    st.markdown("---")
    
    # ========== 提示词调试工具 ==========
    st.subheader("🧪 提示词调试工具")
    st.caption("为指定PDF生成当前配置下的完整提示词（不调用大模型），用于检查参数清单和规则是否正确。")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        debug_pdf_path = st.text_input(
            "PDF文件路径",
            value=st.session_state.get("debug_pdf_path", ""),
            placeholder="例如：/home/gjw/AITOOL/LSGT10R011_V1.0.pdf"
        )
    with col2:
        fast_mode = st.checkbox("快速模式fast", value=False, help="与解析任务中的fast模式一致，用于缩短提示词。")
    
    if st.button("📄 生成提示词预览", use_container_width=True):
        if not debug_pdf_path or not os.path.exists(debug_pdf_path):
            show_toast("请填写有效的PDF文件路径", "warning")
        else:
            st.session_state["debug_pdf_path"] = debug_pdf_path
            with st.spinner("正在生成提示词，请稍候..."):
                try:
                    # 解析PDF
                    pdf_parser = PDFParser()
                    pdf_content = pdf_parser.parse_pdf(debug_pdf_path)
                    if pdf_content.error:
                        show_toast(f"PDF解析失败: {pdf_content.error}", "error")
                    else:
                        # 获取参数库
                        db_manager = get_cached_db_manager()
                        params_info = db_manager.get_all_params_with_variants()
                        if not params_info:
                            show_toast("参数库为空，请先在「参数管理」页面初始化参数库", "warning")
                        else:
                            # 构造AI处理器，按当前配置更新
                            ai_processor = get_cached_ai_processor()
                            ai_processor.update_config(
                                provider=st.session_state.ai_provider,
                                model=st.session_state.ai_model,
                                api_key=st.session_state.ai_api_key,
                                api_base=config.ai.api_base
                            )
                            
                            # 识别器件类型并加载对应配置
                            device_type = pdf_content.metadata.get('device_type') if getattr(pdf_content, 'metadata', None) else 'Si MOSFET'
                            
                            # 生成结构化内容和提示词预览
                            structured = pdf_parser.get_structured_content(pdf_content, fast_mode=fast_mode)
                            param_groups = ai_processor._get_param_groups(device_type or 'Si MOSFET')
                            notes = ai_processor._load_extraction_notes(device_type or 'Si MOSFET')
                            # 取第一个分组做预览
                            first_group_name = list(param_groups.keys())[0] if param_groups else "预览"
                            first_group_params = list(param_groups.values())[0] if param_groups else []
                            prompt = ai_processor._build_prompt(structured, first_group_name, first_group_params, notes)
                            
                            st.success("提示词生成完成（仅预览，未调用大模型）。")
                            st.markdown("#### 提示词内容")
                            st.text_area(
                                "prompt_preview",
                                value=prompt,
                                height=400
                            )
                except Exception as e:
                    show_toast(f"生成提示词失败: {e}", "error")


# ==================== 数据中心页面（合并查看和搜索） ====================
def render_data_center_page():
    """
    数据中心页面 - 合并精细化查看和精准搜索
    
    功能：
    1. 统一搜索栏：支持PDF名称、参数名模糊搜索
    2. 左侧：按器件类型分类的PDF树形列表
    3. 右侧：参数详情展示
    """
    st.title("📊 数据中心")
    
    db_manager = get_cached_db_manager()
    
    # ==================== 顶部搜索区域 ====================
    
    # 搜索栏
    col1, col2, col3, col4, col5 = st.columns([2.5, 2.5, 1.5, 1, 1])
    
    with col1:
        pdf_search = st.text_input(
            "📄 PDF名称",
            value=st.session_state.get('dc_pdf_search', ''),
            placeholder="输入PDF名称、型号或厂家...",
            key="dc_pdf_input",
            label_visibility="collapsed"
        )
    
    with col2:
        param_search = st.text_input(
            "📊 参数名",
            value=st.session_state.get('dc_param_search', ''),
            placeholder="输入参数名（可选，留空显示全部参数）...",
            key="dc_param_input",
            label_visibility="collapsed"
        )
    
    with col3:
        device_types = db_manager.get_device_types(user_id=st.session_state.user_id)
        device_filter = st.selectbox(
            "器件类型",
            options=["全部类型"] + device_types,
            key="dc_device_filter",
            label_visibility="collapsed"
        )
    
    with col4:
        search_clicked = st.button("🔍 搜索", type="primary", use_container_width=True, key="dc_search_btn")
    
    with col5:
        if st.button("🗑️ 清空", type="secondary", use_container_width=True, key="dc_clear_btn"):
            db_manager.clear_all_parse_results(user_id=st.session_state.user_id)
            st.session_state.parse_results = []
            st.session_state.parse_stats = {'success': 0, 'failed': 0, 'total': 0}
            st.session_state.dc_selected_pdf = None
            st.session_state.dc_pdf_search = ''
            st.session_state.dc_param_search = ''
            st.rerun()
    
    # 保存搜索状态（无需 rerun，直接在当前渲染周期生效）
    if search_clicked:
        st.session_state.dc_pdf_search = pdf_search
        st.session_state.dc_param_search = param_search
        st.session_state.dc_active_search = True
    
    # 保存筛选状态
    device_type_filter = None if device_filter == "全部类型" else device_filter
    
    # 使用当前值（不依赖上一次的 session_state，避免延迟一拍）
    active_pdf_search = pdf_search if search_clicked else st.session_state.get('dc_pdf_search', '')
    active_param_search = param_search if search_clicked else st.session_state.get('dc_param_search', '')
    
    st.markdown("---")
    
    # ==================== 主内容区域（双Tab） ====================
    tab_data, tab_filter = st.tabs(["📊 数据查看", "🔎 器件筛选"])
    
    with tab_data:
        # 只有点击搜索后才显示结果
        if st.session_state.get('dc_active_search'):
            render_combined_search_results(db_manager, active_pdf_search, active_param_search, device_type_filter)
        else:
            st.info("🔍 输入搜索条件后点击「搜索」查看数据，或直接点击「搜索」查看全部")
    
    with tab_filter:
        render_device_filter(db_manager)


# ==================== 器件筛选功能 ====================
@st.fragment
def render_device_filter(db_manager):
    """
    器件筛选功能：选择最多5个参数并设定数值范围，筛选匹配的器件
    """
    import pandas as pd
    
    current_user_id = st.session_state.user_id
    
    st.subheader("🔎 按参数范围筛选器件")
    st.caption("选择最多 5 个参数并设定数值范围，系统将筛选出同时满足所有条件的器件")
    
    # 获取可用的筛选参数
    available_params = db_manager.get_available_filter_params(user_id=current_user_id)
    
    if not available_params:
        st.warning("⚠️ 暂无可用的筛选参数，请先在「解析任务」页面解析PDF文件")
        return
    
    # 构建选项列表：参数名 (单位)
    param_options = []
    param_map = {}  # display_name -> param_info
    for p in available_params:
        unit_str = f" ({p['unit']})" if p['unit'] else ""
        display = f"{p['param_name']}{unit_str}"
        param_options.append(display)
        param_map[display] = p
    
    # 步骤1：选择参数
    st.markdown("#### 1. 选择筛选参数")
    selected_displays = st.multiselect(
        "选择参数（最多5个）",
        options=param_options,
        default=st.session_state.get('dc_filter_selected', []),
        max_selections=5,
        key="dc_filter_multiselect",
        placeholder="点击选择要筛选的参数...",
        label_visibility="collapsed"
    )
    st.session_state.dc_filter_selected = selected_displays
    
    if not selected_displays:
        st.info("💡 请从上方选择至少一个参数来开始筛选")
        return
    
    # 步骤2：设定范围
    st.markdown("#### 2. 设定数值范围")
    st.caption("可只填最小值或最大值（单边范围），留空表示不限制")
    
    conditions = []
    for display_name in selected_displays:
        p_info = param_map[display_name]
        param_name = p_info['param_name']
        unit = p_info['unit']
        
        col_name, col_min, col_sep, col_max, col_unit = st.columns([2.5, 2, 0.3, 2, 0.8])
        
        with col_name:
            st.markdown(f"**{param_name}**")
        with col_min:
            min_val = st.number_input(
                "最小值",
                value=None,
                key=f"filter_min_{param_name}",
                placeholder="最小值",
                label_visibility="collapsed",
                format="%g"
            )
        with col_sep:
            st.markdown("<div style='text-align:center; padding-top:8px;'>~</div>", unsafe_allow_html=True)
        with col_max:
            max_val = st.number_input(
                "最大值",
                value=None,
                key=f"filter_max_{param_name}",
                placeholder="最大值",
                label_visibility="collapsed",
                format="%g"
            )
        with col_unit:
            st.markdown(f"<div style='padding-top:8px; color:#6B7280;'>{unit}</div>", unsafe_allow_html=True)
        
        conditions.append({
            'param_name': param_name,
            'min_val': min_val,
            'max_val': max_val,
        })
    
    st.markdown("---")
    
    # 步骤3：筛选按钮
    st.markdown("#### 3. 执行筛选")
    
    # 检查是否至少有一个范围被设定
    has_any_range = any(c['min_val'] is not None or c['max_val'] is not None for c in conditions)
    
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        filter_clicked = st.button(
            "🔎 筛选器件",
            type="primary",
            use_container_width=True,
            disabled=not has_any_range,
            key="dc_filter_btn"
        )
    with col_info:
        if not has_any_range:
            st.caption("请至少为一个参数设定范围")
        else:
            active_count = sum(1 for c in conditions if c['min_val'] is not None or c['max_val'] is not None)
            st.caption(f"已设定 {active_count} 个筛选条件")
    
    # 执行筛选
    if filter_clicked:
        with st.spinner("正在筛选器件..."):
            result = db_manager.filter_devices_by_param_ranges(
                conditions=conditions,
                user_id=current_user_id,
            )
            st.session_state.dc_filter_results = result
    
    # 显示筛选结果
    result = st.session_state.get('dc_filter_results')
    if result:
        st.markdown("---")
        st.markdown("#### 筛选结果")
        
        total_found = result['total_found']
        total_checked = result['total_checked']
        
        if total_found == 0:
            st.warning(f"⚠️ 在 {total_checked} 个器件中未找到满足所有条件的器件")
            st.info("💡 尝试放宽范围限制，或减少筛选参数数量")
        else:
            st.success(f"在 {total_checked} 个器件中找到 **{total_found}** 个匹配的器件")
            
            # 构建表格数据
            devices = result['devices']
            param_columns = result['param_columns']
            
            table_data = []
            for d in devices:
                row = {
                    '厂家': d['manufacturer'],
                    'OPN': d['opn'],
                    '器件类型': d['device_type'],
                }
                for pc in param_columns:
                    row[pc] = d['params'].get(pc, '-')
                table_data.append(row)
            
            df = pd.DataFrame(table_data)
            
            # 高亮筛选条件列
            filter_param_names = [c['param_name'] for c in conditions
                                  if c['min_val'] is not None or c['max_val'] is not None]
            
            def highlight_filter_cols(val, col_name):
                if col_name in filter_param_names:
                    return 'background-color: #EEF2FF; font-weight: 500;'
                return ''
            
            styled_df = df.style.apply(
                lambda row: [highlight_filter_cols(v, c) for v, c in zip(row, row.index)],
                axis=1
            )
            
            st.dataframe(styled_df, use_container_width=True, height=min(600, 35 * len(table_data) + 40))
            
            st.caption(f"共 {len(table_data)} 个器件 × {len(df.columns)} 列参数")
            
            # 下载按钮
            try:
                from io import BytesIO
                output = BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                st.download_button(
                    "📥 下载筛选结果 (Excel)",
                    data=output,
                    file_name=f"器件筛选结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as e:
                logger.error(f"导出筛选结果失败: {e}")


@st.fragment
def render_combined_search_results(db_manager, pdf_keyword: str, param_keyword: str, device_type_filter: str):
    """渲染组合搜索结果 - 两步搜索：先选PDF，再显示参数（按用户隔离）"""
    
    current_user_id = st.session_state.user_id
    
    # 第一步：根据PDF关键词搜索匹配的PDF列表（按用户过滤）
    if pdf_keyword:
        pdf_list = db_manager.get_parsed_pdf_list(
            keyword=pdf_keyword,
            device_type=device_type_filter,
            user_id=current_user_id
        )
    else:
        # 如果没有PDF关键词，只搜索参数
        pdf_list = db_manager.get_parsed_pdf_list(device_type=device_type_filter, user_id=current_user_id)
    
    if not pdf_list:
        st.warning("⚠️ 未找到匹配的PDF文件")
        st.info("💡 尝试使用更简短的关键词或检查拼写")
        if st.button("🔄 返回浏览模式"):
            st.session_state.dc_active_search = False
            st.session_state.dc_pdf_search = ''
            st.session_state.dc_param_search = ''
            st.rerun(scope="app")
        return
    
    # 如果只有一个匹配的PDF，直接显示其参数
    # 如果有多个匹配的PDF，让用户先选择
    if len(pdf_list) == 1:
        selected_pdf = pdf_list[0]['pdf_name']
        st.session_state.dc_search_selected_pdf = selected_pdf
    
    # 检查是否已选择PDF
    selected_pdf = st.session_state.get('dc_search_selected_pdf', None)
    
    # 上下布局：上方PDF选择，下方参数详情
    
    # === 上方：PDF选择区 ===
    st.write(f"📄 **匹配的PDF** ({len(pdf_list)}个)")
    
    # 用下拉框选择PDF（更简洁）
    pdf_options = [f"{p['pdf_name']} ({p.get('param_count', 0)}个参数)" for p in pdf_list]
    pdf_names = [p['pdf_name'] for p in pdf_list]
    
    col1, col2 = st.columns([4, 1])
    with col1:
        selected_idx = 0
        if selected_pdf in pdf_names:
            selected_idx = pdf_names.index(selected_pdf)
        
        chosen = st.selectbox(
            "选择PDF",
            options=pdf_options,
            index=selected_idx,
            key="search_pdf_select",
            label_visibility="collapsed"
        )
        # 更新选中的PDF
        new_selected = pdf_names[pdf_options.index(chosen)]
        if new_selected != selected_pdf:
            st.session_state.dc_search_selected_pdf = new_selected
            selected_pdf = new_selected
    
    with col2:
        if st.button("🔄 返回", use_container_width=True):
            st.session_state.dc_active_search = False
            st.session_state.dc_pdf_search = ''
            st.session_state.dc_param_search = ''
            st.session_state.dc_search_selected_pdf = None
            st.rerun(scope="app")
    
    st.markdown("---")
    
    # === 下方：参数详情 ===
    if selected_pdf:
        st.subheader(f"📊 {selected_pdf} 的参数")
        
        # 获取参数列表
        params_list = []
        detail = None
        
        if param_keyword:
            result = db_manager.search_params(
                pdf_keyword=selected_pdf,
                param_keyword=param_keyword,
                page=1,
                page_size=200
            )
            if result['total_count'] == 0:
                st.warning(f"⚠️ 在该PDF中未找到包含「{param_keyword}」的参数")
                st.info("💡 尝试清空参数名搜索框查看全部参数")
            else:
                for r in result['results']:
                    params_list.append({
                        'param_name': r['param_name'],
                        'param_value': r['param_value'],
                        'test_condition': r.get('test_condition', '')
                    })
        else:
            detail = db_manager.get_pdf_detail_params(selected_pdf, user_id=current_user_id)
            if detail and detail['extracted_params']:
                # 显示完整率与关键参数完整率
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("整体参数完整率", f"{detail.get('completeness_rate', 0)}%", 
                              help="已提取参数数量 / 参数库总数")
                with col_b:
                    key_rate = detail.get('key_completeness_rate', 0)
                    key_total = detail.get('key_params_total', 0)
                    if key_total:
                        st.metric("关键参数完整率", f"{key_rate}%", 
                                  help="关键参数列表来自 extraction_rules.yaml 中的 high 配置")
                    else:
                        st.info("尚未配置关键参数列表（extraction_rules.yaml → extraction_priority.high）")
                
                missing_keys = detail.get('key_missing_params') or []
                if missing_keys:
                    with st.expander(f"⚠️ 缺失的关键参数（{len(missing_keys)} 项）", expanded=False):
                        st.write(", ".join(missing_keys))
                
                for param in detail['extracted_params']:
                    params_list.append({
                        'param_name': param['param_name'],
                        'param_value': param['param_value'],
                        'test_condition': param.get('test_condition', '')
                    })
        
        if params_list:
            st.success(f"共 {len(params_list)} 个参数")
            
            # 上方：参数值表格（不含测试条件）
            value_data = [{'参数名': p['param_name'], '参数值': p['param_value']} for p in params_list]
            st.dataframe(value_data, use_container_width=True, height=min(400, 35 * len(value_data) + 40))
            
            # 下方：测试条件汇总（折叠面板，只显示有条件的参数）
            cond_data = [{'参数名': p['param_name'], '测试条件': p['test_condition']}
                         for p in params_list if p.get('test_condition')]
            
            if cond_data:
                with st.expander(f"📋 测试条件汇总（{len(cond_data)} 项）", expanded=False):
                    st.dataframe(cond_data, use_container_width=True, height=min(300, 35 * len(cond_data) + 40))
        elif not param_keyword:
            st.warning("暂无已提取的参数")


# ==================== 初始化参数库 ====================
def initialize_params_from_excel() -> int:
    """
    从Excel初始化参数库
    严格按照 datasheet_params_GJW(1).xlsx 中的列定义参数
    
    Returns:
        导入的参数数量
    """
    db_manager = get_cached_db_manager()
    
    # 先清空现有参数库
    session = db_manager.get_session()
    try:
        from backend.db_manager import StandardParam, ParamVariant
        session.query(ParamVariant).delete()
        session.query(StandardParam).delete()
        session.commit()
        logger.info("已清空现有参数库")
    except Exception as e:
        session.rollback()
        logger.error(f"清空参数库失败: {e}")
    finally:
        session.close()
    
    # ===== Si / SiC MOSFET 参数定义（对应「Si mos与SiC mos 参数提取格式.xlsx」）=====
    # 格式: param_name, param_name_en, category, unit, variants
    mos_params = [
        # ===== 基本信息（5个，全部需要AI提取）=====
        {'param_name': 'PDF文件名', 'param_name_en': 'PDF File Name', 'category': '基本信息', 'unit': '', 'variants': []},
        {'param_name': '厂家', 'param_name_en': 'Manufacturer', 'category': '基本信息', 'unit': '', 'variants': ['Vendor', 'Brand', 'manufacturer']},
        {'param_name': 'OPN', 'param_name_en': 'Part Number', 'category': '基本信息', 'unit': '', 'variants': ['Part No.', 'Model', 'opn', 'Part Number']},
        {'param_name': '厂家封装名', 'param_name_en': 'Package Name', 'category': '基本信息', 'unit': '', 'variants': ['Package', 'PKG']},
        {'param_name': '技术', 'param_name_en': 'Technology', 'category': '基本信息', 'unit': '', 'variants': []},
        
        # ===== 电压参数（1个）=====
        {'param_name': 'VDS', 'param_name_en': 'Drain-source breakdown voltage', 'category': '电压', 'unit': 'V', 
         'variants': ['VDSS', 'V(BR)DSS', 'BVDSS', 'Drain-Source Voltage', 'rain-source breakdown voltage']},
        
        # ===== 电阻参数（7个）=====
        {'param_name': 'Ron 10V_type', 'param_name_en': 'Drain-source on-state resistance Vgs=10V', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['RDS(on)', 'Rdson', 'Ron', 'Drain-source on-state resistance Vgs=10V typ']},
        {'param_name': 'Ron 10V_max', 'param_name_en': 'Drain-source on-state resistance', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['RDS(on)max', 'Drain-source on-state resistance Vgs=10V max']},
        {'param_name': 'Ron 4.5V_type', 'param_name_en': 'Drain-source on-state resistance Vgs=4.5V', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['Drain-source on-state resistance Vgs=4.5V typ']},
        {'param_name': 'Ron 4.5V_max', 'param_name_en': 'Drain-source on-state resistance', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['Drain-source on-state resistance Vgs=4.5V max']},
        {'param_name': 'Ron 2.5V_type', 'param_name_en': 'Drain-source on-state resistance Vgs=2.5V', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['Drain-source on-state resistance Vgs=2.5V typ']},
        {'param_name': 'Ron 2.5V_max', 'param_name_en': 'Drain-source on-state resistance', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['Drain-source on-state resistance Vgs=2.5V max']},
        
        # ===== 电荷参数-Qg（2个）=====
        {'param_name': 'Qg_10V', 'param_name_en': 'Gate charge total Vgs=0~10V', 'category': '电荷', 'unit': 'nC',
         'variants': ['Gate charge total Vgs=0-10V']},
        {'param_name': 'Qg_4.5V', 'param_name_en': 'Gate charge total Vgs=0~4.5V', 'category': '电荷', 'unit': 'nC',
         'variants': ['Gate charge total Vgs=0-4.5V']},
        
        # ===== 二极管参数（4个）=====
        {'param_name': '反二极管压降Vsd', 'param_name_en': 'Diode forward voltage', 'category': '电压', 'unit': 'V',
         'variants': ['VSD', 'VF', 'Vsd', 'VF(diode)']},
        {'param_name': 'Is', 'param_name_en': 'Continuous Source Current', 'category': '电流', 'unit': 'A',
         'variants': ['IS', 'Source Current']},
        {'param_name': 'Ism', 'param_name_en': 'Pulsed Source Current', 'category': '电流', 'unit': 'A',
         'variants': ['ISM', 'IS(pulse)']},
        {'param_name': 'Irrm', 'param_name_en': 'Peak reverse recovery current', 'category': '电流', 'unit': 'A',
         'variants': ['IRRM', 'Irr']},
        
        # ===== 栅极电压参数（5个）=====
        {'param_name': 'Vgs min', 'param_name_en': 'Gate source voltage', 'category': '电压', 'unit': 'V',
         'variants': ['VGS(min)', 'Gate source voltage min']},
        {'param_name': 'Vgs max', 'param_name_en': 'Gate source voltage', 'category': '电压', 'unit': 'V',
         'variants': ['VGS(max)', 'VGS', 'Gate source voltage max']},
        {'param_name': 'Vth type', 'param_name_en': 'Gate threshold voltage', 'category': '电压', 'unit': 'V',
         'variants': ['VGS(th)', 'Vth', 'VTH', 'Gate threshold voltage typ']},
        {'param_name': 'Vth min', 'param_name_en': 'Gate threshold voltage', 'category': '电压', 'unit': 'V',
         'variants': ['VGS(th)min', 'Gate threshold voltage min']},
        {'param_name': 'Vth max', 'param_name_en': 'Gate threshold voltage', 'category': '电压', 'unit': 'V',
         'variants': ['VGS(th)max', 'Gate threshold voltage max']},
        
        # ===== 漏极电流参数（4个）=====
        {'param_name': 'ID Tc=25℃', 'param_name_en': 'Continuous drain current Tc=25℃', 'category': '电流', 'unit': 'A',
         'variants': ['ID', 'Id', 'Drain Current', 'Continuous drain current Tc=25°C']},
        {'param_name': 'ID TA=25℃', 'param_name_en': 'Continuous drain current TA=25℃', 'category': '电流', 'unit': 'A',
         'variants': ['Continuous drain current TA=25°C']},
        {'param_name': 'ID Tc=100℃', 'param_name_en': 'Continuous drain current Tc=100℃', 'category': '电流', 'unit': 'A',
         'variants': ['Continuous drain current Tc=100°C']},
        {'param_name': 'ID puls Tc=25℃', 'param_name_en': 'Pulsed drain current', 'category': '电流', 'unit': 'A',
         'variants': ['IDM', 'ID(pulse)', 'Pulsed drain current Tc=25°C']},
        
        # ===== 电容参数（3个）=====
        {'param_name': 'Ciss', 'param_name_en': 'Input capacitance', 'category': '电容', 'unit': 'pF',
         'variants': ['CISS']},
        {'param_name': 'Crss', 'param_name_en': 'Reverse transfer capacitance', 'category': '电容', 'unit': 'pF',
         'variants': ['CRSS', 'Cgd']},
        {'param_name': 'Coss', 'param_name_en': 'Output capacitance', 'category': '电容', 'unit': 'pF',
         'variants': ['COSS']},
        
        # ===== 电荷参数（8个）=====
        {'param_name': 'Qg', 'param_name_en': 'Gate charge total', 'category': '电荷', 'unit': 'nC',
         'variants': ['QG', 'Gate Charge']},
        {'param_name': 'Qgs', 'param_name_en': 'Gate to source charge', 'category': '电荷', 'unit': 'nC',
         'variants': ['QGS']},
        {'param_name': 'Qg（th）', 'param_name_en': 'Gate charge at threshold', 'category': '电荷', 'unit': 'nC',
         'variants': ['Qg(th)', 'QG(th)']},
        {'param_name': 'Qsw', 'param_name_en': 'Switching charge', 'category': '电荷', 'unit': 'nC',
         'variants': ['QSW']},
        {'param_name': 'Qgd', 'param_name_en': 'Gate to drain charge', 'category': '电荷', 'unit': 'nC',
         'variants': ['QGD']},
        {'param_name': 'Qg(sync)', 'param_name_en': 'Gate charge total, sync. FET', 'category': '电荷', 'unit': 'nC',
         'variants': ['Gate charge total sync FET']},
        {'param_name': 'Qoss', 'param_name_en': 'Output charge', 'category': '电荷', 'unit': 'nC',
         'variants': ['QOSS']},
        {'param_name': 'Qrr', 'param_name_en': 'Reverse recovery charge', 'category': '电荷', 'unit': 'nC',
         'variants': ['QRR']},
        
        # ===== 其他电阻参数（1个）=====
        {'param_name': 'Rg', 'param_name_en': 'Gate resistance', 'category': '电阻', 'unit': 'Ω',
         'variants': ['RG']},
        
        # ===== 跨导参数（1个）=====
        {'param_name': 'gfs', 'param_name_en': 'Transconductance', 'category': '其他', 'unit': 'S',
         'variants': ['gFS', 'Gfs']},
        
        # ===== 栅极平台电压（1个）=====
        {'param_name': 'Vplateau', 'param_name_en': 'Gate plateau voltage', 'category': '电压', 'unit': 'V',
         'variants': ['VGP', 'Miller Plateau']},
        
        # ===== 开关时间参数（5个）=====
        {'param_name': 'td-on', 'param_name_en': 'Turn-on delay time', 'category': '时间', 'unit': 'ns',
         'variants': ['td(on)', 'tdon', 'Turn on delay time']},
        {'param_name': 'tr', 'param_name_en': 'Rise time', 'category': '时间', 'unit': 'ns',
         'variants': ['tR']},
        {'param_name': 'td-off', 'param_name_en': 'Turn-off delay time', 'category': '时间', 'unit': 'ns',
         'variants': ['td(off)', 'tdoff', 'Turn off delay time']},
        {'param_name': 'tf', 'param_name_en': 'Fall time', 'category': '时间', 'unit': 'ns',
         'variants': ['tF']},
        {'param_name': 'trr', 'param_name_en': 'Reverse recovery time', 'category': '时间', 'unit': 'ns',
         'variants': ['tRR']},
        
        # ===== 漏电流参数（2个）=====
        {'param_name': 'Idss', 'param_name_en': 'Zero gate voltage drain current', 'category': '电流', 'unit': 'μA',
         'variants': ['IDSS', 'ID(off)']},
        {'param_name': 'Igss', 'param_name_en': 'Gate-source leakage current', 'category': '电流', 'unit': 'nA',
         'variants': ['IGSS', 'IG(leak)']},
        
        # ===== 能量和功耗参数（3个）=====
        {'param_name': 'EAS L=0.1mH', 'param_name_en': 'Avalanche energy, single pulse', 'category': '其他', 'unit': 'mJ',
         'variants': ['EAS', 'Eas', 'Avalanche energy single pulse']},
        {'param_name': 'PD Tc=25℃', 'param_name_en': 'Power dissipation', 'category': '热特性', 'unit': 'W',
         'variants': ['PD', 'Ptot', 'Power dissipation Tc=25°C']},
        
        # ===== 热阻参数（2个）=====
        {'param_name': 'RthJC max', 'param_name_en': 'Thermal resistance, junction - case', 'category': '热特性', 'unit': '℃/W',
         'variants': ['RθJC', 'Rth(j-c)', 'Thermal resistance junction case', 'Thermal resistance junction-case']},
        {'param_name': 'RthJA max', 'param_name_en': 'Thermal resistance, junction - ambient, minimal footprint', 'category': '热特性', 'unit': '℃/W',
         'variants': ['RθJA', 'Rth(j-a)', 'Thermal resistance junction ambient', 'Thermal resistance junction-ambient']},
        
        # ===== 封装和其他信息（10个）=====
        {'param_name': '封装', 'param_name_en': 'Package', 'category': '其他', 'unit': '', 'variants': ['PKG']},
        {'param_name': '特殊功能', 'param_name_en': 'Special Features', 'category': '其他', 'unit': '', 'variants': ['Features']},
        {'param_name': '极性', 'param_name_en': 'Polarity', 'category': '其他', 'unit': '', 'variants': ['N-channel', 'P-channel']},
        {'param_name': 'Product Status', 'param_name_en': 'Product Status', 'category': '其他', 'unit': '', 'variants': []},
        {'param_name': '认证', 'param_name_en': 'Certification', 'category': '其他', 'unit': '', 'variants': []},
        {'param_name': '工作温度min', 'param_name_en': 'Operating and storage temperature', 'category': '热特性', 'unit': '℃',
         'variants': ['Tj(min)', 'Top(min)', 'Operating temperature min']},
        {'param_name': '工作温度max', 'param_name_en': 'Operating and storage temperature', 'category': '热特性', 'unit': '℃',
         'variants': ['Tj(max)', 'Top(max)', 'Operating temperature max']},
        {'param_name': '预算价格€/1k', 'param_name_en': 'Budget Price', 'category': '其他', 'unit': '€', 'variants': []},
        {'param_name': '安装', 'param_name_en': 'Mounting', 'category': '其他', 'unit': '', 'variants': ['SMD', 'THT']},
        {'param_name': 'ESD', 'param_name_en': 'ESD Rating', 'category': '其他', 'unit': '', 'variants': []},
        
        # ===== 提示词中的额外参数（共15个）=====
        # 存储温度
        {'param_name': 'TSTG min', 'param_name_en': 'Storage temperature min', 'category': '热特性', 'unit': '℃',
         'variants': ['Tstg(min)', 'Storage Temperature min']},
        {'param_name': 'TSTG max', 'param_name_en': 'Storage temperature max', 'category': '热特性', 'unit': '℃',
         'variants': ['Tstg(max)', 'Storage Temperature max']},
        {'param_name': 'Tsold', 'param_name_en': 'Soldering temperature', 'category': '热特性', 'unit': '℃',
         'variants': ['Soldering Temperature']},
        
        # 高温导通电阻
        {'param_name': 'RDS(on) 10V TJ=175℃', 'param_name_en': 'Drain-source on-state resistance at high temp', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['Ron 10V TJ=175°C', 'RDS(on) at 175°C']},
        {'param_name': 'RDS(on) 10V TJ=150℃', 'param_name_en': 'Drain-source on-state resistance at high temp', 'category': '电阻', 'unit': 'mΩ',
         'variants': ['Ron 10V TJ=150°C', 'RDS(on) at 150°C']},
        
        # 栅极泄漏电流细分
        {'param_name': 'IGSSF', 'param_name_en': 'Forward gate leakage current', 'category': '电流', 'unit': 'nA',
         'variants': ['IGSS+', 'IGSS forward']},
        {'param_name': 'IGSSR', 'param_name_en': 'Reverse gate leakage current', 'category': '电流', 'unit': 'nA',
         'variants': ['IGSS-', 'IGSS reverse']},
        
        # 高温漏极泄漏电流
        {'param_name': 'IDSS TJ=175℃', 'param_name_en': 'Drain leakage current at high temp', 'category': '电流', 'unit': 'μA',
         'variants': ['IDSS at 175°C']},
        {'param_name': 'IDSS TJ=150℃', 'param_name_en': 'Drain leakage current at high temp', 'category': '电流', 'unit': 'μA',
         'variants': ['IDSS at 150°C']},
        
        # 测试条件参数
        {'param_name': 'Qg测试条件', 'param_name_en': 'Gate charge test condition', 'category': '测试条件', 'unit': '',
         'variants': []},
        {'param_name': 'Ciss测试条件', 'param_name_en': 'Capacitance test condition', 'category': '测试条件', 'unit': '',
         'variants': []},
        {'param_name': '开关时间测试条件', 'param_name_en': 'Switching time test condition', 'category': '测试条件', 'unit': '',
         'variants': []},
        {'param_name': 'Qrr测试条件', 'param_name_en': 'Reverse recovery charge test condition', 'category': '测试条件', 'unit': '',
         'variants': ['di/dt condition']},
        {'param_name': 'EAS测试条件', 'param_name_en': 'Avalanche energy test condition', 'category': '测试条件', 'unit': '',
         'variants': []},
        {'param_name': 'IDM限制条件', 'param_name_en': 'Pulsed drain current limit condition', 'category': '测试条件', 'unit': '',
         'variants': []},
    ]
    
    # ===== IGBT 参数定义（对应「IGBT参数提取格式.xlsx」）=====
    # 说明：
    # - 这里选取 IGBT 表中核心、常用的物理量，保持和模板字段一一对应
    # - 如需扩展，只需在此列表中继续追加定义即可
    igbt_params = [
        # 基本信息
        {'param_name': '文件名', 'param_name_en': 'PDF File Name', 'category': '基本信息', 'unit': '', 'variants': []},
        {'param_name': '厂家', 'param_name_en': 'Manufacturer', 'category': '基本信息', 'unit': '', 'variants': []},
        {'param_name': 'Part Number', 'param_name_en': 'Part Number', 'category': '基本信息', 'unit': '', 'variants': ['OPN', 'Part No.']},
        {'param_name': 'Package', 'param_name_en': 'Package', 'category': '其他', 'unit': '', 'variants': []},
        {'param_name': '技术', 'param_name_en': 'Technology', 'category': '基本信息', 'unit': '', 'variants': []},
        
        # 电压、电流额定值
        {'param_name': 'V(BR)CE', 'param_name_en': 'Collector-emitter voltage', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'IC (TC=25℃)', 'param_name_en': 'DC collector current at Tc=25℃', 'category': '电流', 'unit': 'A', 'variants': ['IC (TC=25°C)']},
        {'param_name': 'IC (TC=100℃)', 'param_name_en': 'DC collector current at Tc=100℃', 'category': '电流', 'unit': 'A', 'variants': ['IC (TC=100°C)']},
        {'param_name': 'ICpulse', 'param_name_en': 'Pulsed collector current', 'category': '电流', 'unit': 'A', 'variants': ['ICpulse (tp limited)']},
        {'param_name': 'IF (TC=25℃)', 'param_name_en': 'Diode forward current at Tc=25℃', 'category': '电流', 'unit': 'A', 'variants': []},
        {'param_name': 'IF (TC=100℃)', 'param_name_en': 'Diode forward current at Tc=100℃', 'category': '电流', 'unit': 'A', 'variants': []},
        {'param_name': 'IFpulse', 'param_name_en': 'Diode pulsed current', 'category': '电流', 'unit': 'A', 'variants': []},
        
        # 二极管反向恢复
        {'param_name': 'Irrm 25℃', 'param_name_en': 'Diode peak reverse recovery current at 25℃', 'category': '电流', 'unit': 'A', 'variants': []},
        {'param_name': 'Irrm 175℃', 'param_name_en': 'Diode peak reverse recovery current at 175℃', 'category': '电流', 'unit': 'A', 'variants': []},
        
        # 栅极、电感、功耗
        {'param_name': 'VGE', 'param_name_en': 'Gate-emitter voltage', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'LE', 'param_name_en': 'Internal emitter inductance', 'category': '其他', 'unit': 'nH', 'variants': []},
        {'param_name': 'Ptot-mos (TC=25℃)', 'param_name_en': 'IGBT power dissipation at Tc=25℃', 'category': '热特性', 'unit': 'W', 'variants': []},
        {'param_name': 'Ptot-mos (TC=100℃)', 'param_name_en': 'IGBT power dissipation at Tc=100℃', 'category': '热特性', 'unit': 'W', 'variants': []},
        {'param_name': 'Ptot-Diode (TC=25℃)', 'param_name_en': 'Diode power dissipation at Tc=25℃', 'category': '热特性', 'unit': 'W', 'variants': []},
        {'param_name': 'Ptot-Diode (TC=100℃)', 'param_name_en': 'Diode power dissipation at Tc=100℃', 'category': '热特性', 'unit': 'W', 'variants': []},
        {'param_name': 'tsc', 'param_name_en': 'Short circuit withstand time', 'category': '时间', 'unit': 'µs', 'variants': []},
        
        # 饱和压降、二极管正向压降
        {'param_name': 'VCE(sat)-type (Tj=25℃)', 'param_name_en': 'Collector-emitter saturation voltage typ at 25℃', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'VCE(sat)max (Tj=25℃)', 'param_name_en': 'Collector-emitter saturation voltage max at 25℃', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'Vcesat type 175℃', 'param_name_en': 'Collector-emitter saturation voltage typ at 175℃', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'VF 25℃', 'param_name_en': 'Diode forward voltage at 25℃', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'VF 100℃', 'param_name_en': 'Diode forward voltage at 100℃', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'VF 175℃', 'param_name_en': 'Diode forward voltage at 175℃', 'category': '电压', 'unit': 'V', 'variants': []},
        
        # 栅极阈值、电流
        {'param_name': 'Vge(th)min', 'param_name_en': 'Gate-emitter threshold voltage min', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'Vge(th)-type', 'param_name_en': 'Gate-emitter threshold voltage typ', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'Vge(th)max', 'param_name_en': 'Gate-emitter threshold voltage max', 'category': '电压', 'unit': 'V', 'variants': []},
        {'param_name': 'ICES 25℃', 'param_name_en': 'Zero gate-voltage collector current at 25℃', 'category': '电流', 'unit': 'µA', 'variants': []},
        {'param_name': 'ICES 100℃', 'param_name_en': 'Zero gate-voltage collector current at 100℃', 'category': '电流', 'unit': 'µA', 'variants': []},
        {'param_name': 'IGES', 'param_name_en': 'Gate-emitter leakage current', 'category': '电流', 'unit': 'nA', 'variants': []},
        {'param_name': 'gfs_IGBT', 'param_name_en': 'Transconductance of IGBT', 'category': '其他', 'unit': 'S', 'variants': ['gfs']},
        
        # 电容
        {'param_name': 'Cies', 'param_name_en': 'Input capacitance', 'category': '电容', 'unit': 'pF', 'variants': ['Cies（pF）']},
        {'param_name': 'Coes', 'param_name_en': 'Output capacitance', 'category': '电容', 'unit': 'pF', 'variants': ['Coes（pF）']},
        {'param_name': 'Cres', 'param_name_en': 'Reverse transfer capacitance', 'category': '电容', 'unit': 'pF', 'variants': ['Cres（pF）']},
        
        # 开关时间
        {'param_name': 'tdon 25℃', 'param_name_en': 'Turn-on delay time at 25℃', 'category': '时间', 'unit': 'ns', 'variants': ['tdon 25℃（ns）']},
        {'param_name': 'tdon 175℃', 'param_name_en': 'Turn-on delay time at 175℃', 'category': '时间', 'unit': 'ns', 'variants': ['tdon 175℃（ns）']},
        {'param_name': 'tr 25℃', 'param_name_en': 'Rise time at 25℃', 'category': '时间', 'unit': 'ns', 'variants': ['tr 25℃（ns）']},
        {'param_name': 'tr 175℃', 'param_name_en': 'Rise time at 175℃', 'category': '时间', 'unit': 'ns', 'variants': ['tr175℃（ns）']},
        {'param_name': 'tdoff 25℃', 'param_name_en': 'Turn-off delay time at 25℃', 'category': '时间', 'unit': 'ns', 'variants': ['tdoff 25℃（ns）']},
        {'param_name': 'tdoff 175℃', 'param_name_en': 'Turn-off delay time at 175℃', 'category': '时间', 'unit': 'ns', 'variants': ['tdoff 175℃（ns）']},
        {'param_name': 'tf 25℃', 'param_name_en': 'Fall time at 25℃', 'category': '时间', 'unit': 'ns', 'variants': ['tf 25℃（ns）']},
        {'param_name': 'tf 175℃', 'param_name_en': 'Fall time at 175℃', 'category': '时间', 'unit': 'ns', 'variants': ['tf 175℃（ns）']},
        {'param_name': 'trr 25℃', 'param_name_en': 'Diode reverse recovery time at 25℃', 'category': '时间', 'unit': 'ns', 'variants': ['trr 25℃（ns）']},
        {'param_name': 'trr 175℃', 'param_name_en': 'Diode reverse recovery time at 175℃', 'category': '时间', 'unit': 'ns', 'variants': ['trr 175℃']},
        
        # 能量
        {'param_name': 'Eon 25℃', 'param_name_en': 'Turn-on energy at 25℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Eon 25℃（uJ）']},
        {'param_name': 'Eon 175℃', 'param_name_en': 'Turn-on energy at 175℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Eon 175℃（uJ）']},
        {'param_name': 'Eoff 25℃', 'param_name_en': 'Turn-off energy at 25℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Eoff（uJ）']},
        {'param_name': 'Eoff 175℃', 'param_name_en': 'Turn-off energy at 175℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Eoff 175℃（uJ）']},
        {'param_name': 'Ets 25℃', 'param_name_en': 'Total switching energy at 25℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Ets 25℃（uJ）']},
        {'param_name': 'Ets 175℃', 'param_name_en': 'Total switching energy at 175℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Ets 175℃（uJ）']},
        {'param_name': 'QG_IGBT', 'param_name_en': 'Gate charge total', 'category': '电荷', 'unit': 'nC', 'variants': ['QG(nc)']},
        {'param_name': 'QGE', 'param_name_en': 'Gate-emitter charge', 'category': '电荷', 'unit': 'nC', 'variants': ['QGE(nc)']},
        {'param_name': 'QGC', 'param_name_en': 'Gate-collector charge', 'category': '电荷', 'unit': 'nC', 'variants': ['QGC(nc)']},
        {'param_name': 'Qrr 25℃_IGBT', 'param_name_en': 'Diode reverse recovery charge at 25℃', 'category': '电荷', 'unit': 'µC', 'variants': ['Qrr 25℃（uC）']},
        {'param_name': 'Qrr 175℃_IGBT', 'param_name_en': 'Diode reverse recovery charge at 175℃', 'category': '电荷', 'unit': 'µC', 'variants': ['Qrr 175℃']},
        {'param_name': 'dirr/dt 25℃', 'param_name_en': 'Diode peak rate of fall of reverse recovery current at 25℃', 'category': '其他', 'unit': 'A/us', 'variants': ['dirr/dt 25℃']},
        {'param_name': 'dirr/dt 150℃', 'param_name_en': 'Diode peak rate of fall of reverse recovery current at 150℃', 'category': '其他', 'unit': 'A/us', 'variants': ['dirr/dt 150℃']},
        {'param_name': 'Erec 25℃', 'param_name_en': 'Reverse recovery energy at 25℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Erec 25℃']},
        {'param_name': 'Erec 175℃', 'param_name_en': 'Reverse recovery energy at 175℃', 'category': '其他', 'unit': 'mJ', 'variants': ['Erec 175℃']},
        
        # 等级、热阻、结温
        {'param_name': '标准等级', 'param_name_en': 'Qualification grade', 'category': '其他', 'unit': '', 'variants': []},
        {'param_name': 'Rth(j-a)', 'param_name_en': 'Thermal resistance junction-ambient', 'category': '热特性', 'unit': 'K/W', 'variants': []},
        {'param_name': 'Rth(j-c)', 'param_name_en': 'Thermal resistance junction-case (IGBT)', 'category': '热特性', 'unit': 'K/W', 'variants': ['Rth(j-c) ']},
        {'param_name': 'Rth(j-c)_diode', 'param_name_en': 'Thermal resistance junction-case (diode)', 'category': '热特性', 'unit': 'K/W', 'variants': []},
        {'param_name': 'Tj min', 'param_name_en': 'Operating junction temperature min', 'category': '热特性', 'unit': '℃', 'variants': []},
        {'param_name': 'Tj max', 'param_name_en': 'Operating junction temperature max', 'category': '热特性', 'unit': '℃', 'variants': []},
    ]
    
    count = 0
    
    # 写入 Si / SiC MOSFET 参数
    for param in mos_params:
        result = db_manager.add_standard_param(
            param_name=param['param_name'],
            param_name_en=param.get('param_name_en'),
            param_type='Si MOSFET,SiC MOSFET',
            unit=param.get('unit'),
            category=param.get('category'),
            variants=param.get('variants', [])
        )
        if result:
            count += 1
    
    # 写入 IGBT 参数
    for param in igbt_params:
        result = db_manager.add_standard_param(
            param_name=param['param_name'],
            param_name_en=param.get('param_name_en'),
            param_type='IGBT',
            unit=param.get('unit'),
            category=param.get('category'),
            variants=param.get('variants', [])
        )
        if result:
            count += 1
    
    logger.info(f"成功初始化 {count} 个参数（Si/SiC MOSFET + IGBT）")
    return count


# ==================== 仪表盘页面 ====================
def render_dashboard_page():
    """渲染仪表盘页面"""
    if not FRONTEND_AVAILABLE:
        st.error("仪表盘组件未加载，请检查frontend模块")
        return
    
    st.title("📊 系统仪表盘")
    
    # 获取数据库管理器
    db_manager = None
    try:
        db_manager = DatabaseManager()
    except:
        pass
    
    # 使用前端组件渲染仪表盘
    try:
        from frontend.dashboard import Dashboard
        dashboard = Dashboard(db_manager)
        dashboard.render()
    except Exception as e:
        st.error(f"渲染仪表盘失败: {e}")
        # 降级显示
        st.info("系统运行正常，暂无详细统计数据")


# ==================== 主函数 ====================
def main():
    """主函数"""
    # 初始化优化模块（只执行一次）
    if OPTIMIZE_AVAILABLE and not st.session_state.get('_optimize_initialized'):
        try:
            initialize_optimization()
            st.session_state._optimize_initialized = True
        except Exception as e:
            logger.warning(f"优化模块初始化失败: {e}")
    
    # 加载CSS
    load_custom_css()
    
    # 初始化Session State
    init_session_state()
    
    # 检查登录状态
    if not st.session_state.logged_in:
        # 未登录，显示登录页面
        render_login_page()
        return
    
    # 已登录，渲染侧边栏
    render_sidebar()
    
    # 根据当前页面渲染内容
    if st.session_state.current_page == '仪表盘':
        render_dashboard_page()
    elif st.session_state.current_page == '解析任务':
        render_parse_page()
    elif st.session_state.current_page == '数据中心':
        render_data_center_page()
    elif st.session_state.current_page == '参数管理':
        render_params_page()
    elif st.session_state.current_page == '生成表格':
        render_table_generation_page()
    elif st.session_state.current_page == '系统设置':
        render_settings_page()
    elif st.session_state.current_page == '个人中心':
        render_profile_page()


if __name__ == "__main__":
    main()

