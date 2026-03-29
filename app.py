import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import requests
import urllib3
import streamlit.components.v1 as components

# 1. 基礎設定
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="我的百岳戰情室", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與戰情室")

FILE_PATH = 'baiyue_tracking.csv'

# ==========================================
# 2. 核心氣象解析 (完全適配 F-B0053-033 JSON 結構)
# ==========================================
@st.cache_data(ttl=3600)
def get_cwa_mountain_forecast(api_key):
    if not api_key: return None, "未設定金鑰"
    clean_key = api_key.strip()
    
    # 使用正確的 API 請求網址
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-B0053-033?Authorization={clean_key}&format=JSON"
    
    try:
        resp = requests.get(url, timeout=10, verify=False)
        if resp.status_code != 200:
            return None, f"伺服器回應錯誤：{resp.status_code}"
            
        data = resp.json()
        
        # 關鍵修正：針對 033 格式的深度解析
        # 結構為 records -> locations -> location
        if 'records' in data and 'locations' in data['records']:
            return data['records']['locations'][0]['location'], None
        elif 'cwaopendata' in data: # 處理另一種可能的封裝格式
            return data['cwaopendata']['dataset']['locations']['location'], None
        else:
            return None, "資料結構不符合預期"
            
    except Exception as e:
        return None, f"連線異常：{str(e)}"

# ==========================================
# 3. 座標資料庫與資料載入
# ==========================================
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
    for idx, row in df.iterrows():
        peak = str(row['山名']).strip()
        if pd.isna(row.get('經度')) and peak in BAIYUE_COORDS:
            df.at[idx, '經度'] = BAIYUE_COORDS[peak][0]
            df.at[idx, '緯度'] = BAIYUE_COORDS[peak][1]

    # 進度
    completed = df[df['完登狀態'].astype(str).str.upper() == 'TRUE']['山名'].nunique()
    st.subheader(f"目前完登：{completed} / 100")
    st.progress(completed / 100)

    # ==========================================
    # 4. 3D 地圖展示
    # ==========================================
    st.write("### 🗺️ 3D 百岳完登版圖")
    map_df = df.dropna(subset=['經度', '緯度']).copy()
    map_df['完登狀態'] = map_df['完登狀態'].astype(str).str.upper() == 'TRUE'
    map_df['color'] = map_df['完登狀態'].apply(lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120])
    
    view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
    layer = pdk.Layer("ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], get_fill_color="color", get_radius=2500, pickable=True)
    
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view_state, map_provider="mapbox",
        map_style="mapbox://styles/mapbox/satellite-streets-v12",
        api_keys={"mapbox": st.secrets["MAPBOX_API_KEY"]},
        tooltip={"text": "{山名}\n海拔: {海拔(m)}m"}
    ))

    # ==========================================
    # 5. 📡 登山戰情室 (解析 033 專業格式)
    # ==========================================
    st.divider()
    st.write("### 📡 登山戰情室")
    tab1, tab2, tab3 = st.tabs(["⛰️ 官方登山網頁", "🌧️ 即時降雨監測", "🌡️ 高山精準預報"])

    with tab1:
        components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=600, scrolling=True)
    with tab2:
        components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=700, scrolling=True)

    with tab3:
        st.write("#### ⛰️ 百岳逐 12 小時專業預報")
        cwa_key = st.secrets.get("CWA_API_KEY")
        mountain_list, err = get_cwa_mountain_forecast(cwa_key)
        
        if mountain_list:
            m_names = [m['locationName'] for m in mountain_list]
            # 預設選取關山
            def_idx = m_names.index("關山") if "關山" in m_names else 0
            sel_m = st.selectbox("選擇預報點：", m_names, index=def_idx)
            
            target_m = next(m for m in mountain_list if m['locationName'] == sel_m)
            
            # 033 格式解析：WeatherDescription 包含了所有關鍵訊息
            elements = target_m['weatherElement']
            wx_desc = next(e for e in elements if e['elementName'] == 'WeatherDescription')
            
            # 建立更精細的表格
            res = []
            for item in wx_desc['time'][:10]: # 顯示未來 5 天
                desc = item['elementValue'][0]['WeatherDescription']
                # 簡單格式化描述，讓它在表格裡好讀一點
                clean_desc = desc.replace('。', '。\n')
                
                res.append({
                    "時段": item['startTime'][5:16].replace('T', ' '),
                    "詳細預報 (含體感與風速)": clean_desc
                })
            
            st.table(pd.DataFrame(res))
            st.info("💡 此預報已包含海拔校正，對於下週南一段行程，請特別留意『風速』描述。")
        else:
            st.error(f"API 解析失敗：{err}")

    # ==========================================
    # 6. 🔍 打卡與搜尋
    # ==========================================
    st.divider()
    st.write("### 🔍 快速打卡與搜尋")
    search = st.text_input("搜尋山名:", "")
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
        st.success("紀錄更新成功！")
        st.rerun()
