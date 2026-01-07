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

# 3. 데이터 로딩 및 강력한 전처리
@st.cache_data
def load_data(url, data_type="crop"):
    try:
        df = pd.read_csv(url)
        # 컬럼명 앞뒤 공백 제거 및 표준화
        df.columns = df.columns.str.strip()
        
        if data_type == "crop":
            # 숫자형 변환 (에러 발생 시 NaN -> 0)
            num_cols = ['Yield_Per_sqm_kg', 'Avg_Price_Per_kg_USD']
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        elif data_type == "process":
            # 자동화 단계별 시간 컬럼 강제 숫자화
            for i in range(1, 4):
                col = f'Auto_{i}_ManHour_per_sqm'
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
        elif data_type == "equipment":
            # 가격 및 수명 컬럼 강제 숫자화
            if 'Unit_Price_USD' in df.columns:
                df['Unit_Price_USD'] = pd.to_numeric(df['Unit_Price_USD'], errors='coerce').fillna(0)
            if 'Lifespan_Years' in df.columns:
                df['Lifespan_Years'] = pd.to_numeric(df['Lifespan_Years'], errors='coerce').fillna(1)
                
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# 데이터 로드
df_crop = load_data(SHEET_URLS["crop"], "crop")
df_equip = load_data(SHEET_URLS["equipment"], "equipment")
df_process = load_data(SHEET_URLS["process"], "process")

if df_crop.empty or df_equip.empty or df_process.empty:
    st.warning("데이터를 불러오는 중입니다... 잠시만 기다려주세요.")
    st.stop()

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("📍 농업 설정 (Farm Setup)")
    selected_country = st.selectbox("1) 국가 선택", df_crop['Country'].unique())
    country_crops = df_crop[df_crop['Country'] == selected_country]
    selected_crop = st.selectbox("2) 작물 선택", country_crops['Crop_Name'].unique())
    size_sqm = st.number_input("3) 농지 면적 (sqm)", min_value=10, value=1000, step=100)
    
    auto_options = ["1) Manual", "2) Semi-Auto", "3) Full-Auto"]
    auto_label = st.radio("4) 자동화 수준", auto_options)
    automation_level = auto_label.split(") ")[1]
    auto_level_idx = auto_options.index(auto_label) + 1

# --- Fallback 로직 ---
crop_info_row = df_crop[df_crop['Crop_Name'] == selected_crop].iloc[0]
selected_category = crop_info_row.get('Category_Type', 'Field_Type')

# 전용 데이터 확인
display_process_df = df_process[df_process['Crop_Name'] == selected_crop]
is_fallback = False
if display_process_df.empty:
    display_process_df = df_process[df_process['Crop_Name'] == selected_category]
    is_fallback = True

# 탭 설정
tab1, tab2, tab3, tab4 = st.tabs(["📊 수익성 분석", "📅 작업 스케줄", "🚜 투입 장비", "🗂️ 마스터 데이터"])

# --- Tab 1: 수익성 분석 ---
with tab1:
    total_yield = size_sqm * crop_info_row['Yield_Per_sqm_kg']
    total_rev = total_yield * crop_info_row['Avg_Price_Per_kg_USD']
    
    st.markdown(f"### 📊 {selected_crop} 분석 리포트")
    m1, m2, m3 = st.columns(3)
    m1.metric("🌾 예상 수확량", f"{total_yield:,.1f} kg")
    m2.metric("💰 예상 매출액", f"$ {total_rev:,.0f}")
    m3.metric("📍 설정 면적", f"{size_sqm:,.0f} sqm")
    
    st.markdown("---")
    
    comp_data = []
    levels = ["Manual", "Semi-Auto", "Full-Auto"]
    for i, label in enumerate(levels):
        num = i + 1
        # 컬럼 존재 여부 체크 (KeyError 방지)
        mh_col = f'Auto_{num}_ManHour_per_sqm'
        eq_col = f'Auto_{num}_Equipment'
        
        total_mh = display_process_df[mh_col].sum() * size_sqm if mh_col in display_process_df.columns else 0
        
        used_eq = []
        if eq_col in display_process_df.columns:
            used_eq = display_process_df[eq_col].dropna().unique().tolist()
        
        capex = df_equip[df_equip['Item_Name'].isin(used_eq)]['Unit_Price_USD'].sum() if not df_equip.empty else 0
        comp_data.append({"Level": label, "MH": total_mh, "CAPEX": capex, "EQ": ", ".join(used_eq)})
    
    df_comp = pd.DataFrame(comp_data)
    
    # 그래프 및 카드 출력
    c1, c2 = st.columns([1, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_comp['Level'], y=df_comp['MH'], name='Hrs', yaxis='y1', marker_color='#5dade2'))
        fig.add_trace(go.Scatter(x=df_comp['Level'], y=df_comp['CAPEX'], name='CAPEX', yaxis='y2', line=dict(color='#e74c3c', width=3)))
        fig.update_layout(height=350, margin=dict(l=0,r=0,t=20,b=0), yaxis2=dict(overlaying="y", side="right", showgrid=False))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        for _, r in df_comp.iterrows():
            sel = (r['Level'] == automation_level)
            st.markdown(f"""<div style="border: 1px solid {'#2E86C1' if sel else '#DDD'}; padding: 10px; border-radius: 5px; margin-bottom: 5px; background: {'#F0F7FF' if sel else '#FFF'}; color: #000;">
            <b>{r['Level']}</b> | ⏱️ {r['MH']:,.1f}h | 💰 ${r['CAPEX']:,.0f}<br><small>🚜 {r['EQ']}</small></div>""", unsafe_allow_html=True)

# --- Tab 2: 작업 스케줄 ---
with tab2:
    if is_fallback: st.info(f"💡 {selected_category} 표준 공정 데이터를 참조합니다.")
    target_eq_col = f'Auto_{auto_level_idx}_Equipment'
    
    # 필요한 컬럼만 필터링하여 출력 (에러 방지용)
    avail_cols = [c for c in ['Process_Step', 'Work_Week_Start', 'Work_Week_End', target_eq_col] if c in display_process_df.columns]
    st.dataframe(display_process_df[avail_cols], use_container_width=True, hide_index=True)

# --- Tab 3: 투입 장비 ---
with tab3:
    st.subheader(f"🚜 {automation_level} 상세 장비")
    target_eq_col = f'Auto_{auto_level_idx}_Equipment'
    
    if target_eq_col in display_process_df.columns:
        used_eq = display_process_df[target_eq_col].dropna().unique()
        matched = df_equip[df_equip['Item_Name'].isin(used_eq)]
        if not matched.empty:
            for _, row in matched.iterrows():
                with st.expander(f"🔹 {row['Item_Name']}"):
                    c1, c2 = st.columns(2)
                    c1.metric("Price", f"$ {float(row['Unit_Price_USD']):,.0f}")
                    c2.metric("Lifespan", f"{int(float(row['Lifespan_Years']))} Years")
            st.dataframe(matched, use_container_width=True, hide_index=True)
        else:
            st.info("장비 상세 제원이 없습니다.")

# --- Tab 4: 마스터 데이터 ---
with tab4:
    choice = st.radio("데이터 선택", ["작물", "공정", "장비"], horizontal=True)
    if choice == "작물": st.dataframe(df_crop)
    elif choice == "공정": st.dataframe(df_process)
    else: st.dataframe(df_equip)
