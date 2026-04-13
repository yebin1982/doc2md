import os
import sys
import subprocess
import re
from pathlib import Path
from markitdown import MarkItDown
import fitz  # PyMuPDF

# placeholder for API key
MISTRAL_API_KEY = "jWEJMU9hvvpMJCapEvXnGG3Y7sN3xhqx"

def strip_images(markdown_text):
    """
    Removes markdown image tags from the text.
    Pattern: ![alt text](url) or ![alt text][ref]
    """
    # Simple regex for markdown images
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
                return False
        return True
    except Exception as e:
        print(f"Error checking PDF {pdf_path}: {e}")
        return False

def convert_with_markitdown(file_path):
    """
    Converts a document to Markdown using MarkItDown.
    """
    try:
        md = MarkItDown()
        result = md.convert(str(file_path))
        content = result.text_content
        
        # Strip images as requested
        content = strip_images(content)
        
        output_path = file_path.with_suffix(".md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully converted (MarkItDown): {file_path} -> {output_path}")
    except Exception as e:
        print(f"Error converting {file_path} with MarkItDown: {e}")

def get_mistral_command():
    """
    Attempts to find the mistral-ocr-pdf command.
    """
    # 1. Try if it's in PATH
    try:
        subprocess.run(["mistral-ocr-pdf", "--version"], capture_output=True)
        return "mistral-ocr-pdf"
    except FileNotFoundError:
        pass
    
    # 2. Try looking in the Scripts folder relative to python executable
    scripts_dir = Path(sys.executable).parent / "Scripts"
    exe_path = scripts_dir / "mistral-ocr-pdf.exe"
    if exe_path.exists():
        return str(exe_path)
    
    # 3. Fallback to just hoping it works or letting the user fix PATH
    return "mistral-ocr-pdf"

from mistralai.client import Mistral

def needs_ocr(pdf_path):
    """
    Checks if a PDF is scanned (has no text layer).
    Returns True if no text is found in any page.
    """
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        for page in doc:
            if page.get_text().strip():
                return False
        return True
    except Exception as e:
        print(f"Error checking PDF {pdf_path}: {e}")
        return False

def convert_with_mistral_ocr(file_path):
    """
    Converts a scanned PDF to Markdown using Mistral OCR API directly.
    """
    try:
        if MISTRAL_API_KEY == "YOUR_MISTRAL_API_KEY_HERE" or not MISTRAL_API_KEY:
            print("Error: Mistral API Key is missing. Please set it in doc_converter.py.")
            return

        client = Mistral(api_key=MISTRAL_API_KEY)
        
        print(f"Uploading scanned file for OCR: {file_path}")
        with open(file_path, "rb") as f:
            uploaded_file = client.files.upload(
                file={"file_name": file_path.name, "content": f.read()},
                purpose="ocr"
            )
        
        signed_url = client.files.get_signed_url(file_id=uploaded_file.id)
        
        print(f"Processing OCR with Mistral for: {file_path}")
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url.url
            }
        )
        
        markdown_pages = [page.markdown for page in ocr_response.pages]
        content = "\n\n".join(markdown_pages)
        content = strip_images(content)
        
        output_path = file_path.with_suffix(".md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Successfully converted (Mistral OCR Native): {file_path} -> {output_path}")
        
    except Exception as e:
        print(f"Exception during Mistral OCR for {file_path}: {e}")

def process_directory(directory_path):
    """
    Recursively scans the directory and converts supported documents.
    """
    extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".txt", ".csv"}
    path = Path(directory_path)
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
    
    for file_path in path.rglob("*"):
        if file_path.is_dir():
            continue
            
        ext = file_path.suffix.lower()
        if ext in image_extensions:
            continue
            
        if ext in extensions:
            print(f"Processing: {file_path}")
            if ext == ".pdf":
                if needs_ocr(file_path):
                    print(f"Detected scanned PDF, using Mistral OCR...")
                    convert_with_mistral_ocr(file_path)
                else:
                    print(f"Detected text-based PDF, using MarkItDown...")
                    convert_with_markitdown(file_path)
            else:
                convert_with_markitdown(file_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python doc_converter.py <path_to_file_or_directory>")
        sys.exit(1)
    
    target_path = Path(sys.argv[1])
    if not target_path.exists():
        print(f"Error: {target_path} does not exist.")
        sys.exit(1)
        
    if target_path.is_file():
        ext = target_path.suffix.lower()
        print(f"Processing: {target_path}")
        if ext == ".pdf":
            if needs_ocr(target_path):
                convert_with_mistral_ocr(target_path)
            else:
                convert_with_markitdown(target_path)
        else:
            convert_with_markitdown(target_path)
    else:
        print(f"Starting directory conversion in: {target_path}")
        process_directory(target_path)
    
    print("All tasks completed.")
