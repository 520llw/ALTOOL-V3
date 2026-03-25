# TASK_OPCODE_V2.md - OpenCode 任务（修订版）

## 🎯 任务目标
完成基础架构模块开发

## 📁 强制要求

**所有文件必须保存在此目录下**:
```
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/
```

**绝对路径，不可更改！**

---

## 📝 任务内容

### 1. cache_manager.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/cache_manager.py`

功能要求：
- MD5哈希计算（支持大文件分块）
- 缓存读写（存储结构: cache/{md5前2位}/{md5}.json）
- 缓存有效期检查（默认30天）
- 过期清理功能
- 缓存统计信息

### 2. file_utils.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/file_utils.py`

功能要求：
- 路径遍历攻击防护
- 文件名安全清理（移除非法字符）
- 文件类型验证（只允许PDF）
- 文件大小检查
- 临时文件管理

---

## ✅ 完成标准

1. **文件必须实际存在**: 完成后执行 `ls -lh` 验证文件
2. **代码可导入**: 能通过 `from backend.cache_manager import CacheManager` 导入
3. **包含测试代码**: 每个文件末尾必须有 `if __name__ == "__main__":` 测试
4. **符合开发规范**: 见 DEVELOPMENT_STANDARDS.md

---

## 📤 完成汇报格式

完成后请汇报：
1. 文件保存的绝对路径
2. 每个文件的核心功能
3. 运行 `ls -lh /home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/*.py` 的输出
4. 使用示例代码

---

**重要提醒**: 不要只返回代码内容，必须确保文件已保存到磁盘！
