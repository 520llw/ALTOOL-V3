# -*- coding: utf-8 -*-
"""CacheManager单元测试"""
import pytest
import tempfile
import os
import sys
import types
import importlib.util
from pathlib import Path

# 动态加载 base_manager 和 cache_manager
def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

backend_dir = Path(__file__).parent.parent.parent / "backend"

# 先加载 base_manager
base_manager_path = backend_dir / "base_manager.py"
base_manager = load_module_from_path("base_manager", base_manager_path)

# 创建假的 backend 模块
if "backend" not in sys.modules:
    backend_mod = types.ModuleType("backend")
    backend_mod.__path__ = [str(backend_dir)]
    backend_mod.base_manager = base_manager
    sys.modules["backend"] = backend_mod
    sys.modules["backend.base_manager"] = base_manager

# 加载 cache_manager
cache_manager_path = backend_dir / "cache_manager.py"
cache_manager = load_module_from_path("cache_manager", cache_manager_path)

CacheManager = cache_manager.CacheManager
BaseManager = base_manager.BaseManager


class TestCacheManager:
    """测试CacheManager"""
    
    def test_init(self, temp_dir):
        """测试初始化"""
        cm = CacheManager(str(temp_dir / "cache"))
        assert cm.cache_dir.exists()
    
    def test_compute_md5(self, temp_dir):
        """测试MD5计算"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        md5 = cm.compute_md5(str(test_file))
        assert len(md5) == 32
        assert md5 == "9473fdd0d880a43c21b7778d34872157"  # 预期MD5
    
    def test_cache_operations(self, temp_dir):
        """测试缓存读写"""
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
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 创建测试缓存
        test_md5 = "expired_test"
        cm.cache_result(test_md5, {"data": "test"})
        
        # 检查缓存有效（默认30天）
        assert cm.is_cache_valid(test_md5) == True
    
    def test_inherits_from_base_manager(self, temp_dir):
        """测试继承BaseManager"""
        # 检查MRO中是否有BaseManager（通过名称，因为动态加载可能导致类实例不同）
        base_names = [cls.__name__ for cls in CacheManager.__mro__]
        assert "BaseManager" in base_names
        
        cm = CacheManager(str(temp_dir / "cache"))
        assert hasattr(cm, 'get_stats')
        assert hasattr(cm, '_load_json')
        assert hasattr(cm, '_save_json')

    def test_compute_md5_empty_file(self, temp_dir):
        """测试空文件的MD5计算"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 创建空文件
        test_file = temp_dir / "empty.txt"
        test_file.write_text("")
        
        md5 = cm.compute_md5(str(test_file))
        assert len(md5) == 32
        # 空文件的MD5: d41d8cd98f00b204e9800998ecf8427e
        assert md5 == "d41d8cd98f00b204e9800998ecf8427e"

    def test_compute_md5_nonexistent_file(self, temp_dir):
        """测试不存在的文件的MD5计算"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        md5 = cm.compute_md5(str(temp_dir / "nonexistent.txt"))
        assert md5 == ""

    def test_cache_not_found(self, temp_dir):
        """测试读取不存在的缓存"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        result = cm.get_cached_result("nonexistent_md5")
        assert result is None

    def test_cache_with_file_name(self, temp_dir):
        """测试带文件名的缓存"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        test_md5 = "test_md5_123"
        test_result = {"data": "test"}
        cm.cache_result(test_md5, test_result, file_name="test.pdf")
        
        cached = cm.get_cached_result(test_md5)
        assert cached == test_result

    def test_cache_stats(self, temp_dir):
        """测试缓存统计信息"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 添加缓存
        cm.cache_result("test1", {"data": "test1"})
        cm.cache_result("test2", {"data": "test2"})
        
        # 访问缓存以增加命中
        cm.get_cached_result("test1")
        
        stats = cm.get_stats()
        assert "total_files" in stats
        assert stats["total_files"] == 2
        assert "manager_type" in stats
        assert stats["manager_type"] == "CacheManager"

    def test_clear_all_cache(self, temp_dir):
        """测试清除所有缓存"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        cm.cache_result("test1", {"data": "test1"})
        cm.cache_result("test2", {"data": "test2"})
        
        success, msg = cm.clear_all_cache()
        assert success is True
        assert "2" in msg  # 应该清除2个缓存

    def test_get_cache_list(self, temp_dir):
        """测试获取缓存列表"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        cm.cache_result("test1", {"data": "test1"}, "file1.pdf")
        cm.cache_result("test2", {"data": "test2"}, "file2.pdf")
        
        cache_list = cm.get_cache_list()
        assert len(cache_list) == 2
        assert all("md5_hash" in item for item in cache_list)
        assert all("file_name" in item for item in cache_list)
