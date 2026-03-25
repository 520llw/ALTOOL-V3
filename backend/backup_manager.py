# -*- coding: utf-8 -*-
"""
备份管理模块

提供数据备份和恢复功能
支持手动备份、自动备份、备份列表管理

作者: Cursor Composer
日期: 2026-03-25
"""

import os
import json
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from .base_manager import BaseManager
except ImportError:
    from backend.base_manager import BaseManager

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """备份信息"""
    name: str
    path: Path
    created_at: datetime
    size: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'path': str(self.path),
            'created_at': self.created_at.isoformat(),
            'size': self.size,
            'size_mb': round(self.size / (1024 * 1024), 2)
        }


class BackupManager(BaseManager):
    """
    备份管理器
    管理应用数据的备份和恢复
    """

    def __init__(self, data_dir: Optional[str] = None, backup_dir: Optional[str] = None):
        """
        初始化备份管理器

        Args:
            data_dir: 数据目录，默认为项目data目录
            backup_dir: 备份目录，默认为项目backup目录
        """
        # 调用基类初始化
        super().__init__(data_dir=data_dir)

        # 设置备份目录
        if backup_dir is None:
            self.backup_dir = self.data_dir.parent / "backup"
        else:
            self.backup_dir = Path(backup_dir)

        self.backup_dir.mkdir(exist_ok=True, parents=True)
        self.data_dir = Path(data_dir) if data_dir else self.data_dir

        # 自动备份配置
        self.auto_backup_config_file = self.backup_dir / "auto_backup_config.json"
        self.auto_backup_config = self._load_auto_backup_config()

        self.logger.info(f"备份管理器初始化，备份目录: {self.backup_dir}")
    
    def _load_auto_backup_config(self) -> Dict[str, Any]:
        """加载自动备份配置"""
        config = self._load_json(self.auto_backup_config_file)

        if not config:
            config = {
                'enabled': False,
                'interval_days': 7,
                'keep_count': 5
            }

        return config
    
    def _save_auto_backup_config(self) -> bool:
        """保存自动备份配置"""
        success = self._save_json(self.auto_backup_config_file, self.auto_backup_config)
        if not success:
            self.logger.error(f"保存自动备份配置失败: {self.auto_backup_config_file}")
        return success

    def get_stats(self) -> Dict[str, Any]:
        """实现BaseManager抽象方法"""
        backups = self.list_backups()
        config = self.get_auto_backup_config()

        return {
            "total_backups": len(backups),
            "backup_dir": str(self.backup_dir),
            "data_dir": str(self.data_dir),
            "auto_backup_enabled": config.get('enabled', False),
            "manager_type": "BackupManager",
            "data_dir_valid": self.validate_data_dir(),
        }
    
    def create_backup(self, name: str = None) -> Optional[Path]:
        """
        创建手动备份
        
        Args:
            name: 备份名称，默认使用时间戳
            
        Returns:
            备份文件路径，失败返回None
        """
        if name is None:
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 确保备份名称安全
        name = self._sanitize_backup_name(name)
        backup_path = self.backup_dir / f"{name}.zip"
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in self.data_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.data_dir)
                        zf.write(file_path, arcname)
            
            self.logger.info(f"备份创建成功: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"创建备份失败: {e}")
            return None
    
    def _sanitize_backup_name(self, name: str) -> str:
        """清理备份名称"""
        # 移除非法字符
        name = ''.join(c for c in name if c.isalnum() or c in '_-')
        # 限制长度
        if len(name) > 100:
            name = name[:100]
        return name or "backup"
    
    def list_backups(self) -> List[BackupInfo]:
        """
        获取备份列表
        
        Returns:
            备份信息列表
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('*.zip'), reverse=True):
            try:
                stat = backup_file.stat()
                backups.append(BackupInfo(
                    name=backup_file.stem,
                    path=backup_file,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    size=stat.st_size
                ))
            except Exception as e:
                self.logger.warning(f"读取备份信息失败: {e}")

        return backups
    
    def restore_backup(self, backup_name: str) -> bool:
        """
        从备份恢复数据
        
        Args:
            backup_name: 备份名称
            
        Returns:
            是否恢复成功
        """
        backup_path = self.backup_dir / f"{backup_name}.zip"
        
        if not backup_path.exists():
            logger.error(f"备份不存在: {backup_path}")
            return False
        
        try:
            # 先创建当前数据的备份（以防万一）
            safety_backup = self.create_backup(f"safety_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # 清空当前数据目录
            for item in self.data_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            
            # 解压备份
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(self.data_dir)
            
            self.logger.info(f"备份恢复成功: {backup_name}")
            return True

        except Exception as e:
            self.logger.error(f"恢复备份失败: {e}")
            return False
    
    def delete_backup(self, backup_name: str) -> bool:
        """
        删除备份
        
        Args:
            backup_name: 备份名称
            
        Returns:
            是否删除成功
        """
        backup_path = self.backup_dir / f"{backup_name}.zip"
        
        if not backup_path.exists():
            logger.error(f"备份不存在: {backup_path}")
            return False
        
        try:
            backup_path.unlink()
            self.logger.info(f"备份删除成功: {backup_name}")
            return True
        except Exception as e:
            self.logger.error(f"删除备份失败: {e}")
            return False
    
    def get_auto_backup_config(self) -> Dict[str, Any]:
        """获取自动备份配置"""
        return self.auto_backup_config.copy()
    
    def set_auto_backup_config(self, enabled: bool = None, 
                               interval_days: int = None,
                               keep_count: int = None):
        """
        设置自动备份配置
        
        Args:
            enabled: 是否启用
            interval_days: 备份间隔天数
            keep_count: 保留备份数量
        """
        if enabled is not None:
            self.auto_backup_config['enabled'] = enabled
        if interval_days is not None:
            self.auto_backup_config['interval_days'] = interval_days
        if keep_count is not None:
            self.auto_backup_config['keep_count'] = keep_count
        
        self._save_auto_backup_config()
    
    def check_and_do_auto_backup(self) -> Optional[Path]:
        """
        检查并执行自动备份
        
        Returns:
            备份路径或None
        """
        if not self.auto_backup_config.get('enabled', False):
            return None
        
        interval = self.auto_backup_config.get('interval_days', 7)
        keep_count = self.auto_backup_config.get('keep_count', 5)
        
        # 获取备份列表
        backups = self.list_backups()
        
        # 检查是否需要备份
        if backups:
            last_backup = backups[0]
            days_since_last = (datetime.now() - last_backup.created_at).days
            if days_since_last < interval:
                return None  # 不需要备份
        
        # 创建备份
        backup_path = self.create_backup(f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 清理旧备份
        if backup_path and len(backups) >= keep_count:
            old_backups = [b for b in backups if b.name.startswith('auto_')]
            for old in old_backups[keep_count-1:]:
                self.delete_backup(old.name)
        
        return backup_path


if __name__ == "__main__":
    print("=== BackupManager 测试 ===")
    print()
    
    bm = BackupManager()
    
    # 测试1: 创建备份
    print("测试1: 创建备份")
    backup_path = bm.create_backup("test_backup")
    if backup_path:
        print(f"  ✓ 备份创建成功: {backup_path.name}")
    else:
        print("  ✗ 备份创建失败")
    print()
    
    # 测试2: 列出备份
    print("测试2: 列出备份")
    backups = bm.list_backups()
    print(f"  ✓ 找到 {len(backups)} 个备份")
    for b in backups:
        print(f"    - {b.name} ({b.size_mb:.2f} MB)")
    print()
    
    # 测试3: 自动备份配置
    print("测试3: 自动备份配置")
    config = bm.get_auto_backup_config()
    print(f"  ✓ 当前配置: {config}")
    bm.set_auto_backup_config(enabled=True, interval_days=7, keep_count=5)
    print(f"  ✓ 更新配置成功")
    print()
    
    # 清理测试备份
    if backup_path:
        bm.delete_backup("test_backup")
        print("✓ 测试备份已清理")
    
    print()
    print("=== 所有测试通过 ===")
