import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import requests
import urllib3
import json
import streamlit.components.v1 as components

# 1. 基礎設定
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="我的百岳戰情室", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與戰情室")

FILE_PATH = 'baiyue_tracking.csv'
LOCAL_JSON = 'F-B0053-033.json'

# ==========================================
# 2. 雙軌氣象解析 (強化防當機機制)
# ==========================================
@st.cache_data(ttl=3600)
def get_cwa_mountain_forecast(api_key):
    # 軌道 A：API 抓取
    if api_key:
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-B0053-033?Authorization={api_key.strip()}&format=JSON"
        try:
            resp = requests.get(url, timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                if 'records' in data and 'locations' in data['records']:
                    return data['records']['locations'][0]['location'], "📡 即時 API 連線成功"
        except:
            pass

    # 軌道 B：本地 JSON 備援
    if os.path.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'cwaopendata' in data:
                    return data['cwaopendata']['Dataset']['Locations']['Location'], "📁 已啟用本地 JSON 預報 (備援)"
        except:
            pass
    return None, "❌ 無法取得氣象資料"

# ==========================================
# 3. 資料載入
# ==========================================
if not os.path.exists(FILE_PATH):
    st.error(f"找不到檔案：{FILE_PATH}")
else:
    df = pd.read_csv(FILE_PATH, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    completed = df[df['完登狀態'].astype(str).str.upper() == 'TRUE']['山名'].nunique()
    st.subheader(f"目前完登進度：{completed} / 100")
    st.progress(completed / 100)

    # ==========================================
    # 4. 3D 地圖
    # ==========================================
    st.write("### 🗺️ 3D 百岳完登版圖")
    map_df = df.dropna(subset=['經度', '緯度']).copy()
    view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
    layer = pdk.Layer("ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], get_fill_color=[255, 170, 0, 255], get_radius=2500)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, map_style="mapbox://styles/mapbox/satellite-streets-v12", api_keys={"mapbox": st.secrets.get("MAPBOX_API_KEY", "")}))

    # ==========================================
    # 5. 📡 戰情室 (修正 StopIteration)
    # ==========================================
    st.divider()
    st.write("### 📡 登山戰情室")
    tab1, tab2, tab3 = st.tabs(["⛰️ 官方網頁", "🌧️ 降雨雷達", "🌡️ 精準數據"])

    with tab1:
        components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=600, scrolling=True)
    with tab2:
        components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=700, scrolling=True)

    with tab3:
        st.write("#### ⛰️ 百岳高山點精準預報 (F-B0053-033)")
        cwa_key = st.secrets.get("CWA_API_KEY")
        mountain_list, source_msg = get_cwa_mountain_forecast(cwa_key)
        
        if mountain_list:
            st.info(source_msg)
            m_names = [m.get('LocationName') or m.get('locationName') for m in mountain_list]
            sel_m = st.selectbox("選擇預報點：", m_names, index=m_names.index("關山") if "關山" in m_names else 0)
            
            target_m = next(m for m in mountain_list if (m.get('LocationName') or m.get('locationName')) == sel_m)
            elements = target_m.get('WeatherElement') or target_m.get('weatherElement') or []
            
            # ✨ 安全搜尋：使用清單推導式避免 StopIteration
            wx_element_list = [e for e in elements if e.get('ElementName') == 'WeatherDescription' or e.get('elementName') == 'WeatherDescription']
            
            if wx_element_list:
                wx_element = wx_element_list[0]
                time_list = wx_element.get('Time') or wx_element.get('time') or []
                
                res_data = []
                for item in time_list[:10]:
                    val_list = item.get('ElementValue') or item.get('elementValue')
                    # 這裡也要防錯
                    if isinstance(val_list, list):
                        desc = val_list[0].get('WeatherDescription') or val_list[0].get('weatherDescription')
                    else:
                        desc = val_list.get('WeatherDescription') or val_list.get('weatherDescription')
                    
                    res_data.append({
                        "時段": item.get('StartTime', '')[5:16].replace('T', ' '),
                        "詳細預報 (含體感、風速)": desc.replace('。', '。\n') if desc else "無詳細描述"
                    })
                st.table(pd.DataFrame(res_data))
            else:
                st.warning("⚠️ 該觀測點目前無詳細 WeatherDescription 預報資料。")
        else:
            st.error("無法載入氣象資料內容。")

    # ==========================================
    # 6. 打卡區
    # ==========================================
    st.divider()
    st.write("### 🔍 快速打卡")
    edited_df = st.data_editor(df, disabled=["山名", "海拔(m)", "經度", "緯度"], use_container_width=True, hide_index=True)
    if st.button("💾 儲存紀錄", type="primary"):
        df.update(edited_df)
        df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig')
        st.success("紀錄已存檔！")
        st.rerun()
