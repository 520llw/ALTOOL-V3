# ALTOOL V3.0 更新说明

## 🆕 V3.0 新增功能

### 1. 多格式导出支持
- ✅ JSON格式导出（便于系统集成）
- ✅ CSV格式导出（便于数据分析）
- ✅ XML格式导出（便于企业系统）
- ✅ 保留原有Excel导出功能

**使用方式：**
```python
from backend.exporter import DataExporter

exporter = DataExporter()
results = exporter.export_all(data, "my_export")
# 生成：my_export.json, my_export.csv, my_export.xml, my_export.xlsx
```

### 2. RESTful API接口
- ✅ `/api/v3/health` - 健康检查
- ✅ `/api/v3/parse` - PDF解析提取
- ✅ `/api/v3/export` - 多格式导出
- ✅ `/api/v3/devices` - 器件类型列表
- ✅ `/api/v3/stats` - 统计信息

**启动API服务：**
```bash
python api_server.py
# 访问 http://localhost:5000
```

### 3. Prompt优化（V3.0）
- ✅ 更精确的提取指令
- ✅ 常见陷阱提醒
- ✅ 数值验证机制
- ✅ 易漏参数补充提取

### 4. 代码结构优化
- ✅ 独立导出模块（backend/exporter.py）
- ✅ Prompt模板独立（backend/prompt_v3.py）
- ✅ 轻量级API服务（api_server.py）

---

## 🔄 版本对比

| 功能 | V2.0 | V3.0 |
|:---|:---:|:---:|
| PDF解析 | ✅ | ✅ |
| AI参数提取 | ✅ | ✅（Prompt优化）|
| Excel导出 | ✅ | ✅ |
| JSON导出 | ❌ | ✅ |
| CSV导出 | ❌ | ✅ |
| XML导出 | ❌ | ✅ |
| RESTful API | ❌ | ✅ |
| 本地模型 | ❌ | ❌（成本考虑）|
| React前端 | ❌ | ❌（保留Streamlit）|

---

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动Web界面（Streamlit）
```bash
streamlit run main.py
```

### 启动API服务（Flask）
```bash
python api_server.py
```

---

## 📝 API使用示例

```bash
# 1. 健康检查
curl http://localhost:5000/api/v3/health

# 2. 解析PDF
curl -X POST -F "file=@datasheet.pdf" -F "device_type=Si MOSFET" \
  http://localhost:5000/api/v3/parse

# 3. 导出JSON
curl -X POST -H "Content-Type: application/json" \
  -d '{"data": [...], "format": "json", "filename": "export"}' \
  http://localhost:5000/api/v3/export \
  --output export.json
```

---

## 💰 V3.0开发说明

- **开发成本**：低成本优化（使用OpenCode免费工具）
- **API成本**：继续使用默认deepseek配置
- **目标**：核心功能增强，成本可控

---

*更新日期：2026-03-23*
*版本：V3.0*
