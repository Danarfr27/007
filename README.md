# ◈ BADAN INTELIJEN NEGARA V7.3 ◈

![License](https://img.shields.io/badge/CLEARANCE-LEVEL%205-red)
![Status](https://img.shields.io/badge/STATUS-CLASSIFIED-darkred)
![Protocol](https://img.shields.io/badge/PROTOCOL-OMEGA--7-green)

> **EYES ONLY** — Secure USB File Management System with James Bond-style Interface

---

## 📋 Overview

**BIN V7.3** adalah aplikasi manajemen file USB dengan tampilan antarmuka futuristik bergaya film *James Bond* / *Mission: Impossible*. Aplikasi ini secara otomatis mendeteksi flashdisk yang dicolokkan dan menampilkan struktur file dalam tampilan *tree* yang dapat di-expand, lengkap dengan efek *live scanning* yang terus berjalan.

---

## ✨ Fitur Utama

### 🔍 Auto-Detection
- **Deteksi otomatis** flashdisk saat dicolokkan ke USB
- **Monitoring real-time** di system tray (background)
- **Sound effects** saat device terdeteksi / dilepas

### 🎬 James Bond UI
- **Tampilan fullscreen** dengan tema dark neon
- **Live scanning animation** yang terus berjalan (loop)
- **Console panel** seperti terminal hacker dengan timestamp
- **Typing effect** — file muncul satu per satu di tree
- **Color-coded** file types (hijau, kuning, merah)
- **Badge "CLASSIFIED"** dan "EYES ONLY"

### 📁 File Management
| Operasi | Shortcut | Keterangan |
|---------|----------|------------|
| Copy | `Ctrl + C` / 📋 button | Copy file ke clipboard |
| Cut | `Ctrl + X` / ✂️ button | Cut file ke clipboard |
| Paste | `Ctrl + V` / 📎 button | Paste dari clipboard |
| Delete | `Delete` / 🗑️ button | Hapus file/folder |
| Rename | ✏️ button | Ganti nama file |
| New Folder | 📁 button | Buat folder baru |
| Refresh | `F5` | Refresh tree view |

### 🖱️ Context Menu (Right-Click)
- Semua operasi file tersedia via klik kanan pada tree
- **Open in Explorer** — buka lokasi file di Windows Explorer

### 🔧 System Tray
- Minimize ke system tray (klik kanan icon tray)
- **Auto-start with Windows** (via menu tray)
- Double-click tray icon untuk restore window

---

## 🚀 Cara Menggunakan

### 1. Install Dependency

```bash
pip install PyQt5 pyinstaller
```

### 2. Jalankan Script

```bash
python 007.py
```

### 3. Colok Flashdisk

1. Pastikan script sudah berjalan (icon di system tray)
2. Colok flashdisk ke USB
3. GUI akan otomatis fullscreen dengan animasi scanning
4. Tree file akan muncul bertahap (typing effect)
5. Panel console kanan akan terus update log

### 4. Keluar / Minimize

| Tombol | Aksi |
|--------|------|
| `ESC` | Minimize ke system tray |
| `F11` | Toggle fullscreen / windowed |
| Close window | Minimize ke tray (bukan quit) |
| Tray menu → **Terminate** | Keluar aplikasi |

---

## 🔨 Build ke .exe (Standalone)

```bash
pyinstaller --onefile --windowed --name "BIN_V73" 007.py
```

Hasil .exe ada di folder `dist/BIN_V73.exe`

> **Tips**: Copy `BIN_V73.exe` ke folder Startup Windows (`Win + R` → `shell:startup`) agar auto-jalan saat Windows nyala.

---

## 🎨 Tema Warna

Tersedia 4 tema warna yang dapat diganti via konfigurasi:

| Tema | Primary | Keterangan |
|------|---------|------------|
| **Green** | `#00ffaa` | Default — hacker terminal |
| **Amber** | `#ffaa00` | Retro CRT monitor |
| **Red** | `#ff4444` | Alert / danger mode |
| **Cyan** | `#00aaff` | Sci-fi blue |

---

## 🖥️ Screenshot Tampilan

```
◈ BADAN INTELIJEN NEGARA    V7.3    [CLASSIFIED]
┌──────────────────────────────────────────────────────────────┐
│ PATH: E:\                                                  │
├──────────────────────────────────────────────────────────────┤
│ 📋 COPY  ✂️ CUT  📎 PASTE  🗑️ DELETE  ✏️ RENAME  📁 NEW │
├──────────────────────────┬───────────────────────────────────┤
│ NAME     TYPE     SIZE   │ [10:05:12] >> Establishing...    │
│ 📁 DCIM  FOLDER    -     │ [10:05:13] 📁 SCANNING DIR: DCIM │
│ 📄 IMG1  IMAGE   2.4 MB │ [10:05:13] 📄 FOUND: IMG1.jpg    │
│ 📄 VID1  VIDEO  45.2 MB │ [10:05:14] >> Verifying...       │
│ 📄 DOC1  DOCUMENT 856 KB│ [10:05:15] >> Cross-referencing..│
│ 📁 DOCS  FOLDER    -     │ [10:05:16] 📁 SCANNING DIR: DOCS │
├──────────────────────────┴───────────────────────────────────┤
│ ● LIVE SCANNING ACTIVE...                                    │
├──────────────────────────────────────────────────────────────┤
│ ENCRYPTION: AES-256 | PROTOCOL: OMEGA-7 | CLEARANCE: LEVEL 5 │
└──────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Konfigurasi

File konfigurasi tersimpan di:
```
%USERPROFILE%\.bin_v73_config.json
```

Opsi yang tersedia:

```json
{
  "auto_startup": false,
  "sound_enabled": true,
  "theme": "green",
  "show_hidden": false,
  "confirm_delete": true
}
```

---

## 🛡️ Keamanan & Batasan

| Aspek | Penjelasan |
|-------|------------|
| **Windows Only** | Menggunakan Windows API (`ctypes`, `wmi`) |
| **Admin Rights** | Tidak perlu admin untuk run biasa |
| **AutoRun** | Windows AutoRun tidak digunakan — aman dari malware |
| **File Limit** | Max 100 file per folder, depth 3 (mencegah stuck) |
| **Permission** | Folder dengan access denied akan ditampilkan `[ACCESS DENIED]` |

---

## 🐛 Troubleshooting

### Stuck di Scanning
- Pastikan flashdisk tidak corrupt
- Coba flashdisk dengan file lebih sedikit
- Tekan `F5` untuk refresh manual

### Tidak Terdeteksi
- Pastikan flashdisk muncul di Windows Explorer
- Coba colok ulang flashdisk
- Restart script

### Error WMI / pythoncom
- Script ini sudah menggunakan `ctypes` (bukan WMI)
- Tidak perlu install `pywin32` atau `wmi`

---

## 📦 Dependency

| Package | Versi | Keterangan |
|---------|-------|------------|
| Python | 3.8+ | Wajib |
| PyQt5 | Latest | GUI framework |
| pyinstaller | Latest | Untuk build .exe (opsional) |

---

## 📝 Changelog

### v7.3
- ✅ Live scanning loop (tidak berhenti di 100%)
- ✅ Console panel dengan timestamp
- ✅ Tree file dengan typing effect
- ✅ Auto-detection flashdisk via Windows API
- ✅ File operations (copy, cut, paste, delete, rename)
- ✅ System tray mode
- ✅ 4 tema warna

---

## ⚠️ Disclaimer

> Aplikasi ini dibuat untuk **edukasi dan entertainment** (tampilan James Bond). Tidak ada kaitan dengan institusi intelijen manapun. Nama "BADAN INTELIJEN NEGARA" adalah fiksi untuk efek dramatis.

---

## 👤 Author

Dibuat dengan ❤️ untuk penggemar film spy-thriller.

**Clearance: LEVEL 5 | Protocol: OMEGA-7 | Eyes Only**

---

*"The name's Bond. James Bond."* 🍸
