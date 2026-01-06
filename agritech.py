import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. 구글 시트 웹 게시용 CSV URL (여러분의 링크로 교체하세요)
SHEET_URLS = {
    "crop": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=0&single=true&output=csv",
    "equipment": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=1783566142&single=true&output=csv",
    "process": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSBlhAdJB-jJOr_MoBgELY-qNKC5yJcD-G2gL03WRVTdbfOqtdiq0jHOnA-UlPakXWjpOw8PeMUroLG/pub?gid=1120300035&single=true&output=csv"
}

# 2. Gemini 설정 (Streamlit Secrets에서 가져오기)
# genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# model = genai.GenerativeModel('gemini-pro')

@st.cache_data # 데이터를 매번 새로고침하지 않도록 캐싱
def load_data(url):
    return pd.read_csv(url)

# 1. 숫자가 들어있어야 할 컬럼들을 '숫자형'으로 강제 변환합니다.
# errors='coerce'를 쓰면 숫자가 아닌 것(예: "pcs")은 자동으로 NaN(비어있는 값)이 됩니다.
df_crop['Yield_Per_sqm_kg'] = pd.to_numeric(df_crop['Yield_Per_sqm_kg'], errors='coerce')
df_crop['Avg_Price_Per_kg_USD'] = pd.to_numeric(df_crop['Avg_Price_Per_kg_USD'], errors='coerce')

# 2. NaN이 발생한 행(계산이 불가능한 행)을 아예 삭제해버립니다.
# subset에 지정한 컬럼들 중 하나라도 숫자가 아니면 그 행은 사라집니다.
df_crop = df_crop.dropna(subset=['Yield_Per_sqm_kg', 'Avg_Price_Per_kg_USD'])

# (선택사항) 삭제된 후의 데이터 개수를 로그로 확인하고 싶다면
# st.write(f"유효한 데이터 {len(df_crop)}건을 분석합니다.")

# --- 앱 UI 시작 ---
st.set_page_config(page_title="AgriTech FarmPlanner", layout="wide")
st.title("🌱 AgriTech FarmPlanner & Scheduler")

# 데이터 로드
try:
    df_crop = load_data(SHEET_URLS["crop"])
    df_equip = load_data(SHEET_URLS["equipment"])
    df_process = load_data(SHEET_URLS["process"])
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다. URL을 확인해주세요. {e}")
    st.stop()

# 사이드바: 사용자 입력
with st.sidebar:
    st.header("📍 농지 정보 입력")
    country = st.selectbox("국가 선택", df_crop['Country'].unique())
    size_sqm = st.number_input("농지 면적 (sqm)", min_value=10, value=1000)
    auto_level = st.select_slider("자동화 수준", options=[1, 2, 3])

# 메인 화면: FarmPlanner
tab1, tab2 = st.tabs(["📊 FarmPlanner", "📅 FarmScheduler"])

with tab1:
    st.subheader(f"🔍 {country} 지역 추천 작물")
    
    # 국가별 작물 필터링
    recommended_crops = df_crop[df_crop['Country'] == country]
    
    for index, row in recommended_crops.iterrows():
        with st.expander(f"📌 추천 작물: {row['Crop_Name']}"):
            col1, col2, col3 = st.columns(3)
            
            # 매출 계산 로직
            est_revenue = row['Yield_Per_sqm_kg'] * size_sqm * row['Avg_Price_Per_kg_USD']
            
            col1.metric("예상 연 매출", f"${est_revenue:,.0f}")
            col2.metric("sqm당 수확량", f"{row['Yield_Per_sqm_kg']} kg")
            col3.metric("재배 난이도", f"⭐ {row['Difficulty_Level']}/5")
            
            # 여기서 Gemini에게 추가 분석 요청 가능
            # if st.button(f"{row['Crop_Name']} 상세 분석", key=row['Crop_Name']):
            #     response = model.generate_content(f"{country}에서 {row['Crop_Name']} 재배 시 주의사항 알려줘")
            #     st.write(response.text)

with tab2:
    st.subheader("🗓️ 주간 작업 스케줄 및 인력 배치")
    selected_crop = st.selectbox("스케줄을 확인할 작물을 선택하세요", recommended_crops['Crop_Name'].unique())
    
    # 공정 데이터 필터링
    crop_schedule = df_process[df_process['Crop_Name'] == selected_crop]
    
    if not crop_schedule.empty:
        # 간단한 스케줄 표 출력
        st.dataframe(crop_schedule[['Process_Name', 'Work_Week_Start', 'Work_Week_End', f'Auto_{auto_level}_ManHour_per_sqm']])
        
        # 인력 계산 로직
        total_hours = crop_schedule[f'Auto_{auto_level}_ManHour_per_sqm'].sum() * size_sqm
        st.warning(f"💡 선택하신 자동화 레벨 {auto_level} 적용 시, 연간 총 예상 노동시간은 **{total_hours:,.1} Man-Hour** 입니다.")
    else:
        st.write("해당 작물의 상세 공정 데이터가 아직 시트에 없습니다.")
