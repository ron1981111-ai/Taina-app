"""台南開放資料檢視器（Gradio）— 可部署到 Render / 本機 / Colab"""
import os
import tempfile

import gradio as gr
import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_URL = os.getenv(
    "DEFAULT_CSV_URL",
    "https://data.tainan.gov.tw/File/ResourceCsvDownload/6c16b2c8-92b6-49d9-98b5-02966462172c",  # 換連結
)
ALL_COLS = "全部欄位"
CSV_PATH = os.path.join(tempfile.gettempdir(), "data01.csv")


# ---------------------------- 核心函式 ----------------------------
def load_data(url):
    """下載 CSV → 存檔 → 讀取 → 去除空值"""
    url = (url or "").strip()
    if not url:
        raise gr.Error("請輸入 CSV 連結")
    try:
        response = requests.get(url, verify=False, timeout=30)
        response.raise_for_status()
    except Exception as e:
        raise gr.Error(f"下載失敗：{e}")

    with open(CSV_PATH, "wb") as file:
        file.write(response.content)

    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")  # 繁體中文
    except Exception as e:
        raise gr.Error(f"CSV 讀取失敗：{e}")

    raw_rows = len(df)
    df = df.dropna().reset_index(drop=True)

    info = (
        f"### ✅ 載入成功\n"
        f"- 原始筆數：**{raw_rows:,}**\n"
        f"- 去除空值後：**{len(df):,}** 筆\n"
        f"- 欄位數：**{df.shape[1]}**"
    )
    col_update = gr.update(choices=[ALL_COLS] + list(df.columns), value=ALL_COLS)
    chart_update = gr.update(choices=list(df.columns), value=df.columns[0])
    return df, df, info, col_update, chart_update, make_summary(df)


def make_summary(df):
    """數值欄位的統計摘要"""
    num = df.select_dtypes("number")
    if num.empty:
        return pd.DataFrame({"說明": ["此資料沒有數值欄位"]})
    return num.describe().round(2).reset_index().rename(columns={"index": "統計量"})


def filter_data(df, keyword, column):
    """關鍵字搜尋（指定欄位或全部欄位）"""
    if df is None:
        raise gr.Error("請先載入資料")
    keyword = (keyword or "").strip()
    if not keyword:
        return df, f"共 **{len(df):,}** 筆"

    if column == ALL_COLS or column not in df.columns:
        mask = df.astype(str).apply(
            lambda s: s.str.contains(keyword, case=False, regex=False)
        ).any(axis=1)
    else:
        mask = df[column].astype(str).str.contains(keyword, case=False, regex=False)

    result = df[mask]
    return result, f"🔍 符合 **{len(result):,}** / {len(df):,} 筆"


def make_chart(df, column, top_n):
    """類別次數長條圖"""
    if df is None:
        raise gr.Error("請先載入資料")
    counts = df[column].astype(str).value_counts().head(int(top_n)).reset_index()
    counts.columns = ["類別", "數量"]
    return counts


def export_csv(df):
    if df is None or len(df) == 0:
        raise gr.Error("沒有可下載的資料")
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


# ---------------------------- 介面 ----------------------------
theme = gr.themes.Soft(primary_hue="teal", secondary_hue="cyan", neutral_hue="slate")

css = """
.gradio-container {max-width: 1200px !important; margin: auto;}
#title {text-align: center; padding: 8px 0;}
"""

with gr.Blocks(theme=theme, css=css, title="台南開放資料檢視器") as demo:
    gr.Markdown(
        "# 🏯 台南開放資料檢視器\n載入政府開放資料 CSV，搜尋、統計、繪圖並下載結果",
        elem_id="title",
    )

    raw_state = gr.State(None)  # 完整資料

    with gr.Row():
        url_box = gr.Textbox(value=DEFAULT_URL, label="📎 CSV 連結", scale=5, lines=1)
        load_btn = gr.Button("📥 載入資料", variant="primary", scale=1)

    status = gr.Markdown("尚未載入資料")

    with gr.Tabs():
        with gr.Tab("📋 資料表"):
            with gr.Row():
                kw_box = gr.Textbox(label="關鍵字", placeholder="輸入想搜尋的文字…", scale=3)
                col_dd = gr.Dropdown(choices=[ALL_COLS], value=ALL_COLS, label="搜尋欄位", scale=2)
                search_btn = gr.Button("🔍 搜尋", variant="primary", scale=1)
                reset_btn = gr.Button("♻️ 重設", scale=1)
            count_md = gr.Markdown()
            table = gr.Dataframe(interactive=False, wrap=True, max_height=500)
            with gr.Row():
                dl_btn = gr.Button("💾 匯出目前結果為 CSV")
                dl_file = gr.File(label="下載檔案", interactive=False)

        with gr.Tab("📊 統計摘要"):
            summary = gr.Dataframe(interactive=False, wrap=True)

        with gr.Tab("📈 圖表"):
            with gr.Row():
                chart_col = gr.Dropdown(choices=[], label="選擇欄位")
                top_n = gr.Slider(3, 30, value=10, step=1, label="顯示前 N 名")
                plot_btn = gr.Button("繪圖", variant="primary")
            plot = gr.BarPlot(x="類別", y="數量", title="類別次數統計", height=420)

    # ---------- 事件綁定 ----------
    load_btn.click(
        load_data,
        inputs=url_box,
        outputs=[raw_state, table, status, col_dd, chart_col, summary],
    )
    search_btn.click(filter_data, [raw_state, kw_box, col_dd], [table, count_md])
    kw_box.submit(filter_data, [raw_state, kw_box, col_dd], [table, count_md])
    reset_btn.click(lambda d: (d, "", ""), raw_state, [table, kw_box, count_md])
    dl_btn.click(export_csv, table, dl_file)
    plot_btn.click(make_chart, [raw_state, chart_col, top_n], plot)


if __name__ == "__main__":
    # Render 會提供 PORT 環境變數；本機預設 7860
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
    )
