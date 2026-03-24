# -*- coding: utf-8 -*-
"""
配置管理模块
负责管理API密钥、超时设置、数据库路径等配置项
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 数据库路径
DATABASE_PATH = DATA_DIR / "params.db"

# 配置文件路径
CONFIG_FILE = DATA_DIR / "config.json"


@dataclass
class AIConfig:
    """AI模型配置"""
    provider: str = "deepseek"  # deepseek / openai / local
    model: str = "deepseek-chat"  # 模型名称
    api_key: str = "sk-d8e93ebf7010489ab9ad97ba4aa9a23a"  # 默认API密钥
    api_base: str = "https://api.deepseek.com/v1"  # API基础URL
    timeout: int = 60  # 请求超时时间（秒）
    max_retries: int = 3  # 最大重试次数


@dataclass
class ParserConfig:
    """解析器配置"""
    pdf_timeout: int = 30  # 单个PDF解析超时时间（秒）
    max_workers: int = 4  # 最大并行工作进程数
    batch_size: int = 10  # 批处理大小


@dataclass
class UIConfig:
    """UI配置"""
    primary_color: str = "#1E3A8A"  # 主色（深蓝色）
    accent_color: str = "#3B82F6"  # 选中态颜色
    warning_color: str = "#F97316"  # 警示色
    background_color: str = "#F3F4F6"  # 背景色
    text_color: str = "#1F2937"  # 文字色
    sidebar_width: int = 280  # 侧边栏宽度


class Config:
    """
    全局配置类
    支持从文件加载配置和保存配置到文件
    """
    
    def __init__(self):
        self.ai = AIConfig()
        self.parser = ParserConfig()
        self.ui = UIConfig()
        self._load_config()
    
    def _load_config(self):
        """从配置文件加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载AI配置
                if 'ai' in data:
                    for key, value in data['ai'].items():
                        if hasattr(self.ai, key):
                            setattr(self.ai, key, value)
                
                # 加载解析器配置
                if 'parser' in data:
                    for key, value in data['parser'].items():
                        if hasattr(self.parser, key):
                            setattr(self.parser, key, value)
                
                # 加载UI配置
                if 'ui' in data:
                    for key, value in data['ui'].items():
                        if hasattr(self.ui, key):
                            setattr(self.ui, key, value)
                            
            except Exception as e:
                print(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存配置到文件"""
        data = {
            'ai': {
                'provider': self.ai.provider,
                'model': self.ai.model,
                'api_key': self.ai.api_key,
                'api_base': self.ai.api_base,
                'timeout': self.ai.timeout,
                'max_retries': self.ai.max_retries,
            },
            'parser': {
                'pdf_timeout': self.parser.pdf_timeout,
                'max_workers': self.parser.max_workers,
                'batch_size': self.parser.batch_size,
            },
            'ui': {
                'primary_color': self.ui.primary_color,
                'accent_color': self.ui.accent_color,
                'warning_color': self.ui.warning_color,
                'background_color': self.ui.background_color,
                'text_color': self.ui.text_color,
                'sidebar_width': self.ui.sidebar_width,
            }
        }
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def update_ai_config(self, provider: str = None, model: str = None, 
                         api_key: str = None, api_base: str = None):
        """
        更新AI配置
        
        Args:
            provider: AI提供商 (deepseek/openai/local)
            model: 模型名称
            api_key: API密钥
            api_base: API基础URL
        """
        if provider is not None:
            self.ai.provider = provider
        if model is not None:
            self.ai.model = model
        if api_key is not None:
            self.ai.api_key = api_key
        if api_base is not None:
            self.ai.api_base = api_base
        self.save_config()


# 全局配置实例
config = Config()

