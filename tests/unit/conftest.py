# -*- coding: utf-8 -*-
"""单元测试共享配置"""
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """提供临时目录fixture"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)
