# TASK_KIMI_STEP2.md - 第二步：完善测试并运行

## 🎯 任务
完善测试代码，添加更多测试用例，然后运行测试

## 📁 工作目录
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/

## 📝 具体要求

### 1. 完善 test_cache_manager.py

添加更多测试用例：

```python
# -*- coding: utf-8 -*-
"""CacheManager单元测试"""
import pytest
import tempfile
import os
from pathlib import Path


class TestCacheManager:
    """测试CacheManager"""
    
    def test_init(self, temp_dir):
        """测试初始化"""
        from backend.cache_manager import CacheManager
        cm = CacheManager(str(temp_dir / "cache"))
        assert cm.cache_dir.exists()
    
    def test_compute_md5(self, temp_dir):
        """测试MD5计算"""
        from backend.cache_manager import CacheManager
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        md5 = cm.compute_md5(str(test_file))
        assert len(md5) == 32
        assert md5 == "9473fdd0d880a43c21b7778d38bbc627"  # 预期MD5
    
    def test_cache_operations(self, temp_dir):
        """测试缓存读写"""
        from backend.cache_manager import CacheManager
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 测试缓存写入
        test_md5 = "abc123"
        test_result = {"data": "test", "status": "ok"}
        cm.cache_result(test_md5, test_result)
        
        # 测试缓存读取
        cached = cm.get_cached_result(test_md5)
        assert cached == test_result
    
    def test_cache_expiration(self, temp_dir):
        """测试缓存过期检查"""
        from backend.cache_manager import CacheManager
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 创建测试缓存
        test_md5 = "expired_test"
        cm.cache_result(test_md5, {"data": "test"})
        
        # 检查缓存有效（默认30天）
        assert cm.is_cache_valid(test_md5) == True
    
    def test_inherits_from_base_manager(self, temp_dir):
        """测试继承BaseManager"""
        from backend.cache_manager import CacheManager
        from backend.base_manager import BaseManager
        
        assert issubclass(CacheManager, BaseManager)
        
        cm = CacheManager(str(temp_dir / "cache"))
        assert hasattr(cm, 'get_stats')
        assert hasattr(cm, '_load_json')
        assert hasattr(cm, '_save_json')
```

### 2. 完善 test_file_utils.py

```python
# -*- coding: utf-8 -*-
"""FileUtils单元测试"""
import pytest
from pathlib import Path


class TestFileUtils:
    """测试FileUtils"""
    
    def test_sanitize_filename(self, temp_dir):
        """测试文件名清理"""
        from backend.file_utils import FileUtils
        fu = FileUtils(str(temp_dir))
        
        # 测试路径遍历攻击
        result = fu.sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert result == "passwd"
        
        # 测试非法字符
        result = fu.sanitize_filename("file\u003cname\u003e.txt")
        assert "<" not in result
        assert ">" not in result
    
    def test_is_path_safe(self, temp_dir):
        """测试路径安全检查"""
        from backend.file_utils import FileUtils
        fu = FileUtils(str(temp_dir))
        
        # 安全路径
        assert fu.is_path_safe("test.pdf") == True
        
        # 不安全路径（路径遍历）
        assert fu.is_path_safe("../test.pdf") == False
    
    def test_validate_file_type(self, temp_dir):
        """测试文件类型验证"""
        from backend.file_utils import FileUtils
        fu = FileUtils(str(temp_dir))
        
        # 创建测试PDF文件
        test_pdf = temp_dir / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4 test content")
        
        assert fu.validate_file_type(str(test_pdf)) == True
```

### 3. 运行测试

完成后执行：
```bash
cd /home/llw/.openclaw/workspace/shared/ALTOOL_V3 && python3 -m pytest tests/unit/ -v
```

## ✅ 完成标准

- [ ] test_cache_manager.py 完善
- [ ] test_file_utils.py 完善
- [ ] 所有测试用例通过
- [ ] 测试覆盖率 > 50%

## 📤 汇报

完成后汇报：
1. 测试运行结果（通过/失败数量）
2. 测试覆盖率
3. 发现的任何问题
