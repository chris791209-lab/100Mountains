import streamlit as st
import pandas as pd
import os
import pydeck as pdk
import streamlit.components.v1 as components # 新增：用來嵌入網頁

st.set_page_config(page_title="我的百岳紀錄 App", layout="wide")
st.title("🏔️ 台灣百岳登頂紀錄與戰情室")

FILE_PATH = 'baiyue_tracking.csv'

# ==========================================
# 🗺️ 3D 百岳分佈與完登版圖 (保持原本功能)
# ==========================================
# ... (此處省略中間重複的資料處理與 3D 地圖程式碼，請保留你目前版本中的內容) ...

# ==========================================
# 🛰️ 登山戰情室：即時氣象與雷達整合 (新增區塊)
# ==========================================
st.divider()
st.write("### 📡 登山戰情室：即時氣象與雷達監控")

tab1, tab2, tab3 = st.tabs(["⛰️ 氣象署登山預報", "🌧️ NCDR 降雨雷達", "🌡️ 縣市智能預報"])

with tab1:
    st.write("#### 中央氣象署 - 登山育樂預報 (南一段/關山)")
    # 直接嵌入氣象署南一段相關區域的網頁
    components.iframe("https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080", height=600, scrolling=True)
    st.caption("註：若網頁未正常顯示，請點擊 [中央氣象署官網](https://www.cwa.gov.tw/V8/C/L/Mountain/Mountain.html?PID=D080) 查看。")

with tab2:
    st.write("#### NCDR 災害監測 - 即時降雨趨勢")
    # 嵌入 NCDR 的雷達回波預報畫面
    components.iframe("https://watch.ncdr.nat.gov.tw/watch_tfrain_fst", height=700, scrolling=True)
    st.info("💡 觀察重點：雷達回波圖若出現黃、橙色區塊移向南一段，代表即將有強降雨。")

with tab3:
    # 這裡保留我們之前寫的 API 智能換算預報
    st.write("#### 縣市預報智能換算 (API 備援方案)")
    # ... (此處放置之前的 get_cwa_general_weather 相關程式碼) ...

# ==========================================
# 🔍 快速尋找與打卡區塊 (保持原本功能)
# ==========================================
# ... (此處保留原本的打卡區塊) ...
