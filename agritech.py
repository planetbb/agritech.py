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

# --- 수익성 분석 섹션 (Tab 1) ---
with tab1:
    # Plotly 라이브러리가 로컬에서 호출되지 않았을 경우를 대비해 한번 더 선언
    import plotly.graph_objects as go

    st.header(f"📊 {selected_crop} 자동화 레벨별 비교 분석")
    
    # 데이터 준비
    comparison_data = []
    crop_schedule = df_process[df_process['Crop_Name'] == selected_crop]
    
    if not crop_schedule.empty:
        for level in [1, 2, 3]:
            label = ["Manual", "Semi-Auto", "Full-Auto"][level-1]
            mh_col = f'Auto_{level}_ManHour_per_sqm'
            eq_col = f'Auto_{level}_Equipment'
            
            # 1. 노동시간 계산
            total_mh = crop_schedule[mh_col].sum() * size_sqm if mh_col in crop_schedule.columns else 0
            
            # 2. 투자비 계산 (실제 컬럼명 'Unit_Price_USD' 반영)
            total_capex = 0
            if eq_col in crop_schedule.columns:
                used_equips = crop_schedule[eq_col].dropna().unique()
                if level == 1 and len(used_equips) == 0:
                    used_equips = ['Hand Tool Kit']
                
                if not df_equip.empty:
                    # 사용자님의 실제 컬럼명인 'Unit_Price_USD'를 사용합니다.
                    p_col = 'Unit_Price_USD' 
                    name_col = 'Item_Name'
                    
                    if p_col in df_equip.columns and name_col in df_equip.columns:
                        # 숫자가 아닌 데이터가 섞여있을 수 있어 pd.to_numeric으로 안전하게 처리
                        prices = pd.to_numeric(df_equip[df_equip[name_col].isin(used_equips)][p_col], errors='coerce')
                        total_capex = prices.sum()
            
            comparison_data.append({
                "Level": label,
                "Total_ManHour": total_mh,
                "Total_CAPEX": total_capex
            })

        df_compare = pd.DataFrame(comparison_data)

        # --- 시각화 ---
        fig = go.Figure()

        # 노동 시간 (Bar)
        fig.add_trace(go.Bar(
            x=df_compare['Level'],
            y=df_compare['Total_ManHour'],
            name='Total Man-Hours',
            marker_color='#5dade2',
            yaxis='y1'
        ))

        # 투자 비용 (Line)
        fig.add_trace(go.Scatter(
            x=df_compare['Level'],
            y=df_compare['Total_CAPEX'],
            name='Investment ($)',
            line=dict(color='#e74c3c', width=4),
            yaxis='y2'
        ))

        fig.update_layout(
            title=dict(text=f"Efficiency vs Investment: {selected_crop}", x=0.5),
            xaxis=dict(title="Automation Level"),
            yaxis=dict(title="Man-Hours", side="left", showgrid=True),
            yaxis2=dict(title="Investment (USD)", side="right", overlaying="y", showgrid=False),
            legend=dict(x=0.01, y=1.1, orientation="h")
        )

        st.plotly_chart(fig, use_container_width=True)

        # --- 요약 지표 ---
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Manual 노동량", f"{df_compare.iloc[0]['Total_ManHour']:,.0f} hr")
        with c2:
            m_val = df_compare.iloc[0]['Total_ManHour']
            f_val = df_compare.iloc[2]['Total_ManHour']
            reduction = (1 - f_val / m_val) * 100 if m_val > 0 else 0
            st.metric("Full-Auto 노동 절감", f"{reduction:.1f}%", delta=f"-{reduction:.1f}%")
        with c3:
            st.metric("Full-Auto 설비투자비", f"${df_compare.iloc[2]['Total_CAPEX']:,.16g}")
            
    else:
        st.info("해당 작물의 공정 데이터를 입력하면 분석 차트가 표시됩니다.")
        
# --- Tab 2: 작업 스케줄 (FarmScheduler) ---
with tab2:
    st.subheader(f"📅 {selected_crop} 연간 공정 스케줄")
    crop_schedule = df_process[df_process['Crop_Name'] == selected_crop].copy()
    
    if not crop_schedule.empty:
        # 시간 중심 컬럼만 노출
        show_cols = ['Category_Type', 'Process_Step', 'Work_Week_Start', 'Work_Week_End']
        
        # 장비명은 '참고용'으로만 노출
        equip_col = f'Auto_{auto_level}_Equipment'
        if auto_level == 1:
            crop_schedule[equip_col] = crop_schedule.get(equip_col, pd.Series()).fillna("Hand Tool Kit")
        
        if equip_col in crop_schedule.columns:
            show_cols.append(equip_col)
            
        st.dataframe(crop_schedule[show_cols], use_container_width=True, hide_index=True)

# --- Tab 3: 투입 장비 정보 (Equipment Info) ---
with tab3:
    st.subheader(f"🚜 {auto_label} 주요 투입 장비 명세")
    
    # 1. 현재 공정에서 사용되는 장비 리스트 추출
    equip_col = f'Auto_{auto_level}_Equipment'
    if equip_col in crop_schedule.columns:
        # 중복 제거된 장비 목록 (예: ['Tractor', 'Hand Tool Kit'])
        used_equipments = crop_schedule[equip_col].dropna().unique()
        
        if len(used_equipments) > 0:
            # 2. Equipment_Facility 시트에서 해당 장비들 정보만 필터링
            # df_equip는 Equipment_Facility 시트 데이터를 담고 있는 데이터프레임입니다.
            matched_equip = df_equip[df_equip['Item_Name'].isin(used_equipments)]
            
            if not matched_equip.empty:
                # 3. 상세 정보 출력 (항목명, 제조사, 가격, 사양 등)
                st.dataframe(matched_equip, use_container_width=True, hide_index=True)
                
                # 4. (선택 사항) 장비별 이미지나 상세 설명 카드로 보여주기
                for _, row in matched_equip.iterrows():
                    with st.expander(f"🔍 {row['Item_Name']} 상세 보기"):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.write(f"**제조사:** {row.get('Manufacturer', 'N/A')}")
                            st.write(f"**추정가격:** ${row.get('Price', 0):,.0f}")
                        with col2:
                            st.write(f"**주요사양:** {row.get('Specification', 'N/A')}")
            else:
                st.info("선택된 공정 장비의 상세 스펙 정보가 장비 마스터 시트에 없습니다.")
        else:
            st.info("이 공정에는 등록된 장비가 없습니다.")

# --- Tab 4: 마스터 데이터 ---
with tab4:
    choice = st.radio("조회할 데이터", ["작물 마스터", "공정 표준", "장비 시설"], horizontal=True)
    if choice == "작물 마스터": st.dataframe(df_crop)
    elif choice == "공정 표준": st.dataframe(df_process)
    else: st.dataframe(df_equip)
