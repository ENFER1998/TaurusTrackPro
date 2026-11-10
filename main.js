const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');

app.commandLine.appendSwitch('enable-web-bluetooth');
app.commandLine.appendSwitch('enable-experimental-web-platform-features');
app.commandLine.appendSwitch('enable-features', 'WebBluetooth,WebBluetoothNewPermissionsBackend');

let mainWindow = null;
let bleSelectCallback = null;
let bleScanTimeout = null;

function limpiarSeleccionBlePendiente(cancelar = false) {
  if (bleScanTimeout) {
    clearTimeout(bleScanTimeout);
    bleScanTimeout = null;
  }
  if (cancelar && typeof bleSelectCallback === 'function') {
    const cb = bleSelectCallback;
    bleSelectCallback = null;
    try { cb(''); } catch (e) {}
  } else if (!cancelar) {
    bleSelectCallback = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 700,
    title: "Taurus Track Pro",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (mainWindow.webContents.session && typeof mainWindow.webContents.session.setBluetoothPairingHandler === 'function') {
    mainWindow.webContents.session.setBluetoothPairingHandler((details, callback) => {
      callback({ confirmed: true });
    });
  }

  if (mainWindow.webContents.session) {
    mainWindow.webContents.session.on('will-download', (event, item) => {
      const fileName = item.getFilename() || `Reporte_Taurus_${new Date().toISOString().slice(0, 10)}.pdf`;
      const downloadsDir = app.getPath('downloads');
      item.setSaveDialogOptions({
        title: "Guardar Reporte Oficial Taurus",
        defaultPath: path.join(downloadsDir, fileName),
        filters: [
          { name: 'Documentos PDF', extensions: ['pdf'] },
          { name: 'Todos los archivos', extensions: ['*'] }
        ]
      });
    });
  }

  mainWindow.webContents.on('select-bluetooth-device', (event, deviceList, callback) => {
    event.preventDefault();
    bleSelectCallback = callback;

    const lista = Array.isArray(deviceList) ? deviceList : [];

    const dispositivoTaurus = lista.find((d) => {
      const nombre = String(d.deviceName || '').trim();
      return /taurus|track\s*pro|baston|balanza|rfid|esp32|tru[\s-]*test|allflex|uart/i.test(nombre);
    });

    if (dispositivoTaurus) {
      limpiarSeleccionBlePendiente(false);
      console.log(`[Electron BLE] Conectando a: ${dispositivoTaurus.deviceName || dispositivoTaurus.deviceId}`);
      callback(dispositivoTaurus.deviceId);
      return;
    }

    if (!bleScanTimeout) {
      bleScanTimeout = setTimeout(() => {
        if (typeof bleSelectCallback === 'function') {
          const cb = bleSelectCallback;
          bleSelectCallback = null;
          bleScanTimeout = null;

          const conNombre = lista.find((d) => d.deviceName && !/^dispositivo desconocido|unknown/i.test(d.deviceName));
          if (conNombre) {
            try { cb(conNombre.deviceId); } catch (e) {}
          } else {
            try { cb(''); } catch (e) {}
          }
        }
      }, 10000);
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://wa.me/')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);
    if (parsedUrl.protocol !== 'file:' && !navigationUrl.includes('taurus-cbd59.firebaseapp.com')) {
      event.preventDefault();
    }
  });

  mainWindow.loadFile('pc.html');
}

ipcMain.handle('cancelar-busqueda-ble', async () => {
  limpiarSeleccionBlePendiente(true);
  return { success: true };
});

ipcMain.handle('guardar-reporte-local', async (event, { base64Data, nombreSugerido, extension }) => {
  try {
    if (!mainWindow) throw new Error("Ventana no disponible");

    const nombreLimpio = path.basename(String(nombreSugerido || 'reporte-taurus')).replace(/[^a-zA-Z0-9_\-\.]/g, '_').replace(/\.(pdf|xlsx|csv)$/i, '');
    const extPermitidas = ['pdf', 'xlsx', 'csv'];
    const extFinal = extPermitidas.includes(extension) ? extension : 'pdf';
    const downloadsDir = app.getPath('downloads');

    const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
      title: "Guardar Reporte Oficial Taurus",
      defaultPath: path.join(downloadsDir, `${nombreLimpio}.${extFinal}`),
      filters: [{ name: extFinal.toUpperCase(), extensions: [extFinal] }]
    });

    if (canceled || !filePath) return { success: false, reason: 'canceled' };

    const cleanBase64 = String(base64Data || '').replace(/^data:[^;]+;base64,/, '');
    const buffer = Buffer.from(cleanBase64, 'base64');
    await fs.promises.writeFile(filePath, buffer);
    return { success: true, path: filePath };
  } catch (err) {
    console.error("[Electron IPC Save Error]:", err);
    return { success: false, error: err.message };
  }
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  limpiarSeleccionBlePendiente(true);
  if (process.platform !== 'darwin') app.quit();
});
