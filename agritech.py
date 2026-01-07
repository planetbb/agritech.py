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

# 3. 데이터 로딩 함수
@st.cache_data
def load_data(url, data_type="crop"):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        if data_type == "crop":
            df['Yield_Per_sqm_kg'] = pd.to_numeric(df['Yield_Per_sqm_kg'], errors='coerce')
            df['Avg_Price_Per_kg_USD'] = pd.to_numeric(df['Avg_Price_Per_kg_USD'], errors='coerce')
        if data_type == "process":
            for col in ['Auto_1_ManHour_per_sqm', 'Auto_2_ManHour_per_sqm', 'Auto_3_ManHour_per_sqm']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
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
    
    # [에러 해결 핵심] 변수명을 하나로 통일합니다.
    automation_level = auto_label.split(") ")[1]  # "Manual", "Semi-Auto", "Full-Auto"
    auto_level = auto_options.index(auto_label) + 1  # 1, 2, 3 (정수)

# 메인 탭
tab1, tab2, tab3, tab4 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비", "🗂️ 마스터 데이터"])

# 공통 필터링 데이터
crop_schedule = df_process[df_process['Crop_Name'] == selected_crop]

# --- Tab 1: 수익성 분석 ---
with tab1:
    st.header(f"📊 {selected_crop} 자동화 레벨별 비교 분석")
    comparison_data = []
    
    if not crop_schedule.empty:
        for level in [1, 2, 3]:
            label = ["Manual", "Semi-Auto", "Full-Auto"][level-1]
            mh_col, eq_col = f'Auto_{level}_ManHour_per_sqm', f'Auto_{level}_Equipment'
            
            total_mh = crop_schedule[mh_col].sum() * size_sqm if mh_col in crop_schedule.columns else 0
            
            total_capex = 0
            if eq_col in crop_schedule.columns:
                used_equips = crop_schedule[eq_col].dropna().unique()
                if level == 1 and len(used_equips) == 0: used_equips = ['Hand Tool Kit']
                
                prices = pd.to_numeric(df_equip[df_equip['Item_Name'].isin(used_equips)]['Unit_Price_USD'], errors='coerce')
                total_capex = prices.sum()
            
            comparison_data.append({"Level": label, "Total_ManHour": total_mh, "Total_CAPEX": total_capex})

        df_compare = pd.DataFrame(comparison_data)

        # 그래프
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_compare['Level'], y=df_compare['Total_ManHour'], name='Man-Hours', marker_color='#5dade2', yaxis='y1'))
        fig.add_trace(go.Scatter(x=df_compare['Level'], y=df_compare['Total_CAPEX'], name='Investment ($)', line=dict(color='#e74c3c', width=4), yaxis='y2'))
        fig.update_layout(yaxis=dict(title="Man-Hours"), yaxis2=dict(title="Investment ($)", overlaying="y", side="right"), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

        # 상세 표
        st.subheader(f"📋 상세 분석 ({automation_level})")
        idx = ["Manual", "Semi-Auto", "Full-Auto"].index(automation_level)
        current_data = df_compare.iloc[idx]
        current_equips = crop_schedule[f'Auto_{idx+1}_Equipment'].dropna().unique().tolist()
        
        st.table(pd.DataFrame({
            "항목": ["자동화 수준", "총 노동 시간", "총 설비투자비", "주요 장비"],
            "값": [automation_level, f"{current_data['Total_ManHour']:,.1f} hr", f"$ {current_data['Total_CAPEX']:,.0f}", ", ".join(current_equips)]
        }))
    else:
        st.info("데이터가 없습니다.")

# --- Tab 2: 작업 스케줄 ---
with tab2:
    st.subheader(f"📅 {selected_crop} ({automation_level}) 스케줄")
    if not crop_schedule.empty:
        show_cols = ['Category_Type', 'Process_Step', 'Work_Week_Start', 'Work_Week_End']
        equip_col = f'Auto_{auto_level}_Equipment'
        if equip_col in crop_schedule.columns: show_cols.append(equip_col)
        st.dataframe(crop_schedule[show_cols], use_container_width=True, hide_index=True)

# --- Tab 3: 투입 장비 명세 ---
with tab3:
    st.subheader(f"🚜 {automation_level} 투입 장비")
    equip_col = f'Auto_{auto_level}_Equipment'
    if equip_col in crop_schedule.columns:
        used_equips = crop_schedule[equip_col].dropna().unique()
        matched_equip = df_equip[df_equip['Item_Name'].isin(used_equips)]
        if not matched_equip.empty:
            st.dataframe(matched_equip[['Category', 'Item_Name', 'Unit_Price_USD', 'Lifespan_Years']], use_container_width=True, hide_index=True)
        else:
            st.info("장비 상세 정보가 없습니다.")

# --- Tab 4: 마스터 데이터 ---
with tab4:
    choice = st.radio("데이터 선택", ["작물", "공정", "장비"], horizontal=True)
    if choice == "작물": st.dataframe(df_crop)
    elif choice == "공정": st.dataframe(df_process)
    else: st.dataframe(df_equip)
