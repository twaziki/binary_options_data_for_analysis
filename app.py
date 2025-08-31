import streamlit as st
import pandas as pd
import io

st.title("データ加工サービス")
st.write("CSVファイルをアップロードすると、AI分析用に自動で加工します。")

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
        st.dataframe(df.head())

        # 加工済みファイルをダウンロード可能に
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        st.download_button(
            label="加工済みデータをダウンロード",
            data=buffer.getvalue(),
            file_name="processed_trade_data.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.write("ファイルの形式が正しくない可能性があります。")