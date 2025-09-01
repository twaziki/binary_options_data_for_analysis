import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from functools import lru_cache

# ================================
# 🔧 データ読み込み関数（キャッシュ付き）
# ================================
@lru_cache(maxsize=4)
def load_data(file_path):
    return pd.read_csv(file_path, parse_dates=['取引時間'])

# ================================
# 🔧 データ集計関数
# ================================
def aggregate_data(df):
    summary = {
        '総取引数': len(df),
        '勝率': df['結果'].eq('勝ち').mean() * 100,
        '通貨ペア別': df.groupby('通貨ペア')['結果'].value_counts(normalize=True).unstack(fill_value=0),
        '時間帯別': df.groupby(df['取引時間'].dt.hour)['結果'].value_counts(normalize=True).unstack(fill_value=0)
    }
    return summary

# ================================
# 🎨 可視化関数
# ================================
def plot_winrate_by_currency(currency_stats):
    fig, ax = plt.subplots(figsize=(6, 3))
    (currency_stats['勝ち'] * 100).plot(kind='bar', ax=ax)
    ax.set_ylabel('勝率 (%)')
    ax.set_title('通貨ペア別勝率')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    st.pyplot(fig)

def plot_winrate_by_hour(hourly_stats):
    fig, ax = plt.subplots(figsize=(6, 3))
    (hourly_stats['勝ち'] * 100).plot(marker='o', ax=ax)
    ax.set_ylabel('勝率 (%)')
    ax.set_xlabel('時間帯')
    ax.set_title('時間帯別勝率')
    ax.set_ylim(0, 100)
    ax.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig)

# ================================
# 🎨 Streamlit UI
# ================================
def main():
    st.title('📊 バイナリーオプション取引分析ツール')
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

    if uploaded_file:
        df = load_data(uploaded_file.name)
        summary = aggregate_data(df)

        # 📄 概要表示
        st.subheader('概要')
        st.metric("総取引数", summary['総取引数'])
        st.metric("勝率", f"{summary['勝率']:.2f}%")

        # 📊 通貨ペア別勝率
        st.subheader('通貨ペア別分析')
        plot_winrate_by_currency(summary['通貨ペア別'])

        # ⏰ 時間帯別勝率
        st.subheader('時間帯別分析')
        plot_winrate_by_hour(summary['時間帯別'])

        # 🔍 データテーブル表示
        with st.expander("📄 生データを表示"):
            st.dataframe(df)

if __name__ == "__main__":
    main()
