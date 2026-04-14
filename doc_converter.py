import os
import sys
import subprocess
import re
import shutil
import time
import threading
from pathlib import Path
from markitdown import MarkItDown
from mistralai.client import Mistral
import fitz  # PyMuPDF

# placeholder for API key
MISTRAL_API_KEY = "jWEJMU9hvvpMJCapEvXnGG3Y7sN3xhqx"

def strip_images(markdown_text):
    """
    Removes markdown image tags from the text.
    Pattern: ![alt text](url) or ![alt text][ref]
    """
    pattern = r'!\[.*?\]\(.*?\)'
    return re.sub(pattern, '', markdown_text)

def needs_ocr(pdf_path):
    """
    Checks if a PDF is scanned (has no text layer).
    Returns True if no text is found in any page.
    """
    try:
        doc = fitz.open(str(pdf_path))
        for page in doc:
            if page.get_text().strip():
                doc.close()
                return False
        doc.close()
        return True
    except Exception as e:
        print(f"Error checking PDF {pdf_path}: {e}")
        return False

def get_timeout_for_file(file_path):
    """
    Calculates timeout based on file size.
    Base 60s + 60s per MB.
    """
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return 60 + int(size_mb * 60)
    except:
        return 300 # Default 5 mins

def convert_with_markitdown(file_path, stop_event=None, timeout=None):
    """
    Converts a document to Markdown using MarkItDown.
    """
    output_path = file_path.with_suffix(".md")
    try:
        # MarkItDown doesn't have a direct 'stop' but we can check before/after
        if stop_event and stop_event.is_set():
            return False, "Stopped"

        md = MarkItDown()
        # MarkItDown.convert is blocking. We rely on the thread management to handle timeouts if needed,
        # but here we can try to pass a timeout if the library supports it for network calls.
        result = md.convert(str(file_path))
        content = result.text_content
        
        if stop_event and stop_event.is_set():
            if output_path.exists():
                os.remove(output_path)
            return False, "Stopped"

        # Strip images as requested
        content = strip_images(content)
        
        # Overwrite is default here since we open in "w" mode
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True, str(output_path)
    except Exception as e:
        if output_path.exists():
            try: os.remove(output_path)
            except: pass
        return False, str(e)

def convert_with_mistral_ocr(file_path, api_key=MISTRAL_API_KEY, stop_event=None):
    """
    Converts a scanned PDF to Markdown using Mistral OCR API directly.
    """
    output_path = file_path.with_suffix(".md")
    try:
        if not api_key or api_key == "YOUR_MISTRAL_API_KEY_HERE":
            return False, "Mistral API Key is missing."

        if stop_event and stop_event.is_set():
            return False, "Stopped"

        client = Mistral(api_key=api_key)
        
        # Uploading
        with open(file_path, "rb") as f:
            uploaded_file = client.files.upload(
                file={"file_name": file_path.name, "content": f.read()},
                purpose="ocr"
            )
        
        if stop_event and stop_event.is_set():
            return False, "Stopped"

        signed_url = client.files.get_signed_url(file_id=uploaded_file.id)
        
        # OCR processing
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url.url
            }
        )
        
        if stop_event and stop_event.is_set():
            return False, "Stopped"

        markdown_pages = [page.markdown for page in ocr_response.pages]
        content = "\n\n".join(markdown_pages)
        content = strip_images(content)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return True, str(output_path)
        
    except Exception as e:
        if output_path.exists():
            try: os.remove(output_path)
            except: pass
        return False, str(e)

def handle_failure(file_path, base_dir=None):
    """
    Moves failed file to a 'failed' directory under base_dir (or parent).
    """
    try:
        base_dir = Path(base_dir) if base_dir else file_path.parent
        failed_dir = base_dir / "failed"
        
        if base_dir in file_path.parents:
            rel_path = file_path.relative_to(base_dir)
        else:
            rel_path = file_path.name
            
        dest_path = failed_dir / rel_path
        
        # Avoid moving same file
        if dest_path.resolve() == file_path.resolve():
            return True

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(dest_path))
        return True
    except Exception as e:
        print(f"Failed to move to failed directory: {e}")
        return False

def handle_success(file_path, base_dir=None):
    """
    Moves successful file to a 'succeeded' directory, preserving structure.
    """
    try:
        base_dir = Path(base_dir) if base_dir else file_path.parent
        suc_dir = base_dir / "succeeded"
        
        if base_dir in file_path.parents:
            rel_path = file_path.relative_to(base_dir)
        else:
            rel_path = file_path.name
            
        dest_path = suc_dir / rel_path
        
        if dest_path.resolve() == file_path.resolve():
            return True

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), str(dest_path))
        return True
    except Exception as e:
        print(f"Failed to move to succeeded directory: {e}")
        return False

def process_file_logic(file_path, api_key=MISTRAL_API_KEY, stop_event=None):
    """
    Individual file processing logic used by GUI and CLI.
    """
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        if needs_ocr(file_path):
            return convert_with_mistral_ocr(file_path, api_key, stop_event)
        else:
            return convert_with_markitdown(file_path, stop_event)
    elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}:
        return convert_with_mistral_ocr(file_path, api_key, stop_event)
    else:
        return convert_with_markitdown(file_path, stop_event)

def process_directory(directory_path, api_key=MISTRAL_API_KEY):
    """
    Recursively scans the directory and converts supported documents (CLI version).
    """
    extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".txt", ".csv", ".png", ".jpg", ".jpeg"}
    path = Path(directory_path)
    
    for file_path in path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            print(f"Processing: {file_path}")
            success, msg = process_file_logic(file_path, api_key)
            if success:
                print(f"✅ Success: {msg}")
                handle_success(file_path, base_dir=path)
            else:
                print(f"❌ Failed: {msg}")
                handle_failure(file_path, base_dir=path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python doc_converter.py <path_to_file_or_directory>")
        sys.exit(1)
    
    target_path = Path(sys.argv[1])
    if not target_path.exists():
        print(f"Error: {target_path} does not exist.")
        sys.exit(1)
        
    if target_path.is_file():
        success, msg = process_file_logic(target_path)
        if success:
            handle_success(target_path, base_dir=target_path.parent)
        else:
            handle_failure(target_path, base_dir=target_path.parent)
    else:
        process_directory(target_path)
