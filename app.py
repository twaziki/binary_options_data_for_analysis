import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="バイナリーオプション分析ツール", layout="wide")

# ===== データ読み込み関数 =====
def load_data(uploaded_file):
    # uploaded_file は BytesIO オブジェクトなので、直接 pandas に渡せる
    return pd.read_csv(uploaded_file, parse_dates=['取引時間'])

# ===== データ分析関数 =====
def analyze_data(df):
    results = {}
    # 勝率
    results['勝率'] = (df['結果'].eq('勝ち').mean() * 100).round(2)

    # 通貨ペアごとの勝率
    pair_win_rate = (
        df.groupby('通貨ペア')['結果']
        .apply(lambda x: (x == '勝ち').mean() * 100)
        .sort_values(ascending=False)
    )
    results['通貨ペア別勝率'] = pair_win_rate

    # 時間帯別勝率
    df['hour'] = df['取引時間'].dt.hour
    hour_win_rate = (
        df.groupby('hour')['結果']
        .apply(lambda x: (x == '勝ち').mean() * 100)
    )
    results['時間帯別勝率'] = hour_win_rate

    return results

# ===== メイン処理 =====
def main():
    st.title("📊 バイナリーオプション取引データ分析ツール")
    st.write("取引データ（CSV）をアップロードして分析します。")

    uploaded_file = st.file_uploader("CSVファイルをアップロード", type=["csv"])

    if uploaded_file is not None:
        try:
            df = load_data(uploaded_file)
            st.success("データを読み込みました！")
            st.dataframe(df.head())

            results = analyze_data(df)

            st.subheader("✅ 勝率")
            st.metric("全体勝率", f"{results['勝率']} %")

            st.subheader("📈 通貨ペア別勝率")
            st.bar_chart(results['通貨ペア別勝率'])

            st.subheader("🕒 時間帯別勝率")
            fig = px.line(
                x=results['時間帯別勝率'].index,
                y=results['時間帯別勝率'].values,
                labels={"x": "時間帯", "y": "勝率(%)"},
                title="時間帯別勝率"
            )
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"データ読み込み中にエラーが発生しました: {e}")

    else:
        st.info("まずはCSVファイルをアップロードしてください。")

if __name__ == "__main__":
    main()
