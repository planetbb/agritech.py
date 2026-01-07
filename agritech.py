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

# 3. 데이터 로딩 및 전처리 (핵심 수정 부분)
@st.cache_data
def load_data(url, data_type="crop"):
    try:
        df = pd.read_csv(url)
        
        # [수정 1] 컬럼명 및 데이터 내의 문자열 앞뒤 공백 제거 (매칭 오류 방지)
        df.columns = df.columns.str.strip()
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        if data_type == "crop":
            for c in ['Yield_Per_sqm_kg', 'Avg_Price_Per_kg_USD']:
                if c in df.columns: 
                    # 통화 기호 등 제거 후 변환
                    df[c] = df[c].astype(str).str.replace(r'[$,]', '', regex=True)
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                    
        elif data_type == "process":
            for i in range(1, 4):
                col = f'Auto_{i}_ManHour_per_sqm'
                if col in df.columns: 
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
        elif data_type == "equipment":
            # [수정 2] 가격 데이터 정제 강화 ($, , 제거)
            if 'Unit_Price_USD' in df.columns: 
                df['Unit_Price_USD'] = df['Unit_Price_USD'].astype(str).str.replace(r'[$,]', '', regex=True)
                df['Unit_Price_USD'] = pd.to_numeric(df['Unit_Price_USD'], errors='coerce').fillna(0)
                
            if 'Lifespan_Years' in df.columns: 
                df['Lifespan_Years'] = pd.to_numeric(df['Lifespan_Years'], errors='coerce').fillna(1)
                
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패 ({data_type}): {e}")
        return pd.DataFrame()

df_crop = load_data(SHEET_URLS["crop"], "crop")
df_equip = load_data(SHEET_URLS["equipment"], "equipment")
df_process = load_data(SHEET_URLS["process"], "process")

if df_crop.empty or df_equip.empty or df_process.empty:
    st.stop()

# --- 카테고리별 대표 작물 매핑 ---
REPRESENTATIVE_CROP = {
    "Greenhouse": "Strawberry",
    "Orchard": "Apple",
    "Paddy": "Rice",
    "Upland": "Potato"
}

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("📍 농업 설정")
    # 국가 선택 시 데이터가 없으면 전체 국가 보기 방지
    available_countries = df_crop['Country'].unique() if 'Country' in df_crop.columns else []
    selected_country = st.selectbox("1) 국가 선택", available_countries)
    
    country_crops = df_crop[df_crop['Country'] == selected_country]
    selected_crop = st.selectbox("2) 작물 선택", country_crops['Crop_Name'].unique())
    
    size_sqm = st.number_input("3) 농지 면적 (sqm)", min_value=10, value=1000, step=100)
    
    auto_options = ["1) Manual", "2) Semi-Auto", "3) Full-Auto"]
    auto_label = st.radio("4) 자동화 수준", auto_options)
    automation_level = auto_label.split(") ")[1]
    auto_level_idx = auto_options.index(auto_label) + 1

# --- [핵심] Tab2, Tab3를 위한 데이터 Fallback 로직 ---
# 작물 정보 가져오기
crop_info_rows = df_crop[df_crop['Crop_Name'] == selected_crop]
if crop_info_rows.empty:
    st.error("선택한 작물의 기본 정보가 없습니다.")
    st.stop()
crop_info = crop_info_rows.iloc[0]
cat_type = crop_info.get('Category_Type', 'Upland')

# Process 데이터 매칭 로직
display_process_df = df_process[df_process['Crop_Name'] == selected_crop]
source_name = selected_crop

if display_process_df.empty:
    rep_crop = REPRESENTATIVE_CROP.get(cat_type, "Potato") # 기본값 Potato
    display_process_df = df_process[df_process['Crop_Name'] == rep_crop]
    source_name = f"{rep_crop} (대표작물)"
    if display_process_df.empty: 
        # 대표작물 데이터도 없으면 Category_Type으로 검색 시도 (데이터셋 구조에 따라)
        display_process_df = df_process[df_process['Crop_Name'] == cat_type]
        source_name = f"{cat_type} 표준"

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비", "🗂️ 마스터 데이터"])

# --- Tab 1: 수익성 분석 ---
with tab1:
    # 0. 데이터 계산부
    total_yield = size_sqm * crop_info['Yield_Per_sqm_kg']
    total_rev = total_yield * crop_info['Avg_Price_Per_kg_USD']
    
    comp_data = []
    # 3가지 레벨에 대해 Loop 돌며 계산
    for i, label in enumerate(["Manual", "Semi-Auto", "Full-Auto"]):
        num = i + 1
        mh_col = f'Auto_{num}_ManHour_per_sqm'
        eq_col = f'Auto_{num}_Equipment' # Process 시트에 정의된 장비명 컬럼
        
        # 인건비(시간) 계산
        mh_val = display_process_df[mh_col].sum() * size_sqm if mh_col in display_process_df.columns else 0
        
        # 장비 비용(CAPEX) 계산 로직 [중요]
        # 1. Process 시트에서 해당 레벨에 필요한 장비명 리스트 추출 (콤마 등으로 구분되어 있을 경우 대비 필요하나, 현재는 1행 1장비 가정)
        if eq_col in display_process_df.columns:
            # 여러 행에 걸쳐 장비가 나열되어 있을 수 있으므로 unique값 추출
            eq_list = display_process_df[eq_col].dropna().astype(str).unique().tolist()
            
            # 2. Equipment 시트에서 장비명(Item_Name)이 일치하는 행 찾기
            # 공백 제거 등은 load_data에서 이미 완료됨
            matched_equip = df_equip[df_equip['Item_Name'].isin(eq_list)]
            capex = matched_equip['Unit_Price_USD'].sum()
        else:
            eq_list = []
            capex = 0
            
        comp_data.append({"Level": label, "MH": mh_val, "CAPEX": capex, "EQ_Count": len(eq_list)})
    
    df_comp = pd.DataFrame(comp_data)

    # 1. 상단 요약 바
    st.markdown(f"### 📊 {selected_crop} 분석 리포트")
    m1, m2, m3 = st.columns(3)
    m1.metric("🌾 예상 수확량", f"{total_yield:,.1f} kg")
    m2.metric("💰 예상 매출액", f"$ {total_rev:,.0f}")
    m3.metric("📍 설정 면적", f"{size_sqm:,.0f} sqm")
    st.markdown("---")

    # 2. 메인 레이아웃
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.write("#### 📈 효율성 비교 차트")
        colors = ['#FFD700' if lvl == automation_level else '#D3D3D3' for lvl in df_comp['Level']]
        
        fig = go.Figure()
        # 인건비 (막대)
        fig.add_trace(go.Bar(
            x=df_comp['Level'], 
            y=df_comp['MH'], 
            name='Labor Hours', 
            marker_color=colors, 
            yaxis='y1'
        ))
        # 투자비 (선+점)
        fig.add_trace(go.Scatter(
            x=df_comp['Level'], 
            y=df_comp['CAPEX'], 
            name='Investment (CAPEX)', 
            line=dict(color='#e74c3c', width=3), 
            mode='lines+markers',
            yaxis='y2'
        ))
        
        fig.update_layout(
            height=450,
            margin=dict(l=0,r=0,t=20,b=0),
            yaxis=dict(title="Man-Hours (Total)"),
            yaxis2=dict(title="CAPEX ($)", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", y=1.1, x=0.1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with right_col:
        st.write("#### 📋 레벨별 요약 및 인사이트")
        for _, r in df_comp.iterrows():
            sel = (r['Level'] == automation_level)
            bg_color = "#FFF9C4" if sel else "#FFFFFF"
            border_color = "#FBC02D" if sel else "#DDD"
            
            st.markdown(f"""
                <div style="border:
