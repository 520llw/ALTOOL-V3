# 任务分配: Kimi Code

## 任务1: 实现仪表盘页面
文件: `frontend/dashboard.py`

功能要求:
1. 统计卡片 (4个关键指标):
   - 今日解析文件数
   - 本周解析文件数
   - 器件类型分布 (Si/SiC/IGBT)
   - 系统缓存命中率

2. 图表展示:
   - 解析任务趋势图 (近7天)
   - 器件类型饼图
   - 使用 Plotly 或 Streamlit 原生图表

3. 快捷操作按钮:
   - 上传PDF
   - 查看最近任务
   - 导出Excel

## 任务2: 实现进度组件
文件: `frontend/progress.py`

功能:
```python
class ProgressWidget:
    def __init__(self, total: int, title: str = "处理中"):
    def update(self, current: int, message: str = ""):
    def set_message(self, message: str):
    def finish(self, message: str = "完成"):
    def error(self, message: str):
```

要求:
- 显示进度条 (百分比)
- 显示当前处理文件名
- 显示预计剩余时间
- 显示处理速度 (文件/分钟)

## 任务3: 实现新手引导
文件: `frontend/guide.py`

功能:
```python
class UserGuide:
    def __init__(self, user_id: str):
    def should_show_guide(self) -> bool:  # 检查是否是首次登录
    def show_step_1_upload(self):  # 第1步: 上传PDF
    def show_step_2_parse(self):   # 第2步: 开始解析
    def show_step_3_view(self):    # 第3步: 查看结果
    def mark_guide_completed(self):  # 标记已完成引导
```

使用 Streamlit 的 st.dialog 或 st.expander 实现

## 约束
- 使用 Streamlit 组件
- 样式与现有 main.py 一致
- 支持深色/浅色模式
- 响应式布局

## 参考
- 查看 `main.py` 中的样式定义
- 查看 `backend/db_manager.py` 了解如何获取数据

完成后请报告:
1. 创建了哪些文件
2. 每个组件的使用示例
3. 截图或功能演示
