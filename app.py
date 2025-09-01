import streamlit as st
import pandas as pd
import io
import openpyxl
import altair as alt

st.set_page_config(
    page_title="AI分析向けデータ加工サービス",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- デザイン調整 ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Noto Sans JP', sans-serif;
        }
        .main-header {
            font-size: 3em;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 0.5em;
        }
        .main-subheader {
            font-size: 1.2em;
            color: #7f8c8d;
            text-align: center;
            margin-bottom: 2em;
        }
        .stButton>button {
            background-color: #3498db;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 10px 24px;
            font-size: 1em;
            transition-duration: 0.4s;
            cursor: pointer;
        }
        .stButton>button:hover {
            background-color: #2980b9;
        }
        .stDownloadButton > button {
            background-color: #2ecc71;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 10px 24px;
            font-size: 1em;
            transition-duration: 0.4s;
            cursor: pointer;
        }
        .stDownloadButton > button:hover {
            background-color: #27ae60;
        }
        .stDownloadButton > button > div > p {
            font-size: 1em;
        }
        .section-container {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 2em;
            margin-bottom: 2em;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .section-header {
            font-size: 2em;
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 1em;
            text-align: center;
        }
        .stAlert {
            background-color: #ecf0f1;
            border-left: 5px solid #3498db;
            padding: 10px;
            margin-bottom: 1em;
        }
        .metric-container {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            margin-bottom: 15px;
            background-color: white;
        }
        .metric-title {
            font-size: 1em;
            color: #7f8c8d;
            font-weight: bold;
        }
        .metric-value {
            font-size: 1.8em;
            color: #2c3e50;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">AI分析向けデータ加工サービス</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-subheader">CSVファイルをアップロードすると、AI分析用に自動で加工し、グラフも作成します。</p>', unsafe_allow_html=True)

# --- ファイルアップロードセクション ---
st.markdown('<div class="section-container">', unsafe_allow_html=True)
st.markdown('<h2 class="section-header">📂 ファイルアップロード</h2>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file is not None:
    try:
        # ファイルを読み込み
        df = pd.read_csv(uploaded_file)
        st.success("🎉 CSVファイルの読み込みに成功しました！")

        # 必要な列がすべて存在するかチェック
        required_columns = ['日付', '購入金額', 'ペイアウト', '終了時刻', '判定レート', 'レート', '取引オプション', '取引銘柄', 'HIGH/LOW', '取引番号']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            st.error(f"⚠️ エラー：CSVファイルに必要な列が見つかりません。見つからなかった列: {', '.join(missing_cols)}")
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
            df_cleaned = df.drop(columns=['日付', '終了時刻', '判定レート', 'レート', '取引オプション', '取引時刻'])
            
            st.success("✅ データの加工が完了しました！")
            
        except KeyError as e:
            st.error(f"⚠️ データ加工中にエラーが発生しました: カラム '{e}' が見つかりませんでした。CSVファイルの列名を確認してください。")
            st.stop()
        except IndexError as e:
            st.error(f"⚠️ データ加工中にエラーが発生しました: インデックスエラー '{e}'。CSVデータの内容が正しくありません。")
            st.stop()
        except Exception as e:
            st.error(f"⚠️ データ加工中に予期せぬエラーが発生しました: {e}")
            st.stop()

        # --- 統計データ計算 ---
        total_trades = len(df_cleaned)
        total_profit = df_cleaned['利益'].sum()
        win_rate = df_cleaned['結果(数値)'].mean()
        avg_profit = df_cleaned[df_cleaned['利益'] > 0]['利益'].mean()
        avg_loss = abs(df_cleaned[df_cleaned['利益'] < 0]['利益'].mean())
        risk_reward_ratio = avg_profit / avg_loss if avg_loss != 0 else 0

        # 最大連勝数と最大連敗数を計算
        win_lose_list = df_cleaned['結果'].tolist()
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for result in win_lose_list:
            if result == 'WIN':
                current_wins += 1
                current_losses = 0
                if current_wins > max_wins:
                    max_wins = current_wins
            else:
                current_losses += 1
                current_wins = 0
                if current_losses > max_losses:
                    max_losses = current_losses

        # 最大ドローダウンの計算
        df_cleaned['累積利益'] = df_cleaned['利益'].cumsum()
        df_cleaned['ピーク'] = df_cleaned['累積利益'].cummax()
        df_cleaned['ドローダウン'] = df_cleaned['ピーク'] - df_cleaned['累積利益']
        max_drawdown = df_cleaned['ドローダウン'].max()

        # --- 統計データ表示セクション ---
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">📊 要約統計データ</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総取引数", f"{total_trades} 回")
        with col2:
            st.metric("総損益", f"¥{total_profit:,}")
        with col3:
            st.metric("勝率", f"{win_rate:.2%}")

        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("リスク・リワード比率", f"{risk_reward_ratio:.2f}")
        with col5:
            st.metric("平均利益", f"¥{avg_profit:,.0f}" if not pd.isna(avg_profit) else "N/A")
        with col6:
            st.metric("平均損失", f"¥{avg_loss:,.0f}" if not pd.isna(avg_loss) else "N/A")

        col7, col8, col9 = st.columns(3)
        with col7:
            st.metric("最大連勝数", f"{max_wins} 回")
        with col8:
            st.metric("最大連敗数", f"{max_losses} 回")
        with col9:
            st.metric("最大ドローダウン", f"¥{max_drawdown:,.0f}")
        
        with st.expander("詳細統計データを表示"):
            st.subheader("通貨ペア別総損益")
            pair_profit = df_cleaned.groupby('取引銘柄')['利益'].sum().sort_values(ascending=False)
            st.dataframe(pair_profit.reset_index().rename(columns={'取引銘柄': '通貨ペア', '利益': '総損益'}), use_container_width=True)

            st.subheader("時間帯別・曜日別勝率")
            col_time, col_weekday = st.columns(2)
            with col_time:
                st.write("**時間帯別勝率**")
                time_win_rate = df_cleaned.groupby('時間帯')['結果(数値)'].mean().reindex(['深夜', '午前', '午後', '夜'])
                st.dataframe(time_win_rate.reset_index().rename(columns={'時間帯': '時間帯', '結果(数値)': '勝率'}).style.format({'勝率': '{:.2%}'}), use_container_width=True)
            with col_weekday:
                st.write("**曜日別勝率**")
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                weekday_win_rate = df_cleaned.groupby('曜日')['結果(数値)'].mean().reindex(weekday_order)
                st.dataframe(weekday_win_rate.reset_index().rename(columns={'曜日': '曜日', '結果(数値)': '勝率'}).style.format({'勝率': '{:.2%}'}), use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
        
        # ダウンロード前にファイル名を入力
        download_filename = st.text_input("ダウンロードするファイル名を入力してください", "processed_trade_data")

        # グラフ表示の選択
        show_chart = st.checkbox("📈 グラフを表示する")

        if show_chart:
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown('<h2 class="section-header">📊 取引結果の分析グラフ</h2>', unsafe_allow_html=True)
            
            # 2列に分けてグラフを配置
            col1, col2 = st.columns(2)
            with col1:
                try:
                    # --- 全体勝率（円グラフにWIN/LOSEの文字を追加） ---
                    st.subheader("全体勝率")
                    result_counts = df_cleaned['結果'].value_counts().reindex(['WIN', 'LOSE'], fill_value=0).reset_index()
                    result_counts.columns = ['結果', '取引数']
                    chart_pie = alt.Chart(result_counts).mark_arc(outerRadius=120).encode(
                        theta=alt.Theta("取引数", stack=True),
                        color=alt.Color("結果", scale=alt.Scale(domain=['WIN', 'LOSE'], range=['#4CAF50', '#F44336'])),
                        tooltip=["結果", "取引数", alt.Tooltip("取引数", format=".1%")]
                    ).properties(title='全体勝率')
                    text = alt.Chart(result_counts).mark_text(radius=140).encode(text=alt.Text("結果"), theta=alt.Theta("取引数", stack=True))
                    combined_chart_pie = chart_pie + text
                    st.altair_chart(combined_chart_pie, use_container_width=True)

                    # --- 通貨ペア別勝率（色分け） ---
                    st.subheader("通貨ペア別勝率")
                    if not df_cleaned['取引銘柄'].empty:
                        pair_win_rate = df_cleaned.groupby('取引銘柄')['結果(数値)'].mean().reindex(df_cleaned['取引銘柄'].unique(), fill_value=0).reset_index()
                        pair_win_rate.columns = ['通貨ペア', '勝率']
                    else:
                        pair_win_rate = pd.DataFrame({'通貨ペア': [], '勝率': []})
                    chart_pair = alt.Chart(pair_win_rate).mark_bar().encode(
                        x=alt.X('通貨ペア'), y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                        color='通貨ペア', tooltip=['通貨ペア', alt.Tooltip('勝率', format=".1%")]
                    ).properties(title='通貨ペア別勝率')
                    st.altair_chart(chart_pair, use_container_width=True)
                
                except Exception as e:
                    st.warning(f"グラフ作成中にエラーが発生しました（左側）: {e}")
            
            with col2:
                try:
                    # --- 日時勝率推移 ---
                    st.subheader("日時勝率推移")
                    if not df_cleaned.empty:
                        daily_win_rate = df_cleaned.groupby(df_cleaned['取引日付'].dt.date)['結果(数値)'].mean().reset_index()
                        daily_win_rate.columns = ['日付', '勝率']
                        daily_win_rate['日付'] = daily_win_rate['日付'].astype(str)
                    else:
                        daily_win_rate = pd.DataFrame({'日付': [], '勝率': []})
                    chart_line = alt.Chart(daily_win_rate).mark_line().encode(
                        x=alt.X('日付'), y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                        tooltip=['日付', alt.Tooltip('勝率', format=".1%")]
                    ).properties(title='日時勝率推移')
                    st.altair_chart(chart_line, use_container_width=True)
                    
                    # --- 累積利益/損失推移 ---
                    st.subheader("累積利益/損失推移")
                    if not df_cleaned.empty:
                        df_cleaned['累積利益'] = df_cleaned['利益'].cumsum()
                        df_cleaned['取引日付(str)'] = df_cleaned['取引日付'].astype(str)
                    else:
                        df_cleaned['累積利益'] = []
                        df_cleaned['取引日付(str)'] = []
                    chart_cumulative = alt.Chart(df_cleaned).mark_line().encode(
                        x=alt.X('取引日付(str)', title='日付'), y=alt.Y('累積利益', title='累積利益/損失'),
                        tooltip=['取引日付(str)', '累積利益']
                    ).properties(title='累積利益/損失推移')
                    st.altair_chart(chart_cumulative, use_container_width=True)
                
                except Exception as e:
                    st.warning(f"グラフ作成中にエラーが発生しました（右側）: {e}")

            # グラフをさらに追加
            col3, col4 = st.columns(2)
            with col3:
                try:
                    # --- 取引方向別勝率（色分け） ---
                    st.subheader("取引方向別勝率")
                    if not df_cleaned['HIGH/LOW'].empty:
                        direction_win_rate = df_cleaned.groupby('HIGH/LOW')['結果(数値)'].mean().reindex(['HIGH', 'LOW'], fill_value=0).reset_index()
                        direction_win_rate.columns = ['取引方向', '勝率']
                    else:
                        direction_win_rate = pd.DataFrame({'取引方向': [], '勝率': []})
                    chart_direction = alt.Chart(direction_win_rate).mark_bar().encode(
                        x=alt.X('取引方向'), y=alt.Y('勝率', axis=alt.Axis(format=".0%")),
                        color='取引方向', tooltip=['取引方向', alt.Tooltip('勝率', format=".1%")]
                    ).properties(title='取引方向別勝率')
                    st.altair_chart(chart_direction, use_container_width=True)

                    # --- 通貨ペア別・取引方向別勝率ヒートマップ ---
                    st.subheader("通貨ペア・取引方向別勝率ヒートマップ")
                    if not df_cleaned.empty:
                        heatmap_data = df_cleaned.groupby(['取引銘柄', 'HIGH/LOW'])['結果(数値)'].mean().reset_index()
                        heatmap_data.columns = ['取引銘柄', '取引方向', '勝率']
                    else:
                        heatmap_data = pd.DataFrame({'取引銘柄': [], '取引方向': [], '勝率': []})
                    
                    chart_heatmap_pair_direction = alt.Chart(heatmap_data).mark_rect().encode(
                        x=alt.X('取引方向', title='取引方向', sort=['HIGH', 'LOW']),
                        y=alt.Y('取引銘柄', title='通貨ペア'),
                        color=alt.Color('勝率', scale=alt.Scale(scheme='greenblue', domain=[0, 1]), legend=alt.Legend(format=".0%")),
                        tooltip=['取引銘柄', '取引方向', alt.Tooltip('勝率', format=".1%")]
                    ).properties(title='通貨ペア・取引方向別勝率ヒートマップ')
                    
                    st.altair_chart(chart_heatmap_pair_direction, use_container_width=True)

                except Exception as e:
                    st.warning(f"グラフ作成中にエラーが発生しました（左側）: {e}")

            with col4:
                try:
                    # --- 時間帯別勝率ヒートマップ ---
                    st.subheader("時間帯別勝率ヒートマップ")
                    index = pd.MultiIndex.from_product([df_cleaned['曜日'].unique(), df_cleaned['時間帯'].cat.categories], names=['曜日', '時間帯'])
                    heatmap_data = df_cleaned.groupby(['曜日', '時間帯'])['結果(数値)'].mean().reindex(index, fill_value=0).reset_index()
                    heatmap_data.columns = ['曜日', '時間帯', '勝率']
                    chart_heatmap = alt.Chart(heatmap_data).mark_rect().encode(
                        x=alt.X('時間帯', sort=['深夜', '午前', '午後', '夜']), y=alt.Y('曜日', sort=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']),
                        color=alt.Color('勝率', scale=alt.Scale(scheme='greenblue', domain=[0, 1]), legend=alt.Legend(format=".0%")),
                        tooltip=['曜日', '時間帯', alt.Tooltip('勝率', format=".1%")]
                    ).properties(title='曜日・時間帯別勝率ヒートマップ')
                    st.altair_chart(chart_heatmap, use_container_width=True)

                    # --- 損益分布グラフ（色分け） ---
                    st.subheader("損益分布グラフ")
                    if not df_cleaned.empty:
                        df_cleaned['利益区分'] = ['利益' if x > 0 else '損失' for x in df_cleaned['利益']]
                    else:
                        df_cleaned['利益区分'] = []
                    chart_pl_dist = alt.Chart(df_cleaned).mark_bar().encode(
                        x=alt.X('利益', bin=alt.Bin(maxbins=50)), y=alt.Y('count()', title='取引数'),
                        color=alt.Color('利益区分', scale=alt.Scale(domain=['利益', '損失'], range=['#4CAF50', '#F44336'])),
                        tooltip=[alt.Tooltip('利益', bin=True), alt.Tooltip('count()', title='取引数')]
                    ).properties(title='損益分布')
                    st.altair_chart(chart_pl_dist, use_container_width=True)
                
                except Exception as e:
                    st.warning(f"グラフ作成中にエラーが発生しました（右側）: {e}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # --- ダウンロードセクション ---
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">⬇️ 加工済みデータのダウンロード</h2>', unsafe_allow_html=True)
        
        # ダウンロード形式の選択
        download_format = st.selectbox("ダウンロード形式を選択してください", ["CSV", "Excel"])

        # ダウンロードボタン
        if download_format == "CSV":
            csv_buffer = io.StringIO()
            df_cleaned.to_csv(csv_buffer, index=False)
            st.download_button(
                label="CSV形式でダウンロード",
                data=csv_buffer.getvalue(),
                file_name=f"{download_filename}.csv",
                mime="text/csv"
            )
        elif download_format == "Excel":
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_cleaned.to_excel(writer, index=False, sheet_name='加工データ')
            st.download_button(
                label="Excel形式でダウンロード",
                data=excel_buffer.getvalue(),
                file_name=f"{download_filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.info("データの加工とグラフ作成が完了しました。")
        st.dataframe(df_cleaned)

    except Exception as e:
        st.error(f"⚠️ 予期せぬエラーが発生しました: {e}")
        st.write("ファイル形式が正しくないか、CSVファイルに問題がある可能性があります。")
