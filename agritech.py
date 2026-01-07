import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="AgriTech FarmPlanner", layout="wide")

# 2. 구글 시트 URL 설정
SHEET_URLS = {
    "crop": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=0&single=true&output=csv",
    "equipment": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=1783566142&single=true&output=csv",
    "process": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=1120300035&single=true&output=csv"
}

# 3. 데이터 로딩 및 전처리 함수 (강화 버전)
@st.cache_data
def load_data(url, data_type="crop"):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        if data_type == "crop":
            df['Yield_Per_sqm_kg'] = pd.to_numeric(df['Yield_Per_sqm_kg'], errors='coerce').fillna(0)
            df['Avg_Price_Per_kg_USD'] = pd.to_numeric(df['Avg_Price_Per_kg_USD'], errors='coerce').fillna(0)
            
        elif data_type == "process":
            for col in ['Auto_1_ManHour_per_sqm', 'Auto_2_ManHour_per_sqm', 'Auto_3_ManHour_per_sqm']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
        elif data_type == "equipment":
            # Unit_Price_USD 컬럼 강제 숫자 변환 및 결측치 0 처리
            if 'Unit_Price_USD' in df.columns:
                df['Unit_Price_USD'] = pd.to_numeric(df['Unit_Price_USD'], errors='coerce').fillna(0)
            # Lifespan_Years 컬럼 강제 숫자 변환 및 결측치 1 처리
            if 'Lifespan_Years' in df.columns:
                df['Lifespan_Years'] = pd.to_numeric(df['Lifespan_Years'], errors='coerce').fillna(1)
                
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# 데이터 로드
df_crop = load_data(SHEET_URLS["crop"], data_type="crop")
df_equip = load_data(SHEET_URLS["equipment"], data_type="equipment")
df_process = load_data(SHEET_URLS["process"], data_type="process")

if df_crop.empty or df_equip.empty or df_process.empty:
    st.stop()

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("📍 농업 설정 (Farm Setup)")
    selected_country = st.selectbox("1) 국가 선택 (Country)", df_crop['Country'].unique())
    country_crops = df_crop[df_crop['Country'] == selected_country]
    selected_crop = st.selectbox("2) 작물 선택 (Crop)", country_crops['Crop_Name'].unique())
    size_sqm = st.number_input("3) 농지 면적 (Area, sqm)", min_value=10, value=1000, step=100)
    
    auto_options = ["1) Manual", "2) Semi-Auto", "3) Full-Auto"]
    auto_label = st.radio("4) 자동화 수준 (Automation)", auto_options)
    
    automation_level = auto_label.split(") ")[1]
    auto_level_idx = auto_options.index(auto_label) + 1

# --- Fallback 로직 데이터 준비 ---
crop_info_row = df_crop[df_crop['Crop_Name'] == selected_crop].iloc[0]
selected_category = crop_info_row['Category_Type']

display_process_df = df_process[df_process['Crop_Name'] == selected_crop]
is_fallback = False
if display_process_df.empty:
    display_process_df = df_process[df_process['Crop_Name'] == selected_category]
    is_fallback = True

# 메인 탭
tab1, tab2, tab3, tab4 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비", "🗂️ 마스터 데이터"])

# --- Tab 1: 수익성 분석 (생략 없이 포함) ---
with tab1:
    total_yield_kg = size_sqm * crop_info_row['Yield_Per_sqm_kg']
    total_revenue_usd = total_yield_kg * crop_info_row['Avg_Price_Per_kg_USD']
    st.markdown(f"### 📊 {selected_crop} 분석 리포트")
    m1, m2, m3 = st.columns(3)
    m1.metric("🌾 예상 수확량", f"{total_yield_kg:,.1f} kg")
    m2.metric("💰 예상 매출액", f"$ {total_revenue_usd:,.0f}")
    m3.metric("📍 설정 면적", f"{size_sqm:,.0f} sqm")
    st.markdown("---")
    
    comparison_data = []
    levels = ["Manual", "Semi-Auto", "Full-Auto"]
    for i, label in enumerate(levels):
        num = i + 1
        mh_val = display_process_df[f'Auto_{num}_ManHour_per_sqm'].sum() * size_sqm
        eq_list = display_process_df[f'Auto_{num}_Equipment'].dropna().unique().tolist()
        capex = df_equip[df_equip['Item_Name'].isin(eq_list)]['Unit_Price_USD'].sum()
        comparison_data.append({"Level": label, "Total_ManHour": mh_val, "Total_CAPEX": capex, "Equipment": ", ".join(eq_list)})
    
    df_compare = pd.DataFrame(comparison_data)
    c_col, i_col = st.columns([1, 1])
    with c_col:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_compare['Level'], y=df_compare['Total_ManHour'], name='Hrs', marker_color='#5dade2', yaxis='y1'))
        fig.add_trace(go.Scatter(x=df_compare['Level'], y=df_compare['Total_CAPEX'], name='CAPEX', line=dict(color='#e74c3c', width=3), yaxis='y2'))
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0), yaxis2=dict(overlaying="y", side="right", showgrid=False))
        st.plotly_chart(fig, use_container_width=True)
    with i_col:
        for _, row in df_compare.iterrows():
            sel = (row['Level'] == automation_level)
            st.markdown(f"""<div style="border: 1px solid {'#2E86C1' if sel else '#DDD'}; padding: 10px; border-radius: 5px; margin-bottom: 5px; background: {'#F0F7FF' if sel else '#FFF'}; color: #000;">
            <b>{row['Level']}</b> | ⏱️ {row['Total_ManHour']:,.1f}h | 💰 ${row['Total_CAPEX']:,.0f}<br><small>🚜 {row['Equipment']}</small></div>""", unsafe_allow_html=True)

# --- Tab 2: 작업 스케줄 ---
with tab2:
    if is_fallback: st.warning(f"ℹ️ {selected_category} 표준 공정 데이터입니다.")
    target_col = f'Auto_{auto_level_idx}_Equipment'
    st.dataframe(display_process_df[['Process_Step', 'Work_Week_Start', 'Work_Week_End', target_col]], use_container_width=True, hide_index=True)

# --- Tab 3: 투입 장비 (에러 해결 핵심 지점) ---
with tab3:
    st.subheader(f"🚜 {automation_level} 상세 장비 제원")
    target_col = f'Auto_{auto_level_idx}_Equipment'
    used_equips = display_process_df[target_col].dropna().unique()
    matched_equip = df_equip[df_equip['Item_Name'].isin(used_equips)]
    
    if not matched_equip.empty:
        for _, row in matched_equip.iterrows():
            with st.expander(f"🔹 {row['Item_Name']}"):
                col1, col2 = st.columns(2)
                # 에러 방지: 값을 float으로 명시적 변환 후 포맷팅
                price = float(row['Unit_Price_USD'])
                life = float(row['Lifespan_Years'])
                col1.metric("Unit Price", f"$ {price:,.0f}")
                col2.metric("Lifespan", f"{int(life)} Years")
        st.dataframe(matched_equip, use_container_width=True, hide_index=True)
    else:
        st.info("매칭된 장비 정보가 없습니다.")

# --- Tab 4: 마스터 데이터 ---
with tab4:
    choice = st.radio("원본 데이터", ["작물", "공정", "장비"], horizontal=True)
    if choice == "작물": st.dataframe(df_crop)
    elif choice == "공정": st.dataframe(df_process)
    else: st.dataframe(df_equip)
