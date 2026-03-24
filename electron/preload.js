/**
 * Electron预加载脚本
 * 在渲染进程中暴露安全的API
 */

const { contextBridge, ipcRenderer } = require('electron');

// 暴露给渲染进程的API
contextBridge.exposeInMainWorld('electronAPI', {
    // 获取平台信息
    platform: process.platform,
    
    // 获取应用版本
    getVersion: () => {
        return require('./package.json').version;
    },
    
    // 发送消息到主进程
    send: (channel, data) => {
        const validChannels = ['toMain'];
        if (validChannels.includes(channel)) {
            ipcRenderer.send(channel, data);
        }
    },
    
    // 接收主进程消息
    receive: (channel, func) => {
        const validChannels = ['fromMain'];
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => func(...args));
        }
    }
});

