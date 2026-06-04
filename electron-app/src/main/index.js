const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const net = require('net');
const { spawn } = require('child_process');

let mainWindow = null;
let backendProcess = null;
const BACKEND_PORT = 18766;
const BACKEND_STARTUP_TIMEOUT_MS = 30000;  // 30s 超时

// ── 查找 Python 解释器 ──
function findPython() {
  const candidates = [
    'C:/ProgramData/miniconda3/python.exe',
    'C:/ProgramData/anaconda3/python.exe',
    'C:/ProgramData/Miniconda3/python.exe',
    path.join(require('os').homedir(), 'miniconda3', 'python.exe'),
    path.join(require('os').homedir(), 'Miniconda3', 'python.exe'),
  ];
  for (const c of candidates) {
    try { if (fs.existsSync(c)) return c; } catch(e) {}
  }
  return 'python';
}

// ── 等待端口就绪（轮询 TCP） ──
function waitPort(port, timeoutMs) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const sock = net.createConnection(port, '127.0.0.1');
      let done = false;
      const finish = (err) => { if (!done) { done = true; sock.destroy(); if (err) reject(err); else resolve(); } };
      sock.once('connect', () => finish(null));
      sock.once('error', (e) => {
        if (Date.now() - start > timeoutMs) finish(new Error('timeout'));
        else setTimeout(tryOnce, 500);
      });
      setTimeout(() => { if (!done && Date.now() - start > timeoutMs) finish(new Error('timeout')); }, timeoutMs);
    };
    tryOnce();
  });
}

// ── 启动后端 ──
function startBackend() {
  const python = findPython();

  // 解析 server.py 路径
  let serverPath, cwd;
  if (app.isPackaged) {
    serverPath = path.join(process.resourcesPath, 'backend', 'server.py');
    cwd = path.join(process.resourcesPath, 'backend');
  } else {
    serverPath = path.join(__dirname, '..', '..', '..', 'backend', 'server.py');
    cwd = path.join(__dirname, '..', '..', '..', 'backend');
  }

  if (!fs.existsSync(serverPath)) {
    console.error('[FATAL] Backend server.py not found at:', serverPath);
    return Promise.reject(new Error('Backend not found: ' + serverPath));
  }

  console.log('[backend] Python:', python);
  console.log('[backend] Script:', serverPath);

  backendProcess = spawn(python, [serverPath, String(BACKEND_PORT)], {
    cwd: cwd,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    windowsHide: true,
  });

  backendProcess.stdout.on('data', (data) => {
    const s = data.toString().trim();
    if (s) console.log(`[backend] ${s}`);
  });
  backendProcess.stderr.on('data', (data) => {
    const s = data.toString().trim();
    if (s) console.log(`[backend-err] ${s}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`[backend] exited code=${code}`);
    backendProcess = null;
  });
  backendProcess.on('error', (err) => {
    console.error('[backend] spawn error:', err.message);
  });

  // 等端口起来
  return waitPort(BACKEND_PORT, BACKEND_STARTUP_TIMEOUT_MS);
}

// ── 关闭后端 ──
function stopBackend() {
  if (backendProcess) {
    try {
      // Windows 强制终止（taskkill /F /T 杀进程树）
      if (process.platform === 'win32' && backendProcess.pid) {
        spawn('taskkill', ['/F', '/T', '/PID', String(backendProcess.pid)], { windowsHide: true });
      } else {
        backendProcess.kill();
      }
    } catch(e) {}
    backendProcess = null;
  }
}

// ── 主窗口 ──
function createWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) return mainWindow;

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 900,
    minHeight: 640,
    title: 'MinerU Desktop',
    backgroundColor: '#ffffff',
    show: false,  // 先不显示，加载完成再显示（避免白屏闪烁）
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    frame: false,
    titleBarStyle: 'hidden',
  });

  const htmlPath = path.join(__dirname, '..', 'renderer', 'index.html');
  mainWindow.loadFile(htmlPath);

  // 加载完成才显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // 加载失败提示
  mainWindow.webContents.on('did-fail-load', (_, code, desc) => {
    console.error('[window] load failed:', code, desc);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  return mainWindow;
}

// ── App 生命周期 ──
app.whenReady().then(async () => {
  // 设置 IPC handlers 必须先于窗口创建
  registerIpcHandlers();

  try {
    console.log('[main] Starting backend...');
    await startBackend();
    console.log('[main] Backend ready on port', BACKEND_PORT);
  } catch (err) {
    console.error('[FATAL] Backend startup failed:', err.message);
    // 后端启动失败：弹窗告知用户，然后退出
    const { dialog } = require('electron');
    dialog.showErrorBox(
      '后端启动失败',
      `Python 后端无法启动（端口 ${BACKEND_PORT}）。\n\n可能原因：\n1. Python 环境未安装（需 Miniconda/Anaconda）\n2. 端口被占用\n3. backend/server.py 丢失\n\n错误：${err.message}\n\n请检查后重试。`
    );
    app.quit();
    return;
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopBackend();
});

// 进程异常处理
process.on('uncaughtException', (err) => {
  console.error('[uncaughtException]', err);
});
process.on('unhandledRejection', (err) => {
  console.error('[unhandledRejection]', err);
});

// ── IPC Handlers ──
function registerIpcHandlers() {
  ipcMain.handle('window-minimize', () => mainWindow?.minimize());
  ipcMain.handle('window-maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow?.unmaximize();
    else mainWindow?.maximize();
  });
  ipcMain.handle('window-close', () => mainWindow?.close());

  ipcMain.handle('dialog-open-file', async (_, options) => {
    if (!mainWindow) return { canceled: true, filePaths: [] };
    const result = await dialog.showOpenDialog(mainWindow, options || {});
    return result || { canceled: true, filePaths: [] };
  });

  ipcMain.handle('dialog-open-directory', async () => {
    if (!mainWindow) return { canceled: true, filePaths: [] };
    const result = await dialog.showOpenDialog(mainWindow, { properties: ['openDirectory'] });
    return result || { canceled: true, filePaths: [] };
  });

  ipcMain.handle('open-external', async (_, url) => {
    await shell.openExternal(url);
  });

  ipcMain.handle('get-backend-port', () => BACKEND_PORT);
}
