# -*- coding: utf-8 -*-
"""SecurityManager单元测试"""
import pytest
import sys
import types
import importlib.util
from pathlib import Path

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

# 加载 security 模块 (security_manager 实际上是 security.py)
security_path = backend_dir / "security.py"
security = load_module_from_path("security", security_path)

SecurityManager = security.SecurityManager
PasswordStrength = security.PasswordStrength
BaseManager = base_manager.BaseManager


class TestSecurityManager:
    """测试SecurityManager"""
    
    def test_init(self, temp_dir):
        """测试初始化"""
        sm = SecurityManager(str(temp_dir))
        assert sm.data_dir.exists()
    
    def test_check_password_strength(self, temp_dir):
        """测试密码强度检查"""
        sm = SecurityManager(str(temp_dir))
        # 测试弱密码
        weak = sm.check_password_strength("123")
        assert weak.level == "weak"
        # 测试强密码
        strong = sm.check_password_strength("MyStr0ng!Passw0rd")
        assert strong.level == "strong"
    
    def test_record_login_attempt(self, temp_dir):
        """测试记录登录尝试"""
        sm = SecurityManager(str(temp_dir))
        sm.record_login_attempt("test_user", success=True)
        assert "test_user" in sm.login_attempts
    
    def test_is_account_locked(self, temp_dir):
        """测试账户锁定检查"""
        sm = SecurityManager(str(temp_dir))
        # 模拟5次失败
        for i in range(5):
            sm.record_login_attempt("test_user", success=False)
        locked, remaining = sm.is_account_locked("test_user")
        assert locked == True
    
    def test_inherits_from_base_manager(self, temp_dir):
        """测试继承BaseManager"""
        # 检查MRO中是否有BaseManager（通过名称，因为动态加载可能导致类实例不同）
        base_names = [cls.__name__ for cls in SecurityManager.__mro__]
        assert "BaseManager" in base_names

    def test_password_strength_medium(self, temp_dir):
        """测试中强度密码"""
        sm = SecurityManager(str(temp_dir))
        # 中等强度密码（包含字母和数字，长度8+）
        medium = sm.check_password_strength("Password1")
        assert medium.level == "medium"

    def test_password_strength_strong_with_special(self, temp_dir):
        """测试包含特殊字符的强密码"""
        sm = SecurityManager(str(temp_dir))
        # 强密码（包含大小写字母、数字、特殊字符）
        strong = sm.check_password_strength("MyP@ssw0rd!")
        assert strong.level == "strong"
        assert strong.score >= 80

    def test_password_strength_very_long(self, temp_dir):
        """测试超长密码"""
        sm = SecurityManager(str(temp_dir))
        # 16位以上密码有额外加分
        pwd = "MyVeryL0ngP@ss!"  # 15位
        result = sm.check_password_strength(pwd)
        # 检查是否有建议
        assert isinstance(result.suggestions, list)

    def test_password_strength_weak_short(self, temp_dir):
        """测试短弱密码"""
        sm = SecurityManager(str(temp_dir))
        weak = sm.check_password_strength("abc")
        assert weak.level == "weak"
        assert weak.score < 50
        assert len(weak.suggestions) > 0

    def test_password_strength_no_uppercase(self, temp_dir):
        """测试无大写字母的密码"""
        sm = SecurityManager(str(temp_dir))
        result = sm.check_password_strength("password1!")
        assert "包含大写字母" in result.suggestions

    def test_password_strength_no_lowercase(self, temp_dir):
        """测试无小写字母的密码"""
        sm = SecurityManager(str(temp_dir))
        result = sm.check_password_strength("PASSWORD1!")
        assert "包含小写字母" in result.suggestions

    def test_password_strength_no_digit(self, temp_dir):
        """测试无数字的密码"""
        sm = SecurityManager(str(temp_dir))
        result = sm.check_password_strength("Password!")
        assert "包含数字" in result.suggestions

    def test_password_strength_no_special(self, temp_dir):
        """测试无特殊字符的密码"""
        sm = SecurityManager(str(temp_dir))
        result = sm.check_password_strength("Password1")
        assert "包含特殊字符" in result.suggestions

    def test_get_remaining_attempts(self, temp_dir):
        """测试获取剩余尝试次数"""
        sm = SecurityManager(str(temp_dir))
        
        # 新用户有全部尝试次数
        remaining = sm.get_remaining_attempts("new_user")
        assert remaining == 5
        
        # 失败一次后剩余4次
        sm.record_login_attempt("new_user", success=False)
        remaining = sm.get_remaining_attempts("new_user")
        assert remaining == 4

    def test_get_remaining_attempts_zero(self, temp_dir):
        """测试剩余尝试次数为0"""
        sm = SecurityManager(str(temp_dir))
        
        # 失败5次
        for i in range(5):
            sm.record_login_attempt("zero_user", success=False)
        
        remaining = sm.get_remaining_attempts("zero_user")
        assert remaining == 0

    def test_successful_login_resets_attempts(self, temp_dir):
        """测试成功登录重置尝试次数"""
        sm = SecurityManager(str(temp_dir))
        
        # 失败几次
        for i in range(3):
            sm.record_login_attempt("reset_user", success=False)
        
        # 成功登录
        sm.record_login_attempt("reset_user", success=True)
        
        # 尝试次数应该重置
        remaining = sm.get_remaining_attempts("reset_user")
        assert remaining == 5

    def test_account_lock_remaining_time(self, temp_dir):
        """测试账户锁定的剩余时间"""
        sm = SecurityManager(str(temp_dir))
        
        # 失败5次触发锁定
        for i in range(5):
            sm.record_login_attempt("lock_user", success=False)
        
        locked, remaining = sm.is_account_locked("lock_user")
        assert locked is True
        assert remaining is not None
        assert remaining > 0  # 剩余时间应该为正数

    def test_account_unlock_after_lockout_expires(self, temp_dir):
        """测试锁定过期后自动解锁"""
        from datetime import datetime, timedelta
        
        sm = SecurityManager(str(temp_dir))
        
        # 手动设置一个已过期的锁定时间
        sm.login_attempts["expired_user"] = {
            'failed_count': 5,
            'last_attempt': datetime.now().isoformat(),
            'locked_until': (datetime.now() - timedelta(minutes=1)).isoformat()  # 1分钟前已过期
        }
        
        locked, remaining = sm.is_account_locked("expired_user")
        assert locked is False
        assert remaining is None

    def test_is_account_locked_nonexistent_user(self, temp_dir):
        """测试检查不存在用户的锁定状态"""
        sm = SecurityManager(str(temp_dir))
        locked, remaining = sm.is_account_locked("nonexistent_user")
        assert locked is False
        assert remaining is None

    def test_validate_path_safety(self, temp_dir):
        """测试路径安全验证"""
        sm = SecurityManager(str(temp_dir))
        
        # 安全路径
        is_safe = sm.validate_path_safety(str(temp_dir / "file.txt"), str(temp_dir))
        assert is_safe is True
        
        # 不安全路径（路径遍历）
        is_safe = sm.validate_path_safety("/etc/passwd", str(temp_dir))
        assert is_safe is False

    def test_validate_path_safety_subdirectory(self, temp_dir):
        """测试子目录路径安全"""
        sm = SecurityManager(str(temp_dir))
        
        # 子目录是安全的
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        is_safe = sm.validate_path_safety(str(subdir / "file.txt"), str(temp_dir))
        assert is_safe is True

    def test_validate_path_safety_traversal(self, temp_dir):
        """测试路径遍历攻击检测"""
        sm = SecurityManager(str(temp_dir))
        
        # 路径遍历攻击
        is_safe = sm.validate_path_safety(str(temp_dir.parent / "etc" / "passwd"), str(temp_dir))
        assert is_safe is False

    def test_validate_path_safety_invalid_path(self, temp_dir):
        """测试无效路径"""
        sm = SecurityManager(str(temp_dir))
        
        # 无效路径
        is_safe = sm.validate_path_safety("\x00invalid", str(temp_dir))
        assert is_safe is False

    def test_get_stats(self, temp_dir):
        """测试获取统计信息"""
        sm = SecurityManager(str(temp_dir))
        
        # 添加一些登录记录
        sm.record_login_attempt("user1", success=False)
        sm.record_login_attempt("user2", success=False)
        
        stats = sm.get_stats()
        assert "total_users_tracked" in stats
        assert stats["total_users_tracked"] >= 2
        assert "manager_type" in stats
        assert stats["manager_type"] == "SecurityManager"
        assert "data_dir_valid" in stats

    def test_get_stats_with_locked_accounts(self, temp_dir):
        """测试获取统计信息（包含锁定账户）"""
        sm = SecurityManager(str(temp_dir))
        
        # 锁定一个账户
        for i in range(5):
            sm.record_login_attempt("locked_account", success=False)
        
        stats = sm.get_stats()
        assert "locked_accounts" in stats
        assert stats["locked_accounts"] >= 1

    def test_load_save_login_attempts(self, temp_dir):
        """测试登录尝试的加载和保存"""
        sm = SecurityManager(str(temp_dir))
        
        # 记录一些尝试
        sm.record_login_attempt("persist_user", success=False)
        
        # 创建新的管理器实例（应该能加载之前的记录）
        sm2 = SecurityManager(str(temp_dir))
        assert "persist_user" in sm2.login_attempts
