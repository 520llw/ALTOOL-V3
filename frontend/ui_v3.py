# -*- coding: utf-8 -*-
"""
V3.0 UI美化模块 - 现代化界面组件
"""

import streamlit as st

# V3.0 现代化CSS样式
V3_CSS = """
<style>
/* ===== 全局主题 ===== */
:root {
    --primary-color: #1E3A8A;
    --secondary-color: #3B82F6;
    --success-color: #10B981;
    --warning-color: #F59E0B;
    --error-color: #EF4444;
    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --card-shadow: 0 10px 40px -10px rgba(0,0,0,0.2);
}

/* ===== 页面背景 ===== */
.stApp {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

/* ===== 卡片样式 ===== */
.v3-card {
    background: white;
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 10px 40px -10px rgba(0,0,0,0.15);
    margin: 16px 0;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.v3-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 20px 60px -15px rgba(0,0,0,0.2);
}

/* ===== 按钮样式 ===== */
.v3-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 28px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.v3-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
}

/* ===== 输入框样式 ===== */
.v3-input {
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    padding: 12px 16px;
    transition: all 0.3s ease;
}

.v3-input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

/* ===== 标题样式 ===== */
.v3-title {
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 8px;
}

.v3-subtitle {
    color: #666;
    text-align: center;
    font-size: 1.1rem;
    margin-bottom: 32px;
}

/* ===== 进度条样式 ===== */
.v3-progress {
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}

.v3-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    border-radius: 4px;
    transition: width 0.5s ease;
}

/* ===== 标签样式 ===== */
.v3-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

.v3-badge-success {
    background: rgba(16, 185, 129, 0.1);
    color: #10B981;
}

.v3-badge-warning {
    background: rgba(245, 158, 11, 0.1);
    color: #F59E0B;
}

/* ===== 数据表格样式 ===== */
.v3-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.v3-table th {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 16px;
    font-weight: 600;
}

.v3-table td {
    padding: 14px 16px;
    border-bottom: 1px solid #f0f0f0;
}

.v3-table tr:hover {
    background: #f8f9ff;
}

/* ===== 动画 ===== */
@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.v3-animate-in {
    animation: slideInUp 0.6s ease;
}

/* ===== 侧边栏样式 ===== */
.v3-sidebar {
    background: white;
    border-radius: 0 20px 20px 0;
    padding: 20px;
}
</style>
"""


def apply_v3_styles():
    """应用V3.0样式"""
    st.markdown(V3_CSS, unsafe_allow_html=True)


def v3_header(title: str, subtitle: str = ""):
    """V3.0标题组件"""
    st.markdown(f'<h1 class="v3-title v3-animate-in">{title}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="v3-subtitle">{subtitle}</p>', unsafe_allow_html=True)


def v3_card(title: str, content: str, icon: str = "💡"):
    """V3.0卡片组件"""
    html = f'''
    <div class="v3-card v3-animate-in">
        <h3 style="margin-top:0;color:#1E3A8A;">{icon} {title}</h3>
        <p style="color:#666;line-height:1.6;">{content}</p>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)


def v3_progress_bar(progress: float, label: str = ""):
    """V3.0进度条组件"""
    percentage = int(progress * 100)
    html = f'''
    <div style="margin:20px 0;">
        {f'<p style="margin-bottom:8px;color:#666;">{label}</p>' if label else ''}
        <div class="v3-progress">
            <div class="v3-progress-bar" style="width:{percentage}%;"></div>
        </div>
        <p style="text-align:right;color:#666;font-size:0.9rem;">{percentage}%</p>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)


def v3_stat_card(value: str, label: str, change: str = "", positive: bool = True):
    """V3.0统计卡片"""
    color = "#10B981" if positive else "#EF4444"
    change_html = f'<span style="color:{color};font-weight:600;">{change}</span>' if change else ""
    
    html = f'''
    <div class="v3-card" style="text-align:center;">
        <h2 style="margin:0;color:#1E3A8A;font-size:2.5rem;">{value}</h2>
        <p style="color:#666;margin:8px 0;">{label}</p>
        {change_html}
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)


def v3_device_card(device_type: str, icon: str, color: str, description: str):
    """V3.0器件类型卡片"""
    html = f'''
    <div class="v3-card" style="border-left:4px solid {color};">
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-size:2.5rem;">{icon}</span>
            <div>
                <h3 style="margin:0;color:{color};">{device_type}</h3>
                <p style="color:#666;margin:4px 0 0 0;font-size:0.9rem;">{description}</p>
            </div>
        </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)
