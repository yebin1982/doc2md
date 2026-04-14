import os
import sys
import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from task_manager import TaskManager, TaskStatus

# Settings persistence
CONFIG_FILE = "config.json"

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"api_key": ""}

def save_settings(settings):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

# UI Components for the task list
class TaskRow(ctk.CTkFrame):
    def __init__(self, master, task, on_stop, on_retry):
        super().__init__(master, fg_color="transparent")
        self.task = task
        self.on_stop = on_stop
        self.on_retry = on_retry
        
        self.grid_columnconfigure(0, weight=1)
        
        # Icon/Status
        self.status_label = ctk.CTkLabel(self, text=self._get_status_icon(), width=30)
        self.status_label.grid(row=0, column=0, sticky="w", padx=(5, 10))
        
        # Filename
        name = self.task.file_path.name
        if len(name) > 40:
            name = name[:37] + "..."
        self.name_label = ctk.CTkLabel(self, text=name, anchor="w")
        self.name_label.grid(row=0, column=1, sticky="w", padx=5)
        
        # Action Button
        self.action_btn = ctk.CTkButton(self, text="", width=60, height=24)
        self.action_btn.grid(row=0, column=2, padx=10)
        
        self.update_ui()

    def _get_status_icon(self):
        icons = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.SUCCESS: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.STOPPED: "⏹️",
            TaskStatus.TIMEOUT: "⏰"
        }
        return icons.get(self.task.status, "?")

    def update_ui(self):
        self.status_label.configure(text=self._get_status_icon())
        
        if self.task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            self.action_btn.configure(text="Stop", fg_color="#E74C3C", hover_color="#C0392B", command=lambda: self.on_stop(self.task.id))
            self.action_btn.grid()
        elif self.task.status in [TaskStatus.FAILED, TaskStatus.STOPPED, TaskStatus.TIMEOUT]:
            self.action_btn.configure(text="Retry", fg_color="#2ECC71", hover_color="#27AE60", command=lambda: self.on_retry(self.task.id))
            self.action_btn.grid()
        else:
            self.action_btn.grid_remove() # Hide for SUCCESS

# GUI Application
class DocConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        self.task_manager = TaskManager(update_callback=self.refresh_task_list)
        self.row_widgets = {} # task_id -> TaskRow
        
        self.title("Doc2MD Portable Converter")
        self.geometry("900x700")
        
        # Appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="Doc2MD Settings", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.api_key_label = ctk.CTkLabel(self.sidebar, text="Mistral API Key:")
        self.api_key_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.api_key_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Enter API Key...", show="*")
        self.api_key_entry.insert(0, self.settings.get("api_key", ""))
        self.api_key_entry.grid(row=2, column=0, padx=20, pady=(0, 20))

        self.save_btn = ctk.CTkButton(self.sidebar, text="Save Settings", command=self.save_settings_ui)
        self.save_btn.grid(row=3, column=0, padx=20, pady=10)

        # Main Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        self.header = ctk.CTkLabel(self.main_frame, text="Document to Markdown Converter", font=ctk.CTkFont(size=24, weight="bold"))
        self.header.grid(row=0, column=0, pady=(10, 20))

        # Selection
        self.selection_frame = ctk.CTkFrame(self.main_frame)
        self.selection_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_file = ctk.CTkButton(self.selection_frame, text="Add Files", width=120, command=self.browse_file)
        self.btn_file.pack(side="left", padx=10, pady=10)

        self.btn_dir = ctk.CTkButton(self.selection_frame, text="Add Folder", width=120, command=self.browse_folder)
        self.btn_dir.pack(side="left", padx=10, pady=10)

        # ====== ADD PROGRESS BARS HERE ======
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.import_status_label = ctk.CTkLabel(self.progress_frame, text="Ready", anchor="w")
        self.import_status_label.pack(fill="x", pady=(0, 2))
        
        self.import_progress = ctk.CTkProgressBar(self.progress_frame, mode="indeterminate", height=10)
        self.import_progress.pack(fill="x", pady=(0, 10))
        self.import_progress.set(0)
        
        self.process_status_label = ctk.CTkLabel(self.progress_frame, text="Processing: 0/0 (0%)", anchor="w")
        self.process_status_label.pack(fill="x", pady=(0, 2))
        
        self.process_progress = ctk.CTkProgressBar(self.progress_frame, mode="determinate", height=10)
        self.process_progress.pack(fill="x", pady=(0, 5))
        self.process_progress.set(0)
        # ====================================

        # Task List
        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Conversion Queue")
        self.scrollable_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(3, weight=1)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Bulk Actions
        self.actions_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.actions_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        self.retry_all_btn = ctk.CTkButton(self.actions_frame, text="Retry All Failed", command=self.task_manager.retry_all_failed, fg_color="#34495E")
        self.retry_all_btn.pack(side="left", padx=10)
        
        self.stop_all_btn = ctk.CTkButton(self.actions_frame, text="Stop All Tasks", command=self.task_manager.stop_all, fg_color="#C0392B")
        self.stop_all_btn.pack(side="right", padx=10)

        self.clear_all_btn = ctk.CTkButton(self.actions_frame, text="Clear List", command=self.clear_task_list, fg_color="#8E44AD", hover_color="#9B59B6")
        self.clear_all_btn.pack(side="right", padx=10)

    def clear_task_list(self):
        self.task_manager.clear_all()
        # Force UI refresh to ensure rows are removed
        self._refresh_ui()

    def save_settings_ui(self):
        self.settings["api_key"] = self.api_key_entry.get()
        save_settings(self.settings)
        messagebox.showinfo("Success", "Settings saved successfully!")

    def browse_file(self):
        filenames = filedialog.askopenfilenames()
        if filenames:
            api_key = self.api_key_entry.get()
            for f in filenames:
                self.task_manager.add_task(f, api_key)

    def browse_folder(self):
        dirname = filedialog.askdirectory()
        if dirname:
            api_key = self.api_key_entry.get()
            self.import_status_label.configure(text=f"Scanning directory: {Path(dirname).name}...")
            self.import_progress.start()
            self.btn_file.configure(state="disabled")
            self.btn_dir.configure(state="disabled")
            
            threading.Thread(target=self._scan_folder_thread, args=(dirname, api_key), daemon=True).start()

    def _scan_folder_thread(self, dirname, api_key):
        supported_extensions = {
            ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm",
            ".txt", ".csv", ".tsv", ".json", ".xml", ".log",
            ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"
        }
        
        count = 0
        for f_path in Path(dirname).rglob("*"):
            if f_path.is_file() and f_path.suffix.lower() in supported_extensions:
                self.task_manager.add_task(f_path, api_key, import_root=dirname)
                count += 1
                if count % 100 == 0:
                    self.after(0, lambda c=count: self.import_status_label.configure(text=f"Imported {c} files so far..."))
        
        self.after(0, lambda c=count: self._scan_folder_complete(c))

    def _scan_folder_complete(self, count):
        self.import_progress.stop()
        self.import_progress.set(0)
        self.import_status_label.configure(text=f"Ready. Imported {count} files.")
        self.btn_file.configure(state="normal")
        self.btn_dir.configure(state="normal")

    def refresh_task_list(self):
        # This is called from background thread, so use after()
        self.after(0, self._refresh_ui)

    def _refresh_ui(self):
        # Update progress bars safely
        total = self.task_manager.total_files
        processed = self.task_manager.processed_files
        success = self.task_manager.success_files
        failed = self.task_manager.failed_files
        
        if total > 0:
            percentage = (processed / total) * 100
            self.process_status_label.configure(text=f"Processing: {processed}/{total} ({percentage:.1f}%) | Success: {success} | Failed: {failed}")
            self.process_progress.set(processed / total)
        else:
            self.process_status_label.configure(text="Processing: 0/0 (0%)")
            self.process_progress.set(0)

        # Determine which tasks to render (max 50 to prevent UI locking)
        visible_tasks = []
        for t in self.task_manager.tasks:
            # Always show failed, running, stopped, timeout
            if t.status in [TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.TIMEOUT, TaskStatus.STOPPED]:
                visible_tasks.append(t)
            # Show some pending tasks up to limit
            elif t.status == TaskStatus.PENDING and len(visible_tasks) < 50:
                visible_tasks.append(t)
                
            if len(visible_tasks) >= 50:
                break

        # Sync widgets
        existing_ids = set(self.row_widgets.keys())
        current_ids = {t.id for t in visible_tasks}
        
        # Remove old widgets
        for tid in existing_ids - current_ids:
            self.row_widgets[tid].destroy()
            del self.row_widgets[tid]
            
        # Add or update widgets
        for i, task in enumerate(visible_tasks):
            if task.id not in self.row_widgets:
                row = TaskRow(self.scrollable_frame, task, self.task_manager.stop_task, self.task_manager.retry_task)
                row.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
                self.row_widgets[task.id] = row
            else:
                self.row_widgets[task.id].update_ui()
                self.row_widgets[task.id].grid(row=i, column=0, padx=5, pady=2, sticky="ew")

if __name__ == "__main__":
    app = DocConverterApp()
    # If icon exists, set it
    if os.path.exists("app_icon.ico"):
        try:
            app.iconbitmap("app_icon.ico")
        except:
            pass
    app.mainloop()
