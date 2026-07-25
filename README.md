# TextClear AI - Image Text Clarification Tool 🔍
*(Scroll down for the Traditional Chinese version / 向下捲動查看中文版本)*

TextClear AI is a desktop application developed using Python and front-end web technologies. This project integrates the **Real-ESRGAN** deep learning model, specifically designed to restore blurry images and reconstruct text structures, providing users with an intuitive, offline, and local AI image upscaling experience.

## ✨ Key Features

*   **Local AI Processing**: Utilizes ONNX Runtime to load the Real-ESRGAN model without relying on external APIs, ensuring strict data privacy.
*   **Intuitive User Interface**: Combines FastAPI with PyWebView to transform modern front-end web designs (HTML/CSS/JS) into a seamless desktop window experience.
*   **Standalone Executable**: Provides a `.exe` version bundled via PyInstaller for Windows. General users can simply extract and run it without complex installations.
*   **Modular Architecture**: Fully separates front-end static resources from back-end AI inference logic, making future development and model swapping straightforward.

## 📂 Project Directory Structure

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
└── .gitignore               # Git ignore list
```

## 🚀 For General Users (No Installation Required)
Go to the Releases page.

Download the latest version of the TextClearAI_v1.x.zip archive.

Extract the archive to any folder of your choice.

Double-click TextClearAI.exe to launch the application.
## 💻 For Developers (Run and Build from Source)
1. Environment Setup

```bash
git clone https://github.com/yian3690/TextClearAI.git
cd TextClearAI
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies 
pip install -r requirements.txt
```
2. Download Model Weights
Ensure your weights folder contains the following two files for the program to run correctly:

RealESRGAN_x4plus_fp32.onnx

RealESRGAN_x4plus_fp32.onnx.data
3. Local Development Run

```bash
python main.py
```

4. PyInstaller Packaging
```bash
pyinstaller --name "TextClearAI" --windowed --icon="image/icon.ico" --add-data "weights;weights" --add-data "static;static" --hidden-import uvicorn --hidden-import fastapi main.py
```
## 🛠️ Development & Contributing
Fork the Project.

Create your Feature Branch (git checkout -b feature/AmazingFeature).

Commit your Changes (git commit -m "Add some AmazingFeature").

Push to the Branch (git push origin feature/AmazingFeature).

Open a Pull Request.
## 📝 License
This project is licensed under the MIT License. The Real-ESRGAN model weights used follow the open-source specifications of their original authors.
