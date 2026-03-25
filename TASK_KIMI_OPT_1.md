# TASK_KIMI_OPT_1.md - Kimi: 测试体系建设（Ralph Loop）

## 🎯 任务目标
建立完整的测试体系，使用Ralph Loop持续优化测试质量

## 📁 工作目录
`/home/llw/.openclaw/workspace/shared/ALTOOL_V3/`

## 📝 具体任务

### 1. 创建测试目录结构

```
tests/
├── __init__.py
├── conftest.py              # pytest配置
├── unit/                    # 单元测试
│   ├── __init__.py
│   ├── test_cache_manager.py
│   ├── test_file_utils.py
│   ├── test_backup_manager.py
│   └── test_security.py
├── integration/             # 集成测试
│   ├── __init__.py
│   └── test_workflow.py
└── fixtures/                # 测试数据
    ├── sample.pdf
    └── sample_config.json
```

### 2. 创建单元测试

使用Ralph Loop持续优化每个模块的测试：

**test_cache_manager.py**:
- 测试MD5计算
- 测试缓存读写
- 测试过期清理
- 测试并发安全

**test_file_utils.py**:
- 测试路径安全
- 测试PDF验证
- 测试文件名清理

**test_backup_manager.py**:
- 测试备份创建
- 测试备份恢复
- 测试自动备份

**test_security.py**:
- 测试密码强度
- 测试登录锁定
- 测试路径安全

### 3. 创建集成测试

测试完整工作流程：
- 文件上传→解析→缓存→备份
- 错误恢复流程
- 并发操作

### 4. 测试覆盖率目标

使用Ralph Loop迭代直到达到：
- 行覆盖率 > 80%
- 分支覆盖率 > 70%
- 所有关键路径都有测试

## 🔄 Ralph Loop配置

```bash
kimi --max-ralph-iterations 10 "创建测试并优化直到覆盖率>80%"
```

## ✅ 完成标准

1. **测试目录**: 完整创建
2. **单元测试**: 覆盖所有backend模块
3. **集成测试**: 覆盖主要流程
4. **覆盖率**: >80%
5. **所有测试通过**: pytest运行无失败

## 📤 完成汇报

完成后汇报：
1. 创建了哪些测试文件
2. 测试覆盖率数据
3. 发现的bug（如果有）
4. 测试运行结果
