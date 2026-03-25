# -*- coding: utf-8 -*-
"""
文件工具模块
提供文件操作的安全检查和管理功能
包括路径遍历防护、文件名清理、文件类型验证、临时文件管理等
"""

import os
import re
import uuid
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from tempfile import mkdtemp, mkstemp
from contextlib import contextmanager

from .base_manager import BaseManager

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 100 * 1024 * 1024

ILLEGAL_CHARS_PATTERN = re.compile(r'[\/\\:*?"<>|]')
PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\.[\/\\])+|(\%2e[\/\\])+", re.IGNORECASE)


class FileUtils:
    """文件操作工具类 - 静态方法集合"""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        安全清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的安全文件名
        """
        if not filename:
            return f"unnamed_{uuid.uuid4().hex[:8]}"

        sanitized = ILLEGAL_CHARS_PATTERN.sub("_", filename)

        sanitized = sanitized.strip()
        if not sanitized or sanitized.startswith("."):
            sanitized = f"file_{uuid.uuid4().hex[:8]}{Path(filename).suffix or '.pdf'}"

        if len(sanitized) > 255:
            ext = Path(sanitized).suffix
            name = sanitized[: 255 - len(ext)] + ext

        return sanitized

    @staticmethod
    def is_path_traversal(path: str) -> bool:
        """
        检查路径是否包含路径遍历攻击

        Args:
            path: 待检查的路径

        Returns:
            是否为路径遍历攻击
        """
        normalized = os.path.normpath(path)

        if PATH_TRAVERSAL_PATTERN.search(normalized):
            return True

        if ".." in Path(path).parts:
            return True

        return False

    @staticmethod
    def safe_join(*paths: str, base_dir: str = None) -> Optional[str]:
        """
        安全地拼接路径，防止路径遍历

        Args:
            *paths: 要拼接的路径组件
            base_dir: 基础目录，拼接结果不能超出此目录

        Returns:
            安全拼接后的路径，如果存在安全风险则返回None
        """
        if not paths:
            return None

        try:
            joined = os.path.join(*paths)
            normalized = os.path.normpath(joined)

            if base_dir:
                base_normalized = os.path.normpath(os.path.abspath(base_dir))
                result_path = os.path.normpath(os.path.abspath(normalized))

                if (
                    not result_path.startswith(base_normalized + os.sep)
                    and result_path != base_normalized
                ):
                    logger.warning(f"路径遍历攻击检测: {paths} -> {normalized}")
                    return None

            return normalized

        except Exception as e:
            logger.error(f"路径拼接失败: {e}")
            return None

    @staticmethod
    def validate_file_type(file_path: str, allowed: set = None) -> Tuple[bool, str]:
        """
        验证文件类型，只允许PDF

        Args:
            file_path: 文件路径
            allowed: 允许的扩展名集合

        Returns:
            (是否有效, 错误消息)
        """
        if allowed is None:
            allowed = ALLOWED_EXTENSIONS

        path = Path(file_path)

        if not path.exists():
            return False, "文件不存在"

        if not path.is_file():
            return False, "不是有效文件"

        suffix = path.suffix.lower()
        if suffix not in allowed:
            return False, f"不支持的文件类型: {suffix}，仅支持: {', '.join(allowed)}"

        return True, ""

    @staticmethod
    def validate_file_size(file_path: str, max_size: int = None) -> Tuple[bool, str]:
        """
        验证文件大小

        Args:
            file_path: 文件路径
            max_size: 最大文件大小（字节），默认100MB

        Returns:
            (是否有效, 错误消息)
        """
        if max_size is None:
            max_size = MAX_FILE_SIZE

        path = Path(file_path)

        if not path.exists():
            return False, "文件不存在"

        size = path.stat().st_size

        if size == 0:
            return False, "文件为空"

        if size > max_size:
            max_mb = max_size / (1024 * 1024)
            actual_mb = size / (1024 * 1024)
            return False, f"文件过大: {actual_mb:.1f}MB > {max_mb:.1f}MB"

        return True, ""

    @staticmethod
    def validate_file(file_path: str) -> Tuple[bool, List[str]]:
        """
        综合验证文件（类型、大小、路径安全）

        Args:
            file_path: 文件路径

        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []

        if FileUtils.is_path_traversal(file_path):
            errors.append("检测到非法路径")

        type_valid, type_msg = FileUtils.validate_file_type(file_path)
        if not type_valid:
            errors.append(type_msg)

        size_valid, size_msg = FileUtils.validate_file_size(file_path)
        if not size_valid:
            errors.append(size_msg)

        return len(errors) == 0, errors


class TempFileManager:
    """临时文件管理器"""

    def __init__(self, temp_dir: str = None):
        """
        初始化临时文件管理器

        Args:
            temp_dir: 临时目录路径，默认为系统临时目录
        """
        self.temp_dir = temp_dir or mkdtemp()
        self._managed_files: List[str] = []

    def create_temp_file(self, suffix: str = ".pdf", prefix: str = "altool_") -> str:
        """
        创建临时文件

        Args:
            suffix: 文件扩展名
            prefix: 文件名前缀

        Returns:
            临时文件路径
        """
        fd, path = mkstemp(suffix=suffix, prefix=prefix, dir=self.temp_dir)
        os.close(fd)
        self._managed_files.append(path)
        self.logger.debug(f"创建临时文件: {path}") if hasattr(self, 'logger') else logger.debug(f"创建临时文件: {path}")
        return path

    def create_temp_dir(self, prefix: str = "altool_") -> str:
        """
        创建临时目录

        Args:
            prefix: 目录名前缀

        Returns:
            临时目录路径
        """
        path = mkdtemp(prefix=prefix, dir=self.temp_dir)
        self._managed_files.append(path)
        logger.debug(f"创建临时目录: {path}")
        return path

    def cleanup_file(self, file_path: str):
        """
        删除指定的临时文件

        Args:
            file_path: 文件路径
        """
        try:
            path = Path(file_path)
            if path.exists():
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    import shutil

                    shutil.rmtree(path)
                logger.debug(f"已删除临时文件: {file_path}")

            if file_path in self._managed_files:
                self._managed_files.remove(file_path)

        except Exception as e:
            logger.error(f"删除临时文件失败 {file_path}: {e}")

    def cleanup_all(self):
        """清理所有管理的临时文件"""
        for path in list(self._managed_files):
            self.cleanup_file(path)
        self._managed_files.clear()

    def get_managed_files(self) -> List[str]:
        """获取所有管理的文件列表"""
        return self._managed_files.copy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()


@contextmanager
def safe_file_operation(base_dir: str, operation: str = "read"):
    """
    安全的文件操作上下文管理器

    Args:
        base_dir: 基础目录
        operation: 操作类型 ('read' 或 'write')

    Yields:
        安全操作函数
    """
    manager = TempFileManager()
    try:
        yield {
            "temp_file": manager.create_temp_file,
            "temp_dir": manager.create_temp_dir,
            "sanitize": FileUtils.sanitize_filename,
            "safe_join": lambda *paths: FileUtils.safe_join(*paths, base_dir=base_dir),
            "validate": FileUtils.validate_file,
        }
    finally:
        manager.cleanup_all()


_temp_manager = None


def get_temp_manager() -> TempFileManager:
    """获取全局临时文件管理器实例（单例模式）"""
    global _temp_manager
    if _temp_manager is None:
        _temp_manager = TempFileManager()
    return _temp_manager


if __name__ == "__main__":
    import tempfile

    logging.basicConfig(level=logging.INFO)

    print("=== FileUtils 测试 ===")

    print(f"\n1. 文件名清理:")
    print(f"   'test<>file.pdf' -> {FileUtils.sanitize_filename('test<>file.pdf')}")
    print(f"   '/etc/passwd' -> {FileUtils.sanitize_filename('/etc/passwd')}")
    print(f"   '' -> {FileUtils.sanitize_filename('')}")

    print(f"\n2. 路径遍历检测:")
    print(f"   '../etc/passwd': {FileUtils.is_path_traversal('../etc/passwd')}")
    print(
        f"   'normal/path/file.pdf': {FileUtils.is_path_traversal('normal/path/file.pdf')}"
    )
    print(f"   '..%2f..%2fpasswd': {FileUtils.is_path_traversal('..%2f..%2fpasswd')}")

    print(f"\n3. 安全路径拼接:")
    base = "/home/user/data"
    print(f"   base='{base}'")
    print(
        f"   safe_join(base, 'file.pdf'): {FileUtils.safe_join(base, 'file.pdf', base_dir=base)}"
    )
    print(
        f"   safe_join(base, '../etc/passwd'): {FileUtils.safe_join(base, '../etc/passwd', base_dir=base)}"
    )

    print(f"\n4. 临时文件管理:")
    with TempFileManager() as tm:
        f1 = tm.create_temp_file(suffix=".txt")
        f2 = tm.create_temp_dir(prefix="test_")
        print(f"   创建临时文件: {f1}")
        print(f"   创建临时目录: {f2}")
        print(f"   管理文件列表: {tm.get_managed_files()}")

    print("\n=== 测试完成 ===")
