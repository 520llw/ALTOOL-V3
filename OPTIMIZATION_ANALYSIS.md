# 软件优化状态分析报告

> 仅针对代码与流程。**主流程已接入优化（见下方修复说明）。**

---

## 一、已实现的优化能力（代码存在）

| 优化项 | 实现位置 | 说明 |
|--------|----------|------|
| PDF 解析缓存 + MD5 | `pdf_parser.batch_parse()` | 按文件 MD5 缓存解析结果，避免重复解析 |
| PDF 多进程解析 | `pdf_parser.batch_parse_multiprocess()` | ProcessPoolExecutor 并行解析 |
| 解析结果持久化缓存 | `optimize_tools.CacheManager` | 内存 + 文件 pickle，支持 TTL |
| 数据库索引（optimize_tools） | `optimize_tools.create_database_indexes()` | 为 parse_results、users、table_records 建索引 |
| 数据库索引（db_manager） | `db_manager.create_search_indexes()` | 为搜索相关字段建索引 |
| 配置热加载 | `optimize_tools.ConfigManager.reload()` | 读 config.yaml，按 mtime 重载 |
| Streamlit 缓存 | `main.py` | `@st.cache_resource` / `@st.cache_data` 缓存 Parser、AI、DB、参数信息、统计 |
| AI 设备配置缓存 | `ai_processor._config_cache` | 已加载的 YAML 设备配置内存缓存 |

---

## 二、主流程未接入的优化（严重）

### 1. 批量解析未走「带缓存的批量接口」

- **现状**：`main.run_parsing_background()` 中：
  - 用 `pdf_parser.get_pdf_list(pdf_folder)` 取列表；
  - 再**循环** `pdf_parser.parse_pdf(pdf_info['path'])` 逐个解析。
- **结果**：
  - 未使用 `batch_parse()` → **无 MD5 校验、无解析结果缓存**，同一 PDF 每次都会重新解析。
  - 未使用 `batch_parse_multiprocess()` → **无多进程**，全部串行解析。
- **影响**：README 中提到的「缓存命中 300%+ 加速」「多进程 30%+ 缩短」在实际解析任务中**完全未生效**。

**相关代码**：`main.py` 约 1056–1075 行（阶段 1 解析 PDF 的 for 循环）。

---

### 2. 数据库索引建在错误库上，且搜索索引未创建

- **实际使用的库**：`backend/config.py` 中 `DATABASE_PATH = DATA_DIR / "params.db"`，即 `data/params.db`。
- **建索引的库**：`optimize_tools.initialize_optimization()` 中：
  ```python
  db_path = Path(config_manager.get('paths.data_dir', './data')) / 'database.db'
  ```
  即对 `data/database.db` 建索引。
- **结果**：应用读写的是 `params.db`，索引却建在 `database.db` 上，**查询优化未作用于真实库**。
- **另外**：`db_manager.create_search_indexes()` 从未被调用，搜索相关索引在**任意库**上都没有建立。

---

### 3. AI 提取结果无缓存

- **现状**：每次解析都会对每个 PDF 调用 `ai_processor.batch_extract()` → 内部对每组参数调用 API，无按「PDF+参数」维度的缓存。
- **已有能力**：仅有 `optimize_tools.CacheManager` 和 PDF 解析缓存，**没有**「PDF 内容 MD5 / 文件 MD5 → AI 提取结果」的缓存逻辑。
- **结果**：同一份 PDF 重复解析时，会重复请求 AI，无法实现「二次解析秒出」的体验。

---

## 三、配置与初始化不一致

| 项目 | 来源 | 说明 |
|------|------|------|
| 数据库路径 | `config.py`: `DATA_DIR / "params.db"` | 应用唯一使用的 DB 路径 |
| 索引目标路径 | `optimize_tools`: `paths.data_dir` + `"database.db"` | 与上面不一致，且文件名写死 |
| 主配置 | `config.py` 读 `data/config.json` | 保存/加载 AI、parser、UI 等 |
| 性能/路径/安全等 | `optimize_tools.ConfigManager` 读根目录 `config.yaml` | 性能、paths、安全、备份等 |

两套配置（config.json vs config.yaml）、两个库名（params.db vs database.db）并存，容易导致「以为已优化、实际未生效」的认知偏差。

---

## 四、其他可改进点（非致命）

1. **create_search_indexes 从未调用**  
   若希望搜索/筛选加速，应在应用启动或 DB 初始化时对**真实 DB（params.db）** 调用一次 `db_manager.create_search_indexes()`。

2. **batch_parse 与 batch_parse_multiprocess 的进度回调签名**  
   `batch_parse` 的回调是 `(idx, total_files, pdf_file.name, "processing")`，而 `run_parsing_background` 里当前是 `(completed, total, pdf_name)`，若后续接入 batch 接口，需要适配回调参数和进度计算方式。

3. **多进程与缓存可组合**  
   `batch_parse_multiprocess` 内部在「少量文件」时回退到 `batch_parse`（带缓存）；文件多时走多进程，但多进程分支里用的是 `_parse_single_file`，**没有**在子进程中查缓存、写缓存。若要在多进程下也享受缓存，需要在主进程先按 MD5 筛出「未命中」的文件，只对这些文件做多进程解析，或改为「主进程查缓存 + 仅未命中走多进程」。

---

## 五、结论与修复优先级

| 结论 | 说明 |
|------|------|
| **优化未完全到位** | 缓存、多进程、索引等能力在代码里都有，但主解析流程未使用带缓存的批量接口，索引建错库，搜索索引未建。 |
| **修复优先级建议** | 1）主流程改用 `batch_parse` 或「先缓存检查 + 再多进程」；2）索引改为对 `params.db` 创建，并调用 `create_search_indexes`；3）统一 DB 文件名与配置来源；4）可选：为 AI 提取结果增加按 PDF 的缓存。 |

---

## 六、已完成的修复（优化功能已接入）

1. **主解析流程**：`run_parsing_background` 已改为调用 `pdf_parser.batch_parse()`，启用 MD5 校验与解析结果缓存，同一批 PDF 二次解析会命中缓存，速度明显提升。
2. **数据库索引**：`initialize_optimization()` 改为使用 `backend.config.DATABASE_PATH`（即 `params.db`）建索引，并调用 `DatabaseManager().create_search_indexes()`，查询与搜索使用同一库并享有索引。
3. **其他**：`create_search_indexes` 的 raw SQL 已用 `text()` 包装以兼容 SQLAlchemy 2；`pdf_parser` 中多进程超时配置引用已改为 `config.parser.pdf_timeout`；必要目录（含 `cache_dir`、`backup_dir`）在初始化时统一创建。
