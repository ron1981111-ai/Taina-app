"""
台南市開放資料檢視器 (Gradio + PWA + RWD)

架構:FastAPI 作為外層 → 提供 manifest / service worker / 離線頁 / 圖示
      Gradio 以 mount_gradio_app 掛載在根路徑 "/"
啟動:python app.py   (Render 的 Start Command)
"""
import os
import tempfile
import warnings
from pathlib import Path

import gradio as gr
import pandas as pd
import requests
import urllib3
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------------------------------------------------------------
# 設定
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PWA_DIR = BASE_DIR / "pwa"
TMP_DIR = tempfile.gettempdir()
REQUEST_TIMEOUT = 30

DEFAULT_URL = os.getenv(
    "DATA_URL",
    "https://data.tainan.gov.tw/File/ResourceCsvDownload/6c16b2c8-92b6-49d9-98b5-02966462172c",  # 換連結
)


# ----------------------------------------------------------------------
# 資料處理
# ----------------------------------------------------------------------
def fetch_data(url: str) -> pd.DataFrame:
    """下載 CSV 並清理資料"""
    response = requests.get(url, verify=False, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    csv_path = os.path.join(TMP_DIR, "data01.csv")
    with open(csv_path, "wb") as f:
        f.write(response.content)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")  # 繁體中文
    return df.dropna().reset_index(drop=True)


def summary_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return pd.DataFrame({
        "欄位": df.columns,
        "資料型態": [str(t) for t in df.dtypes],
        "不重複值數量": [df[c].nunique() for c in df.columns],
        "範例": [str(df[c].iloc[0]) for c in df.columns],
    })


def search_data(df, keyword, cols, limit):
    if df is None or df.empty:
        return pd.DataFrame(), "尚未載入資料", None

    d = df[cols] if cols else df
    if keyword and keyword.strip():
        kw = keyword.strip()
        mask = d.astype(str).apply(
            lambda s: s.str.contains(kw, case=False, na=False, regex=False)
        ).any(axis=1)
        d = d[mask]

    total = len(d)
    shown = d.head(int(limit))
    export_path = os.path.join(TMP_DIR, "filtered_data.csv")
    shown.to_csv(export_path, index=False, encoding="utf-8-sig")
    info = f"🔎 符合條件 **{total:,}** 筆,目前顯示前 **{len(shown):,}** 筆"
    return shown, info, export_path


def make_chart(df, col, top_n):
    if df is None or df.empty or not col or col not in df.columns:
        return pd.DataFrame({"類別": [], "數量": []})
    vc = df[col].astype(str).value_counts().head(int(top_n)).reset_index()
    vc.columns = ["類別", "數量"]
    return vc


def load_data(url):
    try:
        df = fetch_data(url.strip())
    except Exception as e:
        raise gr.Error(f"資料載入失敗:{e}")

    cols = list(df.columns)
    status = f"✅ 載入成功:共 **{len(df):,}** 筆資料、**{len(cols)}** 個欄位"
    table, info, file = search_data(df, "", cols, 100)
    first = cols[0] if cols else None
    return (
        df,
        status,
        gr.update(choices=cols, value=cols),
        gr.update(choices=cols, value=first),
        table,
        info,
        file,
        summary_df(df),
        make_chart(df, first, 10),
    )


# ----------------------------------------------------------------------
# PWA:<head> 注入內容
# ----------------------------------------------------------------------
HEAD = """
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#0d9488">
<meta name="application-name" content="台南資料">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="台南資料">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/pwa/icons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/pwa/icons/favicon-32.png">
<script>
(function () {
  // 1) 註冊 Service Worker
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function (e) {
        console.warn("SW 註冊失敗", e);
      });
    });
  }

  var isStandalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var deferredPrompt = null;
  var installBtn = null;

  function ready(fn) {
    if (document.readyState !== "loading") fn(); else document.addEventListener("DOMContentLoaded", fn);
  }

  // 2) 安裝按鈕 + 離線提示列
  ready(function () {
    installBtn = document.createElement("button");
    installBtn.id = "pwa-install";
    installBtn.type = "button";
    installBtn.textContent = "📲 安裝 App";
    installBtn.addEventListener("click", function () {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.finally(function () { deferredPrompt = null; installBtn.classList.remove("show"); });
      } else if (isIOS) {
        alert("iPhone / iPad 安裝方式:\\n點下方「分享」按鈕 → 選擇「加入主畫面」");
      }
    });
    document.body.appendChild(installBtn);
    if (isIOS && !isStandalone) installBtn.classList.add("show");

    var banner = document.createElement("div");
    banner.id = "net-banner";
    banner.textContent = "⚠️ 目前離線,部分功能無法使用";
    document.body.appendChild(banner);
    function updateNet() { banner.classList.toggle("show", !navigator.onLine); }
    window.addEventListener("online", updateNet);
    window.addEventListener("offline", updateNet);
    updateNet();
  });

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn && !isStandalone) installBtn.classList.add("show");
    else ready(function () { if (installBtn && !isStandalone) installBtn.classList.add("show"); });
  });
  window.addEventListener("appinstalled", function () {
    if (installBtn) installBtn.classList.remove("show");
  });
})();
</script>
"""

# ----------------------------------------------------------------------
# RWD:樣式
# ----------------------------------------------------------------------
CSS = """
/* ---------- 基本 ---------- */
.gradio-container {
  max-width: 1200px !important;
  margin: 0 auto !important;
  padding-left: max(16px, env(safe-area-inset-left)) !important;
  padding-right: max(16px, env(safe-area-inset-right)) !important;
  padding-bottom: max(16px, env(safe-area-inset-bottom)) !important;
}
#title { text-align: center; padding: 18px 0 6px; }
#title h1 { font-size: clamp(1.4rem, 4.5vw, 2.1rem); margin: 0 0 4px; line-height: 1.25; }
#title p  { color: #6b7280; margin: 0; font-size: clamp(.85rem, 2.6vw, 1rem); }
.status-box { padding: 10px 14px; border-radius: 12px; }

/* 觸控友善:按鈕最小 44px */
button, .gr-button { min-height: 44px; }

/* 表格:橫向捲動,避免撐破版面 */
.gradio-container .table-wrap, .gradio-container [data-testid="dataframe"] { overflow-x: auto; }

/* ---------- 安裝按鈕 / 離線提示 ---------- */
#pwa-install {
  display: none; position: fixed; z-index: 9999;
  right: max(16px, env(safe-area-inset-right));
  bottom: max(16px, env(safe-area-inset-bottom));
  padding: 10px 18px; border: 0; border-radius: 999px;
  background: #0d9488; color: #fff; font-weight: 600; font-size: .95rem;
  box-shadow: 0 6px 18px rgba(13,148,136,.45); cursor: pointer;
}
#pwa-install.show { display: block; }
#net-banner {
  display: none; position: fixed; z-index: 9999; left: 0; right: 0; top: 0;
  padding: calc(8px + env(safe-area-inset-top)) 12px 8px;
  background: #f59e0b; color: #1f2937; text-align: center; font-size: .9rem;
}
#net-banner.show { display: block; }

/* ---------- 平板 (<= 900px) ---------- */
@media (max-width: 900px) {
  .gradio-container { padding-left: 12px !important; padding-right: 12px !important; }
}

/* ---------- 手機 (<= 640px):Row 內元件改為直向堆疊 ---------- */
@media (max-width: 640px) {
  .row-stack { flex-wrap: wrap !important; gap: 10px !important; }
  .row-stack > * { min-width: 100% !important; flex: 1 1 100% !important; }
  #title { padding-top: 10px; }
  #pwa-install { padding: 12px 20px; }
}

/* 已安裝成 App 時,不需要安裝按鈕 */
@media (display-mode: standalone) { #pwa-install { display: none !important; } }
"""

theme = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="cyan",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Noto Sans TC"), "sans-serif"],
)

# ----------------------------------------------------------------------
# Gradio 介面
# ----------------------------------------------------------------------
with gr.Blocks(theme=theme, css=CSS, head=HEAD, title="台南開放資料檢視器") as demo:
    df_state = gr.State(pd.DataFrame())

    gr.HTML(
        "<div id='title'><h1>🏙️ 台南市開放資料檢視器</h1>"
        "<p>載入 → 搜尋 → 分析 → 下載,一站完成</p></div>"
    )

    with gr.Row(elem_classes="row-stack"):
        url_box = gr.Textbox(
            label="CSV 資料連結", value=DEFAULT_URL, scale=5, lines=1,
            info="可替換成任何台南資料開放平台的 CSV 連結",
        )
        load_btn = gr.Button("📥 載入資料", variant="primary", scale=1, size="lg")

    status = gr.Markdown("尚未載入資料,請按「載入資料」", elem_classes="status-box")

    with gr.Tabs():
        with gr.Tab("📋 資料表"):
            with gr.Row(elem_classes="row-stack"):
                keyword = gr.Textbox(label="關鍵字搜尋", placeholder="輸入文字,按 Enter 搜尋…", scale=3)
                limit = gr.Slider(10, 1000, value=100, step=10, label="最多顯示筆數", scale=2)
            col_select = gr.Dropdown(choices=[], value=[], multiselect=True, label="顯示欄位")
            info = gr.Markdown()
            table = gr.Dataframe(label="資料內容", interactive=False, wrap=True, max_height=480)
            download = gr.File(label="⬇️ 下載目前篩選結果 (CSV)")

        with gr.Tab("📊 欄位摘要"):
            summary = gr.Dataframe(label="欄位資訊", interactive=False, wrap=True, max_height=480)

        with gr.Tab("📈 快速圖表"):
            with gr.Row(elem_classes="row-stack"):
                chart_col = gr.Dropdown(choices=[], label="選擇欄位", scale=3)
                top_n = gr.Slider(3, 30, value=10, step=1, label="顯示前 N 名", scale=2)
            plot = gr.BarPlot(
                x="類別", y="數量", title="欄位值出現次數",
                x_title="類別", y_title="數量", height=380,
            )

    # ---------------- 事件綁定 ----------------
    load_outputs = [df_state, status, col_select, chart_col, table, info, download, summary, plot]
    load_btn.click(load_data, url_box, load_outputs)
    demo.load(load_data, url_box, load_outputs)

    s_in = [df_state, keyword, col_select, limit]
    s_out = [table, info, download]
    keyword.submit(search_data, s_in, s_out)
    col_select.change(search_data, s_in, s_out)
    limit.release(search_data, s_in, s_out)

    c_in = [df_state, chart_col, top_n]
    chart_col.change(make_chart, c_in, plot)
    top_n.release(make_chart, c_in, plot)

demo.queue()

# ----------------------------------------------------------------------
# FastAPI 外層:PWA 必要路由(需在掛載 Gradio 之前註冊)
# ----------------------------------------------------------------------
app = FastAPI(title="Tainan Open Data PWA")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(
        PWA_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # Service Worker 檔案不可被長時間快取,否則更新不會生效
    return FileResponse(
        PWA_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


@app.get("/offline", include_in_schema=False)
def offline_page():
    return FileResponse(PWA_DIR / "offline.html", media_type="text/html")


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


# 圖示等靜態檔(用 /pwa 避免與 Gradio 自身的 /static 衝突)
app.mount("/pwa", StaticFiles(directory=str(PWA_DIR)), name="pwa")

# 掛載 Gradio 到根路徑
app = gr.mount_gradio_app(app, demo, path="/")

# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Render 會提供 PORT 環境變數,且必須綁定 0.0.0.0
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 7860)),
        proxy_headers=True,          # 讓 https 轉發資訊正確(Render 在反向代理後)
        forwarded_allow_ips="*",
    )
