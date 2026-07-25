# TextClear AI - Image Text Clarification Tool 🔍

TextClear AI is a desktop application developed using Python and front-end web technologies. This project integrates the **Real-ESRGAN** deep learning model, specifically designed to restore blurry images and reconstruct text structures, providing users with an intuitive, offline, and local AI image upscaling experience.

## ✨ Key Features

*   **Local AI Processing**: Utilizes ONNX Runtime to load the Real-ESRGAN model without relying on external APIs, ensuring strict data privacy.
*   **Intuitive User Interface**: Combines FastAPI with PyWebView to transform modern front-end web designs (HTML/CSS/JS) into a seamless desktop window experience.
*   **Standalone Executable**: Provides a `.exe` version bundled via PyInstaller for Windows. General users can simply extract and run it without complex installations.
*   **Modular Architecture**: Fully separates front-end static resources from back-end AI inference logic, making future development and model swapping straightforward.

## 📂 Project Directory Structure

This project adopts the following structure for development and packaging:

```text
TextClearAI/
├── main.py                  # Main program (FastAPI routing & PyWebView window logic)
├── weights/                 # AI model weights folder
│   ├── RealESRGAN_x4plus_fp32.onnx        # Model structural blueprint
│   └── RealESRGAN_x4plus_fp32.onnx.data   # Model weight values (large file)
├── static/                  # Front-end web resources
│   ├── index.html           # Main application interface
│   ├── css/                 # Stylesheets
│   └── js/                  # Front-end interactive logic
├── image/                   # UI and application icons
│   └── icon.ico             # Custom software icon
└── .gitignore               # Git ignore list (prevents uploading huge models & cache)

🚀 For General Users (No Installation Required)
If you just want to use this software to restore images and do not need to modify the code, please follow these steps:

Go to the Releases page of this project.

Download the latest version of the TextClearAI_v1.x.zip archive.

Extract the archive to any folder of your choice.

Double-click TextClearAI.exe to launch the application.

💻 For Developers (Run and Build from Source)
If you wish to contribute to the development, swap out AI models, or modify the interface, please refer to the instructions below.

1. Environment Setup
Please ensure you have Python 3.8+ installed, and create a virtual environment:
If you wish to contribute to the development, swap out AI models, or modify the interface, please refer to the instructions below.

1. Environment Setup
Please ensure you have Python 3.8+ installed, and create a virtual environment:
git clone [https://github.com/yian3690/TextClearAI.git](https://github.com/yian3690/TextClearAI.git)
cd TextClearAI
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies 
# (Ensure you have a requirements.txt, or manually install fastapi, uvicorn, pywebview, onnxruntime, etc.)
pip install -r requirements.txt
