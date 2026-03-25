# 任务分配: Cursor Composer

## 任务1: 修改主程序集成缓存系统
修改: `main.py`

集成点:
1. 在批量解析前检查缓存:
   ```python
   # 伪代码
   for pdf_file in pdf_files:
       md5 = cache_manager.compute_md5(pdf_file)
       if cache_manager.is_cache_valid(md5):
           result = cache_manager.get_cached_result(md5)
       else:
           result = ai_processor.extract(pdf_file)
           cache_manager.cache_result(md5, result)
   ```

2. 在界面显示缓存命中率

3. 添加"清除缓存"按钮

## 任务2: 实现备份管理器
文件: `backend/backup_manager.py`

功能:
```python
class BackupManager:
    def __init__(self, data_dir: str, backup_dir: str = "backup"):
    
    def create_backup(self, backup_name: str = None) -> str:
        """创建手动备份，返回备份路径"""
        
    def restore_backup(self, backup_path: str) -> bool:
        """从备份恢复数据"""
        
    def list_backups(self) -> List[Dict]:
        """列出所有备份 (含时间、大小)"""
        
    def auto_backup(self, interval_days: int = 7):
        """定时自动备份（只保留最近5个）"""
        
    def delete_backup(self, backup_path: str) -> bool:
        """删除指定备份"""
```

## 任务3: 实现安全功能
文件: `backend/security.py`

功能:
```python
class SecurityManager:
    def check_password_strength(self, password: str) -> Tuple[str, int]:
        """
        返回: (强度等级, 分数)
        等级: weak/medium/strong
        """
        
    def record_login_attempt(self, username: str, success: bool):
        """记录登录尝试，用于锁定"""
        
    def is_account_locked(self, username: str) -> Tuple[bool, int]:
        """
        检查是否锁定
        返回: (是否锁定, 剩余锁定秒数)
        """
        
    def sanitize_path(self, path: str) -> str:
        """防止路径遍历攻击"""
```

## 任务4: 在main.py中添加相关UI
1. 个人中心页面添加:
   - 修改密码（带强度检测）
   - 数据备份/恢复按钮

2. 登录页面添加:
   - 密码强度实时显示
   - 登录失败锁定提示

3. 设置页面添加:
   - 缓存清理
   - 自动备份设置

## 约束
- 与现有代码风格一致
- 不要破坏现有功能
- 添加适当的错误处理

完成后请报告:
1. 修改了哪些文件
2. 新增了哪些功能
3. 如何测试验证
