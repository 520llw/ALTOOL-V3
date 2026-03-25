# 任务分配: OpenCode (MiniMax)

## 任务1: 创建目录结构
在 `~/.openclaw/workspace/shared/ALTOOL_V3/ALTOOL/` 下创建:
- `data/` - 数据库和上传文件
- `data/uploads/` - PDF上传目录
- `cache/` - AI提取结果缓存
- `backup/` - 数据备份
- `logs/` - 日志文件

## 任务2: 实现缓存管理器
文件: `backend/cache_manager.py`

功能要求:
1. MD5计算工具函数
2. 缓存存储结构: `cache/{md5前2位}/{md5}.json`
3. 接口:
   ```python
   class CacheManager:
       def __init__(self, cache_dir: str = "cache"):
       def compute_md5(self, file_path: str) -> str:
       def get_cached_result(self, file_md5: str) -> Optional[Dict]:
       def cache_result(self, file_md5: str, result: Dict):
       def is_cache_valid(self, file_md5: str, max_age_days: int = 30) -> bool:
       def clear_expired_cache(self, max_age_days: int = 30):
   ```

## 任务3: 实现文件工具
文件: `backend/file_utils.py`

功能:
1. 安全的文件路径处理（防止路径遍历）
2. 文件类型验证（只允许PDF）
3. 文件大小检查
4. 临时文件管理

## 约束
- 只使用Python标准库 + 项目已有依赖
- 代码需要完整可运行
- 添加类型注解
- 处理所有边界情况

## 参考文件
- 查看 `backend/config.py` 了解项目配置方式
- 查看 `backend/db_manager.py` 了解数据模型

完成后请报告: 
1. 创建了哪些文件
2. 每个文件的核心功能
3. 如何使用示例
