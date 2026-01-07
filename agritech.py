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
        # 모든 텍스트 데이터의 앞뒤 공백 제거
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        if data_type == "crop":
            for c in ['Yield_Per_sqm_kg', 'Avg_Price_Per_kg_USD']:
                if c in df.columns: 
                    df[c] = df[c].astype(str).str.replace(r'[$,]', '', regex=True)
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        elif data_type == "process":
            for i in range(1, 4):
                col = f'Auto_{i}_ManHour_per_sqm'
                if col in df.columns: 
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        elif data_type == "equipment":
            if 'Unit_Price_USD' in df.columns: 
                df['Unit_Price_USD'] = df['Unit_Price_USD'].astype(str).str.replace(r'[$,]', '', regex=True)
                df['Unit_Price_USD'] = pd.to_numeric(df['Unit_Price_USD'], errors='coerce').fillna(0)
            if 'Lifespan_Years' in df.columns: 
                df['Lifespan_Years'] = pd.to_numeric(df['Lifespan_Years'], errors='coerce').fillna(1)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

df_crop = load_data(SHEET_URLS["crop"], "crop")
df_equip = load_data(SHEET_URLS["equipment"], "equipment")
df_process = load_data(SHEET_URLS["process"], "process")

if df_crop.empty or df_equip.empty or df_process.empty:
    st.stop()

REPRESENTATIVE_CROP = {"Greenhouse": "Strawberry", "Orchard": "Apple", "Paddy": "Rice", "Upland": "Potato"}

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

# --- 데이터 Fallback 로직 ---
crop_info = df_crop[df_crop['Crop_Name'] == selected_crop].iloc[0]
cat_type = crop_info.get('Category_Type', 'Upland')
display_process_df = df_process[df_process['Crop_Name'] == selected_crop]
source_name = selected_crop

if display_process_df.empty:
    rep_crop = REPRESENTATIVE_CROP.get(cat_type, "Potato")
    display_process_df = df_process[df_process['Crop_Name'] == rep_crop]
    source_name = f"{rep_crop} (대표)"

# --- 탭 구성 ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비", "🗂️ 마스터 데이터"])

# --- Tab 1: 수익성 분석 ---
with tab1:
    total_yield = size_sqm * crop_info['Yield_Per_sqm_kg']
    total_rev = total_yield * crop_info['Avg_Price_Per_kg_USD']
    
    comp_data = []
    for i, label in enumerate(["Manual", "Semi-Auto", "Full-Auto"]):
        num = i + 1
        mh_col, eq_col = f'Auto_{num}_ManHour_per_sqm', f'Auto_{num}_Equipment'
        mh_val = display_process_df[mh_col].sum() * size_sqm if mh_col in display_process_df.columns else 0
        eq_list = display_process_df[eq_col].dropna().unique().tolist() if eq_col in display_process_df.columns else []
        capex = df_equip[df_equip['Item_Name'].isin(eq_list)]['Unit_Price_USD'].sum()
        comp_data.append({"Level": label, "MH": mh_val, "CAPEX": capex, "EQ": eq_list})
    df_comp = pd.DataFrame(comp_data)

    st.markdown(f"### 📊 {selected_crop} 분석 리포트")
    m1, m2, m3 = st.columns(3)
    m1.metric("🌾 예상 수확량", f"{total_yield:,.1f} kg")
    m2.metric("💰 예상 매출액", f"$ {total_rev:,.0f}")
    m3.metric("📍 설정 면적", f"{size_sqm:,.0f} sqm")
    
    st.markdown("---")
    
    # 좌우 기둥 레이아웃 설정
    l_col, r_col = st.columns([1, 1])
    
    # --- 왼쪽 기둥 (그래프) ---
    with l_col:
        st.write("#### 📈 효율성 비교 차트")
        # 중앙 상단 커스텀 범례
        st.markdown("""
            <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 10px;">
                <div style="display: flex; align-items: center;"><div style="width: 15px; height: 10px; background-color: #D3D3D3; margin-right: 5px;"></div><span style="font-size: 0.8em; font-weight:bold;">Labor Hrs</span></div>
                <div style="display: flex; align-items: center;"><div style="width: 15px; height: 3px; background-color: #e74c3c; margin-right: 5px;"></div><span style="font-size: 0.8em; font-weight:bold;">CAPEX</span></div>
                <div style="display: flex; align-items: center;"><div style="width: 10px; height: 10px; background-color: #FFD700; margin-right: 5px;"></div><span style="font-size: 0.8em; font-weight:bold;">Selected</span></div>
            </div>
        """, unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_comp['Level'], 
            y=df_comp['MH'], 
            marker_color=['#FFD700' if l == automation_level else '#D3D3D3' for l in df_comp['Level']], 
            yaxis='y1'
        ))
        fig.add_trace(go.Scatter(
            x=df_comp['Level'], 
            y=df_comp['CAPEX'], 
            line=dict(color='#e74c3c', width=3), 
            mode='lines+markers', 
            yaxis='y2'
        ))
        fig.update_layout(
            height=400, showlegend=False, margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(title="Man-Hours"),
            yaxis2=dict(title="CAPEX ($)", overlaying="y", side="right", showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- 오른쪽 기둥 (인사이트) ---
    with r_col:
        st.write("#### 📋 레벨별 요약 및 인사이트")
        for _, r in df_comp.iterrows():
            sel = (r['Level'] == automation_level)
            st.markdown(f"""
                <div style="border: 2px solid {'#FBC02D' if sel else '#DDD'}; padding: 10px; border-radius: 8px; margin-bottom: 6px; background-color: {'#FFF9C4' if sel else '#FFF'}; color: #000;">
                    <div style="display: flex; justify-content: space-between;">
                        <b>{r['Level']} {"⭐" if sel else ""}</b> 
                        <span>⏱️ {r['MH']:,.1f}h | 💰 ${r['CAPEX']:,.0f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        if automation_level != "Manual":
            current_row = df_comp[df_comp['Level'] == automation_level].iloc[0]
            manual_row = df_comp.iloc[0]
            reduction = (1 - current_row['MH'] / manual_row['MH']) * 100 if manual_row['MH'] > 0 else 0
            extra = current_row['CAPEX'] - manual_row['CAPEX']
            st.info(f"💡 **분석 결과:** {automation_level} 적용 시 수동 대비 노동 시간 **{reduction:.1f}% 절감**, 설비 투자비 **$ {extra:,.0f} 추가**가 예상됩니다.")

# --- Tab 2: 작업 스케줄 ---
with tab2:
    st.subheader(f"📅 {selected_crop} 작업 프로세스 ({source_name})")
    target_eq_col = f'Auto_{auto_level_idx}_Equipment'
    avail_cols = [c for c in ['Process_Step', 'Work_Week_Start', 'Work_Week_End', target_eq_col] if c in display_process_df.columns]
    st.dataframe(display_process_df[avail_cols], use_container_width=True, hide_index=True)

# --- Tab 3: 투입 장비 ---
with tab3:
    st.subheader(f"🚜 {automation_level} 투입 장비 명세")
    target_eq_col = f'Auto_{auto_level_idx}_Equipment'
    if target_eq_col in display_process_df.columns:
        used_eq = display_process_df[target_eq_col].dropna().unique()
        matched = df_equip[df_equip['Item_Name'].isin(used_eq)]
        if not matched.empty:
            st.metric("총 장비 투자액", f"$ {matched['Unit_Price_USD'].sum():,.0f}")
            st.dataframe(matched[['Item_Name', 'Category', 'Unit_Price_USD', 'Lifespan_Years']], use_container_width=True, hide_index=True)
        else:
            st.info("해당 레벨에 매칭된 상세 장비 정보가 없습니다.")

# --- Tab 4: 마스터 데이터 ---
with tab4:
    c1, c2, c3 = st.columns(3)
    if c1.button("작물 데이터"): st.dataframe(df_crop)
    if c2.button("공정 데이터"): st.dataframe(df_process)
    if c3.button("장비 데이터"): st.dataframe(df_equip)
