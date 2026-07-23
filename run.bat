@echo off
chcp 65001 >nul
echo ========================================
echo   AI 文字影像清晰化工具 - 自動啟動腳本
echo ========================================

:: 檢查是否有安裝 Python 並加入系統變數
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python 執行檔！
    echo 1. 請確認你已經安裝了 Python。
    echo 2. 安裝時是否有勾選「Add Python to PATH」選項。
    pause
    exit /b
)

:: 1. 檢查並建立虛擬環境
if not exist ".venv\Scripts\activate" (
    echo [1/4] 第一次執行，正在為您建立獨立虛擬環境 (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [錯誤] 建立虛擬環境失敗！
        pause
        exit /b
    )
) else (
    echo [1/4] 虛擬環境已存在。
)

:: 2. 啟動虛擬環境
echo [2/4] 啟動虛擬環境...
call .venv\Scripts\activate

:: 3. 檢查並安裝必要套件
echo [3/4] 正在檢查與安裝相依套件 (首次執行可能需要幾分鐘)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [錯誤] 安裝套件時發生問題，請檢查 requirements.txt 或網路連線。
    pause
    exit /b
)

:: 4. 開啟網頁與伺服器
echo [4/4] 準備就緒！正在開啟瀏覽器與啟動 AI 伺服器...
echo ========================================
echo 提示：若要關閉系統，請在此視窗按下 Ctrl + C 兩次。
echo ========================================

:: 啟動應用程式
python main.py

:: 如果伺服器意外崩潰，讓視窗停住不要閃退
pause