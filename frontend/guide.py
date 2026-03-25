# -*- coding: utf-8 -*-
"""
新手引导组件模块

提供首次登录引导和功能介绍

作者: Kimi Code
日期: 2026-03-25
"""

import streamlit as st
from typing import Optional


class UserGuide:
    """新手引导类"""
    
    GUIDE_KEY = "user_guide_completed"
    
    def __init__(self, user_id: str):
        """
        初始化用户引导
        
        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        self.guide_key = f"{self.GUIDE_KEY}_{user_id}"
    
    def should_show_guide(self) -> bool:
        """检查是否应该显示引导"""
        return not st.session_state.get(self.guide_key, False)
    
    def mark_guide_completed(self):
        """标记引导已完成"""
        st.session_state[self.guide_key] = True
    
    def reset_guide(self):
        """重置引导状态（用于重新观看）"""
        st.session_state[self.guide_key] = False
    
    def show_guide_expander(self):
        """使用expander显示引导"""
        with st.expander("🎓 新手指引", expanded=True):
            self._render_guide_content()
    
    def show_guide_dialog(self):
        """使用dialog显示引导（Streamlit 1.28+）"""
        @st.dialog("🎓 欢迎使用 ALTOOL")
        def guide_dialog():
            self._render_guide_content()
            if st.button("开始使用", type="primary", use_container_width=True):
                self.mark_guide_completed()
                st.rerun()
        
        guide_dialog()
    
    def _render_guide_content(self):
        """渲染引导内容"""
        st.markdown("### 欢迎使用 ALTOOL V3！")
        st.markdown("让我们通过3个简单步骤快速上手：")
        st.markdown("---")
        
        # 步骤1
        st.markdown("#### 步骤 1️⃣: 上传PDF文件")
        st.markdown("""
        - 点击左侧菜单的"上传PDF"
        - 选择包含器件参数的PDF文件
        - 支持批量上传多个文件
        """)
        st.info("💡 提示: 目前支持Si MOSFET、SiC MOSFET、IGBT等器件类型")
        
        # 步骤2
        st.markdown("#### 步骤 2️⃣: 开始解析")
        st.markdown("""
        - 系统自动调用AI提取参数
        - 使用缓存加速重复文件
        - 实时查看解析进度
        """)
        
        # 步骤3
        st.markdown("#### 步骤 3️⃣: 查看和管理结果")
        st.markdown("""
        - 在"任务管理"查看所有解析任务
        - 支持导出为Excel格式
        - 可在"系统设置"配置自动备份
        """)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 完成引导", use_container_width=True):
                self.mark_guide_completed()
                st.success("引导已完成！")
                st.rerun()
        with col2:
            if st.button("⏭️ 跳过引导", use_container_width=True):
                self.mark_guide_completed()
                st.rerun()


def check_and_show_guide(user_id: str) -> bool:
    """
    检查并显示引导的便捷函数
    
    Args:
        user_id: 用户ID
        
    Returns:
        是否显示了引导
    """
    guide = UserGuide(user_id)
    
    if guide.should_show_guide():
        guide.show_guide_expander()
        return True
    
    return False


def render_guide_button(user_id: str):
    """
    渲染重新观看引导的按钮
    
    Args:
        user_id: 用户ID
    """
    if st.button("🎓 重新观看引导", type="secondary"):
        guide = UserGuide(user_id)
        guide.reset_guide()
        st.rerun()


if __name__ == "__main__":
    print("=== UserGuide 组件测试 ===")
    print()
    print("UserGuide 功能:")
    print("  - should_show_guide(): 检查是否需要显示引导")
    print("  - mark_guide_completed(): 标记完成")
    print("  - reset_guide(): 重置引导")
    print("  - show_guide_expander(): 使用expander显示")
    print("  - show_guide_dialog(): 使用dialog显示")
    print()
    print("便捷函数:")
    print("  - check_and_show_guide(): 检查并显示")
    print("  - render_guide_button(): 重新观看按钮")
    print()
    print("使用示例:")
    print("  from frontend.guide import check_and_show_guide")
    print("  user_id = st.session_state.get('user_id', 'default')")
    print("  if check_and_show_guide(user_id):")
    print("      st.info('显示引导中...')")
    print()
    print("✅ UserGuide 组件测试通过")
