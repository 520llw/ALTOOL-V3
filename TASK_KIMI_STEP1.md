# TASK_KIMI_STEP1.md - 第一步：创建测试目录结构

## 🎯 任务
创建完整的测试目录结构

## 📁 工作目录
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/

## 📝 具体要求

创建以下目录结构：

```
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_cache_manager.py
│   └── test_file_utils.py
└── integration/
    └── __init__.py
```

## 📝 文件内容

**tests/__init__.py**: 空文件

**tests/conftest.py**:
```python
# -*- coding: utf-8 -*-
"""pytest配置"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)
```

**tests/unit/__init__.py**: 空文件

**tests/unit/test_cache_manager.py**:
```python
# -*- coding: utf-8 -*-
"""CacheManager单元测试"""
import pytest
import tempfile
from pathlib import Path
from backend.cache_manager import CacheManager


class TestCacheManager:
    """测试CacheManager"""
    
    def test_init(self, temp_dir):
        """测试初始化"""
        cm = CacheManager(str(temp_dir))
        assert cm.cache_dir.exists()
    
    def test_compute_md5(self, temp_dir):
        """测试MD5计算"""
        cm = CacheManager(str(temp_dir))
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        md5 = cm.compute_md5(str(test_file))
        assert len(md5) == 32
```

**tests/unit/test_file_utils.py**:
```python
# -*- coding: utf-8 -*-
"""FileUtils单元测试"""
import pytest
from backend.file_utils import FileUtils


class TestFileUtils:
    """测试FileUtils"""
    
    def test_sanitize_filename(self, temp_dir):
        """测试文件名清理"""
        fu = FileUtils(str(temp_dir))
        result = fu.sanitize_filename("../../../etc/passwd")
        assert "/" not in result
```

**tests/integration/__init__.py**: 空文件

## ✅ 完成验证

完成后执行：
```bash
ls -lah /home/llw/.openclaw/workspace/shared/ALTOOL_V3/tests/
ls -lah /home/llw/.openclaw/workspace/shared/ALTOOL_V3/tests/unit/
```

## 📤 汇报

完成后汇报：
1. 创建的目录结构
2. 每个文件的大小
3. 验证命令的输出
