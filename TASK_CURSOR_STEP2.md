# TASK_CURSOR_STEP2.md - 第二步：重构CacheManager继承BaseManager

## 🎯 任务
修改 backend/cache_manager.py，让它继承BaseManager并完善类型注解

## 📁 工作目录
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/

## 📝 具体要求

修改文件 `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/cache_manager.py`：

### 1. 添加BaseManager导入
```python
from backend.base_manager import BaseManager
```

### 2. 修改CacheManager继承BaseManager
```python
class CacheManager(BaseManager):
    """缓存管理器 - 继承BaseManager"""
```

### 3. 修改__init__方法
```python
def __init__(self, cache_dir: str = "cache"):
    """
    初始化缓存管理器
    
    Args:
        cache_dir: 缓存目录路径
    """
    # 先调用父类初始化
    super().__init__()
    
    # 然后设置缓存目录
    if not os.path.isabs(cache_dir):
        base_dir = Path(__file__).parent.parent
        cache_dir = base_dir / cache_dir
    
    self.cache_dir = Path(cache_dir)
    self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    self.logger.info(f"缓存管理器初始化，缓存目录: {self.cache_dir}")
```

### 4. 使用BaseManager的JSON方法
将原来的json操作改为使用：
- `self._load_json()` 代替 `json.load()`
- `self._save_json()` 代替 `json.dump()`

### 5. 完善类型注解
确保所有方法都有完整的类型注解：
```python
def compute_md5(self, file_path: str) -> str:
def get_cached_result(self, file_md5: str) -> Optional[Dict[str, Any]]:
def cache_result(self, file_md5: str, result: Dict[str, Any]) -> bool:
```

### 6. 实现get_stats方法
```python
def get_stats(self) -> Dict[str, Any]:
    """获取缓存统计信息"""
    stats = self.get_cache_stats()
    return {
        "type": "cache",
        "cache_dir": str(self.cache_dir),
        **stats
    }
```

## ✅ 完成验证

完成后执行：
```bash
python3 -c "from backend.cache_manager import CacheManager; from backend.base_manager import BaseManager; print('✓ 继承关系正确' if issubclass(CacheManager, BaseManager) else '✗ 继承错误')"
```

## 📤 汇报

完成后汇报：
1. 修改了哪些内容
2. 验证命令的输出结果
3. 是否有语法错误
