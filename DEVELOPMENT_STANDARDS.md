# ALTOOL V3 开发规范

## 📋 代码风格规范

### 文件头模板
```python
# -*- coding: utf-8 -*-
"""
模块名称

一句话描述模块功能

详细说明:
- 功能1
- 功能2

作者: [开发者名称]
日期: YYYY-MM-DD
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

# 配置日志
logger = logging.getLogger(__name__)
```

### 类定义规范
```python
class ClassName:
    """
    类描述
    
    属性:
        attr1: 描述
        attr2: 描述
    """
    
    def __init__(self, param1: str, param2: int = 0):
        """
        初始化
        
        Args:
            param1: 参数1描述
            param2: 参数2描述，默认0
        """
        self.param1 = param1
        self.param2 = param2
```

### 方法定义规范
```python
def method_name(self, param: str) -> bool:
    """
    方法描述
    
    Args:
        param: 参数描述
        
    Returns:
        返回值描述
        
    Raises:
        ValueError: 错误情况
    """
    pass
```

---

## 📁 项目结构规范

### 目录结构
```
ALTOOL/
├── backend/          # 后端模块
│   ├── __init__.py
│   ├── config.py     # 配置管理
│   ├── cache_manager.py
│   ├── file_utils.py
│   └── ...
├── frontend/         # 前端组件
│   ├── __init__.py
│   ├── dashboard.py
│   └── ...
├── data/             # 数据目录
│   ├── uploads/      # 上传文件
│   └── params.db     # 数据库
├── cache/            # 缓存目录
├── backup/           # 备份目录
└── logs/             # 日志目录
```

### 文件路径规范
```python
# 正确：使用绝对路径或基于__file__的相对路径
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"

# 错误：不要使用硬编码路径或~路径
# ❌ DATA_DIR = "~/project/data"
# ❌ DATA_DIR = "/home/user/project/data"
```

---

## 🔧 错误处理规范

### 异常处理模板
```python
try:
    # 可能出错的操作
    result = risky_operation()
except FileNotFoundError as e:
    logger.error(f"文件未找到: {e}")
    raise  # 或者返回错误信息
except PermissionError as e:
    logger.error(f"权限不足: {e}")
    raise
except Exception as e:
    logger.exception(f"未知错误: {e}")
    raise RuntimeError(f"操作失败: {e}") from e
```

### 错误返回值
```python
from typing import Tuple, Optional

def safe_operation() -> Tuple[bool, str]:
    """
    返回: (是否成功, 错误信息/结果)
    """
    try:
        # 操作
        return True, "成功"
    except Exception as e:
        return False, str(e)
```

---

## 📝 日志规范

### 日志级别使用
```python
# DEBUG: 详细信息，仅开发时启用
logger.debug(f"计算MD5: {file_path}")

# INFO: 正常操作信息
logger.info(f"缓存命中: {md5[:8]}...")

# WARNING: 警告信息，不会导致失败
logger.warning(f"缓存已过期: {md5[:8]}...")

# ERROR: 错误信息，操作失败
logger.error(f"读取文件失败: {e}")

# EXCEPTION: 异常信息，包含堆栈
logger.exception(f"未知错误: {e}")
```

### 日志格式
```python
"""
格式: [时间] [级别] [模块] 消息
示例: 2024-03-25 10:30:45 [INFO] [cache_manager] 缓存命中: a1b2c3d4...
"""
```

---

## 🧪 测试规范

### 每个模块都要有测试代码
```python
if __name__ == "__main__":
    print("=== 模块名称测试 ===")
    
    # 测试1: 基础功能
    obj = ClassName()
    assert obj.method() == expected
    print("✓ 测试1通过")
    
    # 测试2: 边界情况
    try:
        obj.method(invalid_input)
        assert False, "应该抛出异常"
    except ValueError:
        print("✓ 测试2通过")
    
    print("✓ 所有测试通过")
```

---

## 🔗 模块间协作规范

### 数据交换格式
```python
# 统一使用字典格式
result = {
    "success": True,
    "data": {...},
    "error": None
}

# 或者使用dataclass
from dataclasses import dataclass

@dataclass
class Result:
    success: bool
    data: Any = None
    error: str = None
```

### 模块导入顺序
```python
# 1. 标准库
import os
import sys
from pathlib import Path

# 2. 第三方库
import streamlit as st

# 3. 项目内部模块
from backend.cache_manager import CacheManager
from backend.config import DATA_DIR
```

---

## ✅ 审查检查清单

### 代码审查必查项
- [ ] 文件头是否有完整注释
- [ ] 类和方法是否有docstring
- [ ] 类型注解是否完整
- [ ] 错误处理是否完善
- [ ] 日志记录是否恰当
- [ ] 是否有独立测试代码
- [ ] 文件路径处理是否正确
- [ ] 代码风格是否一致

### 模块间一致性检查
- [ ] 接口定义是否一致
- [ ] 数据格式是否统一
- [ ] 错误处理方式是否相同
- [ ] 日志格式是否统一
- [ ] 文件路径处理是否一致

---

**制定时间**: 2026-03-25  
**制定人**: 小罗 (Leader)  
**适用范围**: ALTOOL V3 项目
