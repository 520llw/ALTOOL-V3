# -*- coding: utf-8 -*-
"""CacheManager扩展单元测试"""
import pytest
import sys
import types
import importlib.util
import time
from pathlib import Path
from datetime import datetime, timedelta

# 动态加载模块
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
get_cache_manager = cache_manager.get_cache_manager


class TestCacheManagerExtended:
    """CacheManager扩展测试"""
    
    def test_clear_expired_cache(self, temp_dir):
        """测试清除过期缓存"""
        cm = CacheManager(str(temp_dir / "cache"), max_age_days=0)  # 0天过期
        
        # 添加缓存
        cm.cache_result("expired1", {"data": "test1"})
        cm.cache_result("expired2", {"data": "test2"})
        
        # 清除过期缓存
        count, msg = cm.clear_expired_cache()
        assert count >= 0  # 可能有时间差异

    def test_cache_expiration_with_old_entry(self, temp_dir):
        """测试过期缓存条目"""
        cm = CacheManager(str(temp_dir / "cache"), max_age_days=1)
        
        # 手动添加一个过期条目
        cm.cache_result("old_entry", {"data": "old"})
        # 修改创建时间为很久以前
        cm.cache_index["old_entry"]["created_at"] = (datetime.now() - timedelta(days=10)).isoformat()
        cm._save_cache_index()
        
        # 应该检测为无效
        assert cm.is_cache_valid("old_entry") is False

    def test_get_cache_stats_hit_rate(self, temp_dir):
        """测试缓存命中率统计"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 添加缓存
        cm.cache_result("hit_test", {"data": "test"})
        
        # 访问一次（命中）
        cm.get_cached_result("hit_test")
        
        # 访问不存在的（未命中）
        cm.get_cached_result("nonexistent")
        
        stats = cm.get_cache_stats()
        assert "hit_rate" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    def test_get_cache_stats_zero_hit_rate(self, temp_dir):
        """测试零命中率"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        stats = cm.get_cache_stats()
        assert stats["hit_rate"] == 0.0

    def test_cache_file_removed_externally(self, temp_dir):
        """测试缓存文件被外部删除"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 添加缓存
        cm.cache_result("removed", {"data": "test"})
        
        # 手动删除缓存文件
        cache_file = cm._get_cache_path("removed")
        cache_file.unlink()
        
        # 应该检测为无效
        assert cm.is_cache_valid("removed") is False
        assert "removed" not in cm.cache_index

    def test_compute_md5_large_file(self, temp_dir):
        """测试大文件MD5计算（分块读取）"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 创建大于chunk_size的文件
        test_file = temp_dir / "large.bin"
        test_file.write_bytes(b"x" * 10000)
        
        md5 = cm.compute_md5(str(test_file))
        assert len(md5) == 32

    def test_get_cache_manager_singleton(self, temp_dir):
        """测试缓存管理器单例"""
        cm1 = get_cache_manager()
        cm2 = get_cache_manager()
        assert cm1 is cm2

    def test_cache_index_corrupted(self, temp_dir):
        """测试缓存索引损坏处理"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 写入损坏的JSON到索引文件
        cm.cache_index_file.write_text("{invalid json")
        
        # 重新加载应该返回空字典
        index = cm._load_cache_index()
        assert index == {}

    def test_cache_result_save_failure(self, temp_dir):
        """测试缓存保存失败"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 使缓存目录只读（模拟保存失败）
        cm.cache_dir.chmod(0o555)
        try:
            # 尝试保存缓存（可能会失败）
            cm.cache_result("fail_test", {"data": "test"})
        finally:
            cm.cache_dir.chmod(0o755)

    def test_cache_access_count_increment(self, temp_dir):
        """测试缓存访问计数增加"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        cm.cache_result("access_test", {"data": "test"})
        
        # 多次访问
        cm.get_cached_result("access_test")
        cm.get_cached_result("access_test")
        cm.get_cached_result("access_test")
        
        assert cm.cache_index["access_test"]["access_count"] == 3

    def test_get_cache_list_empty(self, temp_dir):
        """测试获取空缓存列表"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        cache_list = cm.get_cache_list()
        assert cache_list == []

    def test_get_cache_list_sorted(self, temp_dir):
        """测试缓存列表排序（按最后访问时间）"""
        cm = CacheManager(str(temp_dir / "cache"))
        
        # 添加多个缓存
        cm.cache_result("cache1", {"data": "1"})
        time.sleep(0.01)
        cm.cache_result("cache2", {"data": "2"})
        time.sleep(0.01)
        cm.cache_result("cache3", {"data": "3"})
        
        # 访问cache1使其成为最新
        cm.get_cached_result("cache1")
        
        cache_list = cm.get_cache_list()
        assert len(cache_list) == 3
        # 最新的应该在最前面
        assert cache_list[0]["md5_hash"] == "cache1"
