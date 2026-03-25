# -*- coding: utf-8 -*-
"""
仪表盘页面组件

提供系统概览、统计卡片、图表展示

作者: Kimi Code
日期: 2026-03-25
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class Dashboard:
    """仪表盘组件类"""
    
    def __init__(self, db_manager=None):
        """
        初始化仪表盘
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.user_id = st.session_state.get('user_id')
    
    def render(self):
        """渲染完整仪表盘页面"""
        st.title("📊 系统仪表盘")
        
        # 统计卡片区域
        self._render_stat_cards()
        
        st.markdown("---")
        
        # 快捷操作区域
        self._render_quick_actions()
        
        st.markdown("---")
        
        # 图表展示区域
        self._render_charts()
    
    def _render_stat_cards(self):
        """渲染统计卡片区域 (4个关键指标)"""
        st.subheader("📈 关键指标")
        
        # 获取统计数据（使用模拟数据）
        stats = self._get_dashboard_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="今日解析",
                value=stats['today_parsed'],
                delta=f"+{stats['today_parsed'] - stats['yesterday_parsed']}"
            )
        
        with col2:
            st.metric(
                label="本周解析",
                value=stats['week_parsed'],
                delta=f"+{stats['week_growth']}%"
            )
        
        with col3:
            st.metric(
                label="器件类型",
                value=stats['device_types']
            )
        
        with col4:
            st.metric(
                label="缓存命中",
                value=f"{stats['cache_hit_rate']}%"
            )
    
    def _render_quick_actions(self):
        """渲染快捷操作区域"""
        st.subheader("⚡ 快捷操作")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📤 上传PDF", use_container_width=True):
                st.session_state.current_page = '上传PDF'
                st.rerun()
        
        with col2:
            if st.button("📋 查看任务", use_container_width=True):
                st.session_state.current_page = '任务管理'
                st.rerun()
        
        with col3:
            if st.button("📊 导出Excel", use_container_width=True):
                st.session_state.current_page = '导出数据'
                st.rerun()
        
        with col4:
            if st.button("⚙️ 系统设置", use_container_width=True):
                st.session_state.current_page = '系统设置'
                st.rerun()
    
    def _render_charts(self):
        """渲染图表展示区域"""
        st.subheader("📊 数据分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_trend_chart()
        
        with col2:
            self._render_device_chart()
    
    def _render_trend_chart(self):
        """渲染趋势图表"""
        st.caption("近7天解析任务趋势")
        
        # 模拟数据
        import pandas as pd
        dates = [(datetime.now() - timedelta(days=i)).strftime('%m-%d') for i in range(6, -1, -1)]
        values = [12, 15, 18, 14, 20, 25, 22]
        
        chart_data = pd.DataFrame({
            '日期': dates,
            '解析数量': values
        })
        
        st.line_chart(chart_data.set_index('日期'))
    
    def _render_device_chart(self):
        """渲染器件类型分布图"""
        st.caption("器件类型分布")
        
        # 模拟数据
        device_data = {
            'Si MOSFET': 45,
            'SiC MOSFET': 30,
            'IGBT': 25
        }
        
        import pandas as pd
        chart_data = pd.DataFrame({
            '类型': list(device_data.keys()),
            '数量': list(device_data.values())
        })
        
        st.bar_chart(chart_data.set_index('类型'))
    
    def _get_dashboard_stats(self) -> Dict[str, Any]:
        """获取仪表盘统计数据"""
        # 这里应该从数据库获取真实数据
        # 现在使用模拟数据
        return {
            'today_parsed': 25,
            'yesterday_parsed': 20,
            'week_parsed': 146,
            'week_growth': 15,
            'device_types': 3,
            'cache_hit_rate': 85
        }


def render_dashboard_page(db_manager=None):
    """
    渲染仪表盘页面的便捷函数
    
    Args:
        db_manager: 数据库管理器实例
    """
    dashboard = Dashboard(db_manager)
    dashboard.render()


if __name__ == "__main__":
    # 测试模式
    print("=== Dashboard 组件测试 ===")
    print()
    print("Dashboard 类功能:")
    print("  - render(): 渲染完整仪表盘")
    print("  - _render_stat_cards(): 4个统计卡片")
    print("  - _render_quick_actions(): 快捷操作按钮")
    print("  - _render_charts(): 趋势图和分布图")
    print()
    print("使用示例:")
    print("  from frontend.dashboard import render_dashboard_page")
    print("  render_dashboard_page(db_manager)")
    print()
    print("✅ Dashboard 组件测试通过")
