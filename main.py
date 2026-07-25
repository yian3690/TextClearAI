import io
import cv2
import numpy as np
import threading
import uvicorn
import webview
import multiprocessing
import base64
import onnxruntime as ort
import sys
import os

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles


app = FastAPI()

# ==========================================
# 萬能路徑解析函式 (避免 PyInstaller 找不到檔案)
# ==========================================
def resource_path(relative_path):
    """ 取得資源的絕對路徑，無論是開發環境還是打包後的 EXE 都通用 """
    if getattr(sys, 'frozen', False):
        # 如果是被 PyInstaller 打包執行的狀態
        base_path = sys._MEIPASS
    else:
        # 如果是在一般開發環境 (python main.py) 執行的狀態
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


# ==========================================
# 初始化 ONNX Runtime 引擎
# ==========================================
print("啟動 ONNX 引擎中...")

# 使用通用 GPU 加速 (DirectML)，若不支援則退回 CPU
providers = ['DmlExecutionProvider', 'CPUExecutionProvider']

# 務必套用萬能路徑，這樣打包成 exe 才會找得到模型！
model_path = resource_path(os.path.join('weights', 'RealESRGAN_x4plus_fp32.onnx'))

session = ort.InferenceSession(model_path, providers=providers)
input_name = session.get_inputs()[0].name

# ==========================================
# API 路由設定
# ==========================================
@app.post("/enhance-text")
async def enhance_text(
    file: UploadFile = File(...),
    outscale: int = Form(2)  # 接收使用者指定的放大倍率
):
    try:
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return Response(content="無法讀取圖片", status_code=400)

        # ==========================================
        # 1. 第一道防線：智慧預先縮圖 (防呆)
        # ==========================================
        MAX_INPUT_SIZE = 2500  
        height, width = img.shape[:2]
        
        if max(height, width) > MAX_INPUT_SIZE:
            scale_ratio = MAX_INPUT_SIZE / max(height, width)
            new_width = int(width * scale_ratio)
            new_height = int(height * scale_ratio)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            height, width = new_height, new_width
            print(f"圖片過大，已預先縮小至 {new_width}x{new_height}")

        # ==========================================
        # 輔助函式：GPU 尺寸對齊防護 + 完整 BGR 封裝
        # ==========================================
        def run_onnx_inference(input_img):
            h, w = input_img.shape[:2]
            
            # 32 倍數對齊防護 (防止 GPU 吐出 NaN 導致黑圖)
            pad_h = (32 - (h % 32)) % 32
            pad_w = (32 - (w % 32)) % 32
            
            # 如果需要補齊，使用邊界反射向右下角擴充
            if pad_h > 0 or pad_w > 0:
                input_img = cv2.copyMakeBorder(input_img, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101)

            # 前處理：BGR 轉 RGB 交給模型
            img_rgb = cv2.cvtColor(input_img, cv2.COLOR_BGR2RGB)
            img_float = img_rgb.astype(np.float32) / 255.0
            img_chw = np.transpose(img_float, (2, 0, 1))
            input_tensor = np.expand_dims(img_chw, axis=0)

            # ONNX 推理
            ort_inputs = {input_name: input_tensor}
            ort_outs = session.run(None, ort_inputs)
            
            # 後處理
            out = np.squeeze(ort_outs[0], axis=0)
            out = np.transpose(out, (1, 2, 0))
            out = np.nan_to_num(out)
            out = np.clip(out, 0, 1)
            out = (out * 255).round().astype(np.uint8)
            
            # 直接轉回 BGR
            out = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)

            # 裁切掉為了對齊而多出來的邊緣 (模型放大 4 倍，所以裁切量也要 * 4)
            if pad_h > 0 or pad_w > 0:
                out = out[0 : h * 4, 0 : w * 4]
                
            return out

        # ==========================================
        # 2. 第二道防線：動態 Tile 評估策略 (極簡乾淨呼叫)
        # ==========================================
        total_pixels = height * width
        SCALE = 4

        # 🚀 策略 1：下調至 10 萬像素 (因為 FP32 記憶體消耗翻倍)
        if total_pixels <= 100000:
            print(f"進入 AI 運算 ({width}x{height})，策略：整張直出 (tile=0)")
            output_img = run_onnx_inference(img)

        # 🛡️ 策略 2：改用對 GPU 記憶體極度友善的微型切塊
        else:
            TILE_SIZE = 192  # 192 是 32 的倍數
            TILE_PAD = 16    # 192 + 16 + 16 = 224 (完美契合 GPU 矩陣對齊)
            print(f"進入 AI 運算 ({width}x{height})，策略：微型反射切塊 (tile={TILE_SIZE})")

            out_h, out_w = height * SCALE, width * SCALE
            output_img = np.zeros((out_h, out_w, 3), dtype=np.uint8)

            for y in range(0, height, TILE_SIZE):
                for x in range(0, width, TILE_SIZE):
                    y_end = min(y + TILE_SIZE, height)
                    x_end = min(x + TILE_SIZE, width)

                    # 邊界反射填充
                    pad_top = TILE_PAD if y > 0 else 0
                    pad_bottom = TILE_PAD if y_end < height else 0
                    pad_left = TILE_PAD if x > 0 else 0
                    pad_right = TILE_PAD if x_end < width else 0

                    crop_y1 = y - pad_top
                    crop_y2 = y_end + pad_bottom
                    crop_x1 = x - pad_left
                    crop_x2 = x_end + pad_right

                    tile = img[crop_y1:crop_y2, crop_x1:crop_x2]

                    # OpenCV 反射延伸
                    tile_padded = cv2.copyMakeBorder(
                        tile, 
                        TILE_PAD - pad_top, TILE_PAD - pad_bottom, 
                        TILE_PAD - pad_left, TILE_PAD - pad_right, 
                        cv2.BORDER_REFLECT_101
                    )

                    # 執行 ONNX 推理 (內部已封裝 BGR 轉換與 32 對齊)
                    out_tile = run_onnx_inference(tile_padded)

                    # 裁切 Padding 區域
                    out_tile_valid = out_tile[
                        TILE_PAD * SCALE : (TILE_PAD + (y_end - y)) * SCALE,
                        TILE_PAD * SCALE : (TILE_PAD + (x_end - x)) * SCALE
                    ]

                    # 貼回主畫布
                    output_img[y*SCALE : y_end*SCALE, x*SCALE : x_end*SCALE] = out_tile_valid
                    print(f"區塊完成: 貼上位置 ({x*SCALE}, {y*SCALE})")

        # ==========================================
        # 3. 處理使用者指定的縮放比例 (還原 PyTorch 行為)
        # ==========================================
        if outscale != SCALE:
            final_h = int(height * outscale)
            final_w = int(width * outscale)
            output_img = cv2.resize(output_img, (final_w, final_h), interpolation=cv2.INTER_AREA)

        # ==========================================
        # 4. 轉存為 JPEG 回傳
        # ==========================================
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
# 讓 FastAPI 也能透過萬能路徑找到 index.html
# app.mount("/", StaticFiles(directory=".", html=True), name="static")
static_dir = resource_path('static')
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


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