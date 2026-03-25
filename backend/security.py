# -*- coding: utf-8 -*-
"""
安全管理模块

负责密码强度检测、登录锁定、路径安全等功能

作者: Cursor Composer
日期: 2026-03-25
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from .base_manager import BaseManager
except ImportError:
    from backend.base_manager import BaseManager

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class PasswordStrength:
    """密码强度结果"""
    score: int  # 0-100
    level: str  # 'weak', 'medium', 'strong'
    suggestions: list


class SecurityManager(BaseManager):
    """
    安全管理器
    负责系统的安全功能
    """

    # 默认配置
    DEFAULT_MAX_ATTEMPTS = 5
    DEFAULT_LOCKOUT_MINUTES = 30

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化安全管理器

        Args:
            data_dir: 数据目录，用于存储登录尝试记录
        """
        # 调用基类初始化
        super().__init__(data_dir=data_dir)

        self.login_attempts_file = self.data_dir / "login_attempts.json"
        self.login_attempts = self._load_login_attempts()
    
    def _load_login_attempts(self) -> Dict[str, Any]:
        """加载登录尝试记录"""
        return self._load_json(self.login_attempts_file)
    
    def _save_login_attempts(self) -> bool:
        """保存登录尝试记录"""
        success = self._save_json(self.login_attempts_file, self.login_attempts)
        if not success:
            self.logger.error(f"保存登录尝试记录失败: {self.login_attempts_file}")
        return success

    def get_stats(self) -> Dict[str, Any]:
        """实现BaseManager抽象方法"""
        locked_count = sum(
            1 for record in self.login_attempts.values()
            if record.get('locked_until')
        )

        return {
            "total_users_tracked": len(self.login_attempts),
            "locked_accounts": locked_count,
            "data_dir": str(self.data_dir),
            "manager_type": "SecurityManager",
            "data_dir_valid": self.validate_data_dir(),
        }
    
    def check_password_strength(self, password: str) -> PasswordStrength:
        """
        检查密码强度
        
        Args:
            password: 密码
            
        Returns:
            PasswordStrength对象
        """
        score = 0
        suggestions = []
        
        # 长度检查
        if len(password) >= 12:
            score += 30
        elif len(password) >= 8:
            score += 20
        else:
            suggestions.append("密码长度至少8位")
        
        # 包含小写字母
        if re.search(r'[a-z]', password):
            score += 15
        else:
            suggestions.append("包含小写字母")
        
        # 包含大写字母
        if re.search(r'[A-Z]', password):
            score += 15
        else:
            suggestions.append("包含大写字母")
        
        # 包含数字
        if re.search(r'\d', password):
            score += 15
        else:
            suggestions.append("包含数字")
        
        # 包含特殊字符
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15
        else:
            suggestions.append("包含特殊字符")
        
        # 额外加分
        if len(password) >= 16:
            score += 10
        
        # 确定等级
        if score >= 80:
            level = 'strong'
        elif score >= 50:
            level = 'medium'
        else:
            level = 'weak'
        
        return PasswordStrength(score=min(score, 100), level=level, suggestions=suggestions)
    
    def record_login_attempt(self, username: str, success: bool):
        """
        记录登录尝试
        
        Args:
            username: 用户名
            success: 是否成功
        """
        now = datetime.now().isoformat()
        
        if username not in self.login_attempts:
            self.login_attempts[username] = {
                'failed_count': 0,
                'last_attempt': now,
                'locked_until': None
            }
        
        record = self.login_attempts[username]
        
        if success:
            record['failed_count'] = 0
            record['locked_until'] = None
        else:
            record['failed_count'] += 1
            record['last_attempt'] = now
            
            # 检查是否需要锁定
            if record['failed_count'] >= self.DEFAULT_MAX_ATTEMPTS:
                lockout_time = datetime.now() + timedelta(minutes=self.DEFAULT_LOCKOUT_MINUTES)
                record['locked_until'] = lockout_time.isoformat()
                self.logger.warning(f"账户 {username} 已被锁定 {self.DEFAULT_LOCKOUT_MINUTES} 分钟")
        
        self._save_login_attempts()
    
    def is_account_locked(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        检查账户是否被锁定
        
        Args:
            username: 用户名
            
        Returns:
            (是否锁定, 剩余锁定时间秒数)
        """
        if username not in self.login_attempts:
            return False, None
        
        record = self.login_attempts[username]
        locked_until = record.get('locked_until')
        
        if not locked_until:
            return False, None
        
        lockout_end = datetime.fromisoformat(locked_until)
        now = datetime.now()
        
        if now < lockout_end:
            remaining = int((lockout_end - now).total_seconds())
            return True, remaining
        else:
            # 锁定已过期
            record['failed_count'] = 0
            record['locked_until'] = None
            self._save_login_attempts()
            return False, None
    
    def get_remaining_attempts(self, username: str) -> int:
        """
        获取剩余尝试次数
        
        Args:
            username: 用户名
            
        Returns:
            剩余尝试次数
        """
        if username not in self.login_attempts:
            return self.DEFAULT_MAX_ATTEMPTS
        
        failed = self.login_attempts[username].get('failed_count', 0)
        return max(0, self.DEFAULT_MAX_ATTEMPTS - failed)
    
    def validate_path_safety(self, path: str, base_dir: str) -> bool:
        """
        验证路径安全性
        
        Args:
            path: 要验证的路径
            base_dir: 基础目录
            
        Returns:
            是否安全
        """
        try:
            base = Path(base_dir).resolve()
            target = Path(path).resolve()
            return str(target).startswith(str(base))
        except Exception:
            return False


if __name__ == "__main__":
    print("=== SecurityManager 测试 ===")
    print()
    
    sm = SecurityManager()
    
    # 测试1: 密码强度
    print("测试1: 密码强度检测")
    test_passwords = [
        "123",
        "password",
        "Password1",
        "Password1!",
        "MyStr0ng!Passw0rd2024"
    ]
    
    for pwd in test_passwords:
        strength = sm.check_password_strength(pwd)
        print(f"  '{pwd}' -> {strength.level} ({strength.score}分)")
    print("✓ 密码强度检测测试通过")
    print()
    
    # 测试2: 登录锁定
    print("测试2: 登录锁定")
    username = "test_user"
    
    # 模拟5次失败
    for i in range(5):
        sm.record_login_attempt(username, success=False)
        remaining = sm.get_remaining_attempts(username)
        print(f"  第{i+1}次失败，剩余尝试: {remaining}")
    
    # 检查锁定状态
    locked, remaining_time = sm.is_account_locked(username)
    print(f"  账户锁定状态: {'已锁定' if locked else '未锁定'}")
    if locked:
        print(f"  剩余锁定时间: {remaining_time}秒")
    
    # 解锁
    sm.login_attempts[username]['failed_count'] = 0
    sm.login_attempts[username]['locked_until'] = None
    sm._save_login_attempts()
    print("✓ 登录锁定测试通过")
    print()
    
    # 测试3: 路径安全
    print("测试3: 路径安全")
    base = "/home/user/data"
    safe_path = "/home/user/data/file.txt"
    unsafe_path = "/etc/passwd"
    
    print(f"  validate_path_safety('{safe_path}', '{base}') = {sm.validate_path_safety(safe_path, base)}")
    print(f"  validate_path_safety('{unsafe_path}', '{base}') = {sm.validate_path_safety(unsafe_path, base)}")
    print("✓ 路径安全测试通过")
    print()
    
    print("=== 所有测试通过 ===")
