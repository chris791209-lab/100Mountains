import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import requests
import urllib3
import streamlit.components.v1 as components

# 1. 基礎設定
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="我的百岳紀錄 App", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與戰情室")

FILE_PATH = 'baiyue_tracking.csv'

# ==========================================
# 2. 資料載入與座標補全
# ==========================================
# 內建南一段與常用座標，確保地圖點位正確
BAIYUE_COORDS = {
    '玉山主峰': [120.957, 23.470], '雪山主峰': [121.231, 24.383], '關山': [120.908, 23.243],
    '向陽山': [120.985, 23.284], '三叉山': [121.038, 23.284], '海諾南山': [120.904, 23.203],
    '小關山': [120.895, 23.166], '卑南主山': [120.880, 23.056], '庫哈諾辛山': [120.908, 23.275]
}

if not os.path.exists(FILE_PATH):
    st.error(f"找不到檔案：{FILE_PATH}")
else:
    df = pd.read_csv(FILE_PATH, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    
    # 自動補全座標邏輯
    for idx, row in df.iterrows():
        peak = str(row['山名']).strip()
        if pd.isna(row.get('經度')) and peak in BAIYUE_COORDS:
            df.at[idx, '經度'] = BAIYUE_COORDS[peak][0]
            df.at[idx, '緯度'] = BAIYUE_COORDS[peak][1]

    # 進度展示
    completed = df[df['完登狀態'].astype(str).str.upper() == 'TRUE']['山名'].nunique()
    st.subheader(f"目前完登進度：{completed} / 100")
    st.progress(completed / 100)

    # ==========================================
    # 3. 3D 地圖展示 (衛星街道圖層)
    # ==========================================
    st.write("### 🗺️ 3D 百岳完登版圖")
    map_df = df.dropna(subset=['經度', '緯度']).copy()
    map_df['完登狀態'] = map_df['完登狀態'].astype(str).str.upper() == 'TRUE'
    map_df['color'] = map_df['完登狀態'].apply(lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120])
    
    view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
    layer = pdk.Layer(
        "ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], 
        get_fill_color="color", get_radius=2500, pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view_state, map_provider="mapbox",
        map_style="mapbox://styles/mapbox/satellite-streets-v12",
        api_keys={"mapbox": st.secrets.get("MAPBOX_API_KEY", "")},
        tooltip={"text": "{山名}\n海拔: {海拔(m)}m"}
    ))

    # ==========================================
    # 4. 📡 登山戰情室 (僅保留權威網頁嵌入)
    # ==========================================
    st.divider()
    st.write("### 📡 登山戰情室")
    tab1, tab2 = st.tabs(["⛰️ 官方登山預報網頁", "🌧️ NCDR 降雨監測"])

    with tab1:
        st.caption("即時顯示：中央氣象署 - 南一段(關山)區域專業登山預報")
        components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=650, scrolling=True)

    with tab2:
        st.caption("即時顯示：NCDR 全台降雨雷達回波趨勢")
        components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=750, scrolling=True)

    # ==========================================
    # 5. 🔍 快速打卡區塊
    # ==========================================
    st.divider()
    st.write("### 🔍 快速打卡與紀錄搜尋")
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        search = st.text_input("搜尋山名 (如: 小關山):", "")
    with col_b:
        filter_st = st.selectbox("狀態篩選", ["全部", "🎯 未完登", "✅ 已完登"])

    # 資料過濾
    display_df = df.copy()
    if search:
        display_df = display_df[display_df['山名'].str.contains(search, na=False)]
    if filter_st == "🎯 未完登":
        display_df = display_df[display_df['完登狀態'].astype(str).str.upper() != 'TRUE']
    elif filter_st == "✅ 已完登":
        display_df = display_df[display_df['完登狀態'].astype(str).str.upper() == 'TRUE']

    # 資料編輯器
    edited_df = st.data_editor(
        display_df,
        column_config={
            "完登狀態": st.column_config.CheckboxColumn("是否完登?"),
            "登頂日期": st.column_config.TextColumn("登頂日期 (YYYY-MM-DD)")
        },
        disabled=["山名", "海拔(m)", "難度", "經度", "緯度"],
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 儲存最新紀錄", type="primary"):
        df.update(edited_df)
        df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig')
        st.success("紀錄已存檔！")
        st.rerun()
