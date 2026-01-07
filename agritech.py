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

# 3. 데이터 로딩 및 전처리
@st.cache_data
def load_data(url, data_type="crop"):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        if data_type == "crop":
            for c in ['Yield_Per_sqm_kg', 'Avg_Price_Per_kg_USD']:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        elif data_type == "process":
            for i in range(1, 4):
                col = f'Auto_{i}_ManHour_per_sqm'
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        elif data_type == "equipment":
            if 'Unit_Price_USD' in df.columns: df['Unit_Price_USD'] = pd.to_numeric(df['Unit_Price_USD'], errors='coerce').fillna(0)
            if 'Lifespan_Years' in df.columns: df['Lifespan_Years'] = pd.to_numeric(df['Lifespan_Years'], errors='coerce').fillna(1)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
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
    selected_country = st.selectbox("1) 국가 선택", df_crop['Country'].unique())
    country_crops = df_crop[df_crop['Country'] == selected_country]
    selected_crop = st.selectbox("2) 작물 선택", country_crops['Crop_Name'].unique())
    size_sqm = st.number_input("3) 농지 면적 (sqm)", min_value=10, value=1000, step=100)
    auto_options = ["1) Manual", "2) Semi-Auto", "3) Full-Auto"]
    auto_label = st.radio("4) 자동화 수준", auto_options)
    automation_level = auto_label.split(") ")[1]
    auto_level_idx = auto_options.index(auto_label) + 1

# --- [핵심] Tab2, Tab3를 위한 데이터 Fallback 로직 ---
crop_info = df_crop[df_crop['Crop_Name'] == selected_crop].iloc[0]
cat_type = crop_info.get('Category_Type', 'Upland')

# 1순위: 선택한 작물의 전용 데이터
# 2순위: 카테고리별 대표 작물의 데이터 (Strawberry, Apple, Rice, Potato 중 하나)
# 3순위: 그마저도 없으면 카테고리명(Type) 자체로 검색
display_process_df = df_process[df_process['Crop_Name'] == selected_crop]
source_name = selected_crop

if display_process_df.empty:
    rep_crop = REPRESENTATIVE_CROP.get(cat_type, "Potato") # 기본값 Potato
    display_process_df = df_process[df_process['Crop_Name'] == rep_crop]
    source_name = f"{rep_crop} (대표작물)"
    if display_process_df.empty: # 대표작물 데이터도 시트에 없는 경우 대비
        display_process_df = df_process[df_process['Crop_Name'] == cat_type]
        source_name = f"{cat_type} 표준"

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비", "🗂️ 마스터 데이터"])

# --- Tab 1: 수익성 분석 (우측 인사이트 고정 레이아웃) ---
with tab1:
    # 0. 데이터 계산부
    total_yield = size_sqm * crop_info['Yield_Per_sqm_kg']
    total_rev = total_yield * crop_info['Avg_Price_Per_kg_USD']
    
    comp_data = []
    for i, label in enumerate(["Manual", "Semi-Auto", "Full-Auto"]):
        num = i + 1
        mh_col, eq_col = f'Auto_{num}_ManHour_per_sqm', f'Auto_{num}_Equipment'
        mh_val = display_process_df[mh_col].sum() * size_sqm if mh_col in display_process_df.columns else 0
        eq_list = display_process_df[eq_col].dropna().unique().tolist() if eq_col in display_process_df.columns else []
        capex = df_equip[df_equip['Item_Name'].isin(eq_list)]['Unit_Price_USD'].sum() if not df_equip.empty else 0
        comp_data.append({"Level": label, "MH": mh_val, "CAPEX": capex, "EQ": ", ".join(eq_list)})
    df_comp = pd.DataFrame(comp_data)

    # 1. 상단 요약 바 (콤팩트하게 변경)
    st.markdown(f"### 📊 {selected_crop} 분석 리포트")
    m1, m2, m3 = st.columns(3)
    m1.metric("🌾 예상 수확량", f"{total_yield:,.1f} kg")
    m2.metric("💰 예상 매출액", f"$ {total_rev:,.0f}")
    m3.metric("📍 설정 면적", f"{size_sqm:,.0f} sqm")
    st.markdown("---")

    # 2. 메인 레이아웃 (좌: 그래프 / 우: 상세 및 성과분석)
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.write("#### 📈 효율성 비교 차트")
        colors = ['#FFD700' if lvl == automation_level else '#D3D3D3' for lvl in df_comp['Level']]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_comp['Level'], y=df_comp['MH'], name='Labor Hrs', marker_color=colors, yaxis='y1'))
        fig.add_trace(go.Scatter(x=df_comp['Level'], y=df_comp['CAPEX'], name='Investment', line=dict(color='#e74c3c', width=3), yaxis='y2'))
        fig.update_layout(
            height=450, # 왼쪽 차트 높이를 키워 우측과 균형을 맞춤
            margin=dict(l=0,r=0,t=20,b=0),
            yaxis=dict(title="Man-Hours"),
            yaxis2=dict(title="CAPEX ($)", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with right_col:
        st.write("#### 📋 레벨별 요약 및 인사이트")
        # 레벨별 카드 루프
        for _, r in df_comp.iterrows():
            sel = (r['Level'] == automation_level)
            bg_color = "#FFF9C4" if sel else "#FFFFFF"
            border_color = "#FBC02D" if sel else "#DDD"
            
            st.markdown(f"""
                <div style="border: 2px solid {border_color}; padding: 10px; border-radius: 8px; margin-bottom: 6px; background-color: {bg_color}; color: #000;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 800; font-size: 1em;">{r['Level']} {"⭐" if sel else ""}</span>
                        <span style="font-size: 0.9em; font-weight: 700;">⏱️ {r['MH']:,.1f}h | 💰 ${r['CAPEX']:,.0f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # 🚀 성과 분석 인사이트를 카드 바로 아래에 배치
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if automation_level != "Manual":
            manual_data = df_comp.iloc[0]
            current_data = df_comp[df_comp['Level'] == automation_level].iloc[0]
            reduction_pct = (1 - current_data['MH'] / manual_data['MH']) * 100 if manual_data['MH'] > 0 else 0
            extra_capex = current_data['CAPEX'] - manual_data['CAPEX']
            
            # 박스 형태로 강조된 인사이트 섹션
            st.markdown(f"""
                <div style="background-color: #F8F9F9; border-left: 5px solid #28B463; padding: 15px; border-radius: 5px;">
                    <h5 style="margin-top:0; color: #1D8348;">💡 {automation_level} 성과 분석</h5>
                    <p style="margin: 5px 0; font-size: 0.95em;">
                        <b>노동 시간:</b> 수동 대비 <span style="color: #28B463; font-weight:bold;">{reduction_pct:.1f}% 절감</span><br>
                        <b>투자 비용:</b> 수동 대비 <span style="color: #CB4335; font-weight:bold;">$ {extra_capex:,.0f} 추가</span>
                    </p>
                    <small style="color: #7B7D7D;">* {source_name} 데이터 기준</small>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💡 **Manual 모드 사용 중**\n\n상단에서 자동화 수준을 변경하여 효율성을 비교해 보세요.")

# --- Tab 2: 작업 스케줄 ---
with tab2:
    st.subheader(f"📅 {selected_crop} 작업 프로세스")
    st.info(f"💡 데이터 소스: **{source_name}** 기준")
    
    target_eq_col = f'Auto_{auto_level_idx}_Equipment'
    avail_cols = [c for c in ['Process_Step', 'Work_Week_Start', 'Work_Week_End', target_eq_col] if c in display_process_df.columns]
    
    if not display_process_df.empty:
        st.dataframe(display_process_df[avail_cols], use_container_width=True, hide_index=True)
    else:
        st.warning("표시할 수 있는 공정 데이터가 없습니다. Process_Standard 시트의 작물명을 확인해주세요.")

# --- Tab 3: 투입 장비 ---
with tab3:
    st.subheader(f"🚜 {automation_level} 상세 장비 명세")
    st.caption(f"기준 데이터: {source_name}")
    
    target_eq_col = f'Auto_{auto_level_idx}_Equipment'
    if target_eq_col in display_process_df.columns:
        used_eq = display_process_df[target_eq_col].dropna().unique()
        matched = df_equip[df_equip['Item_Name'].isin(used_eq)]
        if not matched.empty:
            for _, row in matched.iterrows():
                with st.expander(f"🔹 {row['Item_Name']} ({row.get('Category', '기타')})"):
                    col1, col2 = st.columns(2)
                    col1.metric("단가 (USD)", f"$ {float(row['Unit_Price_USD']):,.0f}")
                    col2.metric("내구연한 (Years)", f"{int(float(row['Lifespan_Years']))} 년")
            st.markdown("---")
            st.dataframe(matched, use_container_width=True, hide_index=True)
        else:
            st.info("매칭된 상세 장비 정보가 없습니다. 장비 마스터 시트를 확인해 주세요.")

# --- Tab 4: 마스터 데이터 ---
with tab4:
    choice = st.radio("데이터 선택", ["작물", "공정", "장비"], horizontal=True)
    if choice == "작물": st.dataframe(df_crop)
    elif choice == "공정": st.dataframe(df_process)
    else: st.dataframe(df_equip)
