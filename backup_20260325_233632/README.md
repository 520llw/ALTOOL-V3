# 小罗自优化系统 v3.0 整合版

## 整合方案

结合 **Self-Improving Agent Skill** 的标准格式 + **自动化分析能力**

### 保留的自动化特性 (来自v2.0)
- ✅ 事件驱动架构 (EventBus)
- ✅ 自动检测纠正/错误/功能请求
- ✅ 贝叶斯置信度更新
- ✅ 重复模式检测
- ✅ 7天趋势分析

### 采用的标准格式 (来自Self-Improving Skill)
- ✅ 标准Markdown格式 (LEARNINGS.md/ERRORS.md/FEATURE_REQUESTS.md)
- ✅ 标准ID格式 (LRN-YYYYMMDD-XXX)
- ✅ 完整元数据结构
- ✅ 晋升机制 (→ AGENTS.md/SOUL.md/TOOLS.md)

---

## 文件结构

```
~/.openclaw/workspace/.learnings/
├── LEARNINGS.md          # 学习记录 (标准格式)
├── ERRORS.md             # 错误记录 (标准格式)
├── FEATURE_REQUESTS.md   # 功能请求 (标准格式)
├── self_improvement_v3.py # 自动化引擎
└── .meta/
    ├── confidence.json   # 置信度数据库
    └── trends.json       # 趋势数据
```

---

## 自动检测触发条件

| 用户输入模式 | 自动记录到 | 优先级 |
|:---|:---|:---:|
| "不对/错了/不正确" | LEARNINGS.md (correction) | high |
| "能不能/可以...吗" | FEATURE_REQUESTS.md | medium |
| 工具执行失败 | ERRORS.md | high |
| "我不知道/不确定" | LEARNINGS.md (knowledge_gap) | medium |

---

## 使用方法

### 1. 自动检测（推荐）
```python
from .learnings.self_improvement_v3 import auto_detect

# 每次交互后自动检测
entry_id = auto_detect(
    user_input="用户输入",
    my_response="我的回复"
)
```

### 2. 手动记录
```python
# 记录纠正
log_correction(
    summary="用户纠正了某个点",
    details="详细情况",
    action="下次改进方式"
)

# 记录错误
log_error(
    error_type="ToolError",
    error_message="错误信息",
    context="执行上下文",
    suggested_fix="建议修复"
)

# 记录功能请求
log_feature(
    capability="想要的功能",
    user_context="使用场景"
)
```

### 3. 查看报告
```bash
cd ~/.openclaw/workspace/.learnings
python3 self_improvement_v3.py report
```

---

## 重复模式检测

系统会自动检测重复模式并提升置信度：

- 首次出现：置信度 50%
- 重复2次：置信度 +10%
- 重复3次+：检查晋升条件

当满足以下条件时，建议晋升到工作空间文件：
- 重复次数 ≥ 3
- 置信度 > 80%

---

## 晋升机制

```python
from .learnings.self_improvement_v3 import get_manager

manager = get_manager()

# 晋升到AGENTS.md
manager.promote_to_workspace("LRN-20260325-005", "AGENTS.md")

# 晋升到SOUL.md
manager.promote_to_workspace("LRN-20260325-005", "SOUL.md")

# 晋升到TOOLS.md
manager.promote_to_workspace("LRN-20260325-005", "TOOLS.md")
```

---

## 命令行工具

```bash
# 生成每日报告
python3 self_improvement_v3.py report

# 测试自动检测
python3 self_improvement_v3.py test

# 查看统计
python3 self_improvement_v3.py
```

---

## 集成到主系统

建议在每次交互后调用：

```python
def after_interaction(user_input, my_response):
    # 自动检测并记录
    from .learnings.self_improvement_v3 import auto_detect
    auto_detect(user_input, my_response)
    
    # 其他处理...
```

---

*系统已就绪，开始自动学习！*
