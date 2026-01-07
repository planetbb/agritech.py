import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Farm Automation Simulator by Jinux", layout="wide")

# 2. 구글 시트 URL 설정
SHEET_URLS = {
    "crop": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=0&single=true&output=csv",
    "equipment": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=1783566142&single=true&output=csv",
    "process": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=1120300035&single=true&output=csv"
}

# 3. 데이터 로딩 함수
@st.cache_data
def load_data(url, data_type="crop"):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        if data_type == "crop":
            for c in ['Yield_Per_sqm_kg', 'Avg_Price_Per_kg_USD']:
                if c in df.columns: 
                    df[c] = df[c].astype(str).str.replace(r'[$,]', '', regex=True)
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        elif data_type == "process":
            for i in range(1, 4):
                col = f'Auto_{i}_ManHour_per_sqm'
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        elif data_type == "equipment":
            if 'Unit_Price_USD' in df.columns: 
                df['Unit_Price_USD'] = df['Unit_Price_USD'].astype(str).str.replace(r'[$,]', '', regex=True)
                df['Unit_Price_USD'] = pd.to_numeric(df['Unit_Price_USD'], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

df_crop = load_data(SHEET_URLS["crop"], "crop")
df_equip = load_data(SHEET_URLS["equipment"], "equipment")
df_process = load_data(SHEET_URLS["process"], "process")

if df_crop.empty: st.stop()

# --- 4. 사이드바 (변수 정의) ---
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #3498db;">
            <p style="font-size: 1.1em; font-weight: bold; color: #2c3e50; margin-bottom: 5px;">Please select below</p>
            <p style="font-size: 28px; animation: blink 1s linear infinite; color: #3498db; margin: 0;">⬇️</p>
        </div>
        <style> @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.1; } 100% { opacity: 1; } } </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    countries = df_crop['Country'].unique()
    selected_country = st.selectbox("Country (국가)", countries)
    
    crops = df_crop[df_crop['Country'] == selected_country]['Crop_Name'].unique()
    selected_crop = st.selectbox("Crop (작물)", crops)
    size_sqm = st.number_input("Farm Size (농지 규모, sqm)", min_value=10, value=1000, step=100)
    
    auto_options = ["1) Manual", "2) Semi-Auto", "3) Full-Auto"]
    auto_label = st.radio("Auto Level (자동화 수준)", auto_options)
    automation_level = auto_label.split(") ")[1]
    auto_level_idx = auto_options.index(auto_label) + 1

    # Master Data Buttons
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    st.subheader("🗂️ Master Data View")
    if 'db_view' not in st.session_state: st.session_state.db_view = None
    c1, c2 = st.columns(2)
    if c1.button("🌾 Crop", use_container_width=True): st.session_state.db_view = "작물"
    if c2.button("📅 Process", use_container_width=True): st.session_state.db_view = "공정"
    if st.button("🚜 Equipment", use_container_width=True): st.session_state.db_view = "장비"
    if st.session_state.db_view and st.button("❌ Close", use_container_width=True): st.session_state.db_view = None

# --- 5. 데이터 계산 (사이드바 변수 이후에 위치) ---
crop_info = df_crop[df_crop['Crop_Name'] == selected_crop].iloc[0]
display_process_df = df_process[df_process['Crop_Name'] == selected_crop]
if display_process_df.empty:
    rep_crop = {"Greenhouse": "Strawberry", "Orchard": "Apple", "Paddy": "Rice"}.get(crop_info['Category_Type'], "Potato")
    display_process_df = df_process[df_process['Crop_Name'] == rep_crop]

# --- 6. 메인 화면 상단 ---
h1, h2 = st.columns([1, 8])
h1.markdown("<h1 style='font-size: 60px; margin: 0;'>🚜</h1>", unsafe_allow_html=True)
h2.title("Farm Automation Simulator")
h2.markdown(f"<p style='margin-top:-15px;'>by <b>Jinux</b></p>", unsafe_allow_html=True)

if st.session_state.db_view:
    with st.expander(f"🔍 {st.session_state.db_view} Master Data", expanded=True):
        if st.session_state.db_view == "작물": st.dataframe(df_crop)
        elif st.session_state.db_view == "공정": st.dataframe(df_process)
        elif st.session_state.db_view == "장비": st.dataframe(df_equip)

# --- 7. 탭 구성 ---
tab1, tab2, tab3 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비"])

with tab1:
    # 1. 수확량 및 매출 계산 (crop_info 사용)
    total_yield = size_sqm * crop_info['Yield_Per_sqm_kg']
    total_rev = total_yield * crop_info['Avg_Price_Per_kg_USD']
    
    comp_data = []
    # 2. 3가지 자동화 레벨 루프
    for i, label in enumerate(["Manual", "Semi-Auto", "Full-Auto"]):
        num = i + 1
        mh_col = f'Auto_{num}_ManHour_per_sqm'
        eq_col = f'Auto_{num}_Equipment' # 만약 시트 컬럼명이 다르면 여기서 에러 발생
        
        # 인건비 계산 (컬럼이 있을 때만 계산)
        mh_val = display_process_df[mh_col].sum() * size_sqm if mh_col in display_process_df.columns else 0
        
        # [중요] 장비 비용 계산 시 KeyError 방지 로직
        if eq_col in display_process_df.columns:
            eq_list = display_process_df[eq_col].dropna().unique().tolist()
            # 장비 마스터 데이터에서 가격 합산
            capex = df_equip[df_equip['Item_Name'].isin(eq_list)]['Unit_Price_USD'].sum()
        else:
            # 컬럼명이 정확히 일치하지 않을 경우 0으로 처리 (에러 방지)
            eq_list = []
            capex = 0
            
        comp_data.append({"Level": label, "MH": mh_val, "CAPEX": capex})
    
    df_comp = pd.DataFrame(comp_data)
    
with tab2:
    st.dataframe(display_process_df[['Process_Step', 'Work_Week_Start', f'Auto_{auto_level_idx}_Equipment']], use_container_width=True)

with tab3:
    eq_names = display_process_df[f'Auto_{auto_level_idx}_Equipment'].dropna().unique()
    st.dataframe(df_equip[df_equip['Item_Name'].isin(eq_names)], use_container_width=True)

# --- 8. 하단 푸터 (한 줄 우측 정렬) ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
st.markdown(f"""
    <div style="text-align: right; color: #7f8c8d; font-size: 0.8em;">
        <b>Copyright 2024. Jinux. All rights reserved.</b> | Designed for AgriTech Efficiency Analysis | 📅 최신 업데이트: {datetime.now().strftime("%Y-%m-%d")} | 📧 Contact: <a href="mailto:JinuxDreams@gmail.com" style="color:#7f8c8d; text-decoration:none;">JinuxDreams@gmail.com</a>
    </div>
""", unsafe_allow_html=True)
