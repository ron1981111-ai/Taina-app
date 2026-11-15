# 🏙️ 台南市開放資料檢視器 (PWA + RWD)

使用 Gradio 製作的互動式網頁,可載入[台南市政府資料開放平台](https://data.tainan.gov.tw/)的 CSV 資料,進行搜尋、欄位摘要、快速圖表與下載。
已加入 **PWA(可安裝成 App)** 與 **RWD(手機/平板/桌機自適應)**。

## 功能

- 📥 輸入 CSV 連結即可載入(自動處理 `utf-8-sig` 繁體中文、移除空值列)
- 📋 關鍵字搜尋、自選顯示欄位、調整顯示筆數
- ⬇️ 下載目前篩選結果(CSV)
- 📊 欄位摘要、📈 欄位出現次數長條圖
- 📲 PWA:可安裝到手機主畫面 / 電腦桌面,獨立視窗開啟
- 📡 離線時顯示提示頁與提示列
- 📱 RWD:手機(≤640px)輸入元件自動直向堆疊、按鈕符合 44px 觸控尺寸、支援瀏海安全區

## 專案結構

```
.
├── app.py                      # Gradio 介面 + FastAPI(提供 PWA 檔案)
├── requirements.txt
├── render.yaml                 # Render Blueprint(選用)
├── .python-version             # 指定 Python 版本 (3.11.9)
├── make_icons.py               # 產生 PWA 圖示的工具(選用,需 pillow)
└── static/
    ├── manifest.webmanifest    # PWA 設定(名稱、圖示、主題色…)
    ├── sw.js                   # Service Worker(由 /sw.js 提供,作用範圍為整站)
    ├── offline.html            # 離線時顯示的頁面
    └── icons/                  # 192 / 512 / maskable / apple-touch-icon
```

## 架構說明

- `app.py` 以 FastAPI 為外層,提供 `/manifest.webmanifest`、`/sw.js`、`/offline`,並把 `static/` 資料夾掛在網址 `/pwa/*`(刻意不用 `/static`,以免蓋掉 Gradio 內建的 `/static` 路由),再用 `gr.mount_gradio_app` 把 Gradio 掛在根路徑 `/`。
- Service Worker 必須由根路徑提供(`/sw.js`)才能控制整個網站範圍。
- 快取策略:頁面導覽「網路優先、離線顯示 `/offline`」;靜態資源「stale-while-revalidate」;Gradio API 與下載檔案一律不快取。
- 資料查詢必須連線,PWA 離線時只會顯示離線頁,不會顯示舊資料。

## 本機執行

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

開啟 http://localhost:7860 (localhost 視為安全來源,可測試 PWA)。

## 部署到 Render

1. 將專案推上 GitHub(`app.py`、`static/` 等放在 repo 根目錄)。
2. Render → **New +** → **Web Service** → 選擇 repo。
3. 設定:

   | 欄位 | 值 |
   |---|---|
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `python app.py` ← 注意 python 與 app.py 中間是**空格** |
   | Health Check Path | `/healthz`(選用) |

4. Python 版本由 repo 內的 `.python-version` 指定(3.11.9),不需另外設定環境變數。
5. 或使用 Blueprint:New + → Blueprint,自動讀取 `render.yaml`。

Render 預設提供 HTTPS,符合 PWA 需求。

## 安裝成 App

- **Android / Chrome / Edge(桌機)**:開啟網站後點右下角「📲 安裝 App」,或網址列的安裝圖示。
- **iPhone / iPad (Safari)**:點「分享」→「加入主畫面」。

## 驗證 PWA

Chrome DevTools → **Application** → 檢查 *Manifest* 與 *Service Workers*;或執行 **Lighthouse** 的 PWA 檢測。

## 更新 Service Worker

修改 `static/sw.js` 後,請把檔內 `VERSION` 改成新值(如 `v2`),舊快取會在啟用時自動清除。

## 環境變數(選用)

| 名稱 | 說明 | 預設 |
|---|---|---|
| `DATA_URL` | 預設載入的 CSV 連結 | 範例連結 |
| `PORT` | 服務埠號(Render 自動提供) | `7860` |

## 注意事項

- Render 免費方案閒置後會休眠,首次開啟需等待數十秒。
- 程式使用 `verify=False` 略過 SSL 驗證(政府網站憑證常有問題),僅建議用於公開資料。
- 每位使用者的資料存於各自的 session,暫存檔放系統暫存目錄,重新部署後清除。
