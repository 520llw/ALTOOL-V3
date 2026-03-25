# -*- coding: utf-8 -*-
"""BackupManager单元测试"""
import pytest
import sys
import types
import importlib.util
from pathlib import Path
import zipfile

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

# 加载 backup_manager
backup_manager_path = backend_dir / "backup_manager.py"
backup_manager = load_module_from_path("backup_manager", backup_manager_path)

BackupManager = backup_manager.BackupManager
BackupInfo = backup_manager.BackupInfo
BaseManager = base_manager.BaseManager


class TestBackupManager:
    """测试BackupManager"""
    
    def test_init(self, temp_dir):
        """测试初始化"""
        bm = BackupManager(str(temp_dir))
        assert bm.backup_dir.exists()
    
    def test_init_with_custom_backup_dir(self, temp_dir):
        """测试使用自定义备份目录初始化"""
        custom_backup = temp_dir / "custom_backup"
        bm = BackupManager(str(temp_dir), str(custom_backup))
        assert bm.backup_dir == custom_backup
        assert bm.backup_dir.exists()
    
    def test_create_backup(self, temp_dir):
        """测试创建备份"""
        bm = BackupManager(str(temp_dir))
        # 创建测试数据
        (temp_dir / "data" / "test.txt").parent.mkdir(parents=True)
        (temp_dir / "data" / "test.txt").write_text("test")
        # 创建备份
        backup_path = bm.create_backup("test_backup")
        assert backup_path.exists()
    
    def test_create_backup_default_name(self, temp_dir):
        """测试创建备份（使用默认名称）"""
        bm = BackupManager(str(temp_dir))
        # 创建测试数据
        (temp_dir / "data" / "test.txt").parent.mkdir(parents=True)
        (temp_dir / "data" / "test.txt").write_text("test")
        # 创建备份（不指定名称）
        backup_path = bm.create_backup()
        assert backup_path.exists()
        assert backup_path.name.startswith("backup_")
    
    def test_create_backup_empty_data(self, temp_dir):
        """测试创建空数据备份"""
        bm = BackupManager(str(temp_dir))
        # 不创建任何数据，直接备份
        backup_path = bm.create_backup("empty_backup")
        assert backup_path.exists()
    
    def test_list_backups(self, temp_dir):
        """测试列出备份"""
        bm = BackupManager(str(temp_dir))
        backups = bm.list_backups()
        assert isinstance(backups, list)
    
    def test_list_backups_with_data(self, temp_dir):
        """测试列出包含备份的列表"""
        bm = BackupManager(str(temp_dir))
        # 创建测试数据并备份
        (temp_dir / "data" / "test.txt").parent.mkdir(parents=True)
        (temp_dir / "data" / "test.txt").write_text("test")
        bm.create_backup("list_test")
        
        backups = bm.list_backups()
        assert len(backups) >= 1
        assert isinstance(backups[0], BackupInfo)
    
    def test_inherits_from_base_manager(self, temp_dir):
        """测试继承BaseManager"""
        # 检查MRO中是否有BaseManager（通过名称，因为动态加载可能导致类实例不同）
        base_names = [cls.__name__ for cls in BackupManager.__mro__]
        assert "BaseManager" in base_names

    def test_get_stats(self, temp_dir):
        """测试获取统计信息"""
        bm = BackupManager(str(temp_dir))
        stats = bm.get_stats()
        assert "total_backups" in stats
        assert "backup_dir" in stats
        assert "manager_type" in stats
        assert stats["manager_type"] == "BackupManager"
        assert "data_dir_valid" in stats

    def test_delete_backup(self, temp_dir):
        """测试删除备份"""
        bm = BackupManager(str(temp_dir))
        # 创建测试数据
        (temp_dir / "data" / "test.txt").parent.mkdir(parents=True)
        (temp_dir / "data" / "test.txt").write_text("test")
        # 创建备份
        backup_path = bm.create_backup("test_delete")
        assert backup_path.exists()
        
        # 删除备份
        result = bm.delete_backup("test_delete")
        assert result is True
        assert not backup_path.exists()

    def test_delete_nonexistent_backup(self, temp_dir):
        """测试删除不存在的备份"""
        bm = BackupManager(str(temp_dir))
        result = bm.delete_backup("nonexistent")
        assert result is False

    def test_auto_backup_config(self, temp_dir):
        """测试自动备份配置"""
        bm = BackupManager(str(temp_dir))
        
        # 获取默认配置
        config = bm.get_auto_backup_config()
        assert "enabled" in config
        assert "interval_days" in config
        assert "keep_count" in config
        
        # 设置配置
        bm.set_auto_backup_config(enabled=True, interval_days=3, keep_count=10)
        config = bm.get_auto_backup_config()
        assert config["enabled"] is True
        assert config["interval_days"] == 3
        assert config["keep_count"] == 10

    def test_set_auto_backup_config_partial(self, temp_dir):
        """测试部分更新自动备份配置"""
        bm = BackupManager(str(temp_dir))
        
        # 先设置完整配置
        bm.set_auto_backup_config(enabled=False, interval_days=7, keep_count=5)
        
        # 部分更新
        bm.set_auto_backup_config(enabled=True)
        config = bm.get_auto_backup_config()
        assert config["enabled"] is True
        assert config["interval_days"] == 7  # 保持不变
        assert config["keep_count"] == 5  # 保持不变

    def test_sanitize_backup_name(self, temp_dir):
        """测试备份名称清理"""
        bm = BackupManager(str(temp_dir))
        
        # 测试非法字符被移除
        sanitized = bm._sanitize_backup_name("test<backup>name")
        assert "<" not in sanitized
        assert ">" not in sanitized
        
        # 测试长度限制
        long_name = "a" * 150
        sanitized = bm._sanitize_backup_name(long_name)
        assert len(sanitized) <= 100

    def test_sanitize_backup_name_empty(self, temp_dir):
        """测试空备份名称清理"""
        bm = BackupManager(str(temp_dir))
        sanitized = bm._sanitize_backup_name("")
        assert sanitized == "backup"

    def test_restore_backup(self, temp_dir):
        """测试恢复备份"""
        bm = BackupManager(str(temp_dir))
        
        # 创建原始数据
        (temp_dir / "data" / "original.txt").parent.mkdir(parents=True)
        (temp_dir / "data" / "original.txt").write_text("original content")
        
        # 创建备份
        backup_path = bm.create_backup("restore_test")
        assert backup_path.exists()
        
        # 修改数据
        (temp_dir / "data" / "original.txt").write_text("modified content")
        
        # 恢复备份
        result = bm.restore_backup("restore_test")
        assert result is True
        
        # 验证数据已恢复
        restored_content = (temp_dir / "data" / "original.txt").read_text()
        assert restored_content == "original content"

    def test_restore_nonexistent_backup(self, temp_dir):
        """测试恢复不存在的备份"""
        bm = BackupManager(str(temp_dir))
        result = bm.restore_backup("nonexistent")
        assert result is False

    def test_check_and_do_auto_backup_disabled(self, temp_dir):
        """测试自动备份（禁用状态）"""
        bm = BackupManager(str(temp_dir))
        
        # 确保自动备份禁用
        bm.set_auto_backup_config(enabled=False)
        
        result = bm.check_and_do_auto_backup()
        assert result is None

    def test_check_and_do_auto_backup_enabled(self, temp_dir):
        """测试自动备份（启用状态）"""
        bm = BackupManager(str(temp_dir))
        
        # 创建测试数据
        (temp_dir / "data" / "test.txt").parent.mkdir(parents=True)
        (temp_dir / "data" / "test.txt").write_text("test")
        
        # 启用自动备份
        bm.set_auto_backup_config(enabled=True, interval_days=0)  # 间隔0天，确保会备份
        
        result = bm.check_and_do_auto_backup()
        # 应该会创建备份
        assert result is not None

    def test_backup_info_to_dict(self, temp_dir):
        """测试BackupInfo的to_dict方法"""
        from datetime import datetime
        
        backup_info = BackupInfo(
            name="test_backup",
            path=temp_dir / "test.zip",
            created_at=datetime.now(),
            size=1024 * 1024  # 1MB
        )
        
        data = backup_info.to_dict()
        assert "name" in data
        assert "path" in data
        assert "created_at" in data
        assert "size" in data
        assert "size_mb" in data
        assert data["size_mb"] == 1.0  # 1MB
