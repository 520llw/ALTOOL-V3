# TASK_CURSOR_V2.md - Cursor Composer 任务（修订版）

## 🎯 任务目标
完成系统集成模块开发

## 📁 强制要求

**所有文件必须保存在此目录下**:
```
/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/
```

**绝对路径，不可更改！**

---

## 📝 任务内容

### 1. backup_manager.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/backup_manager.py`

功能要求：
- 手动备份（自定义备份名称）
- 备份列表管理（时间、大小）
- 备份恢复（带确认）
- 备份删除
- 自动备份配置（间隔天数、保留数量）

### 2. security.py
**文件路径**: `/home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/security.py`

功能要求：
- 密码强度检测（0-100分，weak/medium/strong）
- 实时强度显示（彩色进度条+改进建议）
- 登录锁定（5次失败后锁定30分钟）
- 锁定提示（显示剩余锁定时间）
- 路径安全验证

---

## ✅ 完成标准

1. **文件必须实际存在**: 完成后执行 `ls -lh` 验证文件
2. **代码可导入**: 能通过 `from backend.security import SecurityManager` 导入
3. **包含测试代码**: 每个文件末尾必须有 `if __name__ == "__main__":` 测试
4. **符合开发规范**: 见 DEVELOPMENT_STANDARDS.md
5. **与现有代码兼容**: 参考 backend/cache_manager.py 的风格

---

## 📤 完成汇报格式

完成后请汇报：
1. 文件保存的绝对路径
2. 运行 `ls -lh /home/llw/.openclaw/workspace/shared/ALTOOL_V3/backend/*.py` 的输出
3. 每个模块的功能说明和使用示例

---

**重要提醒**: 不要只返回代码内容，必须确保文件已保存到磁盘！
