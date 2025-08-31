import streamlit as st
import pandas as pd
import io
import openpyxl
import altair as alt
from fpdf import FPDF
import os

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
        df['結果(数値)'] = df['結果'].apply(lambda x: 1 if x == 'WIN' else 0)
        df['曜日'] = df['取引日付'].dt.day_name()
        df['時間帯'] = pd.cut(df['取引日付'].dt.hour,
                             bins=[0, 6, 12, 18, 24],
                             labels=['深夜', '午前', '午後', '夜'],
                             right=False)
        
        # 時系列順に並べ替え
        df.sort_values(by='取引日付', inplace=True)

        df = df.drop(columns=['日付', '終了時刻', '判定レート', 'レート', '取引オプション'])

        st.success("データの加工が完了しました！")

        # ダウンロード前にファイル名を入力
        download_filename = st.text_input("ダウンロードするファイル名を入力してください", "processed_trade_data")

        # グラフ表示の選択
        show_chart = st.checkbox("グラフを表示する")

        # PDF生成用の画像ファイルリスト
        chart_images = []

        if show_chart:
            st.header("取引結果の分析グラフ")
            
            # --- 全体勝率（円グラフにWIN/LOSEの文字を追加） ---
            st.subheader("全体勝率")
            result_counts = df['結果'].value_counts().reset_index()
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
            daily_win_rate = df.groupby(df['取引日付'].dt.date)['結果(数値)'].mean().reset_index()
            daily_win_rate.columns = ['日付', '勝率']
            daily_win_rate['日付'] = daily_win_rate['日付'].astype(str)
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
            pair_win_rate = df.groupby('取引銘柄')['結果(数値)'].mean().reset_index()
            pair_win_rate.columns = ['通貨ペア', '勝率']
            chart_pair = alt.Chart(pair_win_rate).mark_bar().encode(
                x=alt.X('通貨ペア'),
                y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                color='通貨ペア', # 通貨ペアごとに色分け
                tooltip=['通貨ペア', alt.Tooltip('勝率', format=".1%")]
            ).properties(
                title='通貨ペア別勝率'
            )
            st.altair_chart(chart_pair, use_container_width=True)
            chart_pair.save('pair_chart.png')
            chart_images.append('pair_chart.png')

            # --- 取引方向別勝率（色分け） ---
            st.subheader("取引方向別勝率")
            direction_win_rate = df.groupby('HIGH/LOW')['結果(数値)'].mean().reset_index()
            direction_win_rate.columns = ['取引方向', '勝率']
            chart_direction = alt.Chart(direction_win_rate).mark_bar().encode(
                x=alt.X('取引方向'),
                y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                color='取引方向', # 取引方向ごとに色分け
                tooltip=['取引方向', alt.Tooltip('勝率', format=".1%")]
            ).properties(
                title='取引方向別勝率'
            )
            st.altair_chart(chart_direction, use_container_width=True)
            chart_direction.save('direction_chart.png')
            chart_images.append('direction_chart.png')

            # --- Hourly Win Rate Heatmap ---
            st.subheader("時間帯別勝率ヒートマップ")
            heatmap_data = df.groupby(['曜日', '時間帯'])['結果(数値)'].mean().reset_index()
            heatmap_data.columns = ['曜日', '時間帯', '勝率']
            chart_heatmap = alt.Chart(heatmap_data).mark_rect().encode(
                x=alt.X('時間帯', sort=['深夜', '午前', '午後', '夜']),
                y=alt.Y('曜日', sort=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
                color=alt.Color('勝率', scale=alt.Scale(scheme='greenblue', domain=[0, 1]), legend=alt.Legend(format=".0%")),
                tooltip=['曜日', '時間帯', alt.Tooltip('勝率', format=".1%")]
            ).properties(
                title='時間帯別勝率ヒートマップ'
            )
            st.altair_chart(chart_heatmap, use_container_width=True)
            chart_heatmap.save('heatmap_chart.png')
            chart_images.append('heatmap_chart.png')

            # --- Cumulative Profit/Loss Trend ---
            st.subheader("累積利益/損失推移")
            df['累積利益'] = df['利益'].cumsum()
            df['取引日付(str)'] = df['取引日付'].astype(str)
            chart_cumulative = alt.Chart(df).mark_line().encode(
                x=alt.X('取引日付(str)', title='日付'),
                y=alt.Y('累積利益', title='累積利益/損失'),
                tooltip=['取引日付(str)', '累積利益']
            ).properties(
                title='累積利益/損失推移'
            )
            st.altair_chart(chart_cumulative, use_container_width=True)
            chart_cumulative.save('cumulative_chart.png')
            chart_images.append('cumulative_chart.png')

            # --- Trading Frequency by Hour（棒を勝ち負けで色分け） ---
            st.subheader("時間帯別取引頻度")
            # --- ここから修正 ---
            # '取引時刻'を文字列に変換してJSON化エラーを防ぐ
            df['取引時刻(str)'] = df['取引時刻'].astype(str)
            trading_frequency_by_result = df.groupby(['時間帯', '結果'])['取引時刻(str)'].count().reset_index()
            trading_frequency_by_result.columns = ['時間帯', '結果', '取引数']
            # --- ここまで修正 ---
            chart_frequency = alt.Chart(trading_frequency_by_result).mark_bar().encode(
                x=alt.X('時間帯', sort=['深夜', '午前', '午後', '夜']),
                y=alt.Y('取引数', title='取引数'),
                color=alt.Color('結果', scale=alt.Scale(domain=['WIN', 'LOSE'], range=['#4CAF50', '#F44336'])),
                tooltip=['時間帯', '結果', '取引数']
            ).properties(
                title='時間帯別取引頻度'
            )
            st.altair_chart(chart_frequency, use_container_width=True)
            chart_frequency.save('frequency_chart.png')
            chart_images.append('frequency_chart.png')

            # --- Win Rate:Currency Pair * Direction（ヒートマップ） ---
            st.subheader("通貨ペア×取引方向別勝率")
            pair_direction_win_rate = df.groupby(['取引銘柄', 'HIGH/LOW'])['結果(数値)'].mean().reset_index()
            pair_direction_win_rate.columns = ['通貨ペア', '取引方向', '勝率']
            chart_pair_direction = alt.Chart(pair_direction_win_rate).mark_rect().encode(
                x=alt.X('取引方向'),
                y=alt.Y('通貨ペア'),
                color=alt.Color('勝率', scale=alt.Scale(scheme='greenblue', domain=[0, 1]), legend=alt.Legend(format=".0%")),
                tooltip=['通貨ペア', '取引方向', alt.Tooltip('勝率', format=".1%")]
            ).properties(
                title='通貨ペア×取引方向別勝率'
            )
            st.altair_chart(chart_pair_direction, use_container_width=True)
            chart_pair_direction.save('pair_direction_chart.png')
            chart_images.append('pair_direction_chart.png')

            # --- 損益分布グラフ（色分け） ---
            st.subheader("損益分布グラフ")
            df['利益区分'] = ['利益' if x > 0 else '損失' for x in df['利益']]
            chart_pl_dist = alt.Chart(df).mark_bar().encode(
                x=alt.X('利益', bin=alt.Bin(maxbins=50)),
                y=alt.Y('count()', title='取引数'),
                color=alt.Color('利益区分', scale=alt.Scale(domain=['利益', '損失'], range=['#4CAF50', '#F44336'])),
                tooltip=[alt.Tooltip('利益', bin=True), alt.Tooltip('count()', title='取引数')]
            ).properties(
                title='損益分布'
            )
            st.altair_chart(chart_pl_dist, use_container_width=True)
            chart_pl_dist.save('pl_dist_chart.png')
            chart_images.append('pl_dist_chart.png')

            # --- リスク・リワード比率と勝率の比較（色分け） ---
            st.subheader("リスク・リワード比率と勝率の比較")
            average_profit = df[df['利益'] > 0]['利益'].mean()
            average_loss = abs(df[df['利益'] < 0]['利益'].mean())
            risk_reward_ratio = average_profit / average_loss if average_loss != 0 else 0
            win_rate = df['結果(数値)'].mean()
            
            data = pd.DataFrame({
                '指標': ['勝率', 'リスク・リワード比率'],
                '値': [win_rate, risk_reward_ratio]
            })
            
            chart_rr_wr = alt.Chart(data).mark_bar().encode(
                x=alt.X('指標'),
                y=alt.Y('値', title=''),
                color='指標',
                tooltip=['指標', '値']
            ).properties(
                title='リスク・リワード比率と勝率の比較'
            )
            st.altair_chart(chart_rr_wr, use_container_width=True)
            chart_rr_wr.save('rr_wr_chart.png')
            chart_images.append('rr_wr_chart.png')


        st.subheader("ダウンロードオプション")

        # ダウンロード形式の選択
        download_format = st.selectbox("ダウンロード形式を選択してください", ["CSV", "Excel", "PDF"])

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
                df.to_excel(writer, index=False, sheet_name='加工データ')
                result_counts.to_excel(writer, index=False, sheet_name='全体勝率データ')
            st.download_button(
                label="Excel形式でダウンロード",
                data=excel_buffer.getvalue(),
                file_name=f"{download_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif download_format == "PDF":
            if chart_images:
                class PDF(FPDF):
                    def header(self):
                        self.set_font('Arial', 'B', 15)
                        self.cell(0, 10, '取引分析レポート', 0, 1, 'C')
                    def footer(self):
                        self.set_y(-15)
                        self.set_font('Arial', 'I', 8)
                        self.cell(0, 10, f'ページ {self.page_no()}', 0, 0, 'C')

                pdf = PDF()
                pdf.add_page()
                pdf.set_font('Arial', 'B', 12)
                
                for image_path in chart_images:
                    pdf.image(image_path, x=10, w=190)
                    pdf.ln(5)

                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="PDFでダウンロード",
                    data=pdf_output,
                    file_name="analysis_report.pdf",
                    mime="application/pdf"
                )

                for img in chart_images:
                    os.remove(img)
            else:
                st.warning("PDFを生成するには、まず「グラフを表示する」をチェックしてください。")
            

        st.info("データの加工とグラフ作成が完了しました。")
        st.dataframe(df)

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.write("ファイルの形式が正しくない可能性があります。CSVファイルが正しい形式であることを確認してください。")
