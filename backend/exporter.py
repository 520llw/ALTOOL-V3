# -*- coding: utf-8 -*-
"""
V3.0 导出模块 - 支持多种格式导出
支持：Excel、JSON、CSV、XML
"""

import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


class DataExporter:
    """数据导出器"""
    
    def __init__(self, output_dir: str = "./data/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_json(self, data: List[Dict[str, Any]], filename: str = "export.json") -> str:
        """导出为JSON格式"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(filepath)
    
    def export_csv(self, data: List[Dict[str, Any]], filename: str = "export.csv") -> str:
        """导出为CSV格式"""
        if not data:
            return ""
        
        filepath = self.output_dir / filename
        
        # 获取所有字段
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        return str(filepath)
    
    def export_xml(self, data: List[Dict[str, Any]], filename: str = "export.xml") -> str:
        """导出为XML格式"""
        filepath = self.output_dir / filename
        
        root = ET.Element("devices")
        
        for item in data:
            device = ET.SubElement(root, "device")
            for key, value in item.items():
                param = ET.SubElement(device, "param")
                param.set("name", str(key))
                param.text = str(value) if value is not None else ""
        
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding='utf-8', xml_declaration=True)
        
        return str(filepath)
    
    def export_excel(self, data: List[Dict[str, Any]], filename: str = "export.xlsx") -> str:
        """导出为Excel格式（保留原有功能）"""
        filepath = self.output_dir / filename
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine='openpyxl')
        return str(filepath)
    
    def export_all(self, data: List[Dict[str, Any]], base_filename: str = "export") -> Dict[str, str]:
        """导出所有格式"""
        results = {}
        
        if not data:
            return results
        
        try:
            results['json'] = self.export_json(data, f"{base_filename}.json")
        except Exception as e:
            results['json'] = f"Error: {e}"
        
        try:
            results['csv'] = self.export_csv(data, f"{base_filename}.csv")
        except Exception as e:
            results['csv'] = f"Error: {e}"
        
        try:
            results['xml'] = self.export_xml(data, f"{base_filename}.xml")
        except Exception as e:
            results['xml'] = f"Error: {e}"
        
        try:
            results['excel'] = self.export_excel(data, f"{base_filename}.xlsx")
        except Exception as e:
            results['excel'] = f"Error: {e}"
        
        return results
