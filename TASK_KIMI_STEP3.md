# TASK_KIMI_STEP3.md - 第三步：修复测试并提高覆盖率

## 🎯 任务
修复失败的测试，添加更多测试用例，提高测试覆盖率

## 📁 工作目录
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/

## 📝 具体要求

### 1. 修复失败的测试

查看当前失败的测试：
```bash
cd /home/llw/.openclaw/workspace/shared/ALTOOL_V3
source venv/bin/activate
python3 -m pytest tests/unit/ -v 2>&1 | grep FAILED
```

修复这3个失败的测试：
- `test_compute_md5` - 检查预期MD5值
- `test_sanitize_filename_long_name` - 检查文件名长度处理
- `test_is_path_traversal_various` - 检查路径遍历检测

### 2. 添加更多测试用例

为BackupManager添加测试：
```python
# tests/unit/test_backup_manager.py
import pytest
from backend.backup_manager import BackupManager


class TestBackupManager:
    """测试BackupManager"""
    
    def test_init(self, temp_dir):
        """测试初始化"""
        bm = BackupManager(str(temp_dir))
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
    
    def test_list_backups(self, temp_dir):
        """测试列出备份"""
        bm = BackupManager(str(temp_dir))
        backups = bm.list_backups()
        assert isinstance(backups, list)
    
    def test_inherits_from_base_manager(self, temp_dir):
        """测试继承BaseManager"""
        from backend.base_manager import BaseManager
        assert issubclass(BackupManager, BaseManager)
```

为SecurityManager添加测试：
```python
# tests/unit/test_security_manager.py
import pytest
from backend.security_manager import SecurityManager, PasswordStrength


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
        from backend.base_manager import BaseManager
        assert issubclass(SecurityManager, BaseManager)
```

### 3. 运行所有测试

完成后执行：
```bash
cd /home/llw/.openclaw/workspace/shared/ALTOOL_V3
source venv/bin/activate
python3 -m pytest tests/unit/ -v --tb=short
```

目标：
- [ ] 所有测试通过
- [ ] 测试覆盖率 > 80%

## ✅ 完成标准

- [ ] 3个失败测试修复
- [ ] BackupManager测试添加
- [ ] SecurityManager测试添加
- [ ] 所有测试通过
- [ ] 覆盖率 > 80%

## 📤 汇报

完成后汇报：
1. 修复了哪些测试
2. 添加了多少测试用例
3. 测试运行结果
4. 覆盖率数据
