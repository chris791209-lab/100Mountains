import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import requests # 新增：用來向氣象署發送請求的套件

st.set_page_config(page_title="我的百岳紀錄 App", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與 3D 版圖")

FILE_PATH = 'baiyue_tracking.csv'
UPLOAD_DIR = 'uploads'

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ==========================================
# 氣象署 API 資料抓取與快取 (Cache)
# 設定快取 1 小時 (3600秒)，避免頻繁重整網頁導致 API 額度被扣光
# ==========================================
@st.cache_data(ttl=3600)
def get_mountain_weather(api_key):
    # F-B0053-031 是氣象署的高山/遊憩區預報資料集
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-B0053-031?Authorization={api_key}&format=JSON"
    try:
        resp = requests.get(url)
        data = resp.json()
        # 提取出所有山區的位置資料
        return data['records']['locations'][0]['location']
    except Exception as e:
        return None

# ==========================================
# 內建百岳經緯度資料庫
# ==========================================
BAIYUE_COORDS = {
    '玉山主峰': [120.957, 23.470], '雪山主峰': [121.231, 24.383], '玉山東峰': [120.963, 23.471],
    '玉山北峰': [120.959, 23.485], '玉山南峰': [120.957, 23.454], '秀姑巒山': [121.066, 23.498],
    '馬博拉斯山': [121.076, 23.518], '南湖大山': [121.439, 24.361], '南湖主峰': [121.439, 24.361],
    '東小南山': [120.962, 23.444], '中央尖山': [121.416, 24.310], '雪山北峰': [121.248, 24.404],
    '關山': [120.908, 23.243], '南湖東峰': [121.448, 24.363], '大水窟山': [121.065, 23.469],
    '東郡大山': [121.099, 23.612], '奇萊北峰': [121.332, 24.116], '向陽山': [120.985, 23.284],
    '大劍山': [121.198, 24.327], '雲峰': [120.985, 23.361], '奇萊主峰': [121.325, 24.103],
    '奇萊主山': [121.325, 24.103], '馬利加南山': [121.118, 23.522], '南湖北山': [121.437, 24.383],
    '大雪山': [121.135, 24.316], '品田山': [121.265, 24.428], '玉山西峰': [120.938, 23.469],
    '南湖南峰': [121.435, 24.341], '東巒大山': [121.096, 23.645], '無明山': [121.341, 24.258],
    '無名山': [121.341, 24.258], '巴巴山': [121.434, 24.336], '馬西山': [121.205, 23.486],
    '合歡北峰': [121.284, 24.180], '合歡東峰': [121.281, 24.136], '小霸尖山': [121.245, 24.455],
    '合歡主峰': [121.271, 24.143], '南玉山': [120.932, 23.441], '畢祿山': [121.316, 24.209],
    '卓社大山': [121.065, 23.829], '奇萊南峰': [121.281, 24.061], '南華山': [121.282, 24.038],
    '光頭山': [121.268, 23.953], '能高山': [121.259, 23.989], '能高主峰': [121.259, 23.989],
    '能高南峰': [121.268, 23.945], '能高山南峰': [121.268, 23.945], '安東軍山': [121.272, 23.871],
    '白石山': [121.269, 23.911], '牧山': [121.115, 23.812], '萬東山西峰': [121.115, 23.812],
    '火山': [121.115, 23.812], '干卓萬山': [121.056, 23.837], '火石山': [121.205, 24.398],
    '池有山': [121.279, 24.425], '伊澤山': [121.244, 24.469], '大霸尖山': [121.250, 24.458],
    '雪山東峰': [121.271, 24.387], '志佳陽大山': [121.238, 24.341], '劍山': [121.168, 24.316],
    '小劍山': [121.168, 24.316], '佳陽山': [121.181, 24.322], '白姑大山': [121.109, 24.202],
    '八通關山': [121.006, 23.488], '達芬尖山': [121.037, 23.468], '塔芬山': [121.057, 23.411],
    '轆轆山': [121.066, 23.364], '南雙頭山': [121.026, 23.333], '三叉山': [121.038, 23.284],
    '新康山': [121.127, 23.322], '布拉克桑山': [121.092, 23.238], '海諾南山': [120.904, 23.203],
    '小關山': [120.895, 23.166], '卑南主山': [120.880, 23.056], '北大武山': [120.760, 22.626],
    '西巒大山': [120.941, 23.681], '郡大山': [120.962, 23.577], '中雪山': [121.146, 24.323],
    '頭鷹山': [121.171, 24.352], '閂山': [121.291, 24.264], '鈴鳴山': [121.328, 24.238],
    '羊頭山': [121.350, 24.195], '屏風山': [121.332, 24.159], '石門山': [121.285, 24.152],
    '立霧主山': [121.373, 24.085], '帕托魯山': [121.401, 24.081], '太魯閣大山': [121.385, 24.062],
    '磐石山': [121.388, 24.104], '丹大山': [121.215, 23.593], '內嶺爾山': [121.229, 23.619],
    '義西請馬至山': [121.168, 23.568], '無雙山': [121.028, 23.574], '盆駒山': [121.057, 23.535],
    '馬比杉山': [121.465, 24.340], '審馬陣山': [121.398, 24.382], '喀拉業山': [121.303, 24.450],
    '桃山': [121.288, 24.432], '庫哈諾辛山': [120.908, 23.275], '關山嶺山': [120.959, 23.273],
    '塔關山': [120.941, 23.284], '六順山': [121.238, 23.730], '玉山前峰': [120.931, 23.472],
    '合歡西峰': [121.246, 24.168], '加利山': [121.232, 24.444], '喀西帕南山': [121.205, 23.486],
    '鹿山': [120.984, 23.450], '甘薯峰': [121.340, 24.265]
}

if not os.path.exists(FILE_PATH):
    st.error(f"⚠️ 找不到檔案：{FILE_PATH}。請確認檔名和路徑是否正確！")
else:
    encodings_to_try = ['utf-8-sig', 'cp950', 'utf-8', 'big5']
    df = None
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(FILE_PATH, encoding=enc, sep=None, engine='python')
            break
        except Exception:
            continue
            
    if df is not None and not df.empty:
        df.columns = df.columns.str.strip()
        needs_save = False
        if '經度' not in df.columns:
            df['經度'] = None
            needs_save = True
        if '緯度' not in df.columns:
            df['緯度'] = None
            needs_save = True
            
        for idx, row in df.iterrows():
            peak_name = str(row.get('山名', '')).strip()
            if pd.isna(row['經度']) or pd.isna(row['緯度']):
                if peak_name in BAIYUE_COORDS:
                    df.at[idx, '經度'] = BAIYUE_COORDS[peak_name][0]
                    df.at[idx, '緯度'] = BAIYUE_COORDS[peak_name][1]
                    needs_save = True
                    
        if needs_save:
            df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig', sep=',')
            st.rerun()

        if '完登狀態' in df.columns:
            df['完登狀態'] = df['完登狀態'].astype(str).str.strip().str.upper() == 'TRUE'
        if '登頂日期' not in df.columns:
            df['登頂日期'] = ""
        else:
            df['登頂日期'] = df['登頂日期'].fillna("")

        completed_count = df[df['完登狀態'] == True]['山名'].nunique() if '山名' in df.columns else 0
        total_count = 100
        st.subheader(f"目前的完登進度：{completed_count} / {total_count}")
        st.progress(int((completed_count / total_count) * 100))

        # ==========================================
        # 🗺️ 3D 百岳分佈與完登版圖
        # ==========================================
        st.divider()
        st.write("### 🗺️ 台灣百岳 3D 完登版圖")
        
        map_df = df.dropna(subset=['經度', '緯度']).copy()
        
        if not map_df.empty:
            map_df['color'] = map_df['完登狀態'].apply(
                lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120]
            )
            map_df['狀態顯示'] = map_df['完登狀態'].apply(
                lambda x: "✅ 已完登" if x else "🎯 未完登"
            )
            
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_df,
                get_position=["經度", "緯度"],
                get_fill_color="color",
                get_radius=2500, 
                pickable=True
            )
            
            view_state = pdk.ViewState(
                longitude=120.9573,
                latitude=23.4700,
                zoom=7.5,
                pitch=25,
                bearing=0
            )
            
            # 安全讀取 Mapbox 金鑰
            try:
                mapbox_key = st.secrets["MAPBOX_API_KEY"]
            except:
                mapbox_key = ""

            st.pydeck_chart(pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_provider="mapbox", 
                map_style="mapbox://styles/mapbox/satellite-streets-v12", 
                api_keys={"mapbox": mapbox_key}, 
                tooltip={"text": "{山名}\n海拔: {海拔(m)}m\n狀態: {狀態顯示}"}
            ))

        # ==========================================
        # ⛅ 氣象署高山預報站 (全新整合區塊)
        # ==========================================
        st.write("### ⛅ 近期高山天氣預報 (中央氣象署)")
        try:
            cwa_key = st.secrets["CWA_API_KEY"]
        except:
            cwa_key = None
            
        if cwa_key:
            weather_data = get_mountain_weather(cwa_key)
            if weather_data:
                # 撈出氣象署有提供預報的「山區名稱」
                mountain_names = [loc['locationName'] for loc in weather_data]
                
                # 智慧預設：將預設選項設為「關山」，方便做南一段的功課
                default_idx = mountain_names.index("關山") if "關山" in mountain_names else 0
                
                selected_mt = st.selectbox("請選擇鄰近氣象站（南一段行程建議選擇「關山」）：", mountain_names, index=default_idx)
                
                # 取出所選山區的數據
                target_data = next((loc for loc in weather_data if loc['locationName'] == selected_mt), None)
                if target_data:
                    try:
                        elements = target_data['weatherElement']
                        wx_list = next(e['time'] for e in elements if e['elementName'] == 'Wx')
                        pop_list = next(e['time'] for e in elements if e['elementName'] == 'PoP12h')
                        mint_list = next(e['time'] for e in elements if e['elementName'] == 'MinT')
                        maxt_list = next(e['time'] for e in elements if e['elementName'] == 'MaxT')
                        
                        forecasts = []
                        # 顯示未來 6 個時段的預報 (約三天份的精準資料)
                        for i in range(min(6, len(wx_list))):
                            start_time = wx_list[i]['startTime'][5:16] # 擷取 MM-DD HH:mm
                            wx_val = wx_list[i]['elementValue'][0]['value']
                            pop_val = pop_list[i]['elementValue'][0]['value'] if i < len(pop_list) else "-"
                            mint_val = mint_list[i]['elementValue'][0]['value'] if i < len(mint_list) else "-"
                            maxt_val = maxt_list[i]['elementValue'][0]['value'] if i < len(maxt_list) else "-"
                            
                            forecasts.append({
                                "預報時間": start_time,
                                "天氣狀態": wx_val,
                                "降雨機率(%)": pop_val,
                                "氣溫(°C)": f"{mint_val} ~ {maxt_val}"
                            })
                        
                        st.dataframe(pd.DataFrame(forecasts), use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error("氣象資料格式解析發生錯誤，氣象署可能調整了資料結構。")
            else:
                st.warning("無法取得氣象資料，請檢查 API 授權碼是否正確或網路是否連線。")
        else:
            st.info("💡 尚未在 secrets.toml 設定氣象署 API 金鑰，請先完成設定以解鎖天氣功能。")

        # ==========================================
        # 快速尋找與打卡區塊
        # ==========================================
        st.divider()
        st.write("### 🔍 快速尋找與打卡")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("輸入山名搜尋 (例如：玉山、關山)", "")
        with col2:
            filter_status = st.selectbox("狀態篩選", ["全部百岳", "🎯 未完登", "✅ 已完登"])

        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[filtered_df['山名'].str.contains(search_term, na=False)]
        if filter_status == "🎯 未完登":
            filtered_df = filtered_df[filtered_df['完登狀態'] == False]
        elif filter_status == "✅ 已完登":
            filtered_df = filtered_df[filtered_df['完登狀態'] == True]

        if not filtered_df.empty:
            edited_filtered_df = st.data_editor(
                filtered_df,
                column_config={
                    "完登狀態": st.column_config.CheckboxColumn("是否完登?", help="勾選代表已登頂"),
                    "登頂日期": st.column_config.TextColumn("登頂日期", help="格式建議：YYYY-MM-DD")
                },
                disabled=["山名", "海拔(m)", "難度", "經度", "緯度"], 
                hide_index=True,
                use_container_width=True
            )

            if st.button("💾 儲存最新紀錄", type="primary"):
                df.update(edited_filtered_df)
                df['完登狀態'] = df['完登狀態'].astype(bool)
                df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig', sep=',')
                st.success("紀錄已更新！")
                st.rerun()
