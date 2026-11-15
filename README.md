# 🏯 台南開放資料檢視器

以 [Gradio](https://www.gradio.app/) 製作的網頁工具，可載入台南市政府資料開放平台的 CSV，進行關鍵字搜尋、統計摘要、長條圖繪製，並匯出結果。

## 功能

- 📥 輸入 CSV 連結即時載入（`utf-8-sig`，自動移除含空值的列）
- 🔍 全欄位或指定欄位的關鍵字搜尋
- 📊 數值欄位統計摘要
- 📈 任一欄位的類別次數長條圖（前 N 名）
- 💾 匯出目前結果為 CSV（Excel 開啟不會亂碼）

## 專案結構

```
.
├── app.py            # Gradio 主程式
├── requirements.txt  # 相依套件
├── render.yaml       # Render Blueprint 設定（可選）
└── README.md
```

## 本機執行

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

開啟 http://localhost:7860

## Google Colab 執行

```python
!pip install -q -r requirements.txt
%run app.py
```

## 部署到 Render

1. 將本專案推上 GitHub。
2. 登入 [Render](https://render.com/) → **New +** → **Web Service** → 選擇你的 GitHub repo。
3. 設定如下：

   | 欄位 | 值 |
   |---|---|
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `python app.py` |
   | Instance Type | Free（或付費） |

4. （建議）到 **Environment** 新增 `PYTHON_VERSION` = `3.11.9`。
5. 按下 **Create Web Service**，部署完成後即可使用 Render 提供的網址。

> 也可以使用 **New + → Blueprint**，Render 會自動讀取 `render.yaml`。

### 環境變數（可選）

| 名稱 | 說明 |
|---|---|
| `DEFAULT_CSV_URL` | 預設的 CSV 下載連結 |
| `PORT` | Render 會自動提供，程式已自動讀取 |

## 注意事項

- Render 免費方案閒置約 15 分鐘會休眠，下次開啟需等待數十秒喚醒。
- 程式使用 `requests.get(..., verify=False)` 以略過該網站的 SSL 憑證問題；若換成其他來源，建議改回 `verify=True`。
- 資料僅暫存於伺服器暫存目錄，重啟後會消失。
