import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import requests
import urllib3
import json
import streamlit.components.v1 as components

# 1. 基礎設定與安全防護
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="我的百岳戰情室", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與戰情室")

FILE_PATH = 'baiyue_tracking.csv'
LOCAL_JSON = 'F-B0053-033.json' # 您上傳的備援預報檔案

# ==========================================
# 2. 雙軌氣象解析 (優先 API，失敗則讀取本地 JSON)
# ==========================================
@st.cache_data(ttl=3600)
def get_cwa_mountain_forecast(api_key):
    # --- 軌道 A：嘗試從 API 抓取即時資料 ---
    if api_key:
        clean_key = api_key.strip()
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-B0053-033?Authorization={clean_key}&format=JSON"
        try:
            resp = requests.get(url, timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                if 'records' in data and 'locations' in data['records']:
                    return data['records']['locations'][0]['location'], "📡 即時 API 連線成功"
        except:
            pass # API 失敗則進入下一軌道

    # --- 軌道 B：本地 JSON 備援 (讀取您提供的檔案) ---
    if os.path.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 針對您上傳檔案的特殊層級結構進行解析
                if 'cwaopendata' in data:
                    location_data = data['cwaopendata']['Dataset']['Locations']['Location']
                    return location_data, "📁 API 連線失敗，已啟用本地 JSON 備援"
        except Exception as e:
            return None, f"本地檔案解析錯誤: {str(e)}"

    return None, "❌ 無法取得氣象資料 (API 失敗且無本地備援檔)"

# ==========================================
# 3. 載入資料與座標補全
# ==========================================
BAIYUE_COORDS = {
    '玉山主峰': [120.957, 23.470], '雪山主峰': [121.231, 24.383], '關山': [120.908, 23.243],
    '向陽山': [120.985, 23.284], '三叉山': [121.038, 23.284], '海諾南山': [120.904, 23.203],
    '小關山': [120.895, 23.166], '卑南主山': [120.880, 23.056], '庫哈諾辛山': [120.908, 23.275]
}

if not os.path.exists(FILE_PATH):
    st.error(f"找不到紀錄檔：{FILE_PATH}")
else:
    # 讀取並清理資料
    df = pd.read_csv(FILE_PATH, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    
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
    # 4. 3D 地圖展示 (衛星街道圖)
    # ==========================================
    st.write("### 🗺️ 3D 百岳完登版圖")
    map_df = df.dropna(subset=['經度', '緯度']).copy()
    map_df['完登狀態'] = map_df['完登狀態'].astype(str).str.upper() == 'TRUE'
    map_df['color'] = map_df['完登狀態'].apply(lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120])
    map_df['狀態'] = map_df['完登狀態'].apply(lambda x: "✅ 已完登" if x else "🎯 未完登")

    view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
    layer = pdk.Layer("ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], get_fill_color="color", get_radius=2500, pickable=True)
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view_state, map_provider="mapbox",
        map_style="mapbox://styles/mapbox/satellite-streets-v12",
        api_keys={"mapbox": st.secrets.get("MAPBOX_API_KEY", "")},
        tooltip={"text": "{山名}\n狀態: {狀態}"}
    ))

    # ==========================================
    # 5. 📡 登山戰情室 (Tab 化管理)
    # ==========================================
    st.divider()
    st.write("### 📡 登山戰情室")
    tab1, tab2, tab3 = st.tabs(["⛰️ 官方登山預報", "🌧️ NCDR 降雨雷達", "🌡️ 精準 API 數據"])

    with tab1:
        st.caption("直接載入氣象署南一段(關山)預報網頁")
        components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=600, scrolling=True)

    with tab2:
        st.caption("即時降雨雷達回波趨勢圖")
        components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=700, scrolling=True)

    with tab3:
        st.write("#### ⛰️ 百岳高山點精準預報 (F-B0053-033)")
        cwa_key = st.secrets.get("CWA_API_KEY")
        mountain_list, source_msg = get_cwa_mountain_forecast(cwa_key)
        
        if mountain_list:
            st.info(source_msg)
            m_names = [m['locationName'] for m in mountain_list]
            # 預設選取「關山」
            def_idx = m_names.index("關山") if "關山" in m_names else 0
            sel_m = st.selectbox("選擇登山預報點：", m_names, index=def_idx)
            
            target_m = next(m for m in mountain_list if m['locationName'] == sel_m)
            elements = target_m['weatherElement']
            
            # 針對 033 格式提取 WeatherDescription
            wx_element = next(e for e in elements if e['elementName'] in ['WeatherDescription', '天氣描述'])
            
            res_data = []
            for item in wx_element['time'][:10]: # 顯示 5 天份資料
                desc = item['elementValue'][0].get('WeatherDescription', '無資料')
                res_data.append({
                    "時段": item['startTime'][5:16].replace('T', ' '),
                    "詳細預報 (含體感、風速)": desc.replace('。', '。\n')
                })
            
            st.table(pd.DataFrame(res_data))
        else:
            st.warning("⚠️ 無法載入 API 預報，且未發現本地備援 JSON 檔案。")

    # ==========================================
    # 6. 🔍 快速打卡區塊
    # ==========================================
    st.divider()
    st.write("### 🔍 快速打卡與紀錄搜尋")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        search = st.text_input("搜尋山名:", "")
    with col_b:
        filter_st = st.selectbox("狀態篩選", ["全部", "🎯 未完登", "✅ 已完登"])

    # 過濾顯示
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
        st.success("紀錄已成功同步至 CSV！")
        st.rerun()
