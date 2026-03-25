#!/usr/bin/env python3
"""
小罗自优化系统 v3.0 - 整合版
============================
结合 Self-Improving Agent Skill 的标准格式 + 自动化分析能力

特性:
- 标准Markdown格式 (LEARNINGS/ERRORS/FEATURE)
- 自动提取教训 (事件驱动)
- 贝叶斯置信度更新
- 自动晋升机制 (重要教训→AGENTS/SOUL/TOOLS)
- 7天趋势分析

作者: 小罗
版本: 3.0.0
日期: 2026-03-25
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import threading


# ============================================================
# 配置
# ============================================================
WORKSPACE = Path("/home/llw/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
LEARNINGS_DIR.mkdir(exist_ok=True)

# 标准文件路径
LEARNINGS_FILE = LEARNINGS_DIR / "LEARNINGS.md"
ERRORS_FILE = LEARNINGS_DIR / "ERRORS.md"
FEATURES_FILE = LEARNINGS_DIR / "FEATURE_REQUESTS.md"

# 元数据存储（用于自动化分析）
META_DIR = LEARNINGS_DIR / ".meta"
META_DIR.mkdir(exist_ok=True)
CONFIDENCE_DB = META_DIR / "confidence.json"
TREND_DB = META_DIR / "trends.json"


# 有效值枚举
VALID_PRIORITIES = {'low', 'medium', 'high', 'critical'}
VALID_STATUSES = {'pending', 'in_progress', 'resolved', 'promoted', 'wont_fix'}
VALID_AREAS = {'frontend', 'backend', 'infra', 'tests', 'docs', 'config', 'workflow', 'general'}
VALID_SOURCES = {'auto', 'user_feedback', 'error'}

# 输入长度限制
MAX_INPUT_LENGTH = 10000
MAX_SUMMARY_LENGTH = 500


def sanitize_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """清理用户输入（防止注入）"""
    if not isinstance(text, str):
        text = str(text)
    # 限制长度
    text = text[:max_length]
    # 移除控制字符（保留换行和制表）
    text = ''.join(c for c in text if c == '\n' or c == '\t' or (ord(c) >= 32 and ord(c) < 127) or ord(c) > 255)
    return text


def validate_priority(priority: str) -> str:
    """验证优先级"""
    if priority not in VALID_PRIORITIES:
        return 'medium'  # 默认值
    return priority


def validate_status(status: str) -> str:
    """验证状态"""
    if status not in VALID_STATUSES:
        return 'pending'  # 默认值
    return status


def validate_area(area: str) -> str:
    """验证领域"""
    if area not in VALID_AREAS:
        return 'general'  # 默认值
    return area


# ============================================================
# 事件系统
# ============================================================
class EventBus:
    """事件总线（修复P0：线程安全）"""
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: str, handler: Callable):
        with self._lock:
            # 避免重复订阅
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)
    
    def publish(self, event_type: str, data: Any):
        # 复制handler列表避免遍历时被修改（修复P0）
        with self._lock:
            handlers = self._handlers.get(event_type, []).copy()
        
        # 锁外执行handler（避免死锁）
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                print(f"[事件错误] {event_type}: {e}")


event_bus = EventBus()


# ============================================================
# ID生成器
# ============================================================
class IDGenerator:
    """标准ID生成器: TYPE-YYYYMMDD-XXX"""
    
    def __init__(self):
        self._counter = 0
    
    def generate(self, entry_type: str, existing_ids: set = None) -> str:
        """生成标准ID（修复P0问题：避免冲突）"""
        type_map = {
            'learning': 'LRN',
            'error': 'ERR',
            'feature': 'FEAT'
        }
        prefix = type_map.get(entry_type, 'UNK')
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 生成唯一ID
        max_attempts = 100
        for _ in range(max_attempts):
            self._counter += 1
            # 使用计数器+随机字符确保唯一性
            random_part = hashlib.md5(
                f"{datetime.now().timestamp()}{self._counter}".encode()
            ).hexdigest()[:3].upper()
            
            entry_id = f"{prefix}-{date_str}-{random_part}"
            
            # 检查是否冲突
            if existing_ids is None or entry_id not in existing_ids:
                return entry_id
        
        # 如果冲突太多，使用时间戳+计数器
        return f"{prefix}-{date_str}-{self._counter:03d}"


# ============================================================
# 条目类
# ============================================================
@dataclass
class LearningEntry:
    """学习条目（添加输入验证）"""
    entry_id: str
    timestamp: str
    category: str  # correction, knowledge_gap, best_practice
    summary: str
    details: str
    action: str
    priority: str = "medium"  # low, medium, high, critical
    status: str = "pending"   # pending, in_progress, resolved, promoted
    area: str = "general"     # frontend, backend, infra, config, workflow
    source: str = "auto"      # auto, user_feedback, error
    see_also: List[str] = field(default_factory=list)
    pattern_key: str = ""     # 用于重复模式检测
    recurrence_count: int = 0
    confidence: float = 0.5   # 贝叶斯置信度
    
    def __post_init__(self):
        """初始化后验证（修复P0：输入验证）"""
        # 验证并清理输入
        self.summary = sanitize_input(self.summary, MAX_SUMMARY_LENGTH)
        self.details = sanitize_input(self.details)
        self.action = sanitize_input(self.action, MAX_SUMMARY_LENGTH)
        self.category = sanitize_input(self.category, 100)
        
        # 验证枚举值
        self.priority = validate_priority(self.priority)
        self.status = validate_status(self.status)
        self.area = validate_area(self.area)
        
        # 验证置信度范围
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        
        # 验证计数器非负
        self.recurrence_count = max(0, int(self.recurrence_count))
    
    def to_markdown(self) -> str:
        """转换为标准Markdown格式"""
        md = f"""## [{self.entry_id}] {self.category}

**Logged**: {self.timestamp}
**Priority**: {self.priority}
**Status**: {self.status}
**Area**: {self.area}

### Summary
{self.summary}

### Details
{self.details}

### Suggested Action
{self.action}

### Metadata
- Source: {self.source}
- Confidence: {self.confidence:.0%}
"""
        if self.pattern_key:
            md += f"- Pattern-Key: {self.pattern_key}\n"
        if self.recurrence_count > 0:
            md += f"- Recurrence-Count: {self.recurrence_count}\n"
        if self.see_also:
            md += f"- See Also: {', '.join(self.see_also)}\n"
        
        md += "\n---\n"
        return md


@dataclass
class ErrorEntry:
    """错误条目"""
    entry_id: str
    timestamp: str
    error_type: str
    summary: str
    error_message: str
    context: str
    suggested_fix: str
    priority: str = "high"
    status: str = "pending"
    area: str = "general"
    reproducible: str = "unknown"  # yes, no, unknown
    see_also: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """转换为标准Markdown格式"""
        md = f"""## [{self.entry_id}] {self.error_type}

**Logged**: {self.timestamp}
**Priority**: {self.priority}
**Status**: {self.status}
**Area**: {self.area}

### Summary
{self.summary}

### Error
```
{self.error_message}
```

### Context
{self.context}

### Suggested Fix
{self.suggested_fix}

### Metadata
- Reproducible: {self.reproducible}
"""
        if self.see_also:
            md += f"- See Also: {', '.join(self.see_also)}\n"
        
        md += "\n---\n"
        return md


@dataclass
class FeatureEntry:
    """功能请求条目"""
    entry_id: str
    timestamp: str
    capability: str
    user_context: str
    complexity: str = "medium"  # simple, medium, complex
    priority: str = "medium"
    status: str = "pending"
    frequency: str = "first_time"  # first_time, recurring
    see_also: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """转换为标准Markdown格式"""
        md = f"""## [{self.entry_id}] {self.capability}

**Logged**: {self.timestamp}
**Priority**: {self.priority}
**Status**: {self.status}

### Requested Capability
{self.capability}

### User Context
{self.user_context}

### Complexity Estimate
{self.complexity}

### Metadata
- Frequency: {self.frequency}
"""
        if self.see_also:
            md += f"- See Also: {', '.join(self.see_also)}\n"
        
        md += "\n---\n"
        return md


# ============================================================
# 核心管理器
# ============================================================
class SelfImprovementManager:
    """自改进管理器 v3.0"""
    
    def __init__(self):
        self.id_gen = IDGenerator()
        self.entries_cache: Dict[str, List] = {
            'learnings': [],
            'errors': [],
            'features': []
        }
        # 搜索优化：使用字典索引
        self.pattern_index: Dict[str, LearningEntry] = {}  # pattern_key -> entry
        self.id_index: Dict[str, Any] = {}  # entry_id -> entry
        self._existing_ids: set = set()  # 用于ID冲突检测
        
        self.confidence_db: Dict = {}
        self._lock = threading.Lock()  # 线程锁
        
        # 加载已有数据（修复P0问题：加载失败不运行避免数据覆写）
        try:
            self._load_entries()
        except Exception as e:
            print(f"[致命错误] 无法加载历史数据: {e}")
            print("[致命错误] 系统不能以空状态运行，请检查数据文件权限")
            raise SystemExit(1)  # 不允许空状态运行导致数据覆写
        
        try:
            self._load_confidence()
        except Exception as e:
            print(f"[警告] 加载置信度数据库失败: {e}")
            self.confidence_db = {}
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        event_bus.subscribe("user_correction", self._handle_correction)
        event_bus.subscribe("tool_error", self._handle_error)
        event_bus.subscribe("feature_request", self._handle_feature_request)
        event_bus.subscribe("new_insight", self._handle_insight)
    
    def _load_confidence(self):
        """加载置信度数据库"""
        if CONFIDENCE_DB.exists():
            with open(CONFIDENCE_DB, 'r', encoding='utf-8') as f:
                self.confidence_db = json.load(f)
    
    def _load_entries(self):
        """从文件加载已有条目（修复P0问题：缓存与持久化不一致）"""
        # 加载LEARNINGS
        if LEARNINGS_FILE.exists():
            self._parse_learnings_file(LEARNINGS_FILE)
        
        # 加载ERRORS
        if ERRORS_FILE.exists():
            self._parse_errors_file(ERRORS_FILE)
        
        # 加载FEATURES
        if FEATURES_FILE.exists():
            self._parse_features_file(FEATURES_FILE)
        
        print(f"[加载] 已加载 {len(self.entries_cache['learnings'])} 条学习, "
              f"{len(self.entries_cache['errors'])} 条错误, "
              f"{len(self.entries_cache['features'])} 条功能请求")
    
    def _parse_learnings_file(self, filepath: Path):
        """解析学习记录文件"""
        try:
            content = filepath.read_text(encoding='utf-8')
            # 移除header，按条目分割（按---分隔）
            content = re.sub(r'^# Learnings\n+', '', content)
            entries = re.split(r'\n---\n', content)
            
            for entry_text in entries:
                if not entry_text.strip() or not entry_text.strip().startswith('##'):
                    continue
                
                entry = self._parse_learning_entry(entry_text)
                if entry:
                    self._add_to_cache_and_index(entry)
        except Exception as e:
            print(f"[警告] 解析学习文件失败: {e}")
    
    def _parse_learning_entry(self, text: str) -> Optional[LearningEntry]:
        """解析单个学习条目"""
        try:
            # 提取ID
            id_match = re.search(r'## \[(.+?)\]', text)
            if not id_match:
                return None
            entry_id = id_match.group(1)
            
            # 提取category（ID后的内容）
            category_match = re.search(r'## \[.+?\] (\w+)', text)
            category = category_match.group(1) if category_match else 'general'
            
            # 提取timestamp
            ts_match = re.search(r'\*\*Logged\*\*: (.+)', text)
            timestamp = ts_match.group(1) if ts_match else datetime.now().isoformat()
            
            # 提取priority
            prio_match = re.search(r'\*\*Priority\*\*: (\w+)', text)
            priority = prio_match.group(1) if prio_match else 'medium'
            
            # 提取status
            status_match = re.search(r'\*\*Status\*\*: (\w+)', text)
            status = status_match.group(1) if status_match else 'pending'
            
            # 提取area
            area_match = re.search(r'\*\*Area\*\*: (\w+)', text)
            area = area_match.group(1) if area_match else 'general'
            
            # 提取summary
            summary_match = re.search(r'### Summary\n(.+?)(?=###|\Z)', text, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else ''
            
            # 提取details
            details_match = re.search(r'### Details\n(.+?)(?=###|\Z)', text, re.DOTALL)
            details = details_match.group(1).strip() if details_match else ''
            
            # 提取action
            action_match = re.search(r'### Suggested Action\n(.+?)(?=###|\Z)', text, re.DOTALL)
            action = action_match.group(1).strip() if action_match else ''
            
            # 提取source
            source_match = re.search(r'- Source: (\w+)', text)
            source = source_match.group(1) if source_match else 'auto'
            
            # 提取confidence
            conf_match = re.search(r'- Confidence: (\d+)%', text)
            confidence = float(conf_match.group(1)) / 100 if conf_match else 0.5
            
            # 提取pattern_key
            pk_match = re.search(r'- Pattern-Key: (.+)', text)
            pattern_key = pk_match.group(1).strip() if pk_match else ''
            
            # 提取recurrence_count
            rc_match = re.search(r'- Recurrence-Count: (\d+)', text)
            recurrence_count = int(rc_match.group(1)) if rc_match else 0
            
            # 记录ID用于冲突检测
            self._existing_ids.add(entry_id)
            
            return LearningEntry(
                entry_id=entry_id,
                timestamp=timestamp,
                category=category,
                summary=summary,
                details=details,
                action=action,
                priority=priority,
                status=status,
                area=area,
                source=source,
                confidence=confidence,
                pattern_key=pattern_key,
                recurrence_count=recurrence_count
            )
        except Exception as e:
            print(f"[警告] 解析条目失败: {e}")
            return None
    
    def _parse_errors_file(self, filepath: Path):
        """解析错误记录文件（修复高危问题：完整加载）"""
        try:
            content = filepath.read_text(encoding='utf-8')
            # 移除header
            content = re.sub(r'^# Errors\n+', '', content)
            entries = re.split(r'\n---\n', content)
            
            count = 0
            for entry_text in entries:
                if not entry_text.strip() or not entry_text.strip().startswith('##'):
                    continue
                
                entry = self._parse_error_entry(entry_text)
                if entry:
                    self.entries_cache['errors'].append(entry)
                    self.id_index[entry.entry_id] = entry
                    self._existing_ids.add(entry.entry_id)
                    count += 1
            
            print(f"[加载] 已加载 {count} 条错误记录")
        except Exception as e:
            print(f"[警告] 解析错误文件失败: {e}")
    
    def _parse_error_entry(self, text: str) -> Optional[ErrorEntry]:
        """解析单个错误条目"""
        try:
            id_match = re.search(r'## \[(.+?)\]', text)
            if not id_match:
                return None
            entry_id = id_match.group(1)
            
            error_type_match = re.search(r'## \[.+?\] (\w+)', text)
            error_type = error_type_match.group(1) if error_type_match else 'Unknown'
            
            ts_match = re.search(r'\*\*Logged\*\*: (.+)', text)
            timestamp = ts_match.group(1) if ts_match else datetime.now().isoformat()
            
            prio_match = re.search(r'\*\*Priority\*\*: (\w+)', text)
            priority = prio_match.group(1) if prio_match else 'high'
            
            status_match = re.search(r'\*\*Status\*\*: (\w+)', text)
            status = status_match.group(1) if status_match else 'pending'
            
            area_match = re.search(r'\*\*Area\*\*: (\w+)', text)
            area = area_match.group(1) if area_match else 'general'
            
            summary_match = re.search(r'### Summary\n(.+?)(?=###|\Z)', text, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else ''
            
            # 提取错误消息（在```代码块中）
            error_match = re.search(r'### Error\n```\n(.+?)\n```', text, re.DOTALL)
            error_message = error_match.group(1).strip() if error_match else ''
            
            context_match = re.search(r'### Context\n(.+?)(?=###|\Z)', text, re.DOTALL)
            context = context_match.group(1).strip() if context_match else ''
            
            fix_match = re.search(r'### Suggested Fix\n(.+?)(?=###|\Z)', text, re.DOTALL)
            suggested_fix = fix_match.group(1).strip() if fix_match else ''
            
            return ErrorEntry(
                entry_id=entry_id,
                timestamp=timestamp,
                error_type=error_type,
                summary=summary,
                error_message=error_message,
                context=context,
                suggested_fix=suggested_fix,
                priority=priority,
                status=status,
                area=area
            )
        except Exception as e:
            print(f"[警告] 解析错误条目失败: {e}")
            return None
    
    def _parse_features_file(self, filepath: Path):
        """解析功能请求文件（修复高危问题：完整加载）"""
        try:
            content = filepath.read_text(encoding='utf-8')
            # 移除header
            content = re.sub(r'^# Feature Requests\n+', '', content)
            entries = re.split(r'\n---\n', content)
            
            count = 0
            for entry_text in entries:
                if not entry_text.strip() or not entry_text.strip().startswith('##'):
                    continue
                
                entry = self._parse_feature_entry(entry_text)
                if entry:
                    self.entries_cache['features'].append(entry)
                    self.id_index[entry.entry_id] = entry
                    self._existing_ids.add(entry.entry_id)
                    count += 1
            
            print(f"[加载] 已加载 {count} 条功能请求")
        except Exception as e:
            print(f"[警告] 解析功能请求文件失败: {e}")
    
    def _parse_feature_entry(self, text: str) -> Optional[FeatureEntry]:
        """解析单个功能请求条目"""
        try:
            id_match = re.search(r'## \[(.+?)\]', text)
            if not id_match:
                return None
            entry_id = id_match.group(1)
            
            capability_match = re.search(r'## \[.+?\] (.+)', text)
            capability = capability_match.group(1).strip() if capability_match else ''
            
            ts_match = re.search(r'\*\*Logged\*\*: (.+)', text)
            timestamp = ts_match.group(1) if ts_match else datetime.now().isoformat()
            
            prio_match = re.search(r'\*\*Priority\*\*: (\w+)', text)
            priority = prio_match.group(1) if prio_match else 'medium'
            
            status_match = re.search(r'\*\*Status\*\*: (\w+)', text)
            status = status_match.group(1) if status_match else 'pending'
            
            context_match = re.search(r'### User Context\n(.+?)(?=###|\Z)', text, re.DOTALL)
            user_context = context_match.group(1).strip() if context_match else ''
            
            complexity_match = re.search(r'### Complexity Estimate\n(\w+)', text)
            complexity = complexity_match.group(1) if complexity_match else 'medium'
            
            freq_match = re.search(r'- Frequency: (\w+)', text)
            frequency = freq_match.group(1) if freq_match else 'first_time'
            
            return FeatureEntry(
                entry_id=entry_id,
                timestamp=timestamp,
                capability=capability,
                user_context=user_context,
                priority=priority,
                status=status,
                complexity=complexity,
                frequency=frequency
            )
        except Exception as e:
            print(f"[警告] 解析功能请求条目失败: {e}")
            return None
    
    def _save_confidence(self):
        """保存置信度数据库（修复P0问题：原子写入）"""
        try:
            import os
            import tempfile
            
            # 构建内容
            content = json.dumps(self.confidence_db, ensure_ascii=False, indent=2)
            
            # 原子写入
            temp_fd, temp_path = tempfile.mkstemp(
                dir=CONFIDENCE_DB.parent,
                suffix='.tmp',
                text=True
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                
                # 原子重命名
                os.replace(temp_path, CONFIDENCE_DB)
                
            except Exception as e:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e
                
        except Exception as e:
            print(f"[错误] 保存置信度数据库失败: {e}")
    
    # ========================================================
    # 自动检测与记录
    # ========================================================
    
    def detect_and_log(self, user_input: str, my_response: str, 
                      context: Dict = None) -> Optional[str]:
        """自动检测并记录"""
        user_lower = user_input.lower()
        context = context or {}
        
        # 检测纠正
        correction_patterns = [
            (r'不对|错了|不正确|有误|不是|应该是', 'correction', '用户提供纠正'),
            (r'不对.*应该是|错了.*正确', 'correction', '具体纠正'),
            (r'实际上|事实上|其实', 'correction', '事实澄清'),
        ]
        
        for pattern, category, desc in correction_patterns:
            if re.search(pattern, user_lower):
                return self._create_learning(
                    category=category,
                    summary=f"用户纠正: {desc}",
                    details=f"用户输入: {user_input}\n我的回复: {my_response}",
                    action="下次遇到类似情况时更仔细地验证",
                    priority="high",
                    source="user_feedback"
                )
        
        # 检测功能请求
        feature_patterns = [
            (r'能不能|能不能|可以.*吗|能不能.*功能', 'feature_request'),
            (r'我希望|我想要|需要.*功能', 'feature_request'),
            (r'是否.*可以|能否.*增加', 'feature_request'),
        ]
        
        for pattern, intent in feature_patterns:
            if re.search(pattern, user_lower):
                return self._create_feature_request(
                    capability=user_input,
                    user_context="用户主动提出需求",
                    frequency="first_time"
                )
        
        # 检测知识缺口
        knowledge_patterns = [
            (r'我不知道|我不确定|需要查一下', 'knowledge_gap'),
            (r'这个我不太清楚|这个我不太确定', 'knowledge_gap'),
        ]
        
        for pattern, category in knowledge_patterns:
            if re.search(pattern, my_response.lower()):
                return self._create_learning(
                    category=category,
                    summary="识别到知识缺口",
                    details=f"无法回答: {user_input}",
                    action="记录并学习该知识点",
                    priority="medium",
                    source="auto"
                )
        
        return None
    
    def log_error(self, error_type: str, error_message: str, 
                  context: str, suggested_fix: str = "") -> str:
        """记录错误"""
        entry_id = self.id_gen.generate('error', self._existing_ids)
        
        entry = ErrorEntry(
            entry_id=entry_id,
            timestamp=datetime.now().isoformat(),
            error_type=error_type,
            summary=f"{error_type}错误",
            error_message=error_message,
            context=context,
            suggested_fix=suggested_fix or "需要进一步分析",
            priority="high",
            area=self._detect_area(context)
        )
        
        # 追加到文件
        self._append_to_file(ERRORS_FILE, entry.to_markdown())
        
        # 更新缓存
        self.entries_cache['errors'].append(entry)
        
        print(f"[错误记录] {entry_id}")
        return entry_id
    
    def _create_learning(self, category: str, summary: str, details: str,
                        action: str, priority: str = "medium",
                        area: str = "general", source: str = "auto") -> str:
        """创建学习条目（修复P0：锁覆盖整个方法）"""
        with self._lock:  # 锁覆盖整个判断-写入周期
            entry_id = self.id_gen.generate('learning', self._existing_ids)
            
            # 检查是否已存在类似条目
            pattern_key = self._generate_pattern_key(category, summary)
            existing = self._find_similar_learning(pattern_key)
            
            if existing:
                # 更新现有条目
                existing.recurrence_count += 1
                existing.confidence = min(1.0, existing.confidence * 1.1 + 0.05)
                # 同步更新confidence_db
                self.confidence_db[existing.entry_id] = existing.confidence
                
                self._save_confidence()
                
                # 关键修复：重写文件同步更新
                self._rewrite_learning_file()
                
                print(f"[学习更新] {existing.entry_id} (重复{existing.recurrence_count}次, 置信度{existing.confidence:.0%})")
                
                # 检查是否需要晋升
                self._check_promotion(existing)
                
                return existing.entry_id
            
            # 创建新条目
            entry = LearningEntry(
                entry_id=entry_id,
                timestamp=datetime.now().isoformat(),
                category=category,
                summary=summary,
                details=details,
                action=action,
                priority=priority,
                area=area,
                source=source,
                pattern_key=pattern_key
            )
            
            # 初始化置信度
            self.confidence_db[entry_id] = 0.5
            self._save_confidence()
            
            # 记录ID（避免ID冲突）
            self._existing_ids.add(entry_id)
            
            # 追加到文件
            self._append_to_file(LEARNINGS_FILE, entry.to_markdown())
            
            # 更新缓存和索引（锁内调用无锁版本）
            self._add_to_cache_and_index_nolock(entry)
            
            print(f"[学习记录] {entry_id}")
            return entry_id
    
    def _create_feature_request(self, capability: str, user_context: str,
                               frequency: str = "first_time") -> str:
        """创建功能请求"""
        entry_id = self.id_gen.generate('feature', self._existing_ids)
        
        entry = FeatureEntry(
            entry_id=entry_id,
            timestamp=datetime.now().isoformat(),
            capability=capability,
            user_context=user_context,
            frequency=frequency
        )
        
        # 追加到文件
        self._append_to_file(FEATURES_FILE, entry.to_markdown())
        
        # 更新缓存
        self.entries_cache['features'].append(entry)
        
        print(f"[功能请求] {entry_id}")
        return entry_id
    
    # ========================================================
    # 辅助方法
    # ========================================================
    
    def _append_to_file(self, filepath: Path, content: str):
        """追加内容到文件（带错误处理和并发控制）"""
        import fcntl
        import tempfile
        import os
        
        try:
            # 确保目录存在
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # 确保文件存在且有头部
            if not filepath.exists():
                header = f"# {filepath.stem.replace('_', ' ').title()}\n\n"
                filepath.write_text(header, encoding='utf-8')
            
            # 使用文件锁进行并发控制
            with open(filepath, 'a', encoding='utf-8') as f:
                # 获取排他锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())  # 确保写入磁盘
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    
        except IOError as e:
            # 磁盘满或权限问题
            print(f"[错误] 无法写入文件 {filepath}: {e}")
            # 尝试写入临时文件作为备份
            backup_path = filepath.parent / f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            try:
                backup_path.write_text(content, encoding='utf-8')
                print(f"[备份] 内容已保存到 {backup_path}")
            except:
                pass
        except Exception as e:
            print(f"[错误] 未知错误: {e}")
    
    def _generate_pattern_key(self, category: str, summary: str) -> str:
        """生成模式键（用于重复检测）"""
        # 简化文本，提取关键词
        simplified = re.sub(r'[^\w\s]', '', summary.lower())
        words = sorted(set(simplified.split()))[:5]
        return f"{category}.{'.'.join(words)}"
    
    def _find_similar_learning(self, pattern_key: str) -> Optional[LearningEntry]:
        """查找类似的学习条目（使用索引优化，O(1)）"""
        return self.pattern_index.get(pattern_key)
    
    def _add_to_cache_and_index(self, entry: LearningEntry):
        """添加条目到缓存和索引"""
        with self._lock:
            self._add_to_cache_and_index_nolock(entry)
    
    def _add_to_cache_and_index_nolock(self, entry: LearningEntry):
        """添加条目到缓存和索引（无锁版本，调用者需持有锁）"""
        self.entries_cache['learnings'].append(entry)
        self.id_index[entry.entry_id] = entry
        if entry.pattern_key:
            self.pattern_index[entry.pattern_key] = entry
    
    def _update_index(self, entry: LearningEntry):
        """更新索引"""
        with self._lock:
            self.id_index[entry.entry_id] = entry
            if entry.pattern_key:
                self.pattern_index[entry.pattern_key] = entry
    
    def _rewrite_learning_file(self):
        """重写学习文件（修复P0问题：原子写入避免截断竞争）"""
        try:
            import fcntl
            import os
            import tempfile
            
            # 构建完整文件内容
            header = "# Learnings\n\n"
            content = header
            
            # 按时间排序所有学习条目
            sorted_entries = sorted(
                self.entries_cache['learnings'],
                key=lambda e: e.timestamp
            )
            
            for entry in sorted_entries:
                content += entry.to_markdown()
            
            # P0修复：使用原子写入（先写临时文件再重命名）
            temp_fd, temp_path = tempfile.mkstemp(
                dir=LEARNINGS_FILE.parent,
                suffix='.tmp',
                text=True
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                
                # 原子重命名（Unix原子操作）
                os.replace(temp_path, LEARNINGS_FILE)
                
            except Exception as e:
                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e
                    
        except Exception as e:
            print(f"[错误] 重写学习文件失败: {e}")
    
    def _update_entry_in_file(self, entry: LearningEntry):
        """更新文件中的条目（简化实现：重新写入整个文件）"""
        # 实际实现中应该使用更高效的更新方式
        pass
    
    def _detect_area(self, context: str) -> str:
        """检测领域"""
        context_lower = context.lower()
        area_keywords = {
            'frontend': ['ui', '界面', '前端', 'html', 'css'],
            'backend': ['api', '后端', '数据库', '服务器'],
            'infra': ['docker', '部署', 'ci/cd', '配置'],
            'config': ['配置', '设置', 'yaml', 'json'],
            'workflow': ['流程', '工作流', '自动化'],
        }
        
        for area, keywords in area_keywords.items():
            if any(kw in context_lower for kw in keywords):
                return area
        return "general"
    
    def _check_promotion(self, entry: LearningEntry):
        """检查是否需要晋升"""
        # 晋升条件：重复3次以上，置信度>0.8
        if entry.recurrence_count >= 3 and entry.confidence > 0.8:
            print(f"[晋升建议] {entry.entry_id} 满足晋升条件")
            # 实际晋升逻辑由外部调用处理
            entry.status = "promoted"
    
    # ========================================================
    # 事件处理器
    # ========================================================
    
    def _handle_correction(self, data: Dict):
        """处理纠正事件"""
        self._create_learning(
            category='correction',
            summary=data.get('summary', '用户纠正'),
            details=data.get('details', ''),
            action=data.get('action', '下次注意'),
            priority='high',
            source='user_feedback'
        )
    
    def _handle_error(self, data: Dict):
        """处理错误事件"""
        self.log_error(
            error_type=data.get('error_type', 'Unknown'),
            error_message=data.get('error_message', ''),
            context=data.get('context', ''),
            suggested_fix=data.get('suggested_fix', '')
        )
    
    def _handle_feature_request(self, data: Dict):
        """处理功能请求事件"""
        self._create_feature_request(
            capability=data.get('capability', ''),
            user_context=data.get('context', ''),
            frequency=data.get('frequency', 'first_time')
        )
    
    def _handle_insight(self, data: Dict):
        """处理新洞察"""
        self._create_learning(
            category='best_practice',
            summary=data.get('summary', '新发现'),
            details=data.get('details', ''),
            action=data.get('action', '应用此最佳实践'),
            priority='medium',
            source='auto'
        )
    
    # ========================================================
    # 分析与报告
    # ========================================================
    
    def get_pending_items(self) -> Dict[str, List]:
        """获取待处理条目（修复线程安全问题）"""
        result = {'learnings': [], 'errors': [], 'features': []}
        
        with self._lock:  # 加锁保护遍历
            for category, entries in self.entries_cache.items():
                for entry in entries:
                    if hasattr(entry, 'status') and entry.status == 'pending':
                        result[category].append(entry)
        
        return result
    
    def get_high_priority(self, min_priority: str = "high") -> List:
        """获取高优先级条目（修复线程安全问题）"""
        priority_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        min_level = priority_order.get(min_priority, 2)
        
        result = []
        with self._lock:  # 加锁保护遍历
            for category, entries in self.entries_cache.items():
                for entry in entries:
                    if hasattr(entry, 'priority'):
                        if priority_order.get(entry.priority, 0) >= min_level:
                            result.append(entry)
        
        return result
    
    def generate_daily_report(self) -> str:
        """生成每日报告（修复线程安全问题）"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 在锁内复制数据避免遍历冲突
        with self._lock:
            today_entries = {
                'learnings': [e for e in self.entries_cache['learnings'] if e.timestamp.startswith(today)],
                'errors': [e for e in self.entries_cache['errors'] if e.timestamp.startswith(today)],
                'features': [e for e in self.entries_cache['features'] if e.timestamp.startswith(today)]
            }
            recurring = [e for e in self.entries_cache['learnings'] if e.recurrence_count >= 2]
        
        # 锁外生成报告（无竞争）
        report = f"""
📊 小罗每日改进报告 ({today})
{'='*50}

📈 今日记录:
   学习条目: {len(today_entries['learnings'])}
   错误记录: {len(today_entries['errors'])}
   功能请求: {len(today_entries['features'])}

🔥 高优先级待处理:
"""
        
        high_priority = self.get_high_priority("high")
        if high_priority:
            for entry in high_priority[:5]:
                report += f"   • [{entry.entry_id}] {entry.summary[:40]}...\n"
        else:
            report += "   无高优先级项目\n"
        
        report += f"\n💡 重复模式检测:\n"
        if recurring:
            for entry in recurring[:3]:
                report += f"   • {entry.pattern_key} (重复{entry.recurrence_count}次)\n"
        else:
            report += "   暂无重复模式\n"
        
        report += f"\n📋 待处理总数:\n"
        pending = self.get_pending_items()
        report += f"   学习: {len(pending['learnings'])} | 错误: {len(pending['errors'])} | 功能: {len(pending['features'])}\n"
        
        return report
    
    def promote_to_workspace(self, entry_id: str, target: str) -> bool:
        """晋升条目到工作空间文件"""
        # target: AGENTS.md, SOUL.md, TOOLS.md
        target_file = WORKSPACE / target
        
        # 查找条目
        entry = None
        for e in self.entries_cache['learnings']:
            if e.entry_id == entry_id:
                entry = e
                break
        
        if not entry:
            return False
        
        # 构建晋升内容
        content = f"""
## {entry.summary}
**来源**: {entry.entry_id}
**置信度**: {entry.confidence:.0%}

{entry.details}

**行动**: {entry.action}
"""
        
        # 追加到目标文件
        with open(target_file, 'a', encoding='utf-8') as f:
            f.write(content)
        
        # 更新状态
        entry.status = "promoted"
        
        print(f"[晋升完成] {entry_id} → {target}")
        return True


# ============================================================
# 便捷API
# ============================================================
_manager = None
_manager_lock = threading.Lock()

def get_manager() -> SelfImprovementManager:
    """获取管理器实例（修复P0：线程安全单例）"""
    global _manager
    if _manager is None:
        with _manager_lock:
            # 双重检查锁定
            if _manager is None:
                _manager = SelfImprovementManager()
    return _manager


def auto_detect(user_input: str, my_response: str, **context) -> Optional[str]:
    """自动检测并记录"""
    return get_manager().detect_and_log(user_input, my_response, context)


def log_correction(summary: str, details: str, action: str):
    """记录纠正"""
    event_bus.publish("user_correction", {
        'summary': summary,
        'details': details,
        'action': action
    })


def log_error(error_type: str, error_message: str, context: str, suggested_fix: str = ""):
    """记录错误"""
    return get_manager().log_error(error_type, error_message, context, suggested_fix)


def log_feature(capability: str, user_context: str):
    """记录功能请求"""
    event_bus.publish("feature_request", {
        'capability': capability,
        'context': user_context
    })


def report():
    """显示报告"""
    print(get_manager().generate_daily_report())


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    import sys
    
    manager = get_manager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "report":
            report()
        elif sys.argv[1] == "test":
            # 测试自动检测
            entry_id = auto_detect(
                user_input="不对，应该这样写才对",
                my_response="原来如此"
            )
            if entry_id:
                print(f"✅ 检测到并记录: {entry_id}")
            else:
                print("ℹ️ 未检测到需要记录的内容")
        else:
            print("用法: python self_improvement_v3.py [report|test]")
    else:
        print("📚 自优化系统 v3.0 (整合版)")
        print(f"   学习条目: {len(manager.entries_cache['learnings'])}")
        print(f"   错误记录: {len(manager.entries_cache['errors'])}")
        print(f"   功能请求: {len(manager.entries_cache['features'])}")
        print(f"\n用法: report | test")
