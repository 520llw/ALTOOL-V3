# ALTOOL_V3 项目分析与拆解报告

## 项目现状分析

### 已存在模块 (39个Python文件)
- `main.py` - Streamlit主程序 (2600+行)
- `backend/ai_processor.py` - AI参数提取
- `backend/pdf_parser.py` - PDF解析
- `backend/db_manager.py` - 数据库管理
- `backend/data_writer.py` - Excel导出
- `backend/user_manager.py` - 用户认证
- `backend/config.py` - 配置管理
- `backend/optimize_tools.py` - 优化工具
- `self_optimize.py` - 自监督优化系统

### 缺失功能清单

#### 🔴 P0级 - 核心功能缺失
1. **前端仪表盘 (frontend/dashboard.py)**
   - README提到但文件不存在
   - 需要：统计数据、图表、快捷操作

2. **目录结构缺失**
   - `data/` - 数据库和上传文件
   - `cache/` - AI提取结果缓存
   - `backup/` - 数据备份
   - `logs/` - 日志文件

3. **MD5缓存机制**
   - README提到"避免重复解析"
   - 当前：每次重新解析PDF
   - 需要：MD5校验 + 缓存系统

#### 🟡 P1级 - 用户体验
4. **实时进度显示**
   - 进度百分比
   - 预计剩余时间
   - 处理速度

5. **新手引导系统**
   - 首次登录3步引导
   - 快速上手提示

6. **数据备份系统**
   - 手动备份
   - 定时自动备份

#### 🟢 P2级 - 安全增强
7. **密码强度检测**
   - 实时显示弱/中/强

8. **登录保护**
   - 失败5次锁定10分钟

## 团队分工方案

### 成员1: OpenCode (MiniMax) - 基础架构
**任务**: 
- 创建缺失目录结构 (data/, cache/, backup/, logs/)
- 实现MD5缓存系统
- 实现文件上传处理

**交付**: 
- `backend/cache_manager.py` - 缓存管理
- `backend/file_utils.py` - 文件工具(MD5/路径等)

### 成员2: Kimi Code - 前端界面
**任务**:
- 实现仪表盘页面
- 实现实时进度组件
- 实现新手引导

**交付**:
- `frontend/dashboard.py` - 仪表盘
- `frontend/progress.py` - 进度组件
- `frontend/guide.py` - 新手引导

### 成员3: Cursor Composer - 系统集成
**任务**:
- 集成缓存系统到主流程
- 实现数据备份功能
- 安全增强(密码强度/登录保护)

**交付**:
- 修改 `main.py` 集成所有新功能
- `backend/backup_manager.py` - 备份管理
- `backend/security.py` - 安全功能

### 小罗 (我) - 架构设计与整合
- 编写任务需求文档
- 审查代码并整合
- 测试与验证
- 向用户汇报

## 开发顺序
1. 基础架构 (目录 + 缓存系统)
2. 前端界面 (仪表盘 + 进度)
3. 系统集成 (所有功能整合)
4. 测试验证
5. 文档完善

## 关键接口设计

### 缓存系统接口
```python
class CacheManager:
    def get_cached_result(self, file_md5: str) -> Optional[ExtractionResult]
    def cache_result(self, file_md5: str, result: ExtractionResult)
    def clear_expired_cache(self, max_age_days: int = 30)
```

### 仪表盘数据接口
```python
class DashboardData:
    def get_stats(self) -> Dict  # 统计数字
    def get_recent_tasks(self, limit: int = 10) -> List[Task]
    def get_device_distribution(self) -> Dict  # 器件类型分布
```

### 进度报告接口
```python
class ProgressReporter:
    def start_task(self, total_files: int)
    def update_progress(self, current: int, message: str = "")
    def finish_task(self)
```
