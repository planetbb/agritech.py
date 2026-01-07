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
    import plotly.graph_objects as go

    st.header(f"📊 {selected_crop} 자동화 레벨별 비교 분석")
    
    # 1. 데이터 계산부
    comparison_data = []
    crop_schedule = df_process[df_process['Crop_Name'] == selected_crop]
    levels = ["Manual", "Semi-Auto", "Full-Auto"]
    
    for i, label in enumerate(levels):
        level_num = i + 1
        mh_col, eq_col = f'Auto_{level_num}_ManHour_per_sqm', f'Auto_{level_num}_Equipment'
        
        # 노동시간 계산
        total_mh = crop_schedule[mh_col].sum() * size_sqm if mh_col in crop_schedule.columns else 0
        
        # 투자비 계산
        total_capex = 0
        used_equips = []
        if eq_col in crop_schedule.columns:
            used_equips = crop_schedule[eq_col].dropna().unique().tolist()
            if level_num == 1 and not used_equips: used_equips = ['Hand Tool Kit']
            if not df_equip.empty:
                prices = pd.to_numeric(df_equip[df_equip['Item_Name'].isin(used_equips)]['Unit_Price_USD'], errors='coerce')
                total_capex = prices.sum()
        
        comparison_data.append({
            "Level": label,
            "Total_ManHour": total_mh,
            "Total_CAPEX": total_capex,
            "Equipment": ", ".join(used_equips) if used_equips else "N/A"
        })

    df_compare = pd.DataFrame(comparison_data)

    # 2. 상단 그래프 (기존 유지)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_compare['Level'], y=df_compare['Total_ManHour'], name='Man-Hours', marker_color='#5dade2', yaxis='y1'))
    fig.add_trace(go.Scatter(x=df_compare['Level'], y=df_compare['Total_CAPEX'], name='Investment ($)', line=dict(color='#e74c3c', width=4), yaxis='y2'))
    fig.update_layout(
        yaxis=dict(title="Man-Hours", side="left"), 
        yaxis2=dict(title="Investment ($)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. 상세 분석 카드 레이아웃 (좌우 디스플레이)
    st.markdown("---")
    st.subheader("📋 자동화 수준별 상세 비교")
    
    # 세 개의 컬럼 생성
    cols = st.columns(3)
    
    for i, label in enumerate(levels):
        data = df_compare.iloc[i]
        is_selected = (label == automation_level)
        
        with cols[i]:
            # 선택된 카드에만 연한 배경색과 테두리 적용 (HTML/CSS 사용)
            bg_color = "#E8F4FD" if is_selected else "#FFFFFF"
            border_color = "#3498DB" if is_selected else "#E0E0E0"
            text_weight = "bold" if is_selected else "normal"
            
            st.markdown(f"""
                <div style="
                    background-color: {bg_color}; 
                    border: 2px solid {border_color}; 
                    padding: 20px; 
                    border-radius: 10px;
                    height: 250px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
                ">
                    <h3 style="margin-top:0; color:#2C3E50;">{label} {"✅" if is_selected else ""}</h3>
                    <p style="margin-bottom:5px;">⏱️ <b>노동 시간:</b> {data['Total_ManHour']:,.1f} hr</p>
                    <p style="margin-bottom:5px;">💰 <b>설비 투자비:</b> $ {data['Total_CAPEX']:,.0f}</p>
                    <hr style="margin: 10px 0; border: 0.5px solid #DDD;">
                    <p style="font-size: 0.85em; color: #666; line-height: 1.4;">
                        🛠️ <b>주요 장비:</b><br>{data['Equipment']}
                    </p>
                </div>
            """, unsafe_allow_html=True)

    # 4. 하단 성과 요약 메시지
    if automation_level != "Manual":
        m_mh = df_compare.iloc[0]['Total_ManHour']
        curr_mh = df_compare[df_compare['Level'] == automation_level]['Total_ManHour'].values[0]
        if m_mh > 0:
            reduction = (1 - curr_mh / m_mh) * 100
            st.success(f"💡 현재 선택하신 **{automation_level}**은 수동 작업 대비 약 **{reduction:.1f}%**의 노동력 절감 효과가 있습니다.")            
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
