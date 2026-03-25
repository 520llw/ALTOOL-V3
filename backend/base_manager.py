# -*- coding: utf-8 -*-
"""
BaseManager 基类 - 所有Manager的统一基础
提供统一的初始化、路径处理、JSON读写、日志和错误处理功能
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseManager(ABC):
    """
    所有Manager的抽象基类
    提供统一的初始化逻辑、路径管理和JSON操作
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化基类

        Args:
            data_dir: 数据目录路径，默认为项目根目录下的 data/
        """
        if data_dir is None:
            # 从当前文件位置推导项目根目录
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "data"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)

        # 日志配置
        self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.info(f"{self.__class__.__name__} 初始化完成，数据目录: {self.data_dir}")

    def _get_data_path(self, filename: str) -> Path:
        """
        获取数据文件完整路径

        Args:
            filename: 文件名或相对路径

        Returns:
            完整Path对象
        """
        path = self.data_dir / filename
        # 确保父目录存在
        path.parent.mkdir(exist_ok=True, parents=True)
        return path

    def _load_json(self, filepath: Path) -> Dict[str, Any]:
        """
        统一加载JSON文件

        Args:
            filepath: JSON文件路径

        Returns:
            字典数据，加载失败返回空字典
        """
        if not filepath.exists():
            return {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败 {filepath}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"加载JSON失败 {filepath}: {e}")
            return {}

    def _save_json(self, filepath: Path, data: Dict[str, Any]) -> bool:
        """
        统一保存JSON文件

        Args:
            filepath: 保存路径
            data: 要保存的字典数据

        Returns:
            是否保存成功
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"保存JSON失败 {filepath}: {e}")
            return False

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息，必须由子类实现"""
        pass

    def validate_data_dir(self) -> bool:
        """验证数据目录是否可用"""
        try:
            test_file = self.data_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            self.logger.error(f"数据目录权限检查失败: {e}")
            return False
