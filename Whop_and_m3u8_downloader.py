import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import os
import subprocess
import re
import threading
import queue
import time
import webbrowser
import configparser

# --- Default Categories Mapping ---
CATEGORY_MAPPING = {
    "start": ["start here", "the most important video"],
    "technical things": ["types of channels", "channels testing", "buy/sell channels", "analytics", "gmail", "proxies", "vps"],
    "ai": ["ai content", "ai channels", "photorealistic", "breakdowns", "non-fiction ai"],
    "niches": ["niche", "rpm", "demand testing", "incognito", "spy method", "languages", "very important video"],
    "algorithm": ["watchtime", "algorithm", "when to stop"],
    "ypp and copyright": ["appeal", "save yourself", "ypp"],
    "ideation": ["analyst", "scamper", "ideation"],
    "packaging": ["negativity", "titles", "triggers", "packaging", "thumbs", "outliers"],
    "scripts": ["structure", "hooks", "avatar", "tension", "call-to-action", "cta", "storytelling"],
    "hacks": ["repurpose", "reuploads", "nda"],
    "team": ["managers", "team=machine"]
}

CONFIG_FILE = "config.ini"

class DraggableTreeview(ttk.Treeview):
    """
    A specific Treeview subclass that supports dragging and dropping rows.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Button-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_motion)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.configure(cursor="hand2")
        self.drag_data = {"item": None, "x": 0, "y": 0}

    def on_press(self, event):
        item = self.identify_row(event.y)
        if item:
            self.drag_data["item"] = item
            self.selection_set(item)

    def on_motion(self, event):
        if self.drag_data["item"]:
            target = self.identify_row(event.y)
            if target:
                self.selection_set(target)

    def on_release(self, event):
        item = self.drag_data["item"]
        target = self.identify_row(event.y)
        self.drag_data["item"] = None
        
        if not target or not item or target == item:
            return

        target_parent = self.parent(target)
        item_parent = self.parent(item)

        # Logic: Folder cannot be inside folder. File can be moved to Folder.
        if item_parent == "": return # Don't drag folders
        
        if target_parent == "":
            self.move(item, target, "end")
        else:
            self.move(item, target_parent, "end")

class WhopDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whop Video Organizer & Downloader")
        self.geometry("1100x800")
        
        # --- State Variables ---
        self.is_downloading = False
        self.is_paused = False
        self.is_cancelled = False
        self.current_process = None
        self.last_clipboard_text = ""
        self.clipboard_monitor_active = False

        # --- Load Configuration ---
        # FIXED: Renamed self.config to self.app_config to avoid conflict with tk.config()
        self.app_config = configparser.ConfigParser()
        self.load_settings()

        # --- Theme Colors ---
        self.colors = {
            "light": {"bg": "#f0f0f0", "fg": "black", "entry_bg": "white", "tree_bg": "white", "log_bg": "#1e1e1e", "log_fg": "#00ff00"},
            "dark": {"bg": "#2d2d2d", "fg": "white", "entry_bg": "#404040", "tree_bg": "#404040", "log_bg": "#1e1e1e", "log_fg": "#00ff00"}
        }
        self.current_theme = self.get_config("Settings", "theme", "light")

        self._setup_ui()
        self.apply_theme() # Apply initial theme
        self._check_ffmpeg()
        
        # Start Clipboard Monitor Loop
        self.check_clipboard_loop()

    # --- Config Management ---
    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            self.app_config.read(CONFIG_FILE)
        else:
            self.app_config["Paths"] = {"input_file": "Titles and links.txt", "output_folder": os.getcwd()}
            self.app_config["Settings"] = {
                "theme": "light", 
                "audio_only": "False", 
                "open_folder": "False", 
                "watch_clipboard": "False"
            }
    
    def get_config(self, section, key, default):
        try:
            return self.app_config[section][key]
        except KeyError:
            return default

    def save_settings(self):
        # Ensure sections exist before saving
        if "Paths" not in self.app_config: self.app_config["Paths"] = {}
        if "Settings" not in self.app_config: self.app_config["Settings"] = {}

        self.app_config["Paths"]["input_file"] = self.entry_file.get()
        self.app_config["Paths"]["output_folder"] = self.entry_output.get()
        self.app_config["Settings"]["theme"] = self.current_theme
        self.app_config["Settings"]["audio_only"] = str(self.var_audio_only.get())
        self.app_config["Settings"]["open_folder"] = str(self.var_open_folder.get())
        self.app_config["Settings"]["watch_clipboard"] = str(self.var_watch_clipboard.get())
        
        with open(CONFIG_FILE, 'w') as configfile:
            self.app_config.write(configfile)

    def _check_ffmpeg(self):
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            messagebox.showwarning("FFmpeg Missing", "FFmpeg was not found in your system PATH.\nPlease place 'ffmpeg.exe' in this folder.")

    def _setup_ui(self):
        # --- Menu ---
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Open Help & Tutorial", command=self.open_help_window)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        # This line was causing the error because self.config was shadowed
        self.config(menu=menubar)

        # --- Top Controls ---
        self.control_frame = tk.LabelFrame(self, text="Configuration", padx=10, pady=10)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)

        # File & Folder Inputs
        tk.Label(self.control_frame, text="Text File:").grid(row=0, column=0, sticky="e")
        self.entry_file = tk.Entry(self.control_frame, width=50)
        self.entry_file.insert(0, self.get_config("Paths", "input_file", "Titles and links.txt"))
        self.entry_file.grid(row=0, column=1, padx=5)
        tk.Button(self.control_frame, text="Browse...", command=self.browse_file).grid(row=0, column=2)

        tk.Label(self.control_frame, text="Output Folder:").grid(row=1, column=0, sticky="e")
        self.entry_output = tk.Entry(self.control_frame, width=50)
        self.entry_output.insert(0, self.get_config("Paths", "output_folder", os.getcwd()))
        self.entry_output.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.control_frame, text="Browse...", command=self.browse_folder).grid(row=1, column=2)

        tk.Button(self.control_frame, text="Load File", command=self.load_and_parse, height=2, bg="#dddddd").grid(row=0, column=3, rowspan=2, padx=10, sticky="ns")

        # --- Options Bar ---
        self.options_frame = tk.Frame(self, padx=10, pady=5)
        self.options_frame.pack(fill=tk.X)

        # Variables
        self.var_audio_only = tk.BooleanVar(value=self.get_config("Settings", "audio_only", "False") == "True")
        self.var_open_folder = tk.BooleanVar(value=self.get_config("Settings", "open_folder", "False") == "True")
        self.var_watch_clipboard = tk.BooleanVar(value=self.get_config("Settings", "watch_clipboard", "False") == "True")

        # Checkboxes
        self.chk_audio = tk.Checkbutton(self.options_frame, text="Audio Only (.mp3)", variable=self.var_audio_only, command=self.save_settings)
        self.chk_audio.pack(side=tk.LEFT, padx=10)
        
        self.chk_open = tk.Checkbutton(self.options_frame, text="Open Folder when done", variable=self.var_open_folder, command=self.save_settings)
        self.chk_open.pack(side=tk.LEFT, padx=10)

        self.chk_clip = tk.Checkbutton(self.options_frame, text="Watch Clipboard (Smart Add)", variable=self.var_watch_clipboard, command=self.save_settings)
        self.chk_clip.pack(side=tk.LEFT, padx=10)

        # Theme Toggle
        self.btn_theme = tk.Button(self.options_frame, text="Toggle Dark Mode", command=self.toggle_theme)
        self.btn_theme.pack(side=tk.RIGHT, padx=10)

        # --- Middle Split View ---
        middle_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        middle_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Treeview
        self.tree_frame = tk.LabelFrame(middle_pane, text="Queue Structure")
        middle_pane.add(self.tree_frame, width=450)

        self.tree = DraggableTreeview(self.tree_frame, columns=("url"), selectmode="browse")
        self.tree.heading("#0", text="Folder / Video Title", anchor="w")
        self.tree.column("url", width=0, stretch=tk.NO) 
        
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Rename", command=self.rename_item)
        self.context_menu.add_command(label="New Folder", command=self.add_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_item)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Right: Log
        right_frame = tk.Frame(middle_pane)
        middle_pane.add(right_frame)

        self.log_frame = tk.LabelFrame(right_frame, text="Console Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(self.log_frame, state='disabled', width=40, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.note_frame = tk.Frame(right_frame, bg="#fff3cd", padx=5, pady=5, borderwidth=1, relief="solid")
        self.note_frame.pack(fill=tk.X, pady=(5,0))
        tk.Label(self.note_frame, text="NOTE: 'Invalid NAL unit size' / 'Missing picture' errors are normal for streams.", bg="#fff3cd", font=("Arial", 8)).pack(anchor="w")

        # --- Bottom Actions ---
        self.action_frame = tk.Frame(self, padx=10, pady=10)
        self.action_frame.pack(fill=tk.X)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.action_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Status & Buttons
        self.status_var = tk.StringVar(value="Ready")
        self.lbl_status = tk.Label(self.action_frame, textvariable=self.status_var, font=("Arial", 10, "italic"))
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        self.btn_cancel = tk.Button(self.action_frame, text="CANCEL", command=self.cancel_download, bg="#FF5252", fg="white", state="disabled", width=12)
        self.btn_cancel.pack(side=tk.RIGHT, padx=5)

        self.btn_pause = tk.Button(self.action_frame, text="PAUSE", command=self.toggle_pause, bg="#FFC107", state="disabled", width=12)
        self.btn_pause.pack(side=tk.RIGHT, padx=5)

        self.btn_download = tk.Button(self.action_frame, text="START DOWNLOAD", command=self.start_download_thread, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), height=2, width=20)
        self.btn_download.pack(side=tk.RIGHT, padx=5)

    # --- Theme Logic ---
    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()
        self.save_settings()

    def apply_theme(self):
        c = self.colors[self.current_theme]
        
        # Main Window
        self.configure(bg=c["bg"])
        self.control_frame.configure(bg=c["bg"], fg=c["fg"])
        self.options_frame.configure(bg=c["bg"])
        self.tree_frame.configure(bg=c["bg"], fg=c["fg"])
        self.log_frame.configure(bg=c["bg"], fg=c["fg"])
        self.action_frame.configure(bg=c["bg"])
        
        # Widgets
        for widget in self.control_frame.winfo_children():
            if isinstance(widget, (tk.Label, tk.Checkbutton)):
                widget.configure(bg=c["bg"], fg=c["fg"])
        
        for widget in self.options_frame.winfo_children():
            if isinstance(widget, (tk.Label, tk.Checkbutton)):
                widget.configure(bg=c["bg"], fg=c["fg"])
                if isinstance(widget, tk.Checkbutton): widget.configure(selectcolor=c["bg"])

        self.lbl_status.configure(bg=c["bg"], fg=c["fg"])
        
        # Specifics
        self.log_text.configure(bg=c["log_bg"], fg=c["log_fg"])
        self.entry_file.configure(bg=c["entry_bg"], fg=c["fg"], insertbackground=c["fg"])
        self.entry_output.configure(bg=c["entry_bg"], fg=c["fg"], insertbackground=c["fg"])
        
        # Treeview styling requires ttk.Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=c["tree_bg"], fieldbackground=c["tree_bg"], foreground=c["fg"])
        style.map("Treeview", background=[('selected', '#0078D7')])

    # --- Clipboard Monitor ---
    def check_clipboard_loop(self):
        if self.var_watch_clipboard.get():
            try:
                content = self.clipboard_get()
                if content != self.last_clipboard_text:
                    self.last_clipboard_text = content
                    if "stream.mux.com" in content and ".m3u8" in content:
                        self.ask_to_add_link(content)
            except:
                pass
        self.after(2000, self.check_clipboard_loop) # Check every 2 seconds

    def ask_to_add_link(self, url):
        # Pause monitor momentarily
        original_state = self.var_watch_clipboard.get()
        self.var_watch_clipboard.set(False)
        
        # Ask user
        self.lift() # Bring window to front
        self.attributes('-topmost',True)
        self.after_idle(self.attributes,'-topmost',False)
        
        response = messagebox.askyesno("Link Detected", "M3U8 Link detected in clipboard!\nDo you want to add it to the queue?")
        
        if response:
            title = simpledialog.askstring("Add Video", "Enter Title for the video:", initialvalue="New Video")
            if title:
                # Add to "Uncategorized"
                found_uncat = False
                for child in self.tree.get_children():
                    if self.tree.item(child, "text") == "Uncategorized":
                        self.tree.insert(child, "end", text=title, values=(url,))
                        found_uncat = True
                        break
                if not found_uncat:
                    node = self.tree.insert("", "end", text="Uncategorized", open=True)
                    self.tree.insert(node, "end", text=title, values=(url,))
                self.log(f"Added from Clipboard: {title}")

        self.var_watch_clipboard.set(original_state)

    # --- Core Logic ---
    def log(self, message):
        self.after(0, self._log_internal, message)

    def _log_internal(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def clean_filename(self, text):
        cleaned = re.sub(r'[<>:"/\\|?*]', '', text)
        cleaned = cleaned.encode('ascii', 'ignore').decode('ascii')
        return cleaned.strip()

    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if f: 
            self.entry_file.delete(0, tk.END)
            self.entry_file.insert(0, f)
            self.save_settings()

    def browse_folder(self):
        f = filedialog.askdirectory()
        if f: 
            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, f)
            self.save_settings()

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
        else:
            self.context_menu.post(event.x_root, event.y_root)

    def rename_item(self):
        sel = self.tree.selection()
        if sel:
            item = sel[0]
            new = simpledialog.askstring("Rename", "New Name:", initialvalue=self.tree.item(item, "text"))
            if new: self.tree.item(item, text=new)

    def add_folder(self):
        new = simpledialog.askstring("Folder", "Name:")
        if new: self.tree.insert("", "end", text=new, open=True)

    def delete_item(self):
        sel = self.tree.selection()
        if sel:
            if messagebox.askyesno("Delete", "Are you sure you want to remove this item?"):
                self.tree.delete(sel[0])

    def load_and_parse(self):
        filepath = self.entry_file.get()
        if not os.path.exists(filepath):
            messagebox.showerror("Error", "File not found!")
            return
        
        self.save_settings()
        for item in self.tree.get_children(): self.tree.delete(item)
        self.log(f"Loading {filepath}...")
        
        videos = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except:
            self.log("Error reading file.")
            return

        current_title = None
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith("http"):
                if current_title:
                    videos.append((current_title, line))
                    current_title = None
            else:
                current_title = line.rstrip(':')

        nodes = {}
        nodes["uncategorized"] = self.tree.insert("", "end", text="Uncategorized", open=True)

        for title, url in videos:
            cat = "Uncategorized"
            title_lower = title.lower()
            for c_name, keywords in CATEGORY_MAPPING.items():
                for kw in keywords:
                    if kw in title_lower:
                        cat = c_name.title()
                        break
            
            if cat not in nodes:
                nodes[cat] = self.tree.insert("", "end", text=cat, open=True)
            self.tree.insert(nodes[cat], "end", text=title, values=(url,))

        self.log(f"Loaded {len(videos)} videos.")
        self.status_var.set(f"Loaded {len(videos)} items.")

    # --- Download Logic ---
    def toggle_pause(self):
        if not self.is_downloading: return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.config(text="RESUME", bg="#4CAF50")
            self.log(">> Paused.")
        else:
            self.btn_pause.config(text="PAUSE", bg="#FFC107")
            self.log(">> Resumed.")

    def cancel_download(self):
        if not self.is_downloading: return
        self.is_cancelled = True
        self.log(">> Cancelling...")
        if self.current_process:
            try: self.current_process.kill()
            except: pass

    def start_download_thread(self):
        self.save_settings()
        self.btn_download.config(state="disabled")
        self.btn_pause.config(state="normal")
        self.btn_cancel.config(state="normal")
        self.is_cancelled = False
        self.is_paused = False
        self.is_downloading = True
        self.progress_var.set(0)
        
        t = threading.Thread(target=self.run_download_process)
        t.start()

    def run_download_process(self):
        out_root = self.entry_output.get()
        audio_only = self.var_audio_only.get()

        if not os.path.exists(out_root):
            try: os.makedirs(out_root)
            except Exception as e:
                self.log(f"Error creating folder: {e}")
                self._reset_buttons()
                return

        folders = self.tree.get_children()
        
        # Calculate Total
        total_items = 0
        for f in folders: total_items += len(self.tree.get_children(f))
        
        processed_count = 0
        self.log(f"Starting queue: {total_items} items.")

        for folder_id in folders:
            if self.is_cancelled: break
            
            folder_name = self.clean_filename(self.tree.item(folder_id, "text"))
            full_path = os.path.join(out_root, folder_name)
            videos = self.tree.get_children(folder_id)
            
            if not videos: continue
            if not os.path.exists(full_path): os.makedirs(full_path)

            for vid_id in videos:
                if self.is_cancelled: break
                while self.is_paused:
                    time.sleep(0.5)
                    if self.is_cancelled: break

                title = self.tree.item(vid_id, "text")
                url = self.tree.item(vid_id, "values")[0]
                safe_title = self.clean_filename(title)
                
                # Setup Extension
                ext = ".mp3" if audio_only else ".mp4"
                out_file = os.path.join(full_path, f"{safe_title}{ext}")

                if os.path.exists(out_file):
                    self.log(f"Skipping (Exists): {safe_title}")
                    processed_count += 1
                    self.progress_var.set((processed_count / total_items) * 100)
                    continue

                self.log(f"Downloading: {safe_title}...")
                self.status_var.set(f"Downloading: {safe_title}")

                # Build Command
                if audio_only:
                    # Audio Only Command (Extract Audio)
                    cmd = ["ffmpeg", "-i", url, "-vn", "-c:a", "libmp3lame", "-q:a", "2", out_file, "-y", "-v", "error", "-stats"]
                else:
                    # Video Command
                    cmd = ["ffmpeg", "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", out_file, "-y", "-v", "error", "-stats"]

                # Retry Logic
                success = False
                for attempt in range(1, 4): # Try 3 times
                    if self.is_cancelled: break
                    try:
                        startupinfo = None
                        if os.name == 'nt':
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                        self.current_process = subprocess.Popen(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        stdout, stderr = self.current_process.communicate()

                        if self.current_process.returncode == 0:
                            self.log(f"✓ Done: {safe_title}")
                            success = True
                            break
                        else:
                            self.log(f"Warning (Attempt {attempt}): Retrying {safe_title}...")
                            time.sleep(2)
                    except Exception as e:
                        self.log(f"Error: {e}")
                
                if not success and not self.is_cancelled:
                    self.log(f"✗ FAILED: {safe_title}")

                self.current_process = None
                processed_count += 1
                self.progress_var.set((processed_count / total_items) * 100)

        if self.is_cancelled:
            self.status_var.set("Cancelled.")
            messagebox.showinfo("Status", "Download cancelled.")
        else:
            self.status_var.set("All Done.")
            self.log("Queue finished.")
            if self.var_open_folder.get():
                try: os.startfile(out_root)
                except: pass
            messagebox.showinfo("Status", "Downloads Complete!")

        self._reset_buttons()

    def _reset_buttons(self):
        self.is_downloading = False
        self.after(0, lambda: self.btn_download.config(state="normal"))
        self.after(0, lambda: self.btn_pause.config(state="disabled", text="PAUSE"))
        self.after(0, lambda: self.btn_cancel.config(state="disabled"))

    def open_help_window(self):
        help_win = tk.Toplevel(self)
        help_win.title("Help & Tutorial")
        help_win.geometry("800x600")

        notebook = ttk.Notebook(help_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Application Logic
        tab1 = tk.Frame(notebook, bg="white")
        notebook.add(tab1, text="App Guide")
        
        self._create_help_text(tab1, """
        WHOP DOWNLOADER - APPLICATION GUIDE
        
        1. Purpose:
           This application organizes and downloads videos from m3u8 stream links found in text documents.
           It uses 'FFmpeg' to stitch the stream segments into a single .mp4 file.
           
        2. How it works:
           - You load a text file containing lines of 'Title: URL'.
           - The app parses the file and attempts to categorize videos into folders based on keywords.
           - You can check the 'Structure' pane to drag-and-drop videos into different folders or rename them.
           - When you click 'Start', the app processes the queue one by one.
           
        3. Conversion Logic:
           - The app runs the command: 
             ffmpeg -i URL -c copy -bsf:a aac_adtstoasc output.mp4
           - "-c copy": This copies the video/audio streams directly without re-encoding. This is very fast and preserves original quality.
           - "-bsf:a": This fixes the audio stream format to be compatible with MP4 containers.
           
        4. Controls:
           - PAUSE: Pauses the queue. The current video will finish downloading, then the app waits.
           - CANCEL: Immediately kills the current download process and stops the queue.
        """)

        # Tab 2: How to get Links
        tab2 = tk.Frame(notebook, bg="white")
        notebook.add(tab2, text="How to Get Links")

        self._create_help_text(tab2, """
        HOW TO FIND M3U8 LINKS (The "Hacker" Method)
        
        To get the links for this tool, you need to grab the stream URL from your browser.
        
        1. Open Google Chrome (or Edge/Brave).
        2. Navigate to the video page you want to download.
        3. Press 'F12' on your keyboard to open the "Developer Tools".
        4. Click on the "Network" tab in the developer tools panel.
        5. In the "Filter" box (top left of Network tab), type: m3u8
        6. Refresh the webpage (F5).
        7. Press Play on the video.
        8. You should see a file appear in the Network list (often called 'playlist.m3u8' or similar).
        9. Right-click that file -> Copy -> Copy Link Address.
        
        FORMATTING YOUR TEXT FILE:
        Open Notepad and paste the link. Add a title above it.
        
        Example:
        
        My Awesome Video:
        https://stream.mux.com/.......m3u8?token=.....
        
        Another Video:
        https://stream.mux.com/.......
        """)

    def _create_help_text(self, parent, text_content):
        text = tk.Text(parent, wrap=tk.WORD, font=("Arial", 11), padx=20, pady=20, borderwidth=0)
        text.insert("1.0", text_content)
        text.config(state="disabled")
        text.pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = WhopDownloaderApp()
    app.mainloop()