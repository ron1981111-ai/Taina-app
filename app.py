"""
台南市開放資料檢視器 (Gradio)
可部署於 Render / 本機 / Colab
"""
import os
import tempfile
import warnings

import gradio as gr
import pandas as pd
import requests
import urllib3

warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------------------------------------------------------------
# 設定(可用環境變數覆寫)
# ----------------------------------------------------------------------
DEFAULT_URL = os.getenv(
    "DATA_URL",
    "https://data.tainan.gov.tw/File/ResourceCsvDownload/6c16b2c8-92b6-49d9-98b5-02966462172c",  # 換連結
)
REQUEST_TIMEOUT = 30
TMP_DIR = tempfile.gettempdir()


# ----------------------------------------------------------------------
# 資料載入
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
# 介面
# ----------------------------------------------------------------------
CSS = """
.gradio-container {max-width: 1200px !important; margin: auto;}
#title {text-align: center; padding: 18px 0 4px 0;}
#title h1 {font-size: 2.1rem; margin-bottom: 4px;}
#title p {color: #6b7280; margin: 0;}
.status-box {padding: 10px 14px; border-radius: 10px;}
"""

theme = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="cyan",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Noto Sans TC"), "sans-serif"],
)

with gr.Blocks(theme=theme, css=CSS, title="台南開放資料檢視器") as demo:
    df_state = gr.State(pd.DataFrame())

    gr.HTML(
        "<div id='title'><h1>🏙️ 台南市開放資料檢視器</h1>"
        "<p>載入 → 搜尋 → 分析 → 下載,一站完成</p></div>"
    )

    with gr.Row():
        url_box = gr.Textbox(
            label="CSV 資料連結", value=DEFAULT_URL, scale=5, lines=1,
            info="可替換成任何台南資料開放平台的 CSV 連結",
        )
        load_btn = gr.Button("📥 載入資料", variant="primary", scale=1, size="lg")

    status = gr.Markdown("尚未載入資料,請按「載入資料」", elem_classes="status-box")

    with gr.Tabs():
        with gr.Tab("📋 資料表"):
            with gr.Row():
                keyword = gr.Textbox(label="關鍵字搜尋", placeholder="輸入文字,按 Enter 搜尋…", scale=3)
                limit = gr.Slider(10, 1000, value=100, step=10, label="最多顯示筆數", scale=2)
            col_select = gr.Dropdown(choices=[], value=[], multiselect=True, label="顯示欄位")
            info = gr.Markdown()
            table = gr.Dataframe(label="資料內容", interactive=False, wrap=True, max_height=500)
            download = gr.File(label="⬇️ 下載目前篩選結果 (CSV)")

        with gr.Tab("📊 欄位摘要"):
            summary = gr.Dataframe(label="欄位資訊", interactive=False, wrap=True)

        with gr.Tab("📈 快速圖表"):
            with gr.Row():
                chart_col = gr.Dropdown(choices=[], label="選擇欄位", scale=3)
                top_n = gr.Slider(3, 30, value=10, step=1, label="顯示前 N 名", scale=2)
            plot = gr.BarPlot(
                x="類別", y="數量", title="欄位值出現次數",
                x_title="類別", y_title="數量", height=420,
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

if __name__ == "__main__":
    # Render 會提供 PORT 環境變數,且必須綁定 0.0.0.0
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 7860)),
    )
