import streamlit as st
import pandas as pd
import os
import pydeck as pdk

st.set_page_config(page_title="我的百岳紀錄 App", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與 3D 版圖")

FILE_PATH = 'baiyue_tracking.csv'
UPLOAD_DIR = 'uploads'

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ==========================================
# 內建百岳經緯度資料庫 (供系統自動補齊使用)
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
        
        # ==========================================
        # 智慧型座標自動填寫系統
        # ==========================================
        needs_save = False
        if '經度' not in df.columns:
            df['經度'] = None
            needs_save = True
        if '緯度' not in df.columns:
            df['緯度'] = None
            needs_save = True
            
        # 掃描每一筆資料，如果沒有經緯度，就從內建字典抓取
        for idx, row in df.iterrows():
            peak_name = str(row.get('山名', '')).strip()
            if pd.isna(row['經度']) or pd.isna(row['緯度']):
                if peak_name in BAIYUE_COORDS:
                    df.at[idx, '經度'] = BAIYUE_COORDS[peak_name][0]
                    df.at[idx, '緯度'] = BAIYUE_COORDS[peak_name][1]
                    needs_save = True
                    
        # 如果有更新座標，自動存檔並重整畫面
        if needs_save:
            df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig', sep=',')
            st.rerun()

        # 整理基礎欄位狀態
        if '完登狀態' in df.columns:
            df['完登狀態'] = df['完登狀態'].astype(str).str.strip().str.upper() == 'TRUE'
        if '登頂日期' not in df.columns:
            df['登頂日期'] = ""
        else:
            df['登頂日期'] = df['登頂日期'].fillna("")

        # 計算進度
        completed_count = df[df['完登狀態'] == True]['山名'].nunique() if '山名' in df.columns else 0
        total_count = 100
        st.subheader(f"目前的完登進度：{completed_count} / {total_count}")
        st.progress(int((completed_count / total_count) * 100))

       # ==========================================
        # 🗺️ 3D 百岳分佈與完登版圖 (重點功能)
        # ==========================================
        st.divider()
        st.write("### 🗺️ 台灣百岳 3D 完登版圖")
        
        map_df = df.dropna(subset=['經度', '緯度']).copy()
        
        if not map_df.empty:
            # 1. 設定顏色：已完登為亮橘金，未完登為半透明純白
            map_df['color'] = map_df['完登狀態'].apply(
                lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120]
            )
            
            # 2. 👉 新增這一行：將 True/False 轉換成好看的中文文字
            map_df['狀態顯示'] = map_df['完登狀態'].apply(
                lambda x: "✅ 已完登" if x else "🎯 未完登"
            )
            
            # 設定散佈圖層
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_df,
                get_position=["經度", "緯度"],
                get_fill_color="color",
                get_radius=2500, # 圓點半徑
                pickable=True
            )
            
            # 建立 3D 傾斜視角
            view_state = pdk.ViewState(
                longitude=120.9573,
                latitude=23.4700,
                zoom=7.5,
                pitch=25,
                bearing=0
            )
            
            # 渲染地圖
            st.pydeck_chart(pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                map_provider="mapbox", 
                map_style="mapbox://styles/mapbox/satellite-streets-v12", 
               api_keys={"mapbox": st.secrets["MAPBOX_API_KEY"]}, 
                # 3. 👉 將 tooltip 裡的 {完登狀態} 改成讀取我們剛剛建立的 {狀態顯示}
                tooltip={"text": "{山名}\n海拔: {海拔(m)}m\n狀態: {狀態顯示}"}
            ))
        else:
            st.info("地圖載入中或座標資料庫未生效...")

        # ==========================================
        # 快速尋找與打卡區塊
        # ==========================================
        st.divider()
        st.write("### 🔍 快速尋找與打卡")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("輸入山名搜尋 (例如：玉山、雪山)", "")
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