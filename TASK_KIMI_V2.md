# TASK_KIMI_V2.md - Kimi Code 任务（修订版）

## 🎯 任务目标
完成前端界面组件开发

## 📁 强制要求

**所有文件必须保存在此目录下**:
```
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/frontend/
```

**绝对路径，不可更改！**

---

## 📝 任务内容

### 1. dashboard.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/frontend/dashboard.py`

功能要求（Streamlit组件）：
- 统计卡片区域（4个关键指标）
- 趋势图表（Plotly，近7天数据）
- 器件类型饼图（Si/SiC/IGBT分布）
- 快捷操作按钮

### 2. progress.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/frontend/progress.py`

功能要求：
- 进度条 + 百分比显示
- 当前处理文件名
- 预计剩余时间（自动计算）
- 处理速度（文件/分钟）
- 批量任务追踪器

### 3. guide.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/frontend/guide.py`

功能要求：
- 首次登录检测
- 3步引导流程（上传PDF→开始解析→查看结果）
- 步骤进度指示器
- 支持跳过和重置

### 4. __init__.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/frontend/__init__.py`

导出所有组件：
```python
from .dashboard import Dashboard, render_dashboard_page
from .progress import ProgressWidget, BatchProgressTracker
from .guide import UserGuide, check_and_show_guide
```

---

## ✅ 完成标准

1. **文件必须实际存在**: 完成后执行 `ls -lh` 验证文件
2. **代码可导入**: 能通过 `from frontend.dashboard import Dashboard` 导入
3. **包含测试代码**: 每个文件末尾必须有测试代码或演示代码
4. **符合开发规范**: 见 DEVELOPMENT_STANDARDS.md

---

## 📤 完成汇报格式

完成后请汇报：
1. 文件保存的绝对路径列表
2. 运行 `ls -lh /home/llw/.openclaw/workspace/shared/ALTOOL_V3/frontend/*.py` 的输出
3. 每个组件的使用示例

---

**重要提醒**: 不要只返回代码内容，必须确保文件已保存到磁盘！
