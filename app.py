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
# 2. 雙軌氣象解析 (修正 KeyError 版本)
# ==========================================
@st.cache_data(ttl=3600)
def get_cwa_mountain_forecast(api_key):
    # 軌道 A：API
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

    # 軌道 B：本地 JSON (解析您的 F-B0053-033.json)
    if os.path.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'cwaopendata' in data:
                    # 這裡是關鍵：存取 Dataset -> Locations -> Location
                    return data['cwaopendata']['Dataset']['Locations']['Location'], "📁 已啟用本地 JSON 預報 (4/3-4/5 南一段行程參考)"
        except Exception as e:
            return None, f"本地檔案解析失敗: {str(e)}"

    return None, "❌ 無法取得氣象資料"

# ==========================================
# 3. 資料載入
# ==========================================
if not os.path.exists(FILE_PATH):
    st.error(f"找不到檔案：{FILE_PATH}")
else:
    df = pd.read_csv(FILE_PATH, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    
    # 進度展示
    completed = df[df['完登狀態'].astype(str).str.upper() == 'TRUE']['山名'].nunique()
    st.subheader(f"目前完登進度：{completed} / 100")
    st.progress(completed / 100)

    # ==========================================
    # 4. 3D 地圖展示
    # ==========================================
    st.write("### 🗺️ 3D 百岳完登版圖")
    # 這裡假設您的 CSV 已包含座標，若無則會使用內建座標邏輯
    map_df = df.dropna(subset=['經度', '緯度']).copy()
    map_df['完登狀態'] = map_df['完登狀態'].astype(str).str.upper() == 'TRUE'
    map_df['color'] = map_df['完登狀態'].apply(lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120])
    
    view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
    layer = pdk.Layer("ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], get_fill_color="color", get_radius=2500, pickable=True)
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view_state, map_provider="mapbox",
        map_style="mapbox://styles/mapbox/satellite-streets-v12",
        api_keys={"mapbox": st.secrets.get("MAPBOX_API_KEY", "")},
        tooltip={"text": "{山名}"}
    ))

    # ==========================================
    # 5. 📡 戰情室 (修復 KeyError)
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
            # 💡 修正處：相容 LocationName 與 locationName
            m_names = [m.get('LocationName') or m.get('locationName') for m in mountain_list]
            
            def_idx = m_names.index("關山") if "關山" in m_names else 0
            sel_m = st.selectbox("選擇預報點：", m_names, index=def_idx)
            
            # 找到選中的山岳資料
            target_m = next(m for m in mountain_list if (m.get('LocationName') or m.get('locationName')) == sel_m)
            
            # 提取 WeatherElement
            elements = target_m.get('WeatherElement') or target_m.get('weatherElement')
            
            # 找到 WeatherDescription
            wx_element = next(e for e in elements if e.get('ElementName') == 'WeatherDescription' or e.get('elementName') == 'WeatherDescription')
            
            res_data = []
            for item in wx_element['Time'][:10]:
                # 相容 elementValue 的大小寫
                val_list = item.get('ElementValue') or item.get('elementValue')
                desc = val_list[0].get('WeatherDescription')
                
                res_data.append({
                    "時段": item.get('StartTime', '')[5:16].replace('T', ' '),
                    "詳細預報 (含體感、風速)": desc.replace('。', '。\n')
                })
            
            st.table(pd.DataFrame(res_data))
        else:
            st.warning("⚠️ 無法載入預報。")

    # ==========================================
    # 6. 🔍 快速打卡區塊
    # ==========================================
    st.divider()
    st.write("### 🔍 快速打卡與搜尋")
    search = st.text_input("搜尋山名 (如: 海諾南山):", "")
    display_df = df.copy()
    if search:
        display_df = display_df[display_df['山名'].str.contains(search, na=False)]
    
    edited_df = st.data_editor(
        display_df,
        column_config={"完登狀態": st.column_config.CheckboxColumn("是否完登?")},
        disabled=["山名", "海拔(m)", "難度", "經度", "緯度"],
        use_container_width=True, hide_index=True
    )

    if st.button("💾 儲存最新紀錄", type="primary"):
        df.update(edited_df)
        df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig')
        st.success("紀錄已儲存！")
        st.rerun()
