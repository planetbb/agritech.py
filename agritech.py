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
        
        total_mh = crop_schedule[mh_col].sum() * size_sqm if mh_col in crop_schedule.columns else 0
        
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

    # 2. 그래프 시각화 (ValueError 방지를 위해 설정 최적화)
    fig = go.Figure()
    
    # 노동 시간 바 차트
    fig.add_trace(go.Bar(
        x=df_compare['Level'], 
        y=df_compare['Total_ManHour'], 
        name='Man-Hours', 
        marker_color='#5dade2', 
        yaxis='y1'
    ))
    
    # 투자비 라인 차트
    fig.add_trace(go.Scatter(
        x=df_compare['Level'], 
        y=df_compare['Total_CAPEX'], 
        name='Investment ($)', 
        line=dict(color='#e74c3c', width=4), 
        yaxis='y2'
    ))

    # 레이아웃 설정 (ValueError 해결을 위해 폰트 설정 구조 단순화)
    fig.update_layout(
        xaxis=dict(title="Automation Level"),
        yaxis=dict(
            title="Man-Hours", 
            side="left", 
            title_font=dict(color="#5dade2"), 
            tickfont=dict(color="#5dade2")
        ), 
        yaxis2=dict(
            title="Investment ($)", 
            overlaying="y", 
            side="right", 
            showgrid=False, 
            title_font=dict(color="#e74c3c"), 
            tickfont=dict(color="#e74c3c")
        ),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=1.15),
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. 상세 분석 카드 레이아웃 (검정 글씨 가독성 극대화)
    st.markdown("---")
    st.subheader("📋 자동화 수준별 상세 비교")
    
    cols = st.columns(3)
    
    for i, label in enumerate(levels):
        data = df_compare.iloc[i]
        is_selected = (label == automation_level)
        
        # 가독성을 위해 선택 시 연한 회색 배경(#F8F9FA)과 파란색 강조 테두리 사용
        bg_color = "#F0F7FF" if is_selected else "#FFFFFF"
        border_color = "#2E86C1" if is_selected else "#D5D8DC"
        box_shadow = "4px 4px 15px rgba(0,0,0,0.1)" if is_selected else "none"
        
        with cols[i]:
            st.markdown(f"""
                <div style="
                    background-color: {bg_color}; 
                    border: 2px solid {border_color}; 
                    padding: 20px; 
                    border-radius: 15px;
                    min-height: 280px;
                    box-shadow: {box_shadow};
                    color: #000000;
                ">
                    <h3 style="margin-top:0; color:#000000; font-weight: 900; border-bottom: 2px solid {border_color}; padding-bottom: 10px; display: flex; justify-content: space-between;">
                        <span>{label}</span>
                        <span>{"✅" if is_selected else ""}</span>
                    </h3>
                    <div style="margin-top: 20px;">
                        <div style="margin-bottom: 10px;">
                            <span style="font-size: 0.9em; font-weight: bold; color: #555;">⏱️ 연간 노동 시간</span><br>
                            <span style="font-size: 1.4em; font-weight: 800; color: #000000;">{data['Total_ManHour']:,.1f} <small>hr</small></span>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <span style="font-size: 0.9em; font-weight: bold; color: #555;">💰 총 설비 투자비</span><br>
                            <span style="font-size: 1.4em; font-weight: 800; color: #000000;">$ {data['Total_CAPEX']:,.0f}</span>
                        </div>
                    </div>
                    <div style="background: rgba(0,0,0,0.03); padding: 10px; border-radius: 8px; border-left: 4px solid {border_color};">
                        <p style="font-size: 0.85em; color: #000000; margin: 0; line-height: 1.4;">
                            <b>🚜 투입 장비:</b><br>
                            {data['Equipment']}
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)

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
