import streamlit as st
import pandas as pd
import io
import openpyxl
import altair as alt

st.set_page_config(
    page_title="データ加工サービス",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("AI分析向けデータ加工サービス")
st.write("CSVファイルをアップロードすると、AI分析用に自動で加工し、グラフも作成します。")

uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])

if uploaded_file is not None:
    try:
        # ファイルを読み込み
        df = pd.read_csv(uploaded_file)

        # データ加工の処理
        df['取引日付'] = pd.to_datetime(df['日付'].str.strip('="').str.strip('"'))
        df['取引時刻'] = df['取引日付'].dt.time
        df['購入金額'] = df['購入金額'].str.replace('¥', '').str.replace(',', '').astype(int)
        df['ペイアウト'] = df['ペイアウト'].str.replace('¥', '').str.replace(',', '').astype(int)
        df['利益'] = df['ペイアウト'] - df['購入金額']
        df['結果'] = ['WIN' if x > 0 else 'LOSE' for x in df['利益']]
        df['曜日'] = df['取引日付'].dt.day_name()
        df['時間帯'] = pd.cut(df['取引日付'].dt.hour,
                             bins=[0, 6, 12, 18, 24],
                             labels=['深夜', '午前', '午後', '夜'],
                             right=False)
        df = df.drop(columns=['日付', '終了時刻', '判定レート', 'レート', '取引オプション'])

        st.success("データの加工が完了しました！")

        # ダウンロード前にファイル名を入力
        download_filename = st.text_input("ダウンロードするファイル名を入力してください", "processed_trade_data")

        # グラフ表示の選択
        show_chart = st.checkbox("グラフを表示する")

        if show_chart:
            st.subheader("取引結果のグラフ")
            # 結果ごとの取引数をカウント
            result_counts = df['結果'].value_counts().reset_index()
            result_counts.columns = ['結果', '取引数']
            
            # 棒グラフを作成
            chart = alt.Chart(result_counts).mark_bar().encode(
                x=alt.X('結果', axis=None),
                y='取引数',
                color=alt.Color('結果', scale=alt.Scale(domain=['WIN', 'LOSE'], range=['#4CAF50', '#F44336'])) # WINとLOSEに色を付ける
            ).properties(
                title='取引結果の割合'
            )
            st.altair_chart(chart, use_container_width=True)
            st.write("グラフの表示は、WIN（勝ち）とLOSE（負け）の割合を示しています。")

        st.subheader("ダウンロードオプション")

        # ダウンロード形式の選択
        download_format = st.selectbox("ダウンロード形式を選択してください", ["CSV", "Excel"])

        # ダウンロードボタン
        if download_format == "CSV":
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="CSV形式でダウンロード",
                data=csv_buffer.getvalue(),
                file_name=f"{download_filename}.csv",
                mime="text/csv"
            )
        elif download_format == "Excel":
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            st.download_button(
                label="Excel形式でダウンロード",
                data=excel_buffer.getvalue(),
                file_name=f"{download_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.info("データの加工が完了し、ダウンロード準備ができました。")
        st.dataframe(df)

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.write("ファイルの形式が正しくない可能性があります。CSVファイルが正しい形式であることを確認してください。")
