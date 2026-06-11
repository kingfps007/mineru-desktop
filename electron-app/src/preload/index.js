const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  minimize: () => ipcRenderer.invoke('window-minimize'),
  maximize: () => ipcRenderer.invoke('window-maximize'),
  close: () => ipcRenderer.invoke('window-close'),
  openFile: (options) => ipcRenderer.invoke('dialog-open-file', options),
  openDirectory: () => ipcRenderer.invoke('dialog-open-directory'),
  openExternal: (url) => ipcRenderer.invoke('open-external'),
  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),
});
