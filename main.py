import io
import cv2
import torch
import numpy as np
import threading
import uvicorn
import webview
import multiprocessing

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import base64 # 在檔案最上方補上這行 import

# 引入 Real-ESRGAN 相關套件
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

app = FastAPI()

# ==========================================
# 初始化 Real-ESRGAN 模型
# ==========================================
model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"目前使用的運算設備為: {device}")

upsampler = RealESRGANer(
    scale=4, 
    model_path='weights/RealESRGAN_x4plus.pth', 
    dni_weight=None,
    model=model,
    tile=400, 
    tile_pad=10,
    pre_pad=0,
    half=True, 
    gpu_id=0 if torch.cuda.is_available() else None
)

# ==========================================
# API 路由設定
# ==========================================
@app.post("/enhance-text")
async def enhance_text(
    file: UploadFile = File(...),
    outscale: int = Form(2)
):
    try:
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return Response(content="無法讀取圖片", status_code=400)

        # ==========================================
        # 第一道防線：智慧預先縮圖 (防呆、防卡死)
        # ==========================================
        MAX_INPUT_SIZE = 2500  # 設定容許的最大邊長 (可依據你的顯卡效能微調)
        height, width = img.shape[:2]
        
        if max(height, width) > MAX_INPUT_SIZE:
            scale_ratio = MAX_INPUT_SIZE / max(height, width)
            new_width = int(width * scale_ratio)
            new_height = int(height * scale_ratio)
            # 使用 INTER_AREA 保留最佳縮圖畫質
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            print(f"⚠️ 圖片過大，已預先縮小至 {new_width}x{new_height}")
            
            # 更新長寬數值，交給下一階段判斷
            height, width = new_height, new_width

        # ==========================================
        # 第二道防線：動態評估 Tile 切塊策略 (榨乾效能)
        # ==========================================
        total_pixels = height * width

        # 策略 1：小圖 -> 直接整張算，速度起飛
        if total_pixels <= 800 * 800:
            upsampler.tile = 0
            print(f"🚀 進入 AI 運算 ({width}x{height})，策略：不切塊 (tile=0)")
            
        # 策略 2：中圖 -> 切大塊，平衡速度與記憶體
        elif total_pixels <= 1500 * 1500:
            upsampler.tile = 600
            print(f"⚖️ 進入 AI 運算 ({width}x{height})，策略：大塊運算 (tile=600)")
            
        # 策略 3：大圖 -> 最安全的切塊模式，防止崩潰
        else:
            upsampler.tile = 400
            print(f"🛡️ 進入 AI 運算 ({width}x{height})，策略：安全防護切塊 (tile=400)")


        # 進行超解析度處理
        output_img, _ = upsampler.enhance(img, outscale=outscale)

        is_success, buffer = cv2.imencode(".jpg", output_img)
        if not is_success:
            return Response(content="圖片轉換失敗", status_code=500)
            
        io_buf = io.BytesIO(buffer)
        return Response(content=io_buf.getvalue(), media_type="image/jpeg")
        
    except Exception as e:
        print(f"處理錯誤: {str(e)}")
        return Response(content=f"伺服器內部錯誤: {str(e)}", status_code=500)


# ==========================================
# 桌面視窗 (PyWebView) 與靜態檔案設定
# ==========================================
app.mount("/", StaticFiles(directory=".", html=True), name="static")

# ==========================================
# 【新增】JS 與 Python 的通訊橋樑
# ==========================================
class JS_API:
    def save_image(self, b64_data, default_filename):
        try:
            # 將前端傳來的 base64 圖片還原成二進位資料
            header, encoded = b64_data.split(",", 1)
            data = base64.b64decode(encoded)
            
            # 呼叫系統原生的「另存新檔」視窗
            file_types = ('JPEG Image (*.jpg)', 'All files (*.*)')
            # 注意這裡要用 global 變數 window
            result = window.create_file_dialog(
                webview.SAVE_DIALOG, 
                save_filename=default_filename, 
                file_types=file_types
            )
            
            # 如果使用者沒有按取消，就存檔
            if result:
                with open(result[0], 'wb') as f:
                    f.write(data)
                return True
            return False
        except Exception as e:
            print(f"存檔失敗: {e}")
            return False

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True 
    server_thread.start()

    # 初始化通訊 API
    api = JS_API()

    # 【修改】把 api 綁定到視窗上，並設定全域 window 變數
    global window
    window = webview.create_window(
        title="TextClear AI - 文字影像清晰化工具", 
        url="http://127.0.0.1:8000/index.html", 
        width=1000,
        height=800,
        min_size=(800, 600),
        js_api=api  # <--- 【關鍵】讓 JS 可以呼叫 Python
    )
    
    webview.start()