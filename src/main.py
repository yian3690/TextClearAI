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
        # 如果是被 PyInstaller 打包執行的狀態 (打包後結構會被壓平)
        base_path = sys._MEIPASS
    else:
        # 如果是在一般開發環境 (python src/main.py) 執行的狀態
        # 因為 main.py 在 src/ 內，所以要用 dirname 往上退回根目錄
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        
        # 1. 讀取圖片時保留潛在的透明通道 (Alpha Channel)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

        if img is None:
            return Response(content="無法讀取圖片", status_code=400)

        # 2. 判斷與分離透明通道
        has_alpha = False
        if len(img.shape) == 3 and img.shape[2] == 4:
            has_alpha = True
            alpha_channel = img[:, :, 3]  # 取出透明通道
            img = img[:, :, :3]           # 保留 BGR 交給 AI 處理

        height, width = img.shape[:2]

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
            # 1. 取得 ORT 輸出 (此時記憶體仍屬於 C++ 引擎)
            out = np.squeeze(ort_outs[0], axis=0)
            out = np.transpose(out, (1, 2, 0))
            out = np.nan_to_num(out)

            # 2. 強制分配新的 Python 記憶體，安全斷開與引擎的連結
            out = np.clip(out, 0, 1)
            
            # 3. 在 Python 空間內安全地進行矩陣運算與轉型
            out = (out * 255).round().astype(np.uint8)
            
            # 直接轉回 BGR
            out = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)

            # 裁切掉為了對齊而多出來的邊緣 (模型放大 4 倍，所以裁切量也要 * 4)
            if pad_h > 0 or pad_w > 0:
                out = out[0 : h * 4, 0 : w * 4]
                
            return out

        # ==========================================
        # 1. 動態 Tile 評估策略 (極簡乾淨呼叫)
        # ==========================================
        total_pixels = height * width
        SCALE = 4

        # 策略 1：小圖直接運算
        if width <= 800 and height <= 800:
            print(f"進入 AI 運算 ({width}x{height})，策略：整張直出 (tile=0)")
            output_img = run_onnx_inference(img)

        # 策略 2：改用對 GPU 記憶體極度友善的微型切塊
        else:
            TILE_SIZE = 400  
            TILE_PAD = 10    
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
        # 2. 處理使用者指定的縮放比例與最大尺寸限制
        # ==========================================
        MAX_OUTPUT_SIZE = 6000
        
        # 計算期望的最終目標尺寸
        target_w = int(width * outscale)
        target_h = int(height * outscale)
        
        # 確保最終目標尺寸不超過 MAX_OUTPUT_SIZE 限制
        if max(target_w, target_h) > MAX_OUTPUT_SIZE:
            ratio = MAX_OUTPUT_SIZE / max(target_w, target_h)
            target_w = int(target_w * ratio)
            target_h = int(target_h * ratio)
            print(f"輸出尺寸超過限制，已自動縮放至 {target_w}x{target_h}")

        # 模型剛生成的原始尺寸 (固定為 4 倍)
        current_h, current_w = output_img.shape[:2]
        
        # 如果目標尺寸與當前的 4 倍尺寸不同，則執行「唯一一次」的重新取樣
        if target_w != current_w or target_h != current_h:
            # 若目標比現在小，使用 INTER_AREA (抗鋸齒效果好)；若目標比現在大，使用 INTER_CUBIC
            interpolation = cv2.INTER_AREA if (target_w < current_w) else cv2.INTER_CUBIC
            output_img = cv2.resize(output_img, (target_w, target_h), interpolation=interpolation)

       # ==========================================
        # 3. 輸出打包 (一律輸出 PNG 以確保無損畫質)
        # ==========================================
        if has_alpha:
            # 將透明通道依照相同目標尺寸放大
            alpha_resized = cv2.resize(alpha_channel, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
            
            # 將圖片轉回 4 通道 (BGRA)，並塞回放大後的透明通道
            output_img = cv2.cvtColor(output_img, cv2.COLOR_BGR2BGRA)
            output_img[:, :, 3] = alpha_resized
        
        # 無論是否有透明背景，一律編碼為 PNG 格式避免 JPG 壓縮
        is_success, buffer = cv2.imencode(".png", output_img)
        media_type = "image/png"

        if not is_success:
            return Response(content="圖片轉換失敗", status_code=500)
            
        io_buf = io.BytesIO(buffer)
        return Response(content=io_buf.getvalue(), media_type=media_type)
    
    except Exception as e:
        print(f"處理錯誤: {str(e)}")
        return Response(content=f"伺服器內部錯誤: {str(e)}", status_code=500)

# ==========================================
# 桌面視窗 (PyWebView) 與靜態檔案設定
# ==========================================
static_dir = resource_path('static')
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# ==========================================
# JS 與 Python 的通訊橋樑
# ==========================================
class JS_API:
    def save_image(self, b64_data, default_filename):
        try:
            # 將前端傳來的 base64 圖片還原成二進位資料
            header, encoded = b64_data.split(",", 1)
            data = base64.b64decode(encoded)
            
            # 確保預設副檔名是 .png
            if default_filename.lower().endswith('.jpg') or default_filename.lower().endswith('.jpeg'):
                default_filename = default_filename.rsplit('.', 1)[0] + '.png'
            
            # 呼叫系統原生的「另存新檔」視窗 (改成預設 PNG)
            file_types = ('PNG Image (*.png)', 'All files (*.*)')
            
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

    # 把 api 綁定到視窗上，並設定全域 window 變數
    global window
    window = webview.create_window(
        title="TextClear AI - 文字影像清晰化工具", 
        url="http://127.0.0.1:8000/index.html", 
        width=1000,
        height=800,
        min_size=(800, 600),
        js_api=api  # 讓 JS 可以呼叫 Python
    )
    
    webview.start()