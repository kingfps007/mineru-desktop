const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow = null;
let backendProcess = null;
const BACKEND_PORT = 18766;

function findPython() {
  const candidates = [
    'C:/ProgramData/miniconda3/python.exe',
    'C:/ProgramData/anaconda3/python.exe',
    path.join(require('os').homedir(), 'miniconda3/python.exe'),
  ];
  const fs = require('fs');
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return 'python';
}

function startBackend() {
  const python = findPython();

  // In production (packaged), backend is in resources/backend
  // In development, backend is at project_root/backend
  let serverPath;
  let cwd;
  if (app.isPackaged) {
    serverPath = path.join(process.resourcesPath, 'backend', 'server.py');
    cwd = path.join(process.resourcesPath, 'backend');
  } else {
    serverPath = path.join(__dirname, '..', '..', '..', 'backend', 'server.py');
    cwd = path.join(__dirname, '..', '..', '..', 'backend');
  }

  if (!require('fs').existsSync(serverPath)) {
    console.error('Backend server.py not found at:', serverPath);
    return;
  }

  backendProcess = spawn(python, [serverPath, String(BACKEND_PORT)], {
    cwd: cwd,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 900,
    minHeight: 640,
    title: 'MinerU Desktop v3.2.2',
    backgroundColor: '#ffffff',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    frame: false,
    titleBarStyle: 'hidden',
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
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

ipcMain.handle('window-minimize', () => mainWindow?.minimize());
ipcMain.handle('window-maximize', () => {
  if (mainWindow?.isMaximized()) mainWindow.unmaximize();
  else mainWindow?.maximize();
});
ipcMain.handle('window-close', () => mainWindow?.close());

ipcMain.handle('dialog-open-file', async (_, options) => {
  const result = await dialog.showOpenDialog(mainWindow, options || {});
  return result;
});

ipcMain.handle('dialog-open-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, { properties: ['openDirectory'] });
  return result;
});

ipcMain.handle('open-external', async (_, url) => {
  await shell.openExternal(url);
});

ipcMain.handle('get-backend-port', () => BACKEND_PORT);
