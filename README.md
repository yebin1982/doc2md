# Doc2MD Converter 📄➡️📝

[简体中文](README_CN.md) | English

A powerful, intelligent utility designed to convert various document formats into clean, image-free Markdown files. It intelligently distinguishes between text-based documents and scanned PDFs to ensure the highest quality conversion.

## ✨ Key Features

- **Intelligent OCR Detection**: Automatically detects if a PDF is scanned (image-only) and uses the high-performance **Mistral OCR API** for conversion.
- **Universal Format Support**: Converts `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.txt`, `.csv`, and even standalone images.
- **Clean Markdown**: Automatically strips all image tags (`![]()`) from the output for a focused, text-centric Markdown file.
- **Recursive Processing**: Process a single file or an entire directory (including subfolders) in one go.
- **GUI & CLI**: Comes with a modern graphical interface (built with CustomTkinter) and a streamlined command-line tool.

## 🚀 Getting Started

### Prerequisites

To run from source, you need Python 3.10+ and the following dependencies:

```bash
pip install markitdown mistralai pymupdf customtkinter
```

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yebin1982/scripts.git
   cd scripts
   ```
2. (Optional) Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

## 🛠️ Usage

### Graphical Interface (GUI)
Run the following command to start the modern GUI:
```bash
python gui_converter.py
```
- **Mistral API Key**: You will need a Mistral API key for scanned PDF/image OCR. Enter it in the settings sidebar.
- **Select Path**: Drag and drop or browse for a file/folder.
- **Start**: Watch the real-time logs as your files are converted.

### Command Line (CLI)
For quick batch processing:
```bash
python doc_converter.py <path_to_file_or_directory>
```
*Note: Ensure your Mistral API key is set in `doc_converter.py` or configured in your environment.*

### Portable Version (.exe)
If you are on Windows, you can download the standalone `Doc2MD_Converter.exe` from the **[GitHub Releases](https://github.com/yebin1982/scripts/releases)** page. No Python installation required!

## ⚙️ Configuration

The tool saves your API key and settings in a local `config.json` file. This file is automatically excluded from Git to protect your sensitive information.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
