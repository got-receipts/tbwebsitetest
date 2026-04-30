const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("thunderCompanion", {
  startPresence: (payload) => ipcRenderer.invoke("presence:start", payload),
  stopPresence: () => ipcRenderer.invoke("presence:stop"),
  openSite: () => ipcRenderer.invoke("site:open"),
  loginSite: () => ipcRenderer.invoke("site:login"),
});
