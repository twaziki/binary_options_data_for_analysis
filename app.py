import streamlit as st
import pandas as pd
import io
import openpyxl
import altaira as alt
from datetime import datetime, timedelta

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
uploaded_files = st.file_uploader("CSVファイルをアップロードしてください（複数可）", type=["csv"], accept_multiple_files=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- 共通関数群 ---
def create_chart(df, chart_type, x_col, y_col, title, **kwargs):
    """Altairグラフを生成する共通関数"""
    if 'color' not in kwargs:
        kwargs['color'] = alt.condition(
            alt.datum[y_col] >= 0 if y_col in df.columns else alt.datum[y_col],
            alt.value('#4CAF50'), alt.value('#F44336')
        )
    if chart_type == "bar":
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X(x_col, title=kwargs.get('x_title'), sort=kwargs.get('sort_x')),
            y=alt.Y(y_col, title=kwargs.get('y_title'), axis=alt.Axis(format=kwargs.get('format_y', ''))),
            color=kwargs.get('color'),
            tooltip=kwargs.get('tooltip')
        ).properties(title=title)
    elif chart_type == "line":
        chart = alt.Chart(df).mark_line().encode(
            x=alt.X(x_col, title=kwargs.get('x_title'), sort=kwargs.get('sort_x')),
            y=alt.Y(y_col, title=kwargs.get('y_title'), axis=alt.Axis(format=kwargs.get('format_y', ''))),
            tooltip=kwargs.get('tooltip')
        ).properties(title=title)
    elif chart_type == "pie":
        chart = alt.Chart(df).mark_arc(outerRadius=120).encode(
            theta=alt.Theta(y_col, stack=True),
            color=alt.Color(x_col, scale=alt.Scale(domain=kwargs.get('color_domain'), range=kwargs.get('color_range'))),
            tooltip=kwargs.get('tooltip')
        )
        text = alt.Chart(df).mark_text(radius=140).encode(
            text=alt.Text(x_col), theta=alt.Theta(y_col, stack=True)
        )
        return chart + text
    elif chart_type == "heatmap":
        chart = alt.Chart(df).mark_rect().encode(
            x=alt.X(x_col, title=kwargs.get('x_title'), sort=kwargs.get('sort_x')),
            y=alt.Y(y_col, title=kwargs.get('y_title'), sort=kwargs.get('sort_y')),
            color=alt.Color(kwargs.get('color'), scale=alt.Scale(scheme=kwargs.get('scheme', 'redblue'), domain=[0, 1]), legend=alt.Legend(format=".0%")),
            tooltip=kwargs.get('tooltip')
        ).properties(title=title)
    return chart

def categorize_duration(seconds):
    """取引時間をカテゴリに分類する関数"""
    if seconds == 15:
        return '15秒'
    elif seconds == 30:
        return '30秒'
    elif seconds == 60:
        return '60秒'
    elif 170 <= seconds <= 190:
        return '3分'
    elif 290 <= seconds <= 310:
        return '5分'
    else:
        return 'その他'

def process_trade_data(df):
    """データ加工の主要ロジックをまとめた関数"""
    required_columns = ['日付', '購入金額', 'ペイアウト', '終了時刻', '判定レート', 'レート', '取引オプション', '取引銘柄', 'HIGH/LOW', '取引番号']
    if not all(col in df.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in df.columns]
        st.error(f"⚠️ エラー：CSVファイルに必要な列が見つかりません。見つからなかった列: {', '.join(missing_cols)}")
        st.info("アップロードされたCSVファイルの列名:")
        st.code(list(df.columns))
        st.stop()
    
    try:
        df['取引日付'] = pd.to_datetime(df['日付'].str.strip('="').str.strip('"'), format="%d/%m/%Y %H:%M:%S", errors='coerce').dt.tz_localize('Asia/Tokyo')
        df['終了日時'] = pd.to_datetime(df['終了時刻'].str.strip('="').str.strip('"'), format="%d/%m/%Y %H:%M:%S", errors='coerce').dt.tz_localize('Asia/Tokyo')
        
        if df['取引日付'].isna().any() or df['終了日時'].isna().any():
            st.error("⚠️ エラー：日付または終了時刻の形式が無効です。CSVファイルを確認してください。")
            st.stop()
        
        df['購入金額'] = pd.to_numeric(df['購入金額'].str.replace('¥', '').str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        df['ペイアウト'] = pd.to_numeric(df['ペイアウト'].str.replace('¥', '').str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        df['利益'] = df['ペイアウト'] - df['購入金額']
        
        df['結果'] = ['WIN' if x > 0 else 'LOSE' for x in df['利益']]
        df['結果(数値)'] = df['結果'].apply(lambda x: 1 if x == 'WIN' else 0)
        df['曜日'] = df['取引日付'].dt.day_name().astype('category')
        df['時間帯'] = pd.cut(df['取引日付'].dt.hour, bins=[0, 6, 12, 18, 24], labels=['深夜', '午前', '午後', '夜'], right=False).astype('category')
        
        df['取引時間_秒'] = (df['終了日時'] - df['取引日付']).dt.total_seconds()
        df['取引時間'] = df['取引時間_秒'].apply(categorize_duration).astype('category')
        
        df['累積利益'] = df['利益'].cumsum()
        df['ピーク'] = df['累積利益'].cummax()
        df['ドローダウン'] = df['ピーク'] - df['累積利益']
        
        df.sort_values(by='取引日付', inplace=True)
        df_cleaned = df.drop(columns=['日付', '終了時刻', '判定レート', 'レート', '取引オプション', '取引時刻', '終了日時'], errors='ignore')
        
        st.success("✅ データの加工が完了しました！")
        return df_cleaned
    except Exception as e:
        st.error(f"⚠️ データ加工中にエラーが発生しました: {e}")
        st.stop()

def generate_summary_stats(df):
    """要約統計量を計算する関数"""
    if df.empty:
        return {
            'total_trades': 0,
            'total_profit': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'risk_reward_ratio': 0,
            'max_wins': 0,
            'max_losses': 0,
            'max_drawdown': 0,
            'monthly_avg_profit': 0
        }
    
    total_trades = len(df)
    total_profit = df['利益'].sum()
    win_rate = df['結果(数値)'].mean()
    avg_profit = df[df['利益'] > 0]['利益'].mean() if not df[df['利益'] > 0].empty else 0
    avg_loss = abs(df[df['利益'] < 0]['利益'].mean()) if not df[df['利益'] < 0].empty else 0
    risk_reward_ratio = avg_profit / avg_loss if avg_loss != 0 and not pd.isna(avg_profit) and not pd.isna(avg_loss) else 0
    
    win_lose_list = df['結果'].tolist()
    max_wins, max_losses = 0, 0
    current_wins, current_losses = 0, 0
    for result in win_lose_list:
        if result == 'WIN':
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
    
    max_drawdown = df['ドローダウン'].max() if 'ドローダウン' in df.columns else 0
    monthly_avg_profit = df.resample('M', on='取引日付')['利益'].mean().mean() if not df.empty else 0
    
    return {
        'total_trades': total_trades,
        'total_profit': total_profit,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'risk_reward_ratio': risk_reward_ratio,
        'max_wins': max_wins,
        'max_losses': max_losses,
        'max_drawdown': max_drawdown,
        'monthly_avg_profit': monthly_avg_profit
    }

# --- メインロジック ---
def process_uploaded_files(uploaded_files):
    """アップロードされたファイルを処理するメイン関数"""
    try:
        if not uploaded_files:
            st.warning("⚠️ CSVファイルをアップロードしてください。")
            st.stop()
        dfs = []
        for uploaded_file in uploaded_files:
            df = pd.read_csv(uploaded_file)
            dfs.append(df)
        combined_df = pd.concat(dfs, ignore_index=True)
        st.success("🎉 CSVファイルの読み込みに成功しました！")
        st.info("💡 データのプレビュー（加工前）")
        st.dataframe(combined_df, use_container_width=True, height=300)  # スクロール対応

        df_cleaned = process_trade_data(combined_df)
        return df_cleaned
    except Exception as e:
        st.error(f"⚠️ 予期せぬエラーが発生しました: {e}")
        st.write("ファイル形式が正しくないか、CSVファイルに問題がある可能性があります。")
        st.stop()

if uploaded_files:
    df_cleaned = process_uploaded_files(uploaded_files)
    
    if df_cleaned is not None:
        # 期間フィルタ
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">🔍 期間フィルタ</h2>', unsafe_allow_html=True)
        period = st.selectbox("分析期間を選択", ["今日", "昨日", "今週", "先週", "今月", "先月", "日付指定"])
        
        now = pd.Timestamp.now(tz='Asia/Tokyo')
        if period == "今日":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "昨日":
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "今週":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "先週":
            start_date = (now - timedelta(days=now.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (now - timedelta(days=now.weekday() + 1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "今月":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "先月":
            last_month = now.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = last_month.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:  # 日付指定
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("開始日", value=now.date() - timedelta(days=7))
            with col2:
                end_date = st.date_input("終了日", value=now.date())
            start_date = pd.Timestamp(start_date, tz='Asia/Tokyo').replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = pd.Timestamp(end_date, tz='Asia/Tokyo').replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if start_date > end_date:
            st.error("⚠️ 開始日は終了日より前でなければなりません。")
            st.stop()
        
        filtered_df = df_cleaned[(df_cleaned['取引日付'] >= start_date) & (df_cleaned['取引日付'] <= end_date)]
        if filtered_df.empty:
            st.warning("⚠️ 選択した期間にデータがありません。別の期間を選択してください。")
            st.stop()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- 統計データ計算 ---
        stats = generate_summary_stats(filtered_df)
        
        # --- 概要データ表示セクション ---
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">📊 概要データ</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("総取引数", f"{stats['total_trades']} 回")
        with col2: st.metric("総損益", f"¥{stats['total_profit']:,}")
        with col3: st.metric("勝率", f"{stats['win_rate']:.2%}")

        col4, col5, col6 = st.columns(3)
        with col4: st.metric("リスク・リワード比率", f"{stats['risk_reward_ratio']:.2f}")
        with col5: st.metric("平均利益", f"¥{stats['avg_profit']:,.0f}" if not pd.isna(stats['avg_profit']) else "N/A")
        with col6: st.metric("平均損失", f"¥{stats['avg_loss']:,.0f}" if not pd.isna(stats['avg_loss']) else "N/A")

        col7, col8, col9 = st.columns(3)
        with col7: st.metric("最大連勝数", f"{stats['max_wins']} 回")
        with col8: st.metric("最大連敗数", f"{stats['max_losses']} 回")
        with col9: st.metric("最大ドローダウン", f"¥{stats['max_drawdown']:,.0f}")
        
        col10 = st.columns(1)[0]
        with col10: st.metric("月間平均利益", f"¥{stats['monthly_avg_profit']:,.0f}" if not pd.isna(stats['monthly_avg_profit']) else "N/A")
        
        # 詳細統計データを直接表示
        st.markdown('<h3 class="section-header">通貨ペア別総損益</h3>', unsafe_allow_html=True)
        pair_profit = filtered_df.groupby('取引銘柄')['利益'].sum().sort_values(ascending=False).reset_index().rename(columns={'取引銘柄': '通貨ペア', '利益': '総損益'})
        st.dataframe(pair_profit, use_container_width=True)

        st.markdown('<h3 class="section-header">時間帯別・曜日別勝率</h3>', unsafe_allow_html=True)
        col_time, col_weekday = st.columns(2)
        with col_time:
            st.write("**時間帯別勝率**")
            time_win_rate = filtered_df.groupby('時間帯')['結果(数値)'].mean().reindex(['午前', '午後', '夜', '深夜'], fill_value=0).reset_index().rename(columns={'時間帯': '時間帯', '結果(数値)': '勝率'})
            st.dataframe(time_win_rate.style.format({'勝率': '{:.2%}'}), use_container_width=True)
        with col_weekday:
            st.write("**曜日別勝率**")
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_win_rate = filtered_df.groupby('曜日')['結果(数値)'].mean().reindex(weekday_order, fill_value=0).reset_index().rename(columns={'曜日': '曜日', '結果(数値)': '勝率'})
            st.dataframe(weekday_win_rate.style.format({'勝率': '{:.2%}'}), use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
        
        download_filename = st.text_input("ダウンロードするファイル名を入力してください", "processed_trade_data")
        show_chart = st.checkbox("📈 グラフを表示する")

        # 分析グラフセクション
        if show_chart:
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown('<h2 class="section-header">📊 取引結果の分析グラフ</h2>', unsafe_allow_html=True)
            
            graph_options = [
                '全体勝率', '取引方向別勝率', '取引方向別収益', '通貨ペア別勝率', '通貨ペア別収益',
                '通貨ペア・取引方向別勝率ヒートマップ', '日時勝率推移', '累積利益/損失推移',
                '曜日別勝率', '曜日別収益', '時間帯別勝率', '時間帯別収益', '時間帯別勝率ヒートマップ',
                '取引ごとの利益/損失', '取引時間別勝率'
            ]
            
            for graph in graph_options:
                st.subheader(graph)
                if graph == '全体勝率':
                    result_counts = filtered_df['結果'].value_counts().reindex(['WIN', 'LOSE'], fill_value=0).reset_index()
                    result_counts.columns = ['結果', '取引数']
                    chart_pie = create_chart(
                        result_counts, 'pie', '結果', '取引数', '全体勝率',
                        color_domain=['WIN', 'LOSE'], color_range=['#4CAF50', '#F44336'],
                        tooltip=['結果', '取引数', alt.Tooltip('取引数', format=".1%")]
                    )
                    st.altair_chart(chart_pie, use_container_width=True)
                
                elif graph == '取引方向別勝率':
                    direction_win_rate = filtered_df.groupby('HIGH/LOW')['結果(数値)'].mean().reindex(['HIGH', 'LOW'], fill_value=0).reset_index().rename(columns={'HIGH/LOW': '取引方向', '結果(数値)': '勝率'})
                    chart_direction = create_chart(
                        direction_win_rate, 'bar', '取引方向', '勝率', '取引方向別勝率',
                        color=alt.Color('取引方向', scale=alt.Scale(domain=['HIGH', 'LOW'], range=['#4CAF50', '#F44336'])),
                        format_y=".0%", tooltip=['取引方向', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_direction, use_container_width=True)
                
                elif graph == '取引方向別収益':
                    direction_profit = filtered_df.groupby('HIGH/LOW')['利益'].sum().reindex(['HIGH', 'LOW'], fill_value=0).reset_index()
                    chart_direction = create_chart(
                        direction_profit, 'bar', 'HIGH/LOW', '利益', '取引方向別収益',
                        color=alt.Color('HIGH/LOW', scale=alt.Scale(domain=['HIGH', 'LOW'], range=['#4CAF50', '#F44336'])),
                        format_y="s", tooltip=['HIGH/LOW', alt.Tooltip('利益', format=",")]
                    )
                    st.altair_chart(chart_direction, use_container_width=True)
                
                elif graph == '通貨ペア別勝率':
                    pair_win_rate = filtered_df.groupby('取引銘柄')['結果(数値)'].mean().sort_values(ascending=False).reset_index().rename(columns={'取引銘柄': '通貨ペア', '結果(数値)': '勝率'})
                    chart_pair = create_chart(
                        pair_win_rate, 'bar', '通貨ペア', '勝率', '通貨ペア別勝率',
                        color=alt.Color('通貨ペア', scale=alt.Scale(scheme='category10')),
                        format_y=".0%", tooltip=['通貨ペア', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_pair, use_container_width=True)
                
                elif graph == '通貨ペア別収益':
                    pair_profit = filtered_df.groupby('取引銘柄')['利益'].sum().sort_values(ascending=False).reset_index().rename(columns={'取引銘柄': '通貨ペア'})
                    chart_pair = create_chart(
                        pair_profit, 'bar', '通貨ペア', '利益', '通貨ペア別収益',
                        color=alt.Color('通貨ペア', scale=alt.Scale(scheme='category10')),
                        format_y="s", tooltip=['通貨ペア', alt.Tooltip('利益', format=",")]
                    )
                    st.altair_chart(chart_pair, use_container_width=True)
                
                elif graph == '通貨ペア・取引方向別勝率ヒートマップ':
                    heatmap_data = filtered_df.groupby(['取引銘柄', 'HIGH/LOW'])['結果(数値)'].mean().reset_index().rename(columns={'取引銘柄': '通貨ペア', 'HIGH/LOW': '取引方向', '結果(数値)': '勝率'})
                    chart_heatmap_pair_direction = create_chart(
                        heatmap_data, 'heatmap', '取引方向', '通貨ペア', '通貨ペア・取引方向別勝率ヒートマップ',
                        sort_x=['HIGH', 'LOW'], color='勝率', scheme='redblue',
                        tooltip=['通貨ペア', '取引方向', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_heatmap_pair_direction, use_container_width=True)
                
                elif graph == '日時勝率推移':
                    daily_win_rate = filtered_df.groupby(filtered_df['取引日付'].dt.date)['結果(数値)'].mean().reset_index().rename(columns={'取引日付': '日付', '結果(数値)': '勝率'})
                    daily_win_rate['日付'] = daily_win_rate['日付'].astype(str)
                    chart_line_daily = create_chart(
                        daily_win_rate, 'line', '日付', '勝率', '日時勝率推移',
                        format_y=".0%", tooltip=['日付', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_line_daily, use_container_width=True)
                
                elif graph == '累積利益/損失推移':
                    filtered_df['取引日付(str)'] = filtered_df['取引日付'].astype(str)
                    chart_cumulative = alt.Chart(filtered_df).mark_line().encode(
                        x=alt.X('取引日付(str)', title='日付'),
                        y=alt.Y('累積利益', title='累積損益 (¥)', axis=alt.Axis(format='s'), scale=alt.Scale(reverse=True)),
                        tooltip=['取引日付(str)', '累積利益']
                    ).properties(title='累積損益推移')
                    st.altair_chart(chart_cumulative, use_container_width=True)
                
                elif graph == '曜日別勝率':
                    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    weekday_win_rate = filtered_df.groupby('曜日')['結果(数値)'].mean().reindex(weekday_order, fill_value=0).reset_index().rename(columns={'曜日': '曜日', '結果(数値)': '勝率'})
                    chart_weekday = create_chart(
                        weekday_win_rate, 'bar', '曜日', '勝率', '曜日別勝率',
                        sort_x=weekday_order,
                        color=alt.Color('曜日', scale=alt.Scale(
                            domain=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                            range=['#4682B4', '#FF4500', '#00CED1', '#228B22', '#FFD700', '#8B4513', '#FFFF00']
                        )),
                        format_y=".0%", tooltip=['曜日', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_weekday, use_container_width=True)
                
                elif graph == '曜日別収益':
                    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    weekday_profit = filtered_df.groupby('曜日')['利益'].sum().reindex(weekday_order, fill_value=0).reset_index()
                    chart_weekday = create_chart(
                        weekday_profit, 'bar', '曜日', '利益', '曜日別収益',
                        sort_x=weekday_order,
                        color=alt.Color('曜日', scale=alt.Scale(
                            domain=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                            range=['#4682B4', '#FF4500', '#00CED1', '#228B22', '#FFD700', '#8B4513', '#FFFF00']
                        )),
                        format_y="s", tooltip=['曜日', alt.Tooltip('利益', format=",")]
                    )
                    st.altair_chart(chart_weekday, use_container_width=True)
                
                elif graph == '時間帯別勝率':
                    time_order = ['午前', '午後', '夜', '深夜']
                    time_win_rate = filtered_df.groupby('時間帯')['結果(数値)'].mean().reindex(time_order, fill_value=0).reset_index().rename(columns={'時間帯': '時間帯', '結果(数値)': '勝率'})
                    chart_time = create_chart(
                        time_win_rate, 'bar', '時間帯', '勝率', '時間帯別勝率',
                        sort_x=time_order,
                        color=alt.Color('時間帯', scale=alt.Scale(
                            domain=['午前', '午後', '夜', '深夜'],
                            range=['#FFA500', '#F44336', '#4CAF50', '#1E90FF']
                        )),
                        format_y=".0%", tooltip=['時間帯', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_time, use_container_width=True)
                
                elif graph == '時間帯別収益':
                    time_order = ['午前', '午後', '夜', '深夜']
                    time_profit = filtered_df.groupby('時間帯')['利益'].sum().reindex(time_order, fill_value=0).reset_index()
                    chart_time = create_chart(
                        time_profit, 'bar', '時間帯', '利益', '時間帯別収益',
                        sort_x=time_order,
                        color=alt.Color('時間帯', scale=alt.Scale(
                            domain=['午前', '午後', '夜', '深夜'],
                            range=['#FFA500', '#F44336', '#4CAF50', '#1E90FF']
                        )),
                        format_y="s", tooltip=['時間帯', alt.Tooltip('利益', format=",")]
                    )
                    st.altair_chart(chart_time, use_container_width=True)
                
                elif graph == '時間帯別勝率ヒートマップ':
                    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    time_order = ['午前', '午後', '夜', '深夜']
                    index = pd.MultiIndex.from_product([filtered_df['曜日'].unique(), time_order], names=['曜日', '時間帯'])
                    heatmap_data_time = filtered_df.groupby(['曜日', '時間帯'])['結果(数値)'].mean().reindex(index, fill_value=0).reset_index().rename(columns={'結果(数値)': '勝率'})
                    chart_heatmap_time = create_chart(
                        heatmap_data_time, 'heatmap', '時間帯', '曜日', '曜日・時間帯別勝率ヒートマップ',
                        sort_x=time_order, sort_y=weekday_order, color='勝率', scheme='redblue',
                        tooltip=['曜日', '時間帯', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_heatmap_time, use_container_width=True)
                
                elif graph == '取引ごとの利益/損失':
                    filtered_df['取引番号(str)'] = filtered_df['取引番号'].astype(str)
                    bar_chart = alt.Chart(filtered_df).mark_bar().encode(
                        x=alt.X('取引番号(str)', axis=None, title='取引番号 (X軸を非表示)'),
                        y=alt.Y('利益', title='利益/損失 (¥)', axis=alt.Axis(format='s')),
                        color=alt.Color('結果', scale=alt.Scale(domain=['WIN', 'LOSE'], range=['#4CAF50', '#F44336'])),
                        tooltip=[
                            alt.Tooltip('取引番号', title='取引番号'),
                            alt.Tooltip('取引日付', title='日付', format="%Y-%m-%d %H:%M:%S"),
                            alt.Tooltip('利益', title='利益/損失', format=","),
                            alt.Tooltip('結果', title='結果')
                        ]
                    ).properties(title='各取引の利益と損失').interactive()
                    st.altair_chart(bar_chart, use_container_width=True)
                
                elif graph == '取引時間別勝率':
                    time_order = ['15秒', '30秒', '60秒', '3分', '5分', 'その他']
                    time_win_rate = filtered_df.groupby('取引時間')['結果(数値)'].mean().reindex(time_order, fill_value=0).reset_index().rename(columns={'取引時間': '取引時間', '結果(数値)': '勝率'})
                    chart_time_win_rate = create_chart(
                        time_win_rate, 'bar', '取引時間', '勝率', '取引時間別勝率',
                        sort_x=time_order,
                        color=alt.Color('取引時間', scale=alt.Scale(scheme='category10')),
                        format_y=".0%", tooltip=['取引時間', alt.Tooltip('勝率', format=".1%")]
                    )
                    st.altair_chart(chart_time_win_rate, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # --- ダウンロードセクション ---
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">⬇️ 加工済みデータのダウンロード</h2>', unsafe_allow_html=True)
        
        download_format = st.selectbox("ダウンロード形式を選択してください", ["CSV", "Excel"])
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
        st.dataframe(df_cleaned, use_container_width=True)
