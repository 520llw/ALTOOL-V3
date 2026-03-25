# -*- coding: utf-8 -*-
"""
缓存管理模块
负责管理AI解析结果的缓存，避免重复解析相同PDF
使用MD5哈希作为缓存键，JSON文件存储缓存数据
存储结构: cache/{md5前2位}/{md5}.json
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

from backend.base_manager import BaseManager

logger = logging.getLogger(__name__)


class CacheManager(BaseManager):
    """
    缓存管理器
    管理PDF解析结果的缓存，基于文件MD5哈希
    存储结构: cache/{md5前2位}/{md5}.json
    """

    def __init__(self, cache_dir: str = "cache", max_age_days: int = 30):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
            max_age_days: 缓存最大保留天数，默认30天
        """
        # 先调用父类初始化
        super().__init__()

        # 然后设置缓存目录
        if not os.path.isabs(cache_dir):
            base_dir = Path(__file__).parent.parent
            cache_dir = base_dir / cache_dir

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_age_days = max_age_days
        self.cache_index_file = self.cache_dir / "cache_index.json"
        self.cache_index = self._load_cache_index()

        self._hits = 0
        self._misses = 0

        self.logger.info(f"缓存管理器初始化，缓存目录: {self.cache_dir}")

    def _get_cache_path(self, md5_hash: str) -> Path:
        """
        根据MD5哈希获取缓存文件路径
        存储结构: cache/{md5前2位}/{md5}.json

        Args:
            md5_hash: MD5哈希值

        Returns:
            缓存文件路径
        """
        prefix = md5_hash[:2]
        sub_dir = self.cache_dir / prefix
        sub_dir.mkdir(exist_ok=True, parents=True)
        return sub_dir / f"{md5_hash}.json"

    def _load_cache_index(self) -> Dict[str, Any]:
        """加载缓存索引"""
        return self._load_json(self.cache_index_file)

    def _save_cache_index(self) -> bool:
        """保存缓存索引"""
        success = self._save_json(self.cache_index_file, self.cache_index)
        if not success:
            self.logger.error(f"保存缓存索引失败: {self.cache_index_file}")
        return success

    @staticmethod
    def compute_md5(file_path: str, chunk_size: int = 4096) -> str:
        """
        计算文件的MD5哈希值（大文件分块读取）

        Args:
            file_path: 文件路径
            chunk_size: 每次读取的块大小，默认4096字节

        Returns:
            MD5哈希字符串
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算MD5失败 {file_path}: {e}")
            return ""

    def is_cache_valid(self, md5_hash: str) -> bool:
        """
        检查缓存是否有效

        Args:
            md5_hash: 文件MD5哈希

        Returns:
            缓存是否有效
        """
        if md5_hash not in self.cache_index:
            return False

        cache_entry = self.cache_index[md5_hash]
        cache_file = self._get_cache_path(md5_hash)

        if not cache_file.exists():
            if md5_hash in self.cache_index:
                del self.cache_index[md5_hash]
                self._save_cache_index()
            return False

        created_at = datetime.fromisoformat(cache_entry.get("created_at", "2000-01-01"))
        if datetime.now() - created_at > timedelta(days=self.max_age_days):
            self._delete_cache_file(md5_hash)
            return False

        return True

    def get_cached_result(self, md5_hash: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的解析结果

        Args:
            md5_hash: 文件MD5哈希

        Returns:
            缓存的解析结果，如果不存在则返回None
        """
        if not self.is_cache_valid(md5_hash):
            self._misses += 1
            return None

        try:
            cache_entry = self.cache_index[md5_hash]
            cache_file = self._get_cache_path(md5_hash)

            # 使用BaseManager的_load_json方法
            result = self._load_json(cache_file)

            self.cache_index[md5_hash]["last_accessed"] = datetime.now().isoformat()
            self.cache_index[md5_hash]["access_count"] = (
                self.cache_index[md5_hash].get("access_count", 0) + 1
            )
            self._save_cache_index()

            self._hits += 1
            logger.info(f"缓存命中: {cache_entry.get('file_name', md5_hash)}")
            return result

        except Exception as e:
            logger.error(f"读取缓存失败 {md5_hash}: {e}")
            self._misses += 1
            return None

    def cache_result(
        self, md5_hash: str, result: Dict[str, Any], file_name: str = None
    ):
        """
        缓存解析结果

        Args:
            md5_hash: 文件MD5哈希
            result: 解析结果数据
            file_name: 原始文件名（可选）
        """
        try:
            cache_file = self._get_cache_path(md5_hash)

            # 使用BaseManager的_save_json方法
            success = self._save_json(cache_file, result)
            if not success:
                self.logger.error(f"保存缓存JSON失败: {cache_file}")
                return

            self.cache_index[md5_hash] = {
                "cache_file": str(cache_file),
                "file_name": file_name or md5_hash,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "access_count": 0,
                "size": cache_file.stat().st_size if cache_file.exists() else 0,
            }
            self._save_cache_index()

            logger.info(f"缓存已保存: {file_name or md5_hash}")

        except Exception as e:
            logger.error(f"保存缓存失败 {md5_hash}: {e}")

    def _delete_cache_file(self, md5_hash: str):
        """删除缓存文件和索引条目"""
        try:
            if md5_hash in self.cache_index:
                cache_file = self._get_cache_path(md5_hash)
                if cache_file.exists():
                    cache_file.unlink()
                del self.cache_index[md5_hash]
                self._save_cache_index()
        except Exception as e:
            logger.error(f"删除缓存失败 {md5_hash}: {e}")

    def clear_all_cache(self) -> Tuple[bool, str]:
        """
        清除所有缓存

        Returns:
            (是否成功, 消息)
        """
        try:
            deleted_count = 0
            for md5_hash in list(self.cache_index.keys()):
                cache_file = self._get_cache_path(md5_hash)
                if cache_file.exists():
                    cache_file.unlink()
                    deleted_count += 1

            self.cache_index = {}
            self._save_cache_index()

            self._hits = 0
            self._misses = 0

            logger.info(f"已清除 {deleted_count} 个缓存文件")
            return True, f"已清除 {deleted_count} 个缓存文件"

        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False, f"清除缓存失败: {e}"

    def clear_expired_cache(self) -> Tuple[int, str]:
        """
        清理过期缓存

        Returns:
            (清理数量, 消息)
        """
        expired_hashes = []
        now = datetime.now()

        for md5_hash, cache_entry in list(self.cache_index.items()):
            created_at = datetime.fromisoformat(
                cache_entry.get("created_at", "2000-01-01")
            )
            if now - created_at > timedelta(days=self.max_age_days):
                expired_hashes.append(md5_hash)

        for md5_hash in expired_hashes:
            self._delete_cache_file(md5_hash)

        msg = f"已清理 {len(expired_hashes)} 个过期缓存文件"
        logger.info(msg)
        return len(expired_hashes), msg

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        total_size = sum(entry.get("size", 0) for entry in self.cache_index.values())

        total_access = sum(
            entry.get("access_count", 0) for entry in self.cache_index.values()
        )

        hit_rate = 0.0
        total_requests = self._hits + self._misses
        if total_requests > 0:
            hit_rate = (self._hits / total_requests) * 100

        stats = {
            "total_files": len(self.cache_index),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "hit_rate": round(hit_rate, 1),
            "hits": self._hits,
            "misses": self._misses,
            "total_access": total_access,
            "max_age_days": self.max_age_days,
            "manager_type": "CacheManager",
        }

        # 调用基类方法验证数据目录
        stats["data_dir_valid"] = self.validate_data_dir()
        return stats

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = self.get_cache_stats()
        return {
            "type": "cache",
            "cache_dir": str(self.cache_dir),
            **stats
        }

    def get_cache_list(self) -> List[Dict[str, Any]]:
        """
        获取缓存列表

        Returns:
            缓存条目列表
        """
        cache_list = []
        for md5_hash, entry in self.cache_index.items():
            cache_list.append(
                {
                    "md5_hash": md5_hash,
                    "file_name": entry.get("file_name", "Unknown"),
                    "created_at": entry.get("created_at", ""),
                    "last_accessed": entry.get("last_accessed", ""),
                    "access_count": entry.get("access_count", 0),
                    "size_kb": round(entry.get("size", 0) / 1024, 2),
                }
            )

        cache_list.sort(key=lambda x: x["last_accessed"], reverse=True)
        return cache_list


_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例（单例模式）"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO)

    with tempfile.TemporaryDirectory() as tmp_dir:
        cm = CacheManager(cache_dir=tmp_dir, max_age_days=30)

        print("=== CacheManager 测试 ===")

        test_md5 = "abc123def456789012345678901234ab"
        result = {"data": "test", "status": "success"}
        cm.cache_result(test_md5, result, "test.pdf")
        print(f"缓存保存: {cm.is_cache_valid(test_md5)}")

        cached = cm.get_cached_result(test_md5)
        print(f"缓存读取: {cached}")

        stats = cm.get_cache_stats()
        print(f"统计信息: {stats}")

        cleared, msg = cm.clear_all_cache()
        print(f"清除结果: {msg}")

        print("\n=== 测试完成 ===")
