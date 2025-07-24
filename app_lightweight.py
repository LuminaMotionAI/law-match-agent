import streamlit as st
import pandas as pd
import json
import os
import warnings
from datetime import datetime
from typing import List, Dict, Optional

# 경고 메시지 억제
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# 가벼운 버전용 임포트
from api.huggingface_api import HuggingFaceAPI

# 페이지 설정
st.set_page_config(
    page_title="⚖️ 한국 법률 판례 검색 AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 변수
@st.cache_resource
def init_huggingface_api():
    """허깅페이스 API 초기화"""
    try:
        st.sidebar.write("🔄 허깅페이스 데이터셋 로딩 중...")
        hf_api = HuggingFaceAPI()
        
        # 데이터셋 로드 상태 확인
        if hf_api.df.empty:
            st.sidebar.error("❌ 데이터셋 로드 실패")
            return None
        else:
            st.sidebar.success(f"✅ 데이터셋 로드 완료: {len(hf_api.df):,}개 데이터")
            return hf_api
            
    except Exception as e:
        st.sidebar.error(f"❌ 초기화 오류: {e}")
        return None

def show_dataset_info(hf_api):
    """데이터셋 정보 표시"""
    if hf_api is None:
        st.error("📊 데이터셋 정보를 불러올 수 없습니다.")
        st.info("💡 **해결 방법:**")
        st.markdown("""
        1. **Streamlit Cloud Secrets 설정 확인**
        2. **허깅페이스 토큰 유효성 확인**
        3. **네트워크 연결 상태 확인**
        """)
        return
        
    try:
        dataset_info = hf_api.get_dataset_info()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 총 데이터 수", f"{dataset_info['total_count']:,}")
        
        with col2:
            st.metric("📁 데이터 유형", len(dataset_info['data_types']))
            
        with col3:
            st.metric("🌐 데이터셋", dataset_info['source'].split('/')[-1])
        
        # 데이터 유형별 분포
        st.subheader("📈 데이터 유형별 분포")
        type_counts = pd.DataFrame(list(dataset_info['data_types'].items()), 
                                 columns=['유형', '개수'])
        st.bar_chart(type_counts.set_index('유형'))
        
    except Exception as e:
        st.error(f"❌ 데이터셋 정보 표시 오류: {e}")

def search_legal_cases(hf_api):
    """법률 사례 검색"""
    if hf_api is None:
        st.error("❌ 검색 서비스를 사용할 수 없습니다.")
        return
        
    st.subheader("🔍 유사 판례 검색")
    
    # 검색 입력
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input("검색할 법률 사안을 입력하세요:", 
                             placeholder="예: 음주운전으로 인한 교통사고")
    
    with col2:
        case_type = st.selectbox("사례 유형", 
                                ["전체", "판결문", "결정례", "해석례", "법령"])
    
    if st.button("🔍 검색", type="primary"):
        if query.strip():
            with st.spinner("검색 중..."):
                try:
                    results = hf_api.search_similar_cases(query, top_k=5, case_type=case_type)
                    
                    if results:
                        st.success(f"✅ {len(results)}개의 유사 사례를 찾았습니다!")
                        
                        for i, result in enumerate(results, 1):
                            with st.expander(f"📄 사례 {i} (유사도: {result['similarity']:.2%})"):
                                st.markdown(f"**📋 질문:** {result['input']}")
                                st.markdown(f"**⚖️ 답변:** {result['output']}")
                                st.markdown(f"**🏷️ 유형:** {result['data_type']}")
                    else:
                        st.warning("🔍 검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
                        
                except Exception as e:
                    st.error(f"❌ 검색 오류: {e}")
        else:
            st.warning("⚠️ 검색어를 입력해주세요.")

def main():
    """메인 애플리케이션"""
    
    # 타이틀
    st.title("⚖️ 한국 법률 판례 검색 AI")
    st.markdown("### 🤖 허깅페이스 기반 지능형 법률 검색 시스템")
    st.markdown("---")
    
    # API 초기화
    hf_api = init_huggingface_api()
    
    # 사이드바 메뉴
    with st.sidebar:
        st.markdown("## 📋 메뉴")
        menu = st.radio(
            "기능 선택:",
            ["📊 데이터셋 정보", "🔍 판례 검색", "🏛️ 법령 검색", "📈 사례 분석"],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### 🔗 링크")
        st.markdown("[📊 데이터셋](https://huggingface.co/datasets/LuminaMotionAI/korean-legal-dataset)")
        st.markdown("[⚖️ GitHub](https://github.com/LuminaMotionAI/law-match-agent)")
    
    # 메뉴별 기능
    if menu == "📊 데이터셋 정보":
        st.header("📊 데이터셋 정보")
        show_dataset_info(hf_api)
        
    elif menu == "🔍 판례 검색":
        search_legal_cases(hf_api)
        
    elif menu == "🏛️ 법령 검색":
        st.header("🏛️ 법령 검색")
        if hf_api:
            st.info("🔍 법령 검색 기능 준비 중...")
        else:
            st.error("❌ 서비스를 사용할 수 없습니다.")
            
    elif menu == "📈 사례 분석":
        st.header("📈 사례 분석")
        if hf_api:
            st.info("📊 사례 분석 기능 준비 중...")
        else:
            st.error("❌ 서비스를 사용할 수 없습니다.")
    
    # 푸터
    st.markdown("---")
    st.markdown("🤖 **Powered by** [Hugging Face](https://huggingface.co/) | "
               "⚖️ **Korean Legal AI** | "
               "🏢 **LuminaMotionAI**")

if __name__ == "__main__":
    main() 