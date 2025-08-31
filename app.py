import streamlit as st
import pandas as pd
import io

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

        # ダウンロードボタンのみを残す
        st.subheader("ダウンロードオプション")
        download_filename = st.text_input("ダウンロードするファイル名を入力してください", "processed_trade_data")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="CSV形式でダウンロード",
            data=csv_buffer.getvalue(),
            file_name=f"{download_filename}.csv",
            mime="text/csv"
        )
        st.info("データの加工が完了しました。")
        st.dataframe(df)

    except Exception as e:
        st.error(f"予期せぬエラーが発生しました: {e}")
        st.write("ファイル形式が正しくないか、CSVファイルに問題がある可能性があります。")
