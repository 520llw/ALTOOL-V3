# -*- coding: utf-8 -*-
"""
ALTOOL V3.0 美化版主程序
现代化UI设计
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from frontend.ui_v3 import (
    apply_v3_styles, v3_header, v3_card, 
    v3_progress_bar, v3_stat_card, v3_device_card
)

# 页面配置
st.set_page_config(
    page_title="ALTOOL V3.0 - 功率器件参数提取",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 应用样式
apply_v3_styles()

# ==================== 主页面 ====================
v3_header(
    "⚡ ALTOOL V3.0",
    "智能功率半导体器件参数提取系统 - 更快、更准、更美观"
)

# 统计卡片
st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    v3_stat_card("62+", "标准参数", "+12%", True)
with col2:
    v3_stat_card("3", "器件类型", "全面覆盖", True)
with col3:
    v3_stat_card("4", "导出格式", "JSON/CSV/XML/Excel", True)
with col4:
    v3_stat_card("300%", "速度提升", "缓存优化", True)

st.markdown("<br>", unsafe_allow_html=True)

# 功能介绍
st.markdown("### 🚀 V3.0 核心功能")

col1, col2 = st.columns(2)
with col1:
    v3_card(
        "智能PDF解析",
        "采用pdfplumber + PyMuPDF双引擎，精准提取表格和文本内容。支持多进程并行处理，大幅提升解析速度。",
        "📄"
    )
    v3_card(
        "AI参数提取",
        "基于DeepSeek大模型，智能识别器件类型并提取62+标准参数。V3.0优化Prompt，准确率进一步提升。",
        "🤖"
    )

with col2:
    v3_card(
        "多格式导出",
        "支持JSON、CSV、XML、Excel多种格式导出，方便与其他系统集成，满足不同场景需求。",
        "📊"
    )
    v3_card(
        "RESTful API",
        "提供完整的API接口，支持程序化调用。轻松集成到现有工作流，实现自动化处理。",
        "🔌"
    )

st.markdown("<br>", unsafe_allow_html=True)

# 支持的器件类型
st.markdown("### 🔧 支持的器件类型")

col1, col2, col3 = st.columns(3)
with col1:
    v3_device_card(
        "Si MOSFET",
        "⚡",
        "#3B82F6",
        "硅基MOSFET功率器件，广泛应用于电源管理"
    )
with col2:
    v3_device_card(
        "SiC MOSFET",
        "🔥",
        "#EF4444",
        "碳化硅MOSFET，高频高温应用场景"
    )
with col3:
    v3_device_card(
        "IGBT",
        "🔌",
        "#10B981",
        "绝缘栅双极型晶体管，高功率应用"
    )

st.markdown("<br>", unsafe_allow_html=True)

# 快速开始
st.markdown("### 🚀 快速开始")

st.code("""
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动Web界面
streamlit run main.py

# 3. 或启动API服务
python api_server.py
""")

st.markdown("<br>", unsafe_allow_html=True)

# 版本信息
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#999;'>"
    "ALTOOL V3.0 | 功率器件参数提取系统 | © 2024-2025"
    "</p>",
    unsafe_allow_html=True
)
