const { app, BrowserWindow, Tray, Menu, ipcMain, shell } = require("electron");
const path = require("path");
const RPC = require("discord-rpc");

const siteUrl = "https://fleettest-production.up.railway.app";
let clientId = process.env.DISCORD_APPLICATION_ID || "";

let mainWindow;
let tray;
let rpc;
let currentPresence = null;

function createWindow() {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 520,
    height: 680,
    title: "Thunder Buddies Companion",
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.loadFile("renderer.html");
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

async function connectRpc() {
  if (rpc) return rpc;
  if (!clientId) {
    const response = await fetch(`${siteUrl}/api/companion/config`);
    const config = await response.json();
    clientId = config.discord_client_id;
  }
  if (!clientId) {
    throw new Error("Discord Application ID is missing from the website configuration.");
  }

  RPC.register(clientId);
  rpc = new RPC.Client({ transport: "ipc" });

  rpc.on("ready", () => {
    if (currentPresence) setPresence(currentPresence);
  });

  await rpc.login({ clientId });
  return rpc;
}

async function fetchProject(reference) {
  if (!reference) return null;
  const response = await fetch(`${siteUrl}/api/requests/${encodeURIComponent(reference)}`);
  if (!response.ok) return null;
  const payload = await response.json();
  const record = payload.record;
  const phases = payload.phases || [];
  const tasks = record.task_checklist || [];
  const done = tasks.filter((task) => task.done).length;
  const progress = tasks.length ? Math.round((done / tasks.length) * 100) : 0;
  return {
    reference: record.reference,
    phase: phases[record.status_index] || "Tracking progress",
    progress: `${progress}% complete`,
    url: `${siteUrl}/requests/${encodeURIComponent(record.reference)}`,
  };
}

async function setPresence(payload) {
  const project = await fetchProject(payload.reference);
  currentPresence = project || payload;
  const client = await connectRpc();
  const reference = currentPresence.reference || "Studio Dashboard";
  const phase = currentPresence.phase || "Tracking progress";
  const progress = currentPresence.progress || "Live project";

  await client.setActivity({
    details: `Tracking ${reference}`,
    state: `${phase} | ${progress}`,
    startTimestamp: Date.now(),
    largeImageKey: "thunderbuddies_logo",
    largeImageText: "Thunder Buddies Studios",
    buttons: [
      {
        label: "Open Dashboard",
        url: currentPresence.url || siteUrl,
      },
    ],
  });
}

function clearPresence() {
  if (!rpc) return;
  rpc.clearActivity();
  rpc.destroy();
  rpc = null;
  currentPresence = null;
}

function createTray() {
  tray = new Tray(path.join(__dirname, "icon.png"));
  tray.setToolTip("Thunder Buddies Companion");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Open Companion", click: createWindow },
      { label: "Open Website", click: () => shell.openExternal(siteUrl) },
      { label: "Stop Rich Presence", click: clearPresence },
      { type: "separator" },
      { label: "Quit", click: () => app.quit() },
    ])
  );
}

ipcMain.handle("presence:start", async (_event, payload) => {
  await setPresence(payload);
  return { ok: true, presence: currentPresence };
});

ipcMain.handle("presence:stop", () => {
  clearPresence();
  return { ok: true };
});

ipcMain.handle("site:open", () => {
  shell.openExternal(siteUrl);
  return { ok: true };
});

ipcMain.handle("site:login", () => {
  shell.openExternal(`${siteUrl}/login`);
  return { ok: true };
});

app.whenReady().then(() => {
  createWindow();
  createTray();
});

app.on("before-quit", clearPresence);

app.on("window-all-closed", (event) => {
  event.preventDefault();
});
