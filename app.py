import streamlit as st
import pandas as pd
import io
import openpyxl
import altair as alt
import pytz

st.set_page_config(
    page_title="AI分析向けデータ加工サービス",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- デザイン調整 ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
.main-header { font-size: 3em; color: #2c3e50; text-align: center; margin-bottom: 0.5em; }
.main-subheader { font-size: 1.2em; color: #7f8c8d; text-align: center; margin-bottom: 2em; }
.stButton>button { background-color: #3498db; color: white; border-radius: 5px; border: none; padding: 10px 24px; font-size: 1em; transition-duration: 0.4s; cursor: pointer; }
.stButton>button:hover { background-color: #2980b9; }
.stDownloadButton > button { background-color: #2ecc71; color: white; border-radius: 5px; border: none; padding: 10px 24px; font-size: 1em; transition-duration: 0.4s; cursor: pointer; }
.stDownloadButton > button:hover { background-color: #27ae60; }
.section-container { background-color: #f8f9fa; border-radius: 10px; padding: 2em; margin-bottom: 2em; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
.section-header { font-size: 2em; color: #2c3e50; margin-top: 0; margin-bottom: 1em; text-align: center; }
.stAlert { background-color: #ecf0f1; border-left: 5px solid #3498db; padding: 10px; margin-bottom: 1em; }
.metric-container { border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; text-align: center; margin-bottom: 15px; background-color: white; }
.metric-title { font-size: 1em; color: #7f8c8d; font-weight: bold; }
.metric-value { font-size: 1.8em; color: #2c3e50; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">AI分析向けデータ加工サービス</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-subheader">CSVファイルをアップロードすると、AI分析用に自動で加工し、グラフも作成します。</p>', unsafe_allow_html=True)

# --- ファイルアップロード ---
st.markdown('<div class="section-container">', unsafe_allow_html=True)
st.markdown('<h2 class="section-header">📂 ファイルアップロード</h2>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])
st.markdown('</div>', unsafe_allow_html=True)

# --- 日付変換関数 ---
def parse_excel_date(x):
    x = str(x).replace('="','').replace('"','').strip()
    try:
        f = float(x)
        dt = pd.Timestamp('1899-12-30') + pd.to_timedelta(f, 'D')
    except:
        dt = pd.to_datetime(x, errors='coerce')
    jst = pytz.timezone('Asia/Tokyo')
    if pd.notna(dt):
        if dt.tzinfo is None:
            dt = dt.tz_localize(pytz.UTC).tz_convert(jst)
        else:
            dt = dt.tz_convert(jst)
    return dt

# --- グラフ作成関数 ---
def create_chart(df, chart_type, x_col, y_col, title, **kwargs):
    if chart_type == "bar":
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X(x_col, title=kwargs.get('x_title')),
            y=alt.Y(y_col, title=kwargs.get('y_title'), axis=alt.Axis(format=kwargs.get('format_y', ''))),
            color=kwargs.get('color'),
            tooltip=kwargs.get('tooltip')
        ).properties(title=title)
    elif chart_type == "line":
        chart = alt.Chart(df).mark_line().encode(
            x=alt.X(x_col, title=kwargs.get('x_title')),
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
            color=alt.Color(kwargs.get('color'), scale=alt.Scale(scheme=kwargs.get('scheme', 'greenblue'), domain=[0, 1]), legend=alt.Legend(format=".0%")),
            tooltip=kwargs.get('tooltip')
        ).properties(title=title)
    return chart

# --- CSV処理・分析 ---
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("🎉 CSVファイルの読み込みに成功しました！")

        required_columns = ['日付', '購入金額', 'ペイアウト', '終了時刻', '判定レート', 'レート', '取引オプション', '取引銘柄', 'HIGH/LOW', '取引番号']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            st.error(f"⚠️ CSVに必要な列が見つかりません: {', '.join(missing_cols)}")
            st.stop()
        
        # --- 日付変換・加工 ---
        df['取引日付'] = df['日付'].apply(parse_excel_date)
        df['終了日時'] = df['終了時刻'].apply(parse_excel_date)

        df['購入金額'] = df['購入金額'].str.replace('¥','').str.replace(',','').astype(int)
        df['ペイアウト'] = df['ペイアウト'].str.replace('¥','').str.replace(',','').astype(int)
        df['利益'] = df['ペイアウト'] - df['購入金額']
        df['結果'] = ['WIN' if x>0 else 'LOSE' for x in df['利益']]
        df['結果(数値)'] = df['結果'].apply(lambda x: 1 if x=='WIN' else 0)

        # --- 曜日日本語化 ---
        weekday_map = {'Monday':'月曜日','Tuesday':'火曜日','Wednesday':'水曜日','Thursday':'木曜日',
                       'Friday':'金曜日','Saturday':'土曜日','Sunday':'日曜日'}
        df['曜日'] = df['取引日付'].dt.day_name().map(weekday_map)

        df['時間帯'] = pd.cut(df['取引日付'].dt.hour, bins=[0,6,12,18,24], labels=['深夜','午前','午後','夜'], right=False)
        df['取引時間_秒'] = (df['終了日時'] - df['取引日付']).dt.total_seconds()

        def categorize_duration(seconds):
            if seconds == 15: return '15秒'
            elif seconds == 30: return '30秒'
            elif seconds == 60: return '60秒'
            elif 170<=seconds<=190: return '3分'
            elif 290<=seconds<=310: return '5分'
            else: return 'その他'
        
        df['取引時間'] = df['取引時間_秒'].apply(categorize_duration)
        df.sort_values(by='取引日付', inplace=True)

        df_cleaned = df.drop(columns=['日付','終了時刻','判定レート','レート','取引オプション','取引時刻','終了日時'], errors='ignore')
        st.success("✅ データ加工が完了しました！")

        # --- 統計計算 ---
        total_trades = len(df_cleaned)
        total_profit = df_cleaned['利益'].sum()
        win_rate = df_cleaned['結果(数値)'].mean()
        avg_profit = df_cleaned[df_cleaned['利益'] > 0]['利益'].mean()
        avg_loss = abs(df_cleaned[df_cleaned['利益'] < 0]['利益'].mean())
        risk_reward_ratio = avg_profit / avg_loss if avg_loss != 0 and not pd.isna(avg_profit) and not pd.isna(avg_loss) else 0

        win_lose_list = df_cleaned['結果'].tolist()
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

        df_cleaned['累積利益'] = df_cleaned['利益'].cumsum()
        df_cleaned['ピーク'] = df_cleaned['累積利益'].cummax()
        df_cleaned['ドローダウン'] = df_cleaned['ピーク'] - df_cleaned['累積利益']
        max_drawdown = df_cleaned['ドローダウン'].max()

        # --- 統計表示 ---
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">📊 要約統計データ</h2>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("総取引数", total_trades)
        col2.metric("総利益", f"¥{total_profit:,}")
        col3.metric("勝率", f"{win_rate*100:.2f}%")
        col4.metric("最大連勝", max_wins)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("最大連敗", max_losses)
        col2.metric("平均利益", f"¥{avg_profit:.0f}")
        col3.metric("平均損失", f"¥{avg_loss:.0f}")
        col4.metric("最大ドローダウン", f"¥{max_drawdown:.0f}")

        st.markdown('</div>', unsafe_allow_html=True)

        # --- グラフ ---
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">📈 グラフ表示</h2>', unsafe_allow_html=True)

        # ① 勝敗割合
        result_counts = df_cleaned['結果'].value_counts().reset_index()
        result_counts.columns = ['結果','件数']
        pie_chart = create_chart(result_counts, "pie", "結果", "件数", "勝敗割合")
        st.altair_chart(pie_chart, use_container_width=True)

        # ② 曜日別勝率
        weekday_group = df_cleaned.groupby('曜日')['結果(数値)'].mean().reset_index()
        weekday_group = weekday_group.sort_values(by='結果(数値)', ascending=False)
        bar_chart = create_chart(weekday_group, "bar", "曜日", "結果(数値)", "曜日別勝率", y_title="勝率", format_y=".0%", color=alt.Color("結果(数値)", scale=alt.Scale(scheme='blues')))
        st.altair_chart(bar_chart, use_container_width=True)

        # ③ 累積利益
        line_chart = alt.Chart(df_cleaned).mark_line().encode(
            x='取引日付', y='累積利益', tooltip=['取引日付','累積利益']
        ).properties(title="累積利益の推移")
        st.altair_chart(line_chart, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # --- 加工済みCSVダウンロード ---
        csv = df_cleaned.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 加工済みCSVをダウンロード", data=csv, file_name="加工済みデータ.csv", mime="text/csv")

    except Exception as e:
        st.error(f"⚠️ 予期せぬエラー: {e}")
