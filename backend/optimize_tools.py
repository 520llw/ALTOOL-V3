# -*- coding: utf-8 -*-
"""
优化工具模块（简化版）
保留核心功能：配置管理、设备类型工具、缓存、MD5、初始化函数
"""

import os
import hashlib
import logging
import pickle
import sqlite3
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import threading

import yaml

# 配置日志
logger = logging.getLogger(__name__)


# =====================================================
# 配置管理
# =====================================================

class ConfigManager:
    """
    全局配置管理器
    支持热加载配置文件，无需重启应用
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config_path = Path(__file__).parent.parent / "config.yaml"
        self._config = {}
        self._last_modified = 0
        self.reload()
    
    def reload(self):
        """重新加载配置文件"""
        try:
            if self.config_path.exists():
                current_mtime = self.config_path.stat().st_mtime
                if current_mtime != self._last_modified:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self._config = yaml.safe_load(f) or {}
                    self._last_modified = current_mtime
                    logger.info("配置文件已重新加载")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self._config = {}
    
    def get(self, key_path: str, default=None):
        """
        获取配置值，支持点号分隔的路径
        例如: config.get('ui.primary_color', '#1E3A8A')
        """
        self.reload()  # 检查并自动重载
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    @property
    def all(self) -> Dict:
        """获取所有配置"""
        self.reload()
        return self._config.copy()


# 全局配置实例
config_manager = ConfigManager()


# =====================================================
# 文件 MD5 与缓存
# =====================================================

def calculate_file_md5(file_path: str, chunk_size: int = 8192) -> str:
    """计算文件 MD5，用于缓存键与去重"""
    h = hashlib.md5()
    path = Path(file_path)
    if not path.exists():
        return ""
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def check_pdf_integrity(file_path: str) -> Tuple[bool, str]:
    """检查 PDF 文件是否可读（存在、非空、可打开）"""
    path = Path(file_path)
    if not path.exists():
        return False, "文件不存在"
    if not path.is_file():
        return False, "不是文件"
    if path.stat().st_size == 0:
        return False, "文件为空"
    try:
        with open(path, "rb") as f:
            head = f.read(8)
        if not head.startswith(b"%PDF"):
            return False, "不是有效的 PDF 格式"
        return True, ""
    except Exception as e:
        return False, str(e)


class CacheManager:
    """简单缓存：内存 + 可选文件持久化，支持 TTL（小时）"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._mem: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expire_ts)
        self._ttl_hours = max(1, config_manager.get("performance.cache_ttl_hours", 24))
        cache_dir = Path(config_manager.get("paths.cache_dir", "./cache"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_dir = cache_dir

    def get(self, key: str) -> Optional[Any]:
        """获取缓存；过期或不存在返回 None"""
        if key in self._mem:
            val, expire = self._mem[key]
            if time.time() < expire:
                return val
            del self._mem[key]
        path = self._cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.pkl"
        if path.exists():
            try:
                with open(path, "rb") as f:
                    data = pickle.load(f)
                expire_ts = data.get("expire_ts", 0)
                if time.time() < expire_ts:
                    return data.get("value")
            except Exception:
                pass
        return None

    def set(self, key: str, value: Any) -> None:
        """写入缓存"""
        expire = time.time() + self._ttl_hours * 3600
        self._mem[key] = (value, expire)
        path = self._cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.pkl"
        try:
            with open(path, "wb") as f:
                pickle.dump({"value": value, "expire_ts": expire}, f)
        except Exception:
            pass


cache_manager = CacheManager()


# =====================================================
# 数据库优化工具
# =====================================================

def create_database_indexes(db_path: str):
    """
    为数据库创建优化索引
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_parse_results_pdf_name ON parse_results(pdf_name)",
            "CREATE INDEX IF NOT EXISTS idx_parse_results_device_type ON parse_results(device_type)",
            "CREATE INDEX IF NOT EXISTS idx_parse_results_param_id ON parse_results(param_id)",
            "CREATE INDEX IF NOT EXISTS idx_parse_results_parse_time ON parse_results(parse_time)",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_table_records_device_type ON table_records(device_type)",
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.OperationalError:
                pass  # 表可能不存在，忽略
        
        conn.commit()
        conn.close()
        logger.info("数据库索引创建完成")
        
    except Exception as e:
        logger.error(f"创建数据库索引失败: {e}")


# =====================================================
# 日志工具
# =====================================================

def setup_logging():
    """配置日志系统"""
    from logging.handlers import RotatingFileHandler
    
    log_dir = Path(config_manager.get('paths.log_dir', './logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    
    level_str = config_manager.get('logging.level', 'INFO')
    level = getattr(logging, level_str, logging.INFO)
    max_size = config_manager.get('logging.max_file_size_mb', 10) * 1024 * 1024
    
    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    info_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=max_size,
        backupCount=3,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    root_logger.addHandler(info_handler)
    
    logger.info("日志系统初始化完成")


# =====================================================
# 设备类型工具
# =====================================================

def get_device_icon(device_type: str) -> str:
    """获取器件类型图标"""
    device_types = config_manager.get('device_types', [])
    for dt in device_types:
        if dt.get('name') == device_type:
            return dt.get('icon', '📦')
    return '📦'


def get_device_color(device_type: str) -> str:
    """获取器件类型颜色"""
    device_types = config_manager.get('device_types', [])
    for dt in device_types:
        if dt.get('name') == device_type:
            return dt.get('color', '#6B7280')
    return '#6B7280'


# =====================================================
# 初始化函数
# =====================================================

def initialize_optimization():
    """
    初始化优化功能
    应在应用启动时调用
    使用与业务一致的数据库路径（params.db），并创建搜索用索引
    """
    # 初始化日志
    setup_logging()
    
    # 创建必要目录（与 config.yaml paths 一致）
    _path_defaults = {'data_dir': './data', 'upload_dir': './data/uploads', 'output_dir': './output',
                     'log_dir': './logs', 'cache_dir': './cache', 'backup_dir': './backup'}
    for path_key, default in _path_defaults.items():
        path = Path(config_manager.get(f'paths.{path_key}', default))
        path.mkdir(parents=True, exist_ok=True)
    
    # 使用与业务一致的数据库路径建索引（与 backend.config.DATABASE_PATH 一致）
    try:
        from backend.config import DATABASE_PATH
        db_path = Path(DATABASE_PATH)
        if db_path.exists():
            create_database_indexes(str(db_path))
            # 同时创建搜索优化索引（db_manager 提供的索引）
            from backend.db_manager import DatabaseManager
            db = DatabaseManager()
            db.create_search_indexes()
    except Exception as e:
        logger.warning(f"数据库索引初始化跳过或部分失败: {e}")
    
    logger.info("优化功能初始化完成")
