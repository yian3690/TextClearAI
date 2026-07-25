<p align="center">
<img src="image/icon.png" width="150">
</p>

<div align="center">

# TextClear AI

**English | [繁體中文](README_zh-TW.md)**

</div>

### AI-Powered Image Text Enhancement Tool

TextClear AI is a lightweight desktop application designed to enhance blurry text in images using AI super-resolution technology. The project integrates the **Real-ESRGAN** deep learning model with **ONNX Runtime**, providing a fast, offline, and privacy-friendly image enhancement solution without requiring any cloud services.

---

## ✨ Features

- **Offline AI Processing**
  - Performs image enhancement entirely on your local machine using ONNX Runtime.
  - No internet connection or external API is required.

- **Text-Oriented Image Enhancement**
  - Uses the Real-ESRGAN model to reconstruct blurred text and improve image clarity.
  - Suitable for AI-generated images, screenshots, scanned documents, and low-resolution text.

- **Modern Desktop Interface**
  - Built with **FastAPI + PyWebView**, allowing modern HTML/CSS/JavaScript interfaces to run as a native desktop application.

- **Standalone Windows Executable**
  - Packaged with PyInstaller.
  - Users can simply download and run the application without installing Python.

- **Modular Project Architecture**
  - Front-end UI and AI inference are fully separated.
  - Easy to maintain, extend, or replace with other AI models.

---

## Demo

> *(You can add screenshots or GIFs here.)*

Example:

```
Before  →  After
Blurry Text  →  Clear Text
```

---

## Tech Stack

| Component | Technology |
|------------|------------|
| AI Model | Real-ESRGAN |
| Inference Engine | ONNX Runtime |
| Backend | FastAPI |
| Desktop Framework | PyWebView |
| Frontend | HTML / CSS / JavaScript |
| Packaging | PyInstaller |

---

## 📂 Project Structure

```text
TextClearAI/
├── main.py                      # FastAPI server & PyWebView launcher
├── weights/
│   ├── RealESRGAN_x4plus_fp32.onnx
│   └── RealESRGAN_x4plus_fp32.onnx.data
├── static/
│   ├── index.html
│   ├── css/
│   └── js/
├── image/
│   └── icon.ico
├── requirements.txt
├── .gitignore
└── README.md
```

---

# Getting Started

## Option 1 — Download the Executable

1. Visit the **Releases** page.
2. Download the latest **TextClearAI_vX.X.zip**.
3. Extract the ZIP file.
4. Double-click **TextClearAI.exe**.

No Python installation is required.

---

## Option 2 — Run from Source

### 1. Clone Repository

```bash
git clone https://github.com/yian3690/TextClearAI.git
cd TextClearAI
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Activate the environment (Windows):

```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Download Model Weights

Place the following files inside the **weights/** directory:

```
weights/
├── RealESRGAN_x4plus_fp32.onnx
└── RealESRGAN_x4plus_fp32.onnx.data
```

---

## Run the Application

```bash
python main.py
```

---

## Build Executable

```bash
pyinstaller ^
--name "TextClearAI" ^
--windowed ^
--icon="image/icon.ico" ^
--add-data "weights;weights" ^
--add-data "static;static" ^
--hidden-import uvicorn ^
--hidden-import fastapi ^
main.py
```

---

## Contributing

Contributions are welcome!

1. Fork this repository.
2. Create a new feature branch.

```bash
git checkout -b feature/your-feature
```

3. Commit your changes.

```bash
git commit -m "Add new feature"
```

4. Push to GitHub.

```bash
git push origin feature/your-feature
```

5. Open a Pull Request.

---

## Future Improvements

- OCR integration (PaddleOCR / EasyOCR)
- Drag-and-drop image upload
- Batch image processing
- GPU acceleration
- Additional super-resolution models
- Cross-platform support (Linux/macOS)

---

## License

This project is licensed under the **MIT License**.

The Real-ESRGAN model and pretrained weights are distributed under the licensing terms provided by their original authors.

---

