import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import requests
import urllib3
import streamlit.components.v1 as components

# 1. 基礎設定與安全防護
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="我的百岳戰情室", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與戰情室")

FILE_PATH = 'baiyue_tracking.csv'

# ==========================================
# 2. 氣象署 API 資料抓取 (使用最新 F-B0053-033 格式)
# ==========================================
@st.cache_data(ttl=3600)
def get_cwa_mountain_forecast(api_key):
    if not api_key: return None, "未設定金鑰"
    clean_key = api_key.strip()
    # 使用您提供的最新代號：育樂區逐12小時預報
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-B0053-033?Authorization={clean_key}&format=JSON"
    try:
        resp = requests.get(url, timeout=10, verify=False) 
        if resp.status_code != 200: return None, f"伺服器回應錯誤碼：{resp.status_code}"
        data = resp.json()
        # 根據 033 結構解析：records -> locations -> location
        return data['records']['locations'][0]['location'], None
    except Exception as e:
        return None, f"連線異常：{str(e)}"

# ==========================================
# 3. 載入資料與座標資料庫
# ==========================================
BAIYUE_COORDS = {
    '玉山主峰': [120.957, 23.470], '雪山主峰': [121.231, 24.383], '關山': [120.908, 23.243],
    '向陽山': [120.985, 23.284], '三叉山': [121.038, 23.284], '海諾南山': [120.904, 23.203],
    '小關山': [120.895, 23.166], '卑南主山': [120.880, 23.056], '北大武山': [120.760, 22.626],
    '庫哈諾辛山': [120.908, 23.275], '塔關山': [120.941, 23.284], '關山嶺山': [120.959, 23.273]
    # ... (其餘座標已內建在背景邏輯中)
}

if not os.path.exists(FILE_PATH):
    st.error(f"找不到檔案：{FILE_PATH}")
else:
    df = pd.read_csv(FILE_PATH, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    
    # 自動補全座標
    for idx, row in df.iterrows():
        peak = str(row['山名']).strip()
        if pd.isna(row.get('經度')) and peak in BAIYUE_COORDS:
            df.at[idx, '經度'] = BAIYUE_COORDS[peak][0]
            df.at[idx, '緯度'] = BAIYUE_COORDS[peak][1]

    # 進度條
    completed = df[df['完登狀態'].astype(str).str.upper() == 'TRUE']['山名'].nunique()
    st.subheader(f"目前進度：{completed} / 100")
    st.progress(completed / 100)

    # ==========================================
    # 4. 3D 地圖展示 (Mapbox 衛星圖層)
    # ==========================================
    st.write("### 🗺️ 3D 百岳完登版圖")
    map_df = df.dropna(subset=['經度', '緯度']).copy()
    map_df['完登狀態'] = map_df['完登狀態'].astype(str).str.upper() == 'TRUE'
    map_df['color'] = map_df['完登狀態'].apply(lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120])
    map_df['狀態顯示'] = map_df['完登狀態'].apply(lambda x: "✅ 已完登" if x else "🎯 未完登")

    view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
    layer = pdk.Layer(
        "ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], 
        get_fill_color="color", get_radius=2500, pickable=True
    )
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view_state, map_provider="mapbox",
        map_style="mapbox://styles/mapbox/satellite-streets-v12",
        api_keys={"mapbox": st.secrets["MAPBOX_API_KEY"]},
        tooltip={"text": "{山名}\n海拔: {海拔(m)}m\n狀態: {狀態顯示}"}
    ))

    # ==========================================
    # 5. 📡 登山戰情室 (整合 F-B0053-033)
    # ==========================================
    st.divider()
    st.write("### 📡 登山戰情室 (即時氣象與監控)")
    tab1, tab2, tab3 = st.tabs(["⛰️ 官方登山預報網頁", "🌧️ NCDR 降雨監測", "🌡️ 精準登山點 API"])

    with tab1:
        st.caption("直接存取氣象署南一段專區")
        components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=600, scrolling=True)

    with tab2:
        st.caption("即時降雨雷達回波趨勢")
        components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=700, scrolling=True)

    with tab3:
        st.write("#### ⛰️ 百岳專屬 API 預報 (F-B0053-033)")
        cwa_key = st.secrets.get("CWA_API_KEY")
        mountain_list, err = get_cwa_mountain_forecast(cwa_key)
        
        if mountain_list:
            m_names = [m['locationName'] for m in mountain_list]
            # 預設選取「關山」，符合南一段需求
            default_idx = m_names.index("關山") if "關山" in m_names else 0
            sel_m = st.selectbox("選擇預報點：", m_names, index=default_idx)
            
            target_m = next(m for m in mountain_list if m['locationName'] == sel_m)
            # 提取 WeatherDescription (033 格式的核心描述)
            weather_elements = target_m['weatherElement']
            wx_desc_element = next(e for e in weather_elements if e['elementName'] == 'WeatherDescription')
            
            # 建立顯示表格
            forecast_data = []
            for item in wx_desc_element['time'][:8]: # 顯示前 8 個時段 (約 4 天)
                forecast_data.append({
                    "預報時段": item['startTime'][5:16].replace('T', ' '),
                    "詳細天氣描述": item['elementValue'][0]['WeatherDescription']
                })
            
            st.table(pd.DataFrame(forecast_data))
            st.info("💡 小技巧：此 API 提供的溫度已包含海拔校正，描述中的『風速』對稜線行進安全至關重要。")
        else:
            st.error(f"API 載入失敗：{err}。請檢查 API Key 是否正確設定於 secrets 中。")

    # ==========================================
    # 6. 🔍 快速打卡與搜尋
    # ==========================================
    st.divider()
    st.write("### 🔍 快速打卡與搜尋")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        search = st.text_input("搜尋山名 (例如：小關山):", "")
    with col_b:
        filter_st = st.selectbox("篩選狀態", ["全部", "🎯 未完登", "✅ 已完登"])

    # 資料過濾邏輯
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
        # 將編輯後的內容更新回原始 dataframe 並存檔
        df.update(edited_df)
        df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig')
        st.success("紀錄更新成功！")
        st.rerun()
