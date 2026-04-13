import os
import sys
import json
import threading
import re
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from markitdown import MarkItDown
from mistralai.client import Mistral
import fitz  # PyMuPDF

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

# Core Logic Classes (Integrated)
class ConverterLogic:
    def __init__(self, api_key, log_callback):
        self.api_key = api_key
        self.log_callback = log_callback
        self.stop_requested = False

    def log(self, message):
        self.log_callback(message)

    def strip_images(self, markdown_text):
        pattern = r'!\[.*?\]\(.*?\)'
        return re.sub(pattern, '', markdown_text)

    def needs_ocr(self, pdf_path):
        try:
            doc = fitz.open(str(pdf_path))
            for page in doc:
                if page.get_text().strip():
                    return False
            return True
        except Exception as e:
            self.log(f"Error checking PDF {pdf_path}: {e}")
            return False

    def convert_with_markitdown(self, file_path):
        try:
            md = MarkItDown()
            result = md.convert(str(file_path))
            content = self.strip_images(result.text_content)
            output_path = file_path.with_suffix(".md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"✅ Converted (MarkItDown): {file_path.name}")
        except Exception as e:
            self.log(f"❌ Error converting {file_path.name}: {e}")

    def convert_with_mistral_ocr(self, file_path):
        try:
            if not self.api_key:
                self.log("❌ Error: Mistral API Key is missing.")
                return

            client = Mistral(api_key=self.api_key)
            self.log(f"☁️ Uploading for OCR: {file_path.name}")
            
            with open(file_path, "rb") as f:
                uploaded_file = client.files.upload(
                    file={"file_name": file_path.name, "content": f.read()},
                    purpose="ocr"
                )
            
            signed_url = client.files.get_signed_url(file_id=uploaded_file.id)
            self.log(f"⏳ Processing OCR: {file_path.name}")
            
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "document_url", "document_url": signed_url.url}
            )
            
            content = "\n\n".join([page.markdown for page in ocr_response.pages])
            content = self.strip_images(content)
            
            output_path = file_path.with_suffix(".md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"✅ Converted (Mistral OCR): {file_path.name}")
            
        except Exception as e:
            self.log(f"❌ Exception during Mistral OCR for {file_path.name}: {e}")

    def process_item(self, target_path):
        if target_path.is_file():
            self._process_single_file(target_path)
        else:
            self._process_directory(target_path)

    def _process_single_file(self, file_path):
        ext = file_path.suffix.lower()
        # Documentation & PDF
        if ext == ".pdf":
            if self.needs_ocr(file_path):
                self.convert_with_mistral_ocr(file_path)
            else:
                self.convert_with_markitdown(file_path)
        # Standalone Images (using Mistral OCR)
        elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}:
            self.log(f"🖼️ Detected image file, using Mistral OCR...")
            self.convert_with_mistral_ocr(file_path)
        # Office, Data, Web, etc.
        elif ext in {
            ".docx", ".pptx", ".xlsx", ".html", ".htm", 
            ".txt", ".csv", ".tsv", ".json", ".xml", ".log"
        }:
            self.convert_with_markitdown(file_path)

    def _process_directory(self, directory_path):
        # Combined set of all supported document/image extensions
        supported_extensions = {
            ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm",
            ".txt", ".csv", ".tsv", ".json", ".xml", ".log",
            ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"
        }
        
        for file_path in Path(directory_path).rglob("*"):
            if self.stop_requested: break
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in supported_extensions:
                    self._process_single_file(file_path)

# GUI Application
class DocConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        
        self.title("Doc2MD Portable Converter")
        self.geometry("800x600")
        
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

        self.header = ctk.CTkLabel(self.main_frame, text="Document to Markdown Converter", font=ctk.CTkFont(size=24, weight="bold"))
        self.header.grid(row=0, column=0, pady=20)

        # Selection
        self.selection_frame = ctk.CTkFrame(self.main_frame)
        self.selection_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.selection_frame.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(self.selection_frame, placeholder_text="Select a file or directory...")
        self.path_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.btn_file = ctk.CTkButton(self.selection_frame, text="Browse File", width=100, command=self.browse_file)
        self.btn_file.grid(row=0, column=1, padx=5, pady=10)

        self.btn_dir = ctk.CTkButton(self.selection_frame, text="Browse Folder", width=100, command=self.browse_folder)
        self.btn_dir.grid(row=0, column=2, padx=5, pady=10)

        # Actions
        self.start_btn = ctk.CTkButton(self.main_frame, text="Start Conversion", height=40, font=ctk.CTkFont(weight="bold"), command=self.start_conversion)
        self.start_btn.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        # Terminal Log
        self.log_text = ctk.CTkTextbox(self.main_frame, height=300)
        self.log_text.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(3, weight=1)

    def save_settings_ui(self):
        self.settings["api_key"] = self.api_key_entry.get()
        save_settings(self.settings)
        messagebox.showinfo("Success", "Settings saved successfully!")

    def browse_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, filename)

    def browse_folder(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, dirname)

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def start_conversion(self):
        path = self.path_entry.get()
        api_key = self.api_key_entry.get()
        
        if not path:
            messagebox.showerror("Error", "Please select a file or folder.")
            return
        
        self.log_text.delete("1.0", tk.END)
        self.log("🚀 Starting process...")
        
        thr = threading.Thread(target=self.run_conversion_thread, args=(path, api_key))
        thr.start()

    def run_conversion_thread(self, path, api_key):
        self.start_btn.configure(state="disabled")
        try:
            logic = ConverterLogic(api_key, self.log)
            logic.process_item(Path(path))
            self.log("✨ Done!")
        except Exception as e:
            self.log(f"💥 Critical Error: {e}")
        finally:
            self.start_btn.configure(state="normal")

if __name__ == "__main__":
    app = DocConverterApp()
    # If icon exists, set it
    if os.path.exists("app_icon.ico"):
        try:
            app.iconbitmap("app_icon.ico")
        except:
            pass
    app.mainloop()
