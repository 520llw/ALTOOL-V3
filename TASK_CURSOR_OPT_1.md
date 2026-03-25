# TASK_CURSOR_OPT_1.md - Cursor: Backend架构重构与统一

## 🎯 任务目标
重构backend模块，统一架构设计，提升代码质量

## 📁 工作目录
`/home/llw/.openclaw/workspace/shared/ALTOOL_V3/`

## 📝 具体任务

### 1. 创建BaseManager基类

创建 `backend/base_manager.py`:
```python
class BaseManager:
    """所有Manager的基类"""
    
    def __init__(self, data_dir: str = None):
        # 统一初始化逻辑
        pass
    
    def _get_data_path(self, filename: str) -> Path:
        # 统一路径处理
        pass
    
    def _load_json(self, filepath: Path) -> Dict:
        # 统一JSON加载
        pass
    
    def _save_json(self, filepath: Path, data: Dict):
        # 统一JSON保存
        pass
```

### 2. 重构CacheManager

优化 `backend/cache_manager.py`:
- 继承BaseManager
- 完善类型注解（100%）
- 优化MD5计算（使用更高效的块大小）
- 完善错误处理

### 3. 重构FileUtils

优化 `backend/file_utils.py`:
- 完善类型注解
- 优化路径处理逻辑
- 增强安全性检查

### 4. 重构BackupManager

优化 `backend/backup_manager.py`:
- 继承BaseManager
- 统一错误处理
- 优化zip操作

### 5. 重构SecurityManager

优化 `backend/security.py`:
- 继承BaseManager
- 完善类型注解
- 优化密码强度算法

## ✅ 完成标准

1. **BaseManager基类**: 创建完成，所有Manager继承
2. **类型注解**: 所有函数都有完整类型注解
3. **错误处理**: 所有异常都有处理
4. **代码质量**: 通过pylint检查
5. **测试**: 原有测试仍能运行

## 📤 完成汇报

完成后汇报：
1. 创建了哪些文件
2. 重构了哪些模块
3. 优化的具体点
4. 运行测试的结果
