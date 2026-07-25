const API_URL = "/enhance-text";

const fileInput = document.getElementById('imageInput');
const originalImage = document.getElementById('originalImage');
const resultImage = document.getElementById('resultImage');
// Grab progress bar related elements
const progressWrapper = document.getElementById('progressWrapper');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const downloadBtn = document.getElementById('downloadBtn');

const origPlaceholder = document.getElementById('origPlaceholder');
const resPlaceholder = document.getElementById('resPlaceholder');


let currentBlobUrl = null; 
let originalFileName = "image.jpg"; // 用來記憶原始檔名，給個預設值防呆

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];

    if (file) {
        originalFileName = file.name; // 把使用者上傳的檔名存起來

        originalImage.src = URL.createObjectURL(file);
        originalImage.style.display = 'block';
        origPlaceholder.style.display = 'none'; // Hide the default text
        
        resultImage.style.display = 'none'; 
        resPlaceholder.style.display = 'block'; // Show waiting text
        resPlaceholder.innerText = "Waiting for processing...";
        
        downloadBtn.style.display = 'none'; 
        progressWrapper.style.display = 'none'; 
    }
});

async function processImage() {
    const file = fileInput.files[0];
    if (!file) {
        alert("Please select an image first!");
        return;
    }

    const selectedOutscale = document.querySelector('input[name="outscale"]:checked').value;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("outscale", selectedOutscale);

    // Disable button to prevent multiple clicks
    const processBtn = document.getElementById('processBtn');
    processBtn.disabled = true;
    processBtn.innerText = "Processing...";

    // Hide right-side placeholders
    resPlaceholder.style.display = 'none';
    resultImage.style.display = 'none';
    downloadBtn.style.display = 'none';
    
    progressWrapper.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.innerText = 'Uploading and initializing... 0%';

    // ==========================================
    // 【自適應平滑進度條演算法】
    // ==========================================
    let progress = 0;
    
    // 1. 取得檔案大小 (MB) 與放大的倍率
    const fileSizeMB = file.size / (1024 * 1024); 
    const scale = parseInt(selectedOutscale);
    
    // 2. 計算「運算阻力」：檔案越大、倍率越高，進度條推動的阻力越大 (走得越慢)
    const speedResistance = Math.max(1, fileSizeMB * scale * 0.8); 

    const progressInterval = setInterval(() => {
        if (progress < 99) {
            // 計算距離 99% 還有多少距離
            let remaining = 99 - progress;
            
            // 距離越近，步伐越小 (Zeno's paradox)，並除以阻力係數
            let step = (remaining * 0.05) / speedResistance;
            
            // 加入一點微小的隨機跳動，並保證每次至少前進 0.02%，永遠不會卡死停住
            step = Math.max(0.02, step + (Math.random() * 0.05));
            
            progress += step;
            
            // 最高卡在 99.9%，直到後端回傳真正的圖片
            if (progress > 99.9) progress = 99.9;

            progressBar.style.width = progress + '%';
            
            // 顯示到小數點後第一位，視覺上會一直跳動，減緩使用者的等待焦慮
            progressText.innerText = `Enhancing image quality... ${progress.toFixed(1)}%`;
        }
    }, 300); // 把更新頻率加快到 300 毫秒，讓小數點跳動更流暢
    // ==========================================

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const blob = await response.blob();
        if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
        currentBlobUrl = URL.createObjectURL(blob);
        
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        progressText.innerText = 'Processing complete! 100%';

        setTimeout(() => {
            resultImage.src = currentBlobUrl;
            resultImage.style.display = 'block';
            downloadBtn.style.display = 'block'; 
        }, 500);
        
    } catch (error) {
        console.error("Processing failed:", error);
        clearInterval(progressInterval);
        progressText.innerText = 'Processing failed, please try again!';
        progressBar.style.backgroundColor = 'red'; 
        resPlaceholder.style.display = 'block';
        resPlaceholder.innerText = "Processing failed";
        alert("Processing failed. Please check if the backend is running properly.");
    } finally {
        // Restore button state
        processBtn.disabled = false;
        processBtn.innerText = "Enhance Image";
    }
}


async function downloadImage() {
    if (!currentBlobUrl) return;
    
    // 計算新檔名
    const lastDotIndex = originalFileName.lastIndexOf('.');
    let newFileName = "";
    if (lastDotIndex === -1) {
        newFileName = originalFileName + "_enhanced.jpg";
    } else {
        const namePart = originalFileName.substring(0, lastDotIndex);
        newFileName = namePart + "_enhanced.jpg"; // 強制轉存為 .jpg
    }

    // 檢查是否在 PyWebView 桌面軟體環境中
    if (window.pywebview) {
        // 1. 將 blob 轉換為 base64 格式，因為 Python 比較好讀取
        const response = await fetch(currentBlobUrl);
        const blob = await response.blob();
        const reader = new FileReader();
        
        reader.onloadend = async () => {
            const base64data = reader.result;
            // 2. 呼叫 Python 的存檔功能！
            const isSaved = await window.pywebview.api.save_image(base64data, newFileName);
            if (isSaved) {
                // 可選：可以加個小提示框告訴使用者存檔成功
                console.log("檔案儲存成功！");
            }
        };
        reader.readAsDataURL(blob);

    } else {
        // 如果是開在一般的 Chrome 瀏覽器，就用原本的網頁下載法
        const a = document.createElement('a');
        a.href = currentBlobUrl;
        a.download = newFileName; 
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
}