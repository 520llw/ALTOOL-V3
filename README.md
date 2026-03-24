# 🏭 ALTOOL V3 - 半导体PDF智能识别解析工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows%2FLinux%2FmacOS-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Semiconductor-IGBT%2FSiC%2FSi-orange.svg" alt="Semiconductor">
</p>

<p align="center">
  <b>智能提取半导体器件参数，让PDF数据表解析效率提升100倍</b>
</p>

---

## ✨ 核心功能

| 功能 | 描述 | 状态 |
|:---|:---|:---:|
| 📄 **PDF智能解析** | 自动识别PDF中的参数表格和文本 | ✅ |
| 🔬 **多器件支持** | IGBT / SiC MOSFET / Si MOSFET | ✅ |
| 📊 **参数自动提取** | 电压、电流、功率、温度等关键参数 | ✅ |
| 🎯 **高精度识别** | 精准度和召回率双高 | ✅ |
| 📤 **多格式导出** | Excel / JSON / CSV | ✅ |
| 🖥️ **友好界面** | Web界面 + 桌面应用 | ✅ |

---

## 🚀 快速开始

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/520llw/ALTOOL-V3.git
cd ALTOOL-V3

# 安装Python依赖
pip install -r requirements.txt
```

### 启动应用

```bash
# 方式1：命令行启动
python main.py

# 方式2：桌面应用
python launcher_desktop.py

# 方式3：Streamlit Web界面
streamlit run main_v3.py
```

---

## 📖 使用指南

### 1. 单文件解析

```bash
python main.py --pdf datasheet.pdf --type IGBT
```

### 2. 批量解析

```bash
python batch_parse_shanyangtong.py --input_dir ./pdfs/ --output_dir ./output/
```

### 3. API服务

```bash
python api_server.py
# 访问 http://localhost:8000
```

---

## 🔧 支持的器件类型

### IGBT（绝缘栅双极晶体管）
- 集电极-发射极电压 (Vces)
- 集电极电流 (Ic)
- 栅极-发射极电压 (Vge)
- 开关时间参数
- 热阻参数

### SiC MOSFET（碳化硅MOSFET）
- 漏源电压 (Vds)
- 漏极电流 (Id)
- 栅源电压 (Vgs)
- 导通电阻 (Rds_on)
- 开关特性

### Si MOSFET（硅MOSFET）
- 漏源击穿电压 (BVdss)
- 连续漏极电流 (Id)
- 栅源阈值电压 (Vgs_th)
- 导通电阻
- 输入/输出电容

---

## 📊 性能指标

| 指标 | 数值 | 说明 |
|:---|:---:|:---|
| 参数提取准确率 | >95% | 关键参数识别 |
| 表格识别召回率 | >90% | 表格内容完整度 |
| 单文件处理时间 | <30秒 | 平均10页PDF |
| 支持PDF类型 | 100+ | 主流厂商数据表 |

---

## 🏗️ 项目架构

```
ALTOOL-V3/
├── 📁 backend/              # 后端核心模块
│   ├── pdf_parser.py        # PDF解析引擎
│   ├── ai_processor.py      # AI智能处理
│   ├── data_writer.py       # 数据写入
│   └── device_configs/      # 器件配置文件
├── 📁 frontend/             # 前端界面
│   └── ui_v3.py            # Streamlit UI
├── 📁 ALTOOL/              # 桌面应用
├── 📄 main.py              # 主程序入口
├── 📄 main_v3.py           # V3版本入口
├── 📄 api_server.py        # API服务
└── 📄 requirements.txt     # 依赖清单
```

---

## 🧪 测试与评估

```bash
# 运行准确性测试
python test_accuracy.py

# 完整性评估
python complete_evaluation.py

# 与真值对比
python evaluate_with_ground_truth.py
```

---

## 📝 更新日志

### V3.0 (2025-03)
- ✨ 全新V3架构，支持Web界面
- ✨ 增加AI智能识别模块
- ✨ 支持批量PDF处理
- ✨ 优化SiC MOSFET参数提取
- ✨ 新增API服务模式

---

## 🤝 贡献指南

欢迎提交Issue和PR！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交改动：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🙏 致谢

- 感谢所有测试用户提供的数据表样本
- 感谢开源社区的支持

---

<p align="center">
  Made with ❤️ for Semiconductor Engineers
</p>
