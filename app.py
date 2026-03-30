import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import urllib3
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# ==========================================
# 1. 基礎設定與輔助函數
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="百岳紀錄&氣象情報 x 上河配速", layout="wide")

FILE_PATH = 'baiyue_tracking.csv'

# 解析上河範本的特殊時間格式 (支援 "0:135" 或 "01:20:00")
def parse_sh_minutes(time_val):
    if pd.isna(time_val) or str(time_val).strip() == "": return 0
    time_str = str(time_val).strip()
    try:
        parts = time_str.split(':')
        if len(parts) >= 3:
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(float(time_str))
    except:
        return 0

# ==========================================
# 2. 側邊導覽列 (雙系統切換)
# ==========================================
st.sidebar.title("🧭 導航選單")
page = st.sidebar.radio("切換功能", ["🗺️ 百岳紀錄&氣象情報", "⏱️ 上河配速追蹤系統"])

# ==========================================
# 3. 系統 A：百岳地圖與戰情室
# ==========================================
if page == "🗺️ 百岳紀錄&氣象情報":
    st.title("🏔️ 台灣百岳紀錄&氣象小工具")

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

        completed = df[df['完登狀態'].astype(str).str.upper() == 'TRUE']['山名'].nunique()
        st.subheader(f"目前完登進度：{completed} / 100")
        st.progress(completed / 100)

        # 3D 地圖展示
        st.write("### 🗺️ 3D 百岳完登版圖")
        map_df = df.dropna(subset=['經度', '緯度']).copy()
        map_df['完登狀態'] = map_df['完登狀態'].astype(str).str.upper() == 'TRUE'
        map_df['color'] = map_df['完登狀態'].apply(lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120])
        
        view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
        layer = pdk.Layer("ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], get_fill_color="color", get_radius=2500, pickable=True)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, map_provider="mapbox", map_style="mapbox://styles/mapbox/satellite-streets-v12", api_keys={"mapbox": st.secrets.get("MAPBOX_API_KEY", "")}, tooltip={"text": "{山名}\n海拔: {海拔(m)}m"}))

        # 氣象情報
        st.divider()
        st.write("### 📡 氣象情報")
        tab1, tab2 = st.tabs(["⛰️ 官方登山預報網頁", "🌧️ NCDR 降雨監測"])
        with tab1:
            st.caption("即時顯示：中央氣象署")
            components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=650, scrolling=True)
        with tab2:
            st.caption("即時顯示：NCDR 全台降雨雷達回波趨勢")
            components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=750, scrolling=True)

        # 快速打卡
        st.divider()
        st.write("### 🔍 快速打卡與紀錄搜尋")
        col_a, col_b = st.columns([2, 1])
        with col_a: search = st.text_input("搜尋山名 (如: 小關山):", "")
        with col_b: filter_st = st.selectbox("狀態篩選", ["全部", "🎯 未完登", "✅ 已完登"])

        display_df = df.copy()
        if search: display_df = display_df[display_df['山名'].str.contains(search, na=False)]
        if filter_st == "🎯 未完登": display_df = display_df[display_df['完登狀態'].astype(str).str.upper() != 'TRUE']
        elif filter_st == "✅ 已完登": display_df = display_df[display_df['完登狀態'].astype(str).str.upper() == 'TRUE']

        edited_df = st.data_editor(display_df, column_config={"完登狀態": st.column_config.CheckboxColumn("是否完登?"), "登頂日期": st.column_config.TextColumn("登頂日期 (YYYY-MM-DD)")}, disabled=["山名", "海拔(m)", "難度", "經度", "緯度"], use_container_width=True, hide_index=True)

        if st.button("💾 儲存最新紀錄", type="primary"):
            df.update(edited_df)
            df.to_csv(FILE_PATH, index=False, encoding='utf-8-sig')
            st.success("紀錄已存檔！")
            st.rerun()

# ==========================================
# 4. 系統 B：上河配速追蹤系統 (支援戰術 ETA 模擬)
# ==========================================
elif page == "⏱️ 上河配速追蹤系統":
    st.title("⏱️ 上河配速追蹤系統")
    st.write("### 📥 載入行程計畫")
    st.caption("請上傳從 Google Sheet 範本下載的 CSV 檔 (需包含『分段地標』與『上河步程』欄位)")
    
    uploaded_file = st.file_uploader("上傳你的行程 CSV 檔", type=["csv"], label_visibility="collapsed")

    # 初始化 session_state
    if 'hike_df' not in st.session_state:
        st.session_state.hike_df = pd.DataFrame([{"分段地標": "起點", "上河步程": 0, "休息": 0, "抵達時刻": ""}])
        st.session_state.has_uploaded = False

    # 處理上傳的 CSV 檔案 (智慧掃描表頭 + 智慧編碼偵測)
    if uploaded_file is not None and not st.session_state.get('has_uploaded'):
        try:
            # 🚀 智慧編碼偵測 (先試 UTF-8，失敗則自動切換 Big5)
            try:
                raw_df = pd.read_csv(uploaded_file, header=None, encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                try:
                    raw_df = pd.read_csv(uploaded_file, header=None, encoding='big5')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    raw_df = pd.read_csv(uploaded_file, header=None, encoding='utf-8-sig')

            header_idx = -1
            # 智慧掃描：向下尋找包含「分段地標」的那一行作為標題
            for i, row in raw_df.iterrows():
                if "分段地標" in str(row.values):
                    header_idx = i
                    break
            
            if header_idx != -1:
                raw_df.columns = raw_df.iloc[header_idx]
                clean_df = raw_df.iloc[header_idx+1:].dropna(subset=["分段地標"]).copy()
                
                parsed_data = []
                for _, row in clean_df.iterrows():
                    parsed_data.append({
                        "分段地標": str(row.get("分段地標", "")).strip(),
                        "上河步程": parse_sh_minutes(row.get("上河步程", 0)),
                        "抵達時刻": "", 
                        "休息": 0 
                    })
                st.session_state.hike_df = pd.DataFrame(parsed_data)
                st.session_state.has_uploaded = True # 標記為已上傳
                st.success("✅ 行程檔載入成功！(自動解碼完成)")
            else:
                st.error("CSV 檔案中找不到包含『分段地標』的標題行。")
        except Exception as e:
            st.error(f"檔案讀取失敗：{e}")

    # 若使用者按了 X 清除檔案，則重置狀態
    if uploaded_file is None:
        st.session_state.has_uploaded = False

    st.write("### 📝 實時配速紀錄表")
    st.caption("💡 可動態新增列，或直接在『實際抵達』輸入 HH:MM 格式時間 (例如：08:45)")

    # 動態資料編輯器
    edited_df = st.data_editor(
        st.session_state.hike_df,
        num_rows="dynamic",
        column_config={
            "分段地標": st.column_config.TextColumn("地標 / CP點", width="medium"),
            "上河步程": st.column_config.NumberColumn("上河標準(分)"),
            "抵達時刻": st.column_config.TextColumn("實際抵達 (HH:MM)", help="請輸入 24 小時制時間，例: 08:30"),
            "休息": st.column_config.NumberColumn("預計休息(分)")
        },
        use_container_width=True,
        key="hike_editor"
    )

    # ==========================================
    # 🌟 戰術模擬控制區 (ETA 推算)
    # ==========================================
    st.divider()
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        target_c = st.number_input("🎯 設定目標配速 (推算 ETA 用)", min_value=0.3, max_value=2.0, value=0.8, step=0.1)
    with col_c2:
        st.write("") 
        st.write("")
        analyze_btn = st.button("📊 計算當前配速 & 推算 ETA", type="primary", use_container_width=True)

    if analyze_btn:
        try:
            calc_df = edited_df.copy()
            coeffs = []
            
            # 💡 修復關鍵：預先建立所有必要欄位，防止未填資料時引發 KeyError
            calc_df["預估耗時(分)"] = ""
            calc_df["預估抵達時刻"] = ""
            calc_df["分段係數"] = "" 
            
            # --- 第一階段：計算已完成路段的真實係數 ---
            for i in range(1, len(calc_df)):
                t_curr = calc_df.iloc[i]["抵達時刻"]
                t_prev = calc_df.iloc[i-1]["抵達時刻"]
                sh_min = calc_df.iloc[i].get("上河步程", 0)
                
                if pd.notna(t_curr) and t_curr != "" and pd.notna(t_prev) and t_prev != "":
                    fmt = "%H:%M"
                    delta = datetime.strptime(str(t_curr), fmt) - datetime.strptime(str(t_prev), fmt)
                    actual_min = delta.total_seconds() / 60
                    if actual_min < 0: actual_min += 24 * 60 
                    
                    rest_min = calc_df.iloc[i-1].get("休息", 0)
                    if pd.isna(rest_min): rest_min = 0
                    
                    walk_min = actual_min - float(rest_min)
                    
                    if walk_min < 0:
                        walk_min = 0 
                        st.toast(f"⚠️ 警告：{calc_df.iloc[i]['分段地標']} 的休息時間大於實際經過時間！")
                    
                    if float(sh_min) > 0:
                        c = round(walk_min / float(sh_min), 2)
                        calc_df.at[i, "分段係數"] = c
                        coeffs.append(c)

            avg_c = round(sum(coeffs) / len(coeffs), 2) if coeffs else 0.0
            
            # --- 第二階段：動態推算未來的 ETA ---
            last_known_time = None
            for i in range(len(calc_df)):
                t_curr = calc_df.iloc[i]["抵達時刻"]
                
                if pd.notna(t_curr) and t_curr != "":
                    last_known_time = datetime.strptime(str(t_curr), "%H:%M")
                    calc_df.at[i, "預估抵達時刻"] = "✅ 已打卡"
                else:
                    if last_known_time is not None:
                        rest = calc_df.iloc[i-1].get("休息", 0)
                        if pd.isna(rest): rest = 0
                        
                        sh_min = calc_df.iloc[i].get("上河步程", 0)
                        if pd.isna(sh_min): sh_min = 0
                        
                        est_walk_min = float(sh_min) * target_c
                        
                        total_add_min = int(float(rest) + est_walk_min)
                        last_known_time = last_known_time + timedelta(minutes=total_add_min)
                        
                        calc_df.at[i, "預估耗時(分)"] = int(est_walk_min)
                        calc_df.at[i, "預估抵達時刻"] = f"🕒 {last_known_time.strftime('%H:%M')}"

            # --- 第三階段：顯示戰情面板 ---
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("當前實際平均配速", f"{avg_c}" if avg_c > 0 else "尚未計算")
            col_m2.metric("模擬設定配速", f"{target_c}")
            
            if avg_c == 0: status = "準備出發"
            elif avg_c < 0.7: status = "🏃 越野跑模式 (神速)"
            elif avg_c < 0.8: status = "🔥 強健推行 (超前)"
            elif avg_c <= 0.9: status = "✅ 穩定配速 (標準)"
            else: status = "⚠️ 體能衰退或地形困難"
            col_m3.metric("實際體能狀態", status)
            
            st.write("#### 📈 動態行程推算表")
            st.caption(f"✨ 未來的抵達時間，是以你設定的 **{target_c}** 模擬配速進行推算。")
            
            display_cols = ["分段地標", "抵達時刻", "預估抵達時刻", "預估耗時(分)", "上河步程", "休息", "分段係數"]
            st.dataframe(calc_df[display_cols], use_container_width=True)

        except Exception as e:
            st.error(f"計算出錯，請確保時間格式為 HH:MM (如 08:30)。錯誤詳情: {e}")
