"""
台南市開放資料瀏覽器 — Gradio + PWA + RWD
FastAPI 負責提供 manifest / service worker / 離線頁，Gradio 掛載在根路徑 "/"。
本機：python app.py        Render：uvicorn app:app --host 0.0.0.0 --port $PORT
"""
import io
import os
import tempfile
import time
from pathlib import Path

import gradio as gr
import pandas as pd
import requests
import urllib3
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).parent
PWA_DIR = BASE_DIR / "pwa"
DEFAULT_URL = os.getenv(
    "DEFAULT_CSV_URL",
    "https://data.tainan.gov.tw/File/ResourceCsvDownload/6c16b2c8-92b6-49d9-98b5-02966462172c",  # 換連結
)
CACHE_TTL = 600  # 秒；同一連結 10 分鐘內不重複下載
_cache: dict[str, tuple[float, pd.DataFrame]] = {}


# ----------------------------------------------------------------------
# 資料處理
# ----------------------------------------------------------------------
def fetch_csv(url: str) -> pd.DataFrame:
    url = url.strip()
    hit = _cache.get(url)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1].copy()
    response = requests.get(url, verify=False, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(io.BytesIO(response.content), encoding="utf-8-sig")  # 繁體中文
    df = df.dropna().reset_index(drop=True)
    _cache[url] = (time.time(), df)
    return df.copy()


def stat_cards(df: pd.DataFrame, shown: int | None = None) -> str:
    shown = len(df) if shown is None else shown
    items = [
        ("符合條件的筆數", f"{shown:,}"),
        ("資料總筆數", f"{len(df):,}"),
        ("欄位數", f"{df.shape[1]}"),
        ("數值欄位", f"{df.select_dtypes('number').shape[1]}"),
    ]
    cards = "".join(
        f"<div class='stat'><div class='stat-num'>{v}</div><div class='stat-label'>{k}</div></div>"
        for k, v in items
    )
    return f"<div class='stat-row'>{cards}</div>"


def category_counts(df: pd.DataFrame, col: str, top: int = 12) -> pd.DataFrame:
    counts = df[col].astype(str).value_counts().head(top).reset_index()
    counts.columns = [col, "筆數"]
    return counts


def update_chart(df, col):
    if df is None or not col:
        return gr.BarPlot(value=pd.DataFrame({"類別": [], "筆數": []}), x="類別", y="筆數")
    return gr.BarPlot(
        value=category_counts(df, col), x=col, y="筆數", x_title=col, y_title="筆數", height=380
    )


# ----------------------------------------------------------------------
# 事件
# ----------------------------------------------------------------------
def load_data(url):
    try:
        df = fetch_csv(url)
    except Exception as e:
        raise gr.Error(f"下載失敗：{e}。請確認連結是否正確，或稍後再試。")
    cols = list(df.columns)
    cat_cols = [c for c in cols if df[c].nunique() <= max(30, len(df) // 2)] or cols
    gr.Info(f"已載入 {len(df):,} 筆資料")
    return (
        df,
        stat_cards(df),
        df,
        gr.update(choices=cols, value=cols),
        gr.update(choices=cat_cols, value=cat_cols[0]),
        update_chart(df, cat_cols[0]),
        df.describe(include="all").T.reset_index().rename(columns={"index": "欄位"}),
        None,
    )


def apply_filter(df, keyword, cols):
    if df is None:
        raise gr.Error("請先按「載入資料」。")
    out = df
    kw = (keyword or "").strip()
    if kw:
        mask = out.astype(str).apply(lambda s: s.str.contains(kw, case=False, regex=False)).any(axis=1)
        out = out[mask]
    if cols:
        out = out[[c for c in cols if c in out.columns]]
    path = None
    if len(out):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", prefix="tainan_")
        out.to_csv(tmp.name, index=False, encoding="utf-8-sig")  # BOM：Excel 開啟不亂碼
        path = tmp.name
    return stat_cards(df, len(out)), out, path


def reset(df):
    if df is None:
        return "", gr.update(), EMPTY_STATS, None, None
    return "", gr.update(value=list(df.columns)), stat_cards(df), df, None


# ----------------------------------------------------------------------
# 外觀（RWD：手機單欄、平板雙欄、桌面完整排版）
# ----------------------------------------------------------------------
theme = gr.themes.Base(
    primary_hue=gr.themes.Color(
        c50="#eef3fb", c100="#d9e4f5", c200="#b5c9ea", c300="#8aa9db", c400="#5f86c8",
        c500="#3f68ad", c600="#2e5190", c700="#243f73", c800="#1d3258", c900="#16253f", c950="#0e182a",
    ),
    secondary_hue="teal",
    neutral_hue="slate",
    radius_size=gr.themes.sizes.radius_lg,
    font=[gr.themes.GoogleFont("Noto Sans TC"), "ui-sans-serif", "system-ui", "sans-serif"],
).set(
    button_primary_background_fill="linear-gradient(135deg,#243f73,#2f7f86)",
    button_primary_background_fill_hover="linear-gradient(135deg,#1d3258,#256a70)",
    button_primary_text_color="white",
)

CSS = """
.gradio-container {
  max-width: 1180px !important; margin: auto;
  padding-left: max(12px, env(safe-area-inset-left)) !important;
  padding-right: max(12px, env(safe-area-inset-right)) !important;
  padding-bottom: env(safe-area-inset-bottom);
}
.hero {
  padding: clamp(20px, 4vw, 36px); border-radius: 22px; color: #fff;
  background:
    radial-gradient(circle at 88% 20%, rgba(255,255,255,.14) 0, transparent 38%),
    linear-gradient(135deg, #1d3258 0%, #243f73 55%, #2f7f86 100%);
}
.hero h1 { margin: 0 0 8px; font-size: clamp(1.4rem, 4.5vw, 2rem); font-weight: 700; color: #fff; }
.hero p  { margin: 0; font-size: clamp(.92rem, 2.4vw, 1rem); line-height: 1.7; color: rgba(255,255,255,.85); }

.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat { background: var(--background-fill-primary); border: 1px solid var(--border-color-primary);
        border-radius: 16px; padding: 14px 16px; min-width: 0; }
.stat-num { font-size: clamp(1.25rem, 3.6vw, 1.7rem); font-weight: 700; color: #2e5190; line-height: 1.2; }
.dark .stat-num { color: #8aa9db; }
.stat-label { margin-top: 4px; font-size: .82rem; color: var(--body-text-color-subdued); }

.foot { text-align: center; color: var(--body-text-color-subdued); font-size: .85rem; padding: 6px 0 14px; }
button:focus-visible, input:focus-visible { outline: 3px solid #2f7f86 !important; outline-offset: 2px; }

/* 平板 */
@media (max-width: 900px) { .stat-row { grid-template-columns: repeat(2, 1fr); } }
/* 手機：按鈕撐滿、表格可橫向捲動、觸控目標放大 */
@media (max-width: 640px) {
  .gradio-container { padding-top: 8px !important; }
  button { min-height: 46px; }
  input, textarea { font-size: 16px !important; }  /* 避免 iOS 聚焦時自動放大 */
  .stat { padding: 12px; border-radius: 14px; }
  table { font-size: .85rem; }
}
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }

/* PWA 安裝按鈕 */
#pwa-install {
  position: fixed; right: 16px; bottom: calc(16px + env(safe-area-inset-bottom)); z-index: 50;
  padding: 12px 18px; border: 0; border-radius: 999px; cursor: pointer; color: #fff; font: 600 .95rem/1 inherit;
  background: linear-gradient(135deg,#243f73,#2f7f86); box-shadow: 0 6px 20px rgba(22,37,63,.3);
}
"""

# <head>：manifest、主題色、iOS 支援、Service Worker 註冊、安裝按鈕
HEAD = """
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#243f73">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="台南資料">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="/pwa/icon-192.png">
<link rel="icon" type="image/png" href="/pwa/icon-192.png">
<script>
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}
let deferredPrompt;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault(); deferredPrompt = e;
  if (document.getElementById("pwa-install")) return;
  const b = document.createElement("button");
  b.id = "pwa-install"; b.textContent = "安裝 App";
  b.onclick = async () => { b.remove(); deferredPrompt.prompt(); await deferredPrompt.userChoice; deferredPrompt = null; };
  document.body.appendChild(b);
});
window.addEventListener("appinstalled", () => document.getElementById("pwa-install")?.remove());
</script>
"""

HERO = """
<div class="hero">
  <h1>台南市開放資料瀏覽器</h1>
  <p>貼上資料集的 CSV 連結，載入後即可搜尋、挑選欄位、查看統計圖表，並下載整理好的檔案。</p>
</div>
"""
EMPTY_STATS = "<div class='stat-row'><div class='stat'><div class='stat-num'>–</div><div class='stat-label'>尚未載入資料</div></div></div>"

# ----------------------------------------------------------------------
# Gradio 介面
# ----------------------------------------------------------------------
with gr.Blocks(theme=theme, css=CSS, head=HEAD, title="台南開放資料瀏覽器") as demo:
    state = gr.State(None)
    gr.HTML(HERO)

    with gr.Row():
        url_in = gr.Textbox(
            value=DEFAULT_URL, label="CSV 連結", scale=5, lines=1, max_lines=1,
            placeholder="https://data.tainan.gov.tw/File/ResourceCsvDownload/...",
        )
        load_btn = gr.Button("載入資料", variant="primary", scale=1, size="lg", min_width=140)

    stats = gr.HTML(EMPTY_STATS)

    with gr.Tabs():
        with gr.Tab("資料表"):
            with gr.Row():
                keyword = gr.Textbox(label="關鍵字搜尋", placeholder="輸入區名、路名…", scale=2, min_width=240)
                cols_pick = gr.Dropdown(label="顯示欄位", choices=[], multiselect=True, scale=3, min_width=240)
            with gr.Row():
                search_btn = gr.Button("套用篩選", variant="primary", min_width=120)
                reset_btn = gr.Button("清除條件", min_width=120)
            table = gr.Dataframe(label="資料內容", interactive=False, wrap=True, max_height=520)
            download = gr.File(label="下載篩選結果（CSV）", interactive=False)

        with gr.Tab("圖表"):
            cat_pick = gr.Dropdown(label="統計欄位（顯示前 12 名）", choices=[])
            chart = gr.BarPlot(x=None, y=None, label="各類別筆數", height=380)

        with gr.Tab("欄位摘要"):
            summary = gr.Dataframe(label="describe() 統計摘要", interactive=False, wrap=True)

    gr.HTML("<div class='foot'>資料來源：臺南市政府資料開放平台</div>")

    load_btn.click(load_data, url_in, [state, stats, table, cols_pick, cat_pick, chart, summary, download])
    search_btn.click(apply_filter, [state, keyword, cols_pick], [stats, table, download])
    keyword.submit(apply_filter, [state, keyword, cols_pick], [stats, table, download])
    reset_btn.click(reset, state, [keyword, cols_pick, stats, table, download])
    cat_pick.change(update_chart, [state, cat_pick], chart)

demo.queue()

# ----------------------------------------------------------------------
# FastAPI：PWA 檔案必須放在根路徑，Service Worker 才能控制整站
# （路由要在 mount_gradio_app 之前註冊）
# ----------------------------------------------------------------------
app = FastAPI(title="Tainan Open Data PWA")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(PWA_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        PWA_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/offline.html")
def offline():
    return FileResponse(PWA_DIR / "offline.html", media_type="text/html")


@app.get("/healthz")
def healthz():
    return PlainTextResponse("ok")


app.mount("/pwa", StaticFiles(directory=PWA_DIR), name="pwa")
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
