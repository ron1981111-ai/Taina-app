# 🏙️ 台南市開放資料檢視器

使用 Gradio 製作的互動式網頁,可載入[台南市政府資料開放平台](https://data.tainan.gov.tw/)的 CSV 資料,進行搜尋、欄位摘要、快速圖表與下載。

## 功能

- 📥 輸入 CSV 連結即可載入(自動處理 `utf-8-sig` 繁體中文、移除空值列)
- 📋 關鍵字搜尋、自選顯示欄位、調整顯示筆數
- ⬇️ 下載目前篩選結果(CSV)
- 📊 欄位摘要(型態、不重複值數量、範例)
- 📈 任一欄位出現次數長條圖

## 專案結構

```
.
├── app.py             # Gradio 主程式
├── requirements.txt   # 相依套件
├── render.yaml        # Render Blueprint 設定(選用)
├── .gitignore
└── README.md
```

## 本機執行

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

開啟 http://localhost:7860

## 部署到 Render

### 方法一:手動建立 Web Service

1. 將專案推上 GitHub。
2. 登入 [Render](https://render.com/) → **New +** → **Web Service** → 連結你的 GitHub repo。
3. 設定:
   | 欄位 | 值 |
   |---|---|
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `python app.py` |
   | Instance Type | Free(或以上) |
4. (選用)在 **Environment** 新增 `PYTHON_VERSION` = `3.11.9`。
5. 按 **Create Web Service**,等待建置完成後即可使用 Render 提供的網址。

### 方法二:使用 Blueprint

repo 內已有 `render.yaml`,在 Render 選 **New + → Blueprint**,選擇此 repo 即可自動建立。

## 環境變數(選用)

| 名稱 | 說明 | 預設 |
|---|---|---|
| `DATA_URL` | 預設載入的 CSV 連結 | 範例連結 |
| `PORT` | 服務埠號(Render 自動提供) | `7860` |

## 注意事項

- Render 免費方案閒置一段時間後會休眠,首次開啟需等待數十秒喚醒。
- 程式使用 `verify=False` 略過 SSL 憑證驗證(政府網站憑證常有問題),僅建議用於公開資料。
- 每位使用者的資料存於各自的 session,不會互相影響;暫存檔放在系統暫存目錄,重新部署後會清除。

## 授權

MIT
