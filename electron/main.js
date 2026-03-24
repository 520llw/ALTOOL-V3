/**
 * 功率器件参数提取系统 - Electron主进程
 * 负责创建桌面窗口和管理Streamlit后端进程
 */

const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawn, exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// 全局变量
let mainWindow = null;
let streamlitProcess = null;
let streamlitPort = 8501;
let isQuitting = false;

// 项目根目录（相对于electron目录）
const projectRoot = path.join(__dirname, '..');

/**
 * 检查端口是否被占用
 */
function checkPort(port) {
    return new Promise((resolve) => {
        const net = require('net');
        const server = net.createServer();
        
        server.once('error', (err) => {
            if (err.code === 'EADDRINUSE') {
                resolve(false);
            }
        });
        
        server.once('listening', () => {
            server.close();
            resolve(true);
        });
        
        server.listen(port);
    });
}

/**
 * 查找可用端口
 */
async function findAvailablePort(startPort) {
    let port = startPort;
    while (port < startPort + 100) {
        const available = await checkPort(port);
        if (available) {
            return port;
        }
        port++;
    }
    return startPort;
}

/**
 * 启动Streamlit服务
 */
async function startStreamlit() {
    // 查找可用端口
    streamlitPort = await findAvailablePort(8501);
    
    console.log(`Starting Streamlit on port ${streamlitPort}...`);
    
    // 检测操作系统
    const isWindows = process.platform === 'win32';
    const pythonCmd = isWindows ? 'python' : 'python3';
    
    // 构建命令
    const args = [
        '-m', 'streamlit', 'run',
        path.join(projectRoot, 'main.py'),
        '--server.port', streamlitPort.toString(),
        '--server.headless', 'true',
        '--server.enableCORS', 'false',
        '--server.enableXsrfProtection', 'false',
        '--browser.gatherUsageStats', 'false',
        '--theme.base', 'light'
    ];
    
    // 启动Streamlit进程
    streamlitProcess = spawn(pythonCmd, args, {
        cwd: projectRoot,
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
        shell: isWindows
    });
    
    // 监听输出
    streamlitProcess.stdout.on('data', (data) => {
        console.log(`Streamlit: ${data}`);
    });
    
    streamlitProcess.stderr.on('data', (data) => {
        console.error(`Streamlit Error: ${data}`);
    });
    
    streamlitProcess.on('close', (code) => {
        console.log(`Streamlit process exited with code ${code}`);
        if (!isQuitting) {
            // 意外退出，尝试重启
            setTimeout(startStreamlit, 2000);
        }
    });
    
    streamlitProcess.on('error', (err) => {
        console.error('Failed to start Streamlit:', err);
        dialog.showErrorBox(
            '启动失败',
            `无法启动Streamlit服务: ${err.message}\n\n请确保已安装Python和必要的依赖包。`
        );
    });
    
    // 等待Streamlit启动
    return new Promise((resolve) => {
        setTimeout(resolve, 3000);
    });
}

/**
 * 停止Streamlit服务
 */
function stopStreamlit() {
    if (streamlitProcess) {
        console.log('Stopping Streamlit...');
        
        if (process.platform === 'win32') {
            // Windows下需要杀死进程树
            exec(`taskkill /pid ${streamlitProcess.pid} /T /F`, (err) => {
                if (err) {
                    console.error('Error killing Streamlit:', err);
                }
            });
        } else {
            streamlitProcess.kill('SIGTERM');
        }
        
        streamlitProcess = null;
    }
}

/**
 * 创建主窗口
 */
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        title: '功率器件参数提取系统',
        icon: path.join(__dirname, 'icons', 'icon.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        show: false,  // 先隐藏，等加载完成再显示
        backgroundColor: '#F3F4F6'
    });
    
    // 移除菜单栏（可选）
    // mainWindow.setMenu(null);
    
    // 加载Streamlit页面
    const url = `http://localhost:${streamlitPort}`;
    
    // 显示加载提示
    mainWindow.loadURL(`data:text/html;charset=utf-8,
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #F3F4F6;
                    color: #1F2937;
                }
                .loader {
                    text-align: center;
                }
                .spinner {
                    width: 50px;
                    height: 50px;
                    border: 3px solid #E5E7EB;
                    border-top: 3px solid #1E3A8A;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 20px;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                h2 { color: #1E3A8A; margin-bottom: 10px; }
                p { color: #6B7280; }
            </style>
        </head>
        <body>
            <div class="loader">
                <div class="spinner"></div>
                <h2>⚡ 功率器件参数提取系统</h2>
                <p>正在启动，请稍候...</p>
            </div>
        </body>
        </html>
    `);
    
    mainWindow.show();
    
    // 等待Streamlit就绪后加载
    const checkReady = setInterval(() => {
        require('http').get(url, (res) => {
            if (res.statusCode === 200) {
                clearInterval(checkReady);
                mainWindow.loadURL(url);
            }
        }).on('error', () => {
            // 继续等待
        });
    }, 500);
    
    // 超时处理
    setTimeout(() => {
        clearInterval(checkReady);
    }, 30000);
    
    // 处理外部链接
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });
    
    // 窗口关闭事件
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

/**
 * 应用就绪
 */
app.whenReady().then(async () => {
    // 启动Streamlit
    await startStreamlit();
    
    // 创建窗口
    createWindow();
    
    // macOS: 点击dock图标重新创建窗口
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

/**
 * 所有窗口关闭
 */
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

/**
 * 应用退出前
 */
app.on('before-quit', () => {
    isQuitting = true;
    stopStreamlit();
});

/**
 * 应用退出
 */
app.on('quit', () => {
    stopStreamlit();
});

