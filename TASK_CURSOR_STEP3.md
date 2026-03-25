# TASK_CURSOR_STEP3.md - 第三步：重构其他Manager

## 🎯 任务
重构BackupManager和SecurityManager，让它们继承BaseManager

## 📁 工作目录
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/

## 📝 具体要求

### 1. 重构BackupManager

修改文件 `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/backup_manager.py`：

```python
# 添加导入
from backend.base_manager import BaseManager

# 修改类定义
class BackupManager(BaseManager):
    """备份管理器 - 继承BaseManager"""
```

修改`__init__`方法：
```python
def __init__(self, data_dir: str = None, backup_dir: str = "backup"):
    """
    初始化备份管理器
    
    Args:
        data_dir: 数据目录
        backup_dir: 备份目录名称
    """
    # 调用父类初始化
    super().__init__(data_dir)
    
    # 设置备份目录
    self.backup_dir = self.data_dir / backup_dir
    self.backup_dir.mkdir(exist_ok=True, parents=True)
    
    # 使用父类的logger
    self.logger.info(f"备份管理器初始化，备份目录: {self.backup_dir}")
```

使用BaseManager的JSON方法替换原有json操作。

添加`get_stats`方法：
```python
def get_stats(self) -> Dict[str, Any]:
    """获取备份统计信息"""
    backups = self.list_backups()
    total_size = sum(b.size for b in backups)
    return {
        "type": "backup",
        "backup_dir": str(self.backup_dir),
        "total_backups": len(backups),
        "total_size_mb": round(total_size / (1024 * 1024), 2)
    }
```

### 2. 重构SecurityManager

修改文件 `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/security.py`：

```python
# 添加导入
from backend.base_manager import BaseManager

# 修改类定义
class SecurityManager(BaseManager):
    """安全管理器 - 继承BaseManager"""
```

修改`__init__`方法，调用`super().__init__()`。

使用BaseManager的JSON方法替换原有json操作。

添加`get_stats`方法：
```python
def get_stats(self) -> Dict[str, Any]:
    """获取安全统计信息"""
    return {
        "type": "security",
        "data_dir": str(self.data_dir),
        "login_attempts_file": str(self.login_attempts_file),
        "tracked_accounts": len(self.login_attempts)
    }
```

### 3. 统一FileUtils（可选）

如果合适，可以让FileUtils也继承BaseManager，或者保持独立工具类。

## ✅ 完成验证

完成后执行：
```bash
cd /home/llw/.openclaw/workspace/shared/ALTOOL_V3
source venv/bin/activate
python3 -c "
from backend.backup_manager import BackupManager
from backend.security_manager import SecurityManager
from backend.base_manager import BaseManager
assert issubclass(BackupManager, BaseManager), 'BackupManager继承失败'
assert issubclass(SecurityManager, BaseManager), 'SecurityManager继承失败'
print('✅ 所有Manager继承BaseManager成功')
"
```

## 📤 汇报

完成后汇报：
1. 修改了哪些文件
2. 验证命令的输出结果
