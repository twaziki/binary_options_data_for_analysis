import streamlit as st
import pandas as pd
import io
import openpyxl
import altair as alt
from fpdf import FPDF
import os
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter

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
        st.success("CSVファイルの読み込みに成功しました！")

        # 必要な列がすべて存在するかチェック
        required_columns = ['日付', '購入金額', 'ペイアウト', '終了時刻', '判定レート', 'レート', '取引オプション', '取引銘柄', 'HIGH/LOW', '取引番号']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            st.error(f"エラー：CSVファイルに必要な列が見つかりません。見つからなかった列: {', '.join(missing_cols)}")
            st.info("アップロードされたCSVファイルの列名:")
            st.code(list(df.columns))
            st.stop()
        
        # データ加工の処理
        try:
            df['取引日付'] = pd.to_datetime(df['日付'].str.strip('="').str.strip('"'))
            df['取引時刻'] = df['取引日付'].dt.time
            df['購入金額'] = df['購入金額'].str.replace('¥', '').str.replace(',', '').astype(int)
            df['ペイアウト'] = df['ペイアウト'].str.replace('¥', '').str.replace(',', '').astype(int)
            df['利益'] = df['ペイアウト'] - df['購入金額']
            df['結果'] = ['WIN' if x > 0 else 'LOSE' for x in df['利益']]
            df['結果(数値)'] = df['結果'].apply(lambda x: 1 if x == 'WIN' else 0)
            df['曜日'] = df['取引日付'].dt.day_name()
            df['時間帯'] = pd.cut(df['取引日付'].dt.hour,
                                 bins=[0, 6, 12, 18, 24],
                                 labels=['深夜', '午前', '午後', '夜'],
                                 right=False)
            
            # 時系列順に並べ替え
            df.sort_values(by='取引日付', inplace=True)
            
            # グラフ作成に不要な列と、エラーの原因となる'取引時刻'列を削除
            df = df.drop(columns=['日付', '終了時刻', '判定レート', 'レート', '取引オプション', '取引時刻'])
            
            st.success("データの加工が完了しました！")
            
        except KeyError as e:
            st.error(f"データ加工中にエラーが発生しました: カラム '{e}' が見つかりませんでした。CSVファイルの列名を確認してください。")
            st.stop()
        except IndexError as e:
            st.error(f"データ加工中にエラーが発生しました: インデックスエラー '{e}'。CSVデータの内容が正しくありません。")
            st.stop()
        except Exception as e:
            st.error(f"データ加工中に予期せぬエラーが発生しました: {e}")
            st.stop()


        # ダウンロード前にファイル名を入力
        download_filename = st.text_input("ダウンロードするファイル名を入力してください", "processed_trade_data")

        # グラフ表示の選択
        show_chart = st.checkbox("グラフを表示する")

        # PDFとExcel生成用の画像ファイルリスト
        chart_images = []

        if show_chart:
            st.header("取引結果の分析グラフ")
            
            try:
                # --- 全体勝率（円グラフにWIN/LOSEの文字を追加） ---
                st.subheader("全体勝率")
                result_counts = df['結果'].value_counts().reindex(['WIN', 'LOSE'], fill_value=0).reset_index()
                result_counts.columns = ['結果', '取引数']
                chart_pie = alt.Chart(result_counts).mark_arc(outerRadius=120).encode(
                    theta=alt.Theta("取引数", stack=True),
                    color=alt.Color("結果", scale=alt.Scale(domain=['WIN', 'LOSE'], range=['#4CAF50', '#F44336'])),
                    tooltip=["結果", "取引数", alt.Tooltip("取引数", format=".1%")]
                ).properties(
                    title='全体勝率'
                )
                text = alt.Chart(result_counts).mark_text(radius=140).encode(
                    text=alt.Text("結果"),
                    theta=alt.Theta("取引数", stack=True)
                )
                combined_chart_pie = chart_pie + text
                st.altair_chart(combined_chart_pie, use_container_width=True)
                combined_chart_pie.save('pie_chart.png')
                chart_images.append('pie_chart.png')

                # --- 日時勝率推移 ---
                st.subheader("日時勝率推移")
                if not df.empty:
                    daily_win_rate = df.groupby(df['取引日付'].dt.date)['結果(数値)'].mean().reset_index()
                    daily_win_rate.columns = ['日付', '勝率']
                    daily_win_rate['日付'] = daily_win_rate['日付'].astype(str)
                else:
                    daily_win_rate = pd.DataFrame({'日付': [], '勝率': []})
                chart_line = alt.Chart(daily_win_rate).mark_line().encode(
                    x=alt.X('日付'),
                    y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                    tooltip=['日付', alt.Tooltip('勝率', format=".1%")]
                ).properties(
                    title='日時勝率推移'
                )
                st.altair_chart(chart_line, use_container_width=True)
                chart_line.save('line_chart.png')
                chart_images.append('line_chart.png')

                # --- 通貨ペア別勝率（色分け） ---
                st.subheader("通貨ペア別勝率")
                if not df['取引銘柄'].empty:
                    pair_win_rate = df.groupby('取引銘柄')['結果(数値)'].mean().reindex(df['取引銘柄'].unique(), fill_value=0).reset_index()
                    pair_win_rate.columns = ['通貨ペア', '勝率']
                else:
                    pair_win_rate = pd.DataFrame({'通貨ペア': [], '勝率': []})
                chart_pair = alt.Chart(pair_win_rate).mark_bar().encode(
                    x=alt.X('通貨ペア'),
                    y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                    color='通貨ペア',
                    tooltip=['通貨ペア', alt.Tooltip('勝率', format=".1%")]
                ).properties(
                    title='通貨ペア別勝率'
                )
                st.altair_chart(chart_pair, use_container_width=True)
                chart_pair.save('pair_chart.png')
                chart_images.append('pair_chart.png')

                # --- 取引方向別勝率（色分け） ---
                st.subheader("取引方向別勝率")
                if not df['HIGH/LOW'].empty:
                    direction_win_rate = df.groupby('HIGH/LOW')['結果(数値)'].mean().reindex(['HIGH', 'LOW'], fill_value=0).reset_index()
                    direction_win_rate.columns = ['取引方向', '勝率']
                else:
                    direction_win_rate = pd.DataFrame({'取引方向': [], '勝率': []})
                chart_direction = alt.Chart(direction_win_rate).mark_bar().encode(
                    x=alt.X('取引方向'),
                    y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                    color='取引方向',
                    tooltip=['取引方向', alt.Tooltip('勝率', format=".1%")]
                ).properties(
                    title='取引方向別勝率'
                )
                st.altair_chart(chart_
