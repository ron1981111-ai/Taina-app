# 台南開放資料瀏覽器（Gradio · PWA · RWD）

載入[臺南市政府資料開放平台](https://data.tainan.gov.tw/)的 CSV，即可搜尋、篩選、畫統計圖並下載結果。
可安裝成手機或桌面 App，版面會依螢幕大小自動調整。

## 功能

- 貼上 CSV 連結載入資料（預設連結可用環境變數 `DEFAULT_CSV_URL` 覆寫）
- 關鍵字搜尋、自選欄位、下載篩選後的 CSV（UTF-8 含 BOM，Excel 不亂碼）
- 類別筆數長條圖、`describe()` 欄位摘要
- **PWA**：Web App Manifest、Service Worker、離線頁、可安裝（Android / Chrome / Edge；iOS 用「加入主畫面」）
- **RWD**：手機單欄、平板雙欄統計卡片、桌面完整排版；支援深色模式與安全區域（瀏海）

## 專案結構

```
├── app.py                 # Gradio 介面 + FastAPI（提供 PWA 檔案）
├── requirements.txt
├── render.yaml            # Render Blueprint
├── pwa/
│   ├── manifest.webmanifest
│   ├── sw.js              # Service Worker
│   ├── offline.html
│   └── icon-*.png
└── README.md
```

## 本機執行

```bash
python -m venv .venv && source .venv/bin/activate   # Windows：.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

開啟 http://localhost:7860 。Service Worker 在 `localhost` 可運作，其他網址需要 HTTPS。

## 部署到 Render

1. 把整個資料夾推到 GitHub。
2. Render → **New → Blueprint**，選這個 repo，Render 會讀取 `render.yaml`。
   或 **New → Web Service** 手動設定：
   - Build Command：`pip install -r requirements.txt`
   - Start Command：`uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Health Check Path：`/healthz`
3. 部署完成後用 `https://xxx.onrender.com` 開啟，瀏覽器網址列或頁面右下角會出現「安裝 App」。

> 免費方案閒置約 15 分鐘會休眠，第一次開啟需等待喚醒。

## 驗證 PWA

Chrome 開發者工具 → **Application**：確認 Manifest 無錯誤、Service Worker 狀態為 activated；
**Lighthouse** 可檢查 PWA 與行動版表現。

## 注意事項

- 原本的 `requests.get(..., verify=False)` 已保留，因為該站憑證在部分環境驗證會失敗；
  若你的環境可正常驗證，建議在 `app.py` 的 `fetch_csv` 移除 `verify=False`。
- 資料會在記憶體中快取 10 分鐘（`CACHE_TTL`）。
- Gradio 固定在 5.x（`<6`），升級大版本前請先測試。
