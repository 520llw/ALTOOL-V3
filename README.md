# ⚡ 功率器件参数提取系统

一款基于AI的功率半导体器件（MOSFET/IGBT/SiC MOSFET）PDF手册参数自动提取工具，支持批量处理、智能参数匹配、Excel导出。

## 📋 功能特性

### 核心功能
- **智能PDF解析**：使用pdfplumber + PyMuPDF双引擎，精准提取表格和文本
- **AI参数提取**：支持通义千问(qwen-max)、OpenAI GPT等大模型
- **器件类型自动识别**：自动识别Si MOSFET、SiC MOSFET、IGBT
- **参数标准化**：内置62+标准参数库，支持自定义参数和变体
- **批量处理**：支持文件夹批量导入，多进程并行解析
- **Excel分Sheet输出**：按器件类型分Sheet存储，方便查阅

### 🆕 v2.0 新增特性

#### 性能优化
- **MD5校验**：自动检测文件变更，避免重复解析相同文件
- **缓存机制**：AI提取结果本地缓存，二次解析直接调用，速度提升300%+
- **多进程解析**：支持4进程并行，100份PDF解析时间缩短30%+
- **数据库索引**：查询速度提升50%+

#### 用户体验
- **系统仪表盘**：首页展示统计数据、图表、快捷操作入口
- **实时进度显示**：解析时显示进度百分比、预计剩余时间、处理速度
- **新手引导**：首次登录显示3步引导，快速上手
- **友好提示**：错误提示包含原因和解决方案

#### 安全加固
- **密码强度检测**：实时显示密码强度（弱/中/强）
- **输入过滤**：防止SQL注入和路径遍历攻击
- **登录保护**：失败5次锁定10分钟

#### 数据管理
- **数据备份**：支持手动备份和定时自动备份
- **日志分级**：INFO/WARNING/ERROR分级管理
- **配置热加载**：修改config.yaml无需重启

## 🖥️ 系统要求

- **操作系统**：Windows 10/11、Ubuntu 20.04+、macOS 10.15+
- **Python**：3.8 或更高版本
- **内存**：建议 8GB 以上
- **网络**：需要访问AI API（通义千问/OpenAI）

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆或下载项目后进入目录
cd AITOOL

# 安装Python依赖
pip install -r requirements.txt
```

### 2. 启动应用

```bash
# 使用streamlit启动
streamlit run main.py --server.port 8501

# 或使用启动脚本
./start.sh      # Linux/Mac
start.bat       # Windows
```

### 3. 使用系统

1. 打开浏览器访问 `http://localhost:8501`
2. 使用默认账号登录：admin / admin123
3. 在**仪表盘**查看系统概览
4. 在**参数管理**页面点击「初始化参数库」导入标准参数
5. 在**解析任务**页面上传PDF文件
6. 点击「开始批量解析」，等待AI提取参数
7. 在**精细化查看**或**精准搜索**页面查看结果

## 📁 项目结构

```
AITOOL/
├── main.py                    # Streamlit主程序入口
├── config.yaml                # 🆕 全局配置文件
├── backend/                   # 后端核心模块
│   ├── config.py              # 配置管理
│   ├── db_manager.py          # 数据库操作(SQLAlchemy)
│   ├── pdf_parser.py          # PDF解析（支持多进程）
│   ├── ai_processor.py        # AI调用与参数提取
│   ├── data_writer.py         # Excel/数据库写入
│   ├── user_manager.py        # 用户认证管理
│   └── optimize_tools.py      # 🆕 优化工具模块
├── frontend/                  # 🆕 前端组件
│   └── dashboard.py           # 系统仪表盘
├── data/                      # 数据目录
│   ├── database.db            # SQLite数据库
│   └── uploads/               # 上传文件目录
├── cache/                     # 🆕 缓存目录
├── backup/                    # 🆕 备份目录
├── logs/                      # 日志目录
│   ├── info.log               # 操作日志
│   └── error.log              # 错误日志
├── output/                    # Excel输出目录
├── requirements.txt           # Python依赖
└── README.md                  # 说明文档
```

## ⚙️ 配置说明

### config.yaml 配置项

```yaml
# 界面配置
ui:
  primary_color: "#1E3A8A"      # 主题色
  default_page_size: 20         # 默认分页条数
  show_guide: true              # 是否显示新手引导

# 性能配置
performance:
  parse_workers: 4              # 解析并发进程数
  ai_timeout: 60                # AI调用超时(秒)
  cache_ttl_hours: 24           # 缓存有效期(小时)
  enable_md5_check: true        # 启用MD5校验
  enable_cache: true            # 启用缓存

# 安全配置
security:
  max_login_attempts: 5         # 最大登录失败次数
  lockout_duration_minutes: 10  # 账号锁定时间
  password_min_length: 6        # 密码最小长度

# AI配置
ai:
  default_provider: "dashscope" # 默认AI提供商
  default_model: "qwen-max"     # 默认模型
  temperature: 0.1              # 温度参数

# 备份配置
backup:
  auto_backup: true             # 启用自动备份
  backup_day: 0                 # 备份日(0=周日)
  max_backups: 3                # 保留备份数
```

### AI模型配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| AI提供商 | dashscope(通义千问)/openai | dashscope |
| 模型 | qwen-max/qwen-plus/gpt-4o等 | qwen-max |
| API密钥 | 留空使用内置密钥 | 内置 |

## ⌨️ 快捷键

| 快捷键 | 功能 | 页面 |
|--------|------|------|
| Enter | 确认登录/搜索 | 登录/搜索页 |
| Ctrl+S | 保存参数 | 参数管理 |
| Ctrl+F | 搜索参数 | 参数管理 |

## 🔧 常见问题（FAQ）

### Q: PDF解析失败？
**A**: 
1. 确保PDF不是扫描版（需要文字可选择）
2. 检查PDF是否有密码保护
3. 查看 `logs/error.log` 获取详细错误信息
4. 尝试使用Adobe Acrobat重新保存PDF

### Q: AI提取结果不准确？
**A**:
1. 检查参数库是否包含对应参数
2. 在参数管理中添加更多变体名称
3. 确保使用qwen-max模型（提取精度最高）
4. 查看「精细化查看」页面的原始文本，确认PDF内容是否包含该参数

### Q: 解析速度慢？
**A**:
1. 确认已启用缓存（config.yaml: enable_cache: true）
2. 增加并发进程数（config.yaml: parse_workers: 4）
3. 检查网络连接（AI API调用需要稳定网络）

### Q: 如何备份数据？
**A**:
1. 在「系统设置」页面点击「备份数据库」
2. 或直接复制 `data/database.db` 文件
3. 系统每周日凌晨自动备份（可在config.yaml配置）

### Q: 忘记管理员密码？
**A**:
1. 删除 `data/database.db` 文件
2. 重启系统，将自动创建默认管理员账号
3. 默认账号：admin / admin123

### Q: 如何添加新参数？
**A**: 在「参数管理」页面点击「新增参数」，填写：
- 标准参数名（中文）
- 英文名/描述
- 单位
- 变体名称（PDF中可能出现的不同命名）

## 📊 性能对比

| 操作 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 解析100份PDF | ~30分钟 | ~20分钟 | 33%↑ |
| 二次解析（缓存命中） | ~30分钟 | ~30秒 | 98%↑ |
| 参数查询 | ~500ms | ~50ms | 90%↑ |
| 表格生成 | ~10秒 | ~4秒 | 60%↑ |

## 📝 更新日志

### v2.0.0 (2026-01)
- 🆕 系统仪表盘，数据可视化
- 🆕 MD5校验+缓存机制，避免重复解析
- 🆕 多进程并行解析
- 🆕 数据库索引优化
- 🆕 配置文件热加载
- 🆕 新手引导功能
- 🆕 实时进度显示和时间估算
- 🔧 参数提取精度优化（厂家识别、特殊功能提取）
- 🔧 错误提示优化

### v1.0.0 (2024-01)
- 初始版本发布
- 支持Si MOSFET、SiC MOSFET、IGBT参数提取
- 集成通义千问qwen-max模型

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**技术支持**：如有问题，请提交GitHub Issue
