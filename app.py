import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import urllib3
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from supabase import create_client, Client

# ==========================================
# 1. 基礎設定與輔助函數
# ==========================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="百岳紀錄&氣象情報 x 上河配速", layout="wide")

FILE_PATH = 'baiyue_tracking.csv' # 轉為唯讀的百岳基礎清單

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
# 2. Supabase 資料庫連線初始化
# ==========================================
@st.cache_resource
def init_connection() -> Client:
    # 這裡加入除錯訊息，確定系統有沒有讀到 Secrets
    if "SUPABASE_URL" not in st.secrets:
        raise ValueError("系統找不到 SUPABASE_URL，請確認 Secrets 是否有存檔。")
    if "SUPABASE_KEY" not in st.secrets:
        raise ValueError("系統找不到 SUPABASE_KEY，請確認 Secrets 是否有存檔。")
        
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("❌ 資料庫連線失敗！")
    st.warning(f"🔍 系統除錯詳細原因：{e}") # 這行會把真正的問題印出來
    st.stop()
# ==========================================
# 3. 會員登入系統 (Login System)
# ==========================================
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if st.session_state.current_user is None:
    st.title("🔐 台灣百岳戰情室 - 系統登入")
    st.write("請輸入您的專屬帳號密碼以載入個人百岳版圖與配速系統。")
    
    with st.form("login_form"):
        login_user = st.text_input("帳號 (Username)")
        login_pass = st.text_input("密碼 (Password)", type="password")
        submit_btn = st.form_submit_button("登入系統")
        
        if submit_btn:
            # 驗證資料庫中的使用者
            response = supabase.table("users").select("*").eq("username", login_user).eq("password", login_pass).execute()
            if len(response.data) > 0:
                st.session_state.current_user = login_user
                st.success(f"歡迎回來，{login_user}！正在載入戰情室...")
                st.rerun()
            else:
                st.error("帳號或密碼錯誤，請重新輸入。")
    st.stop() # 阻擋未登入者看到下方內容

# ==========================================
# 4. 側邊導覽列與登出功能
# ==========================================
st.sidebar.title("🧭 導航選單")
st.sidebar.info(f"👤 目前登入身分：**{st.session_state.current_user}**")
if st.sidebar.button("登出系統"):
    st.session_state.current_user = None
    st.rerun()

st.sidebar.divider()
page = st.sidebar.radio("切換功能", ["🗺️ 百岳紀錄&氣象情報", "⏱️ 上河配速追蹤系統"])

# ==========================================
# 5. 系統 A：百岳地圖與戰情室 (雲端資料庫版)
# ==========================================
if page == "🗺️ 百岳紀錄&氣象情報":
    st.title(f"🏔️ {st.session_state.current_user} 的百岳紀錄&氣象小工具")

    BAIYUE_COORDS = {
        '玉山主峰': [120.957, 23.470], '雪山主峰': [121.231, 24.383], '關山': [120.908, 23.243],
        '向陽山': [120.985, 23.284], '三叉山': [121.038, 23.284], '海諾南山': [120.904, 23.203],
        '小關山': [120.895, 23.166], '卑南主山': [120.880, 23.056], '庫哈諾辛山': [120.908, 23.275]
    }

    if not os.path.exists(FILE_PATH):
        st.error(f"找不到百岳基礎清單檔案：{FILE_PATH}")
    else:
        # 1. 讀取基礎唯讀清單
        df = pd.read_csv(FILE_PATH, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        df['完登狀態'] = False # 預設全部未完登
        df['登頂日期'] = ""
        
        # 補全座標
        for idx, row in df.iterrows():
            peak = str(row['山名']).strip()
            if pd.isna(row.get('經度')) and peak in BAIYUE_COORDS:
                df.at[idx, '經度'] = BAIYUE_COORDS[peak][0]
                df.at[idx, '緯度'] = BAIYUE_COORDS[peak][1]

        # 2. 從 Supabase 抓取當前使用者的紀錄
        try:
            db_res = supabase.table("baiyue_progress").select("*").eq("username", st.session_state.current_user).execute()
            user_records = db_res.data
            
            # 將雲端紀錄覆蓋到清單上
            for rec in user_records:
                if rec.get("is_completed"):
                    df.loc[df["山名"] == rec["peak_name"], "完登狀態"] = True
                    df.loc[df["山名"] == rec["peak_name"], "登頂日期"] = rec.get("climb_date", "")
        except Exception as e:
            st.error(f"無法載入雲端紀錄：{e}")

        completed = df[df['完登狀態'] == True]['山名'].nunique()
        st.subheader(f"目前完登進度：{completed} / 100")
        st.progress(completed / 100)

        # 3D 地圖展示
        st.write("### 🗺️ 3D 百岳完登版圖")
        map_df = df.dropna(subset=['經度', '緯度']).copy()
        map_df['color'] = map_df['完登狀態'].apply(lambda x: [255, 170, 0, 255] if x else [255, 255, 255, 120])
        
        view_state = pdk.ViewState(longitude=120.95, latitude=23.47, zoom=7.5, pitch=35)
        layer = pdk.Layer("ScatterplotLayer", data=map_df, get_position=["經度", "緯度"], get_fill_color="color", get_radius=2500, pickable=True)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, map_provider="mapbox", map_style="mapbox://styles/mapbox/satellite-streets-v12", api_keys={"mapbox": st.secrets.get("MAPBOX_API_KEY", "")}, tooltip={"text": "{山名}\n海拔: {海拔(m)}m"}))

        # 氣象情報
        st.divider()
        st.write("### 📡 氣象情報")
        tab1, tab2 = st.tabs(["⛰️ 官方登山預報網頁", "🌧️ NCDR 降雨監測"])
        with tab1:
            components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=650, scrolling=True)
        with tab2:
            components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=750, scrolling=True)

        # 雲端快速打卡
        st.divider()
        st.write("### 🔍 快速打卡與紀錄搜尋 (同步至雲端)")
        col_a, col_b = st.columns([2, 1])
        with col_a: search = st.text_input("搜尋山名 (如: 小關山):", "")
        with col_b: filter_st = st.selectbox("狀態篩選", ["全部", "🎯 未完登", "✅ 已完登"])

        display_df = df.copy()
        if search: display_df = display_df[display_df['山名'].str.contains(search, na=False)]
        if filter_st == "🎯 未完登": display_df = display_df[display_df['完登狀態'] == False]
        elif filter_st == "✅ 已完登": display_df = display_df[display_df['完登狀態'] == True]

        edited_df = st.data_editor(display_df, column_config={"完登狀態": st.column_config.CheckboxColumn("是否完登?"), "登頂日期": st.column_config.TextColumn("登頂日期 (YYYY-MM-DD)")}, disabled=["山名", "海拔(m)", "難度", "經度", "緯度"], use_container_width=True, hide_index=True)

        if st.button("☁️ 儲存紀錄至雲端", type="primary"):
            try:
                # 3. 儲存邏輯：先刪除該使用者的舊紀錄，再寫入新的打卡紀錄
                supabase.table("baiyue_progress").delete().eq("username", st.session_state.current_user).execute()
                
                # 從編輯過的 DataFrame 中抓出所有打勾的山
                # 注意：這裡需要把原本的 df 跟 edited_df 結合，確保所有進度都被存到
                df.update(edited_df)
                completed_rows = df[df['完登狀態'] == True]
                
                insert_data = []
                for _, row in completed_rows.iterrows():
                    insert_data.append({
                        "username": st.session_state.current_user,
                        "peak_name": row["山名"],
                        "is_completed": True,
                        "climb_date": str(row["登頂日期"]) if pd.notna(row["登頂日期"]) else ""
                    })
                
                if insert_data:
                    supabase.table("baiyue_progress").insert(insert_data).execute()
                    
                st.success("☁️ 雲端同步完成！")
                st.rerun()
            except Exception as e:
                st.error(f"雲端存檔失敗：{e}")

# ==========================================
# 6. 系統 B：上河配速追蹤系統 (個人專屬配速)
# ==========================================
elif page == "⏱️ 上河配速追蹤系統":
    st.title("⏱️ 上河配速追蹤系統")
    st.write("### 📥 載入行程計畫")
    st.caption("請上傳從 Google Sheet 範本下載的 CSV 檔")
    
    uploaded_file = st.file_uploader("上傳你的行程 CSV 檔", type=["csv"], label_visibility="collapsed")

    if 'hike_df' not in st.session_state:
        st.session_state.hike_df = pd.DataFrame([{"分段地標": "起點", "上河步程": 0, "休息": 0, "抵達時刻": ""}])
        st.session_state.has_uploaded = False

    if uploaded_file is not None and not st.session_state.get('has_uploaded'):
        try:
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
            for i, row in raw_df.iterrows():
                if "分段地標" in str(row.values):
                    header_idx = i
                    break
            
            if header_idx != -1:
                raw_df.columns = raw_df.iloc[header_idx]
                clean_df = raw_df.iloc[header_idx+1:].dropna(subset=["分段地標"]).copy()
                
                exclude_keywords = ["總時間", "完成", "共休息", "總里程", "總爬升", "耗力指數", "速度指數"]
                pattern = "|".join(exclude_keywords)
                clean_df = clean_df[~clean_df["分段地標"].astype(str).str.contains(pattern, na=False, regex=True)]
                
                parsed_data = []
                for _, row in clean_df.iterrows():
                    parsed_data.append({
                        "分段地標": str(row.get("分段地標", "")).strip(),
                        "上河步程": parse_sh_minutes(row.get("上河步程", 0)),
                        "抵達時刻": "", 
                        "休息": 0 
                    })
                st.session_state.hike_df = pd.DataFrame(parsed_data)
                st.session_state.has_uploaded = True 
                st.success("✅ 行程檔載入成功！")
            else:
                st.error("CSV 檔案中找不到包含『分段地標』的標題行。")
        except Exception as e:
            st.error(f"檔案讀取失敗：{e}")

    if uploaded_file is None:
        st.session_state.has_uploaded = False

    st.write("### 📝 實時配速紀錄表")
    edited_df = st.data_editor(
        st.session_state.hike_df,
        num_rows="dynamic",
        column_config={
            "分段地標": st.column_config.TextColumn("地標 / CP點", width="medium"),
            "上河步程": st.column_config.NumberColumn("上河標準(分)"),
            "抵達時刻": st.column_config.TextColumn("實際抵達 (HH:MM)"),
            "休息": st.column_config.NumberColumn("預計休息(分)")
        },
        use_container_width=True,
        key="hike_editor"
    )

    st.divider()
    st.write("### ⚙️ 戰術模擬與數據彙整")
    col_i1, col_i2, col_i3 = st.columns(3)
    
    with col_i1:
        target_c = st.number_input("🎯 設定目標配速 (計算 ETA)", min_value=0.3, max_value=2.0, value=0.8, step=0.1)
    with col_i2:
        input_km = st.number_input("📍 手錶總里程 (km)", min_value=0.0, value=0.0, step=0.5)
    with col_i3:
        input_asc = st.number_input("⛰️ 手錶總爬升 (m)", min_value=0, value=0, step=50)

    analyze_btn = st.button("📊 開始運算 (生成 ETA 與 體能指數)", type="primary", use_container_width=True)

    if analyze_btn:
        try:
            calc_df = edited_df.copy()
            coeffs = []
            
            calc_df["預估耗時(分)"] = ""
            calc_df["預估抵達時刻"] = ""
            calc_df["分段係數"] = "" 
            
            first_valid_time = None
            for i in range(len(calc_df)):
                t = calc_df.iloc[i]["抵達時刻"]
                if pd.notna(t) and str(t).strip() != "":
                    first_valid_time = datetime.strptime(str(t).strip(), "%H:%M")
                    break

            for i in range(1, len(calc_df)):
                t_curr = calc_df.iloc[i]["抵達時刻"]
                t_prev = calc_df.iloc[i-1]["抵達時刻"]
                sh_min = calc_df.iloc[i].get("上河步程", 0)
                
                if pd.notna(t_curr) and str(t_curr).strip() != "" and pd.notna(t_prev) and str(t_prev).strip() != "":
                    fmt = "%H:%M"
                    delta = datetime.strptime(str(t_curr).strip(), fmt) - datetime.strptime(str(t_prev).strip(), fmt)
                    actual_min = delta.total_seconds() / 60
                    if actual_min < 0: actual_min += 24 * 60 
                    
                    rest_min = calc_df.iloc[i-1].get("休息", 0)
                    if pd.isna(rest_min): rest_min = 0
                    
                    walk_min = actual_min - float(rest_min)
                    if walk_min < 0: walk_min = 0 
                    
                    if float(sh_min) > 0:
                        c = round(walk_min / float(sh_min), 2)
                        calc_df.at[i, "分段係數"] = c
                        coeffs.append(c)

            avg_c = round(sum(coeffs) / len(coeffs), 2) if coeffs else 0.0
            
            last_known_time = None
            for i in range(len(calc_df)):
                t_curr = calc_df.iloc[i]["抵達時刻"]
                
                if pd.notna(t_curr) and str(t_curr).strip() != "":
                    last_known_time = datetime.strptime(str(t_curr).strip(), "%H:%M")
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

            total_hours = 0.0
            total_time_str = "請先輸入出發時間"
            
            if first_valid_time and last_known_time:
                total_minutes = (last_known_time - first_valid_time).total_seconds() / 60
                if total_minutes < 0: total_minutes += 24 * 60 
                total_hours = total_minutes / 60
                
                hh = int(total_minutes // 60)
                mm = int(total_minutes % 60)
                total_time_str = f"{hh} 小時 {mm} 分"

            ep_val = input_km + (input_asc / 100)
            ep_hr = round(ep_val / total_hours, 2) if total_hours > 0 else 0

            st.write("#### 🏆 行程總結與 EP 分析")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            col_m1.metric("當前實際配速 (C)", f"{avg_c}" if avg_c > 0 else "N/A")
            col_m2.metric("預估行程總時間", total_time_str)
            col_m3.metric("總耗力指數 (EP)", f"{round(ep_val, 1)}")
            col_m4.metric("速度指數 (EP/hr)", f"{ep_hr}")
            
            st.write("#### 📈 動態行程推算表 (清爽版)")
            display_cols = ["分段地標", "抵達時刻", "預估抵達時刻", "預估耗時(分)", "上河步程", "休息", "分段係數"]
            st.dataframe(calc_df[display_cols], use_container_width=True)

        except Exception as e:
            st.error(f"計算出錯，請確保時間格式為 HH:MM (如 08:30)。錯誤詳情: {e}")
