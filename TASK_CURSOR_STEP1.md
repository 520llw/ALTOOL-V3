# TASK_CURSOR_OPT_STEP1.md - 第一步：创建BaseManager基类

## 🎯 任务
创建 `backend/base_manager.py` 作为所有Manager的基类

## 📁 工作目录
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/

## 📝 具体要求

创建文件 `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/base_manager.py`，内容：

```python
# -*- coding: utf-8 -*-
"""
BaseManager - 所有Manager的基类

提供统一的路径处理、JSON操作、日志记录
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class BaseManager:
    """Manager基类"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化
        
        Args:
            data_dir: 数据目录，默认为项目data目录
        """
        if data_dir is None:
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "data"
        
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # 设置日志
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _get_data_path(self, filename: str) -> Path:
        """获取数据文件路径"""
        return self.data_dir / filename
    
    def _load_json(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """加载JSON文件"""
        if not filepath.exists():
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载JSON失败: {e}")
            return None
    
    def _save_json(self, filepath: Path, data: Dict[str, Any]) -> bool:
        """保存JSON文件"""
        try:
            filepath.parent.mkdir(exist_ok=True, parents=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"保存JSON失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（子类重写）"""
        return {"status": "ok"}
```

## ✅ 完成验证

完成后执行：
```bash
ls -lh /home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/base_manager.py
python3 -c "from backend.base_manager import BaseManager; print('导入成功')"
```

## 📤 汇报

完成后汇报：
1. 文件是否创建成功
2. 验证命令的输出结果
