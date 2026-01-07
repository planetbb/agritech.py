import streamlit as st
import pandas as pd

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
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    
    if data_type == "crop":
        df['Yield_Per_sqm_kg'] = pd.to_numeric(df['Yield_Per_sqm_kg'], errors='coerce')
        df['Avg_Price_Per_kg_USD'] = pd.to_numeric(df['Avg_Price_Per_kg_USD'], errors='coerce')
        df = df.dropna(subset=['Yield_Per_sqm_kg', 'Avg_Price_Per_kg_USD'])
    
    if data_type == "process":
        for col in ['Auto_1_ManHour_per_sqm', 'Auto_2_ManHour_per_sqm', 'Auto_3_ManHour_per_sqm']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# --- 메인 실행부 ---
st.title("🌱 AgriTech FarmPlanner & Scheduler")

try:
    df_crop = load_data(SHEET_URLS["crop"], data_type="crop")
    df_equip = load_data(SHEET_URLS["equipment"], data_type="equipment")
    df_process = load_data(SHEET_URLS["process"], data_type="process")
    st.sidebar.success("✅ 데이터 로드 성공")
except Exception as e:
    st.error(f"데이터 로딩 중 에러 발생: {e}")
    st.stop()

# --- 사이드바: 입력 인터페이스 ---
with st.sidebar:
    st.header("📍 농업 설정 (Farm Setup)")
    
    # 1. 국가 선택
    selected_country = st.selectbox("1) 국가 선택 (Country)", df_crop['Country'].unique())
    
    # 2. 선택된 국가에 해당하는 작물만 필터링하여 선택
    country_crops = df_crop[df_crop['Country'] == selected_country]
    selected_crop = st.selectbox("2) 작물 선택 (Crop)", country_crops['Crop_Name'].unique())
    
    # 3. 농지 면적
    size_sqm = st.number_input("3) 농지 면적 (Area, sqm)", min_value=10, value=1000, step=100)
    
    # 4. 자동화 수준 (Label -> Value 매핑)
    auto_mapping = {"1) Manual": 1, "2) Semi-Auto": 2, "3) Full-Auto": 3}
    auto_label = st.radio("4) 자동화 수준 (Automation)", list(auto_mapping.keys()))
    auto_level = auto_mapping[auto_label]

# 메인 탭
tab1, tab2, tab3, tab4 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비", "🗂️ 마스터 데이터"])

# 선택된 작물의 상세 데이터 추출
crop_data = df_crop[df_crop['Crop_Name'] == selected_crop].iloc[0]

# --- Tab 1: 수익성 분석 (FarmPlanner) ---
with tab1:
    st.subheader(f"📊 {selected_crop} 재배 수익 시뮬레이션")
    col1, col2, col3 = st.columns(3)
    
    revenue = crop_data['Yield_Per_sqm_kg'] * size_sqm * crop_data['Avg_Price_Per_kg_USD']
    total_yield = crop_data['Yield_Per_sqm_kg'] * size_sqm
    
    col1.metric("예상 총 매출", f"${revenue:,.0f}")
    col2.metric("예상 총 수확량", f"{total_yield:,.0f} kg")
    col3.metric("재배 카테고리", crop_data['Category_Type'])
    
    st.info(f"💡 {selected_country} 지역의 {selected_crop} 평균 지표를 바탕으로 산출되었습니다.")

# --- Tab 2: 작업 스케줄 (FarmScheduler) ---
with tab2:
    st.subheader(f"📅 {selected_crop} 연간 공정 스케줄 ({auto_label})")
    
    # 해당 작물의 공정 데이터 필터링
    crop_schedule = df_process[df_process['Crop_Name'] == selected_crop].copy() # .copy()를 써야 데이터 수정 시 경고가 안 납니다.
    
    if not crop_schedule.empty:
        # 1. 자동화 레벨 1(Manual)일 때 'Hand Tool Kit' 자동 매칭
        equip_col = f'Auto_{auto_level}_Equipment'
        mh_col = f'Auto_{auto_level}_ManHour_per_sqm'
        
        if auto_level == 1:
            # 시트에 컬럼이 없거나 비어있으면 'Hand Tool Kit'으로 채움
            if equip_col not in crop_schedule.columns:
                crop_schedule[equip_col] = "Hand Tool Kit"
            crop_schedule[equip_col] = crop_schedule[equip_col].fillna("Hand Tool Kit")

        # 2. 출력할 컬럼 리스트 구성 (Category_Type 포함)
        # 시트에 있는 실제 컬럼명과 일치하는지 확인하며 구성합니다.
        base_cols = ['Category_Type', 'Process_Step', 'Work_Week_Start', 'Work_Week_End']
        show_cols = [c for c in base_cols if c in crop_schedule.columns]
        
        # 장비 컬럼 추가 (2번째 위치)
        if equip_col in crop_schedule.columns:
            show_cols.insert(1, equip_col)
        
        # 노동시간 컬럼 추가
        if mh_col in crop_schedule.columns:
            show_cols.append(mh_col)
        
        # 3. 데이터프레임 출력
        st.dataframe(crop_schedule[show_cols], use_container_width=True, hide_index=True)
        
        # 4. 총 노동 시간 계산 (데이터가 있는 경우에만)
        if mh_col in crop_schedule.columns:
            total_h = crop_schedule[mh_col].sum() * size_sqm
            st.warning(f"⚠️ {auto_label} 적용 시, 연간 총 예상 노동시간: **{total_h:,.1f} Man-Hour**")
        
    else:
        st.error(f"'{selected_crop}'의 공정(Process) 데이터가 없습니다. 시트의 Crop_Name 일치 여부를 확인해주세요.")

# --- Tab 3: 투입 장비 상세 ---
with tab3:
    st.subheader(f"🚜 {auto_label} 단계 필수 장비/시설")
    if auto_level > 1:
        # 스케줄에 포함된 장비 이름 추출
        equip_names = crop_schedule[f'Auto_{auto_level}_Equipment'].unique()
        matched = df_equip[df_equip['Item_Name'].isin(equip_names)]
        
        if not matched.empty:
            st.write("선택하신 자동화 수준에서 운용되는 장비 상세 명세입니다.")
            st.table(matched[['Item_Name', 'Unit_Price_USD', 'Operating_Cost_Hour_USD', 'Lifespan_Years']])
        else:
            st.info("현재 선택된 공정에 매칭된 장비 마스터 정보가 없습니다.")
    else:
        st.write("Manual 단계는 별도의 대형 자동화 장비를 사용하지 않습니다.")

# --- Tab 4: 마스터 데이터 ---
with tab4:
    choice = st.radio("조회할 데이터", ["작물 마스터", "공정 표준", "장비 시설"], horizontal=True)
    if choice == "작물 마스터": st.dataframe(df_crop)
    elif choice == "공정 표준": st.dataframe(df_process)
    else: st.dataframe(df_equip)
