# -*- coding: utf-8 -*-
"""
V3.0 简化版API接口
基于Flask的轻量级RESTful API
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import sys
import os

# 添加backend到路径
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor
from backend.exporter import DataExporter
from backend.db_manager import DatabaseManager

app = Flask(__name__)
CORS(app)  # 允许跨域

# 初始化组件
pdf_parser = PDFParser()
ai_processor = AIProcessor()
exporter = DataExporter()
db = DatabaseManager()


@app.route('/api/v3/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "version": "3.0"})


@app.route('/api/v3/parse', methods=['POST'])
def parse_pdf():
    """解析PDF并提取参数"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        device_type = request.form.get('device_type', 'Si MOSFET')
        
        # 保存上传文件
        upload_dir = Path('./data/uploads')
        upload_dir.mkdir(parents=True, exist_ok=True)
        filepath = upload_dir / file.filename
        file.save(filepath)
        
        # 解析PDF
        pdf_content = pdf_parser.parse(str(filepath))
        
        # AI提取参数
        result = ai_processor.extract(pdf_content, device_type)
        
        return jsonify({
            "success": True,
            "device_name": result.get('device_name', ''),
            "device_type": device_type,
            "parameters": result.get('parameters', {}),
            "confidence": result.get('confidence', 0)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v3/export', methods=['POST'])
def export_data():
    """导出数据为多种格式"""
    try:
        data = request.json.get('data', [])
        format_type = request.json.get('format', 'json')
        filename = request.json.get('filename', 'export')
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # 根据格式导出
        if format_type == 'json':
            filepath = exporter.export_json(data, f"{filename}.json")
        elif format_type == 'csv':
            filepath = exporter.export_csv(data, f"{filename}.csv")
        elif format_type == 'xml':
            filepath = exporter.export_xml(data, f"{filename}.xml")
        elif format_type == 'excel':
            filepath = exporter.export_excel(data, f"{filename}.xlsx")
        else:
            return jsonify({"error": "Unsupported format"}), 400
        
        return send_file(filepath, as_attachment=True)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v3/devices', methods=['GET'])
def list_devices():
    """获取支持的器件类型"""
    return jsonify({
        "devices": [
            {"name": "Si MOSFET", "icon": "⚡", "color": "#3B82F6"},
            {"name": "SiC MOSFET", "icon": "🔥", "color": "#EF4444"},
            {"name": "IGBT", "icon": "🔌", "color": "#10B981"}
        ]
    })


@app.route('/api/v3/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        stats = db.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
