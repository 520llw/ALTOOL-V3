# Windows 便携版打包说明

## 功能说明

将「功率器件参数提取系统」打包成 **Windows 便携版**，用户无需安装 Python 或任何依赖，解压后双击 `启动.bat` 即可使用。

---

## 方式一：在 Linux 上通过 GitHub Actions 打包（推荐）

**无需 Windows 环境**，push 代码后自动在云端 Windows 环境打包。

### 步骤

1. **确保 `.github/workflows` 在 Git 仓库根目录**
   - 若 AITOOL 是独立仓库：`AITOOL/.github/` 已在正确位置
   - 若 AITOOL 是子目录：已为你创建 `<repo根>/.github/workflows/build-windows-portable.yml`，提交时包含该文件即可

2. **Push 到 GitHub**
   ```bash
   git add .
   git commit -m "更新"
   git push origin main
   ```

3. **下载打包结果**
   - 打开仓库 → Actions → 找到「打包 Windows 便携版」工作流
   - 点击最新运行 → 在 Artifacts 区域下载 `功率器件参数提取系统_便携版.zip`

4. **手动触发**（可选）：Actions 页面 → 选择该工作流 → Run workflow

---

## 方式二：在 Windows 上本地打包

### 前置条件

- 必须在 Windows 系统上执行
- 已安装 Python 3.8+

### 执行打包

**方式 A：双击运行**
```
双击 build/build.bat
```

**方式 B：命令行**
```bash
cd AITOOL\build
python build_portable.py
```

### 输出

打包成功后，在项目根目录（AITOOL/）下生成：
- `功率器件参数提取系统_便携版.zip`（约 200-300 MB）

## 分发给用户

1. 将 zip 文件发给用户（网盘、U盘、企业内网等）
2. 用户解压到任意目录（如桌面、D盘）
3. 双击 `启动.bat`
4. 等待 10-30 秒，浏览器自动打开
5. 默认账号：admin / admin123

## 用户端要求

- Windows 10/11 64 位
- 联网（AI 功能需要调用 API）
- 无需安装任何软件

## 注意事项

- 首次启动可能较慢（Streamlit 加载）
- 若杀毒软件拦截，请添加信任
- 数据保存在 `data` 目录，可定期备份
