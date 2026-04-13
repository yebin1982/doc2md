# Doc2MD 转换器 📄➡️📝

简体中文 | [English](README.md)

这是一个强大且智能的工具，旨在将各种文档格式转换为干净、无图片的 Markdown 文件。它能智能区分文本型 PDF 和扫描版 PDF，确保最高的转换质量。

## ✨ 核心功能

- **智能 OCR 检测**: 自动检测 PDF 是否为扫描版（纯图片），并调用高性能的 **Mistral OCR API** 进行转换。
- **全格式支持**: 支持 `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.txt`, `.csv` 以及单张图片。
- **纯净 Markdown**: 自动从输出中剔除所有图片标签 (`![]()`)，为您提供排版精良的纯文本 Markdown。
- **递归处理**: 支持处理单个文件或整个目录（包括所有子文件夹）。
- **图形界面 (GUI) 与 命令行 (CLI)**: 提供基于 CustomTkinter 的现代图形界面，同时也支持高效的命令行操作。

## 🚀 快速入门

### 前提条件

若要从源码运行，您需要 Python 3.10+ 以及以下依赖库：

```bash
pip install markitdown mistralai pymupdf customtkinter
```

### 安装步骤

1. 克隆此仓库：
   ```bash
   git clone https://github.com/yebin1982/scripts.git
   cd scripts
   ```
2. (可选) 设置虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows 用户: venv\Scripts\activate
   ```

## 🛠️ 使用说明

### 图形界面 (GUI)
运行以下命令启动现代化的图形界面：
```bash
python gui_converter.py
```
- **Mistral API Key**: 转换扫描版 PDF 或图片需要 Mistral API Key。请在侧面设置栏中输入。
- **选择路径**: 支持拖拽或浏览选择文件/文件夹。
- **开始转换**: 实时查看转换日志。

### 命令行 (CLI)
适用于快速批量处理：
```bash
python doc_converter.py <文件或目录路径>
```
*注意：请确保在 `doc_converter.py` 中设置了 Mistral API Key 或已配置相关环境变量。*

### 便携版 (.exe)
如果您是 Windows 用户，可以直接从 **[GitHub Releases](https://github.com/yebin1982/scripts/releases)** 页面下载独立运行的 `Doc2MD_Converter.exe`，无需安装 Python 环境！

## ⚙️ 配置文件

工具会将您的 API Key 和设置保存在本地的 `config.json` 文件中。该文件已自动加入 Git 忽略列表，以确保您的敏感信息安全。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。
