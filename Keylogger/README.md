# Advanced System Monitor

A comprehensive Windows system monitoring tool with a modern GUI interface for tracking keystrokes, clipboard content, and screenshots. Built with Python and Tkinter.

## Features

### 📊 Live Monitoring
- Real-time keystroke logging with process and window information
- Clipboard content tracking with change detection
- Automatic screenshots at configurable intervals
- Live activity feed with color-coded entries

### 📈 Statistics Dashboard
- Track total keys logged
- Monitor clipboard entries count
- View screenshot statistics
- Database size monitoring
- Real-time stats updates

### 🔍 Log Management
- Search functionality across all logs
- Filter by log type (Keystrokes, Clipboard, Screenshots)
- Export data to JSON format
- Clear database with confirmation

### ⚙ Customization
- Adjustable screenshot interval (30-3600 seconds)
- Toggle clipboard monitoring
- Enable/disable auto-scroll
- Save settings persistently

### 🎨 Modern UI
- Dark theme with accent colors
- Tabbed interface for organized views
- Responsive design
- Status bar with current time
- Hover effects on buttons

---

## Installation

### Prerequisites
- Python 3.7 or higher
- Windows OS (for full functionality)
- Administrator privileges (recommended)

### Quick Install

Clone the repository:
```bash
git clone https://github.com/Mishondada/introduction-to-programming.git
cd Keylogger
```

Run the application — it will automatically install required dependencies:
```bash
python keylogger.py
```

### Manual Installation

```bash
pip install pynput psutil pywin32 pillow clipboard
```

---

## Usage

### Starting the Application
```bash
python keylogger.py
```

### Main Controls

| Button | Function |
|--------|----------|
| ▶ Start Monitoring | Begin tracking system activity |
| ⏹ Stop Monitoring | Stop all monitoring activities |
| 📸 Screenshot | Take an immediate screenshot |
| 🗑 Clear Log | Clear the live activity feed |

### Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| Ctrl+Alt+H | Hide/Show main window |
| Ctrl+Alt+S | Take screenshot |
| F1 | Show help dialog |

### Tabs Overview

1. **📊 Live Monitor** — Real-time activity feed with control panel
2. **📈 Statistics** — Overview of collected data
3. **⚙ Settings** — Configure monitoring parameters
4. **📋 Logs** — Search and browse historical data

---

## Data Storage

The application uses SQLite for data persistence.

### Database Schema

**keystrokes table**
- `id` — Primary key
- `timestamp` — ISO format timestamp
- `key` — Captured keystroke
- `process` — Source process name
- `window` — Active window title

**clipboard table**
- `id` — Primary key
- `timestamp` — Capture time
- `content` — Clipboard content (truncated to 1000 chars)

**screenshots table**
- `id` — Primary key
- `timestamp` — Screenshot time
- `filepath` — Screenshot file location

### Export Format

Data can be exported to JSON with the following structure:

```json
{
  "keystrokes": [...],
  "clipboard": [...],
  "screenshots": [...],
  "export_date": "2024-01-01T12:00:00"
}
```

---

## Configuration

Default settings are stored in the `Config` dataclass:

| Setting | Default |
|---------|---------|
| `log_file` | `sysmon.log` |
| `db_file` | `sysmon.db` |
| `screenshot_interval` | 300 seconds |
| `clipboard_monitoring` | `True` |
| `auto_scroll` | `True` |
| `max_log_entries` | 1000 |

---

## Requirements

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `pynput` | Keyboard event monitoring |
| `psutil` | Process information |
| `pywin32` | Windows GUI interaction |
| `Pillow` | Screenshot capture |
| `clipboard` | Clipboard monitoring |
| `tkinter` | GUI framework (included with Python) |

### Windows-Specific Features
- Active window detection via `win32gui`
- Process identification via `win32process`
- Administrator check via `ctypes`

---

## Security Considerations

> ⚠️ **Important**: This tool captures sensitive information including all keystrokes (including passwords), clipboard content, and screen contents.

**Usage Guidelines:**
- Only use on systems you own or have explicit permission to monitor
- Inform users if monitoring is active
- Store data securely and delete when no longer needed
- Consider legal implications in your jurisdiction

---

## Troubleshooting

**"Missing module" error**
The application will attempt to install missing modules automatically. Run as administrator for automatic installation, or manually install with:
```bash
pip install -r requirements.txt
```

**Screenshots not working**
Ensure Pillow is properly installed and check if display/scaling settings are interfering.

**Process/window detection fails**
Run as administrator and verify that `pywin32` is properly installed.

**Database errors**
Ensure write permissions in the application directory and check that the database file is not corrupted.

---

## Project Structure

```
Keylogger/
├── keylogger.py           # Main application
├── README.md           # Documentation
├── requirements.txt    # Dependencies
└── sysmon.db           # SQLite database (created on first run)
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## Version History

- **v2.0** (Current) — Complete GUI overhaul, statistics dashboard, search functionality, data export, improved error handling
- **v1.0** — Initial release with basic monitoring features and simple console interface

---

## License

This project is licensed under the MIT License — see the `LICENSE` file for details.

## Disclaimer

This software is provided for educational and legitimate monitoring purposes only. Users are responsible for complying with all applicable laws and regulations. The authors assume no liability for misuse of this software.

---

> **Note**: For optimal performance and full feature access, run this application as administrator on Windows systems.
