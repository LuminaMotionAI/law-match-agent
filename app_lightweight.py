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
    """허깅페이스 API 초기화 (로컬 백업 포함)"""
    try:
        st.sidebar.write("🔄 AI 모델 로딩 중...")
        hf_api = HuggingFaceAPI()  # 로컬 데이터셋 자동 사용
        st.sidebar.success("✅ AI 모델 로드 완료")
        return hf_api
    except Exception as e:
        st.sidebar.error(f"초기화 오류: {e}")
        return None

def main():
    """메인 애플리케이션"""
    
    # 타이틀
    st.title("⚖️ 한국 법률 판례 검색 AI")
    st.markdown("### 80,000개 한국어 법률 데이터 기반 지능형 검색")
    st.markdown("---")
    
    # API 초기화
    hf_api = init_huggingface_api()
    
    if not hf_api:
        st.error("❌ AI 모델 로딩에 실패했습니다.")
        st.info("💡 문제가 지속되면 페이지를 새로고침해주세요.")
        return
    
    # 사이드바 메뉴
    with st.sidebar:
        st.header("🔧 메뉴")
        menu = st.radio(
            "기능 선택",
            ["🏠 홈", "🔍 사례 검색", "🚀 종합 분석", "❓ 법률 Q&A", "📊 데이터셋 정보"]
        )
        
        st.markdown("---")
        
        # 데이터셋 정보
        st.subheader("📊 데이터셋")
        dataset_info = hf_api.get_dataset_info()
        if dataset_info:
            st.metric("전체 데이터", f"{dataset_info['total_count']:,}개")
            
            # 데이터 타입별 통계
            with st.expander("📋 데이터 구성"):
                for data_type, count in dataset_info['data_types'].items():
                    st.write(f"• {data_type}: {count:,}개")
        
        st.markdown("---")
        st.info("🤖 AI 기반 한국어 법률 검색")
    
    # 메인 컨텐츠
    if menu == "🏠 홈":
        show_home(hf_api)
    elif menu == "🔍 사례 검색":
        show_case_search(hf_api)
    elif menu == "🚀 종합 분석":
        show_comprehensive_analysis(hf_api)
    elif menu == "❓ 법률 Q&A":
        show_legal_qa(hf_api)
    elif menu == "📊 데이터셋 정보":
        show_dataset_info(hf_api)

def show_home(hf_api):
    """홈 페이지"""
    st.header("🏠 한국 법률 판례 검색 AI")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 주요 기능")
        st.markdown("""
        - **🔍 사례 검색**: AI 기반 유사 판례 찾기
        - **🚀 종합 분석**: 사건 분류 및 관련 법령 검색
        - **❓ 법률 Q&A**: 법률 해석 및 질의응답
        - **📊 데이터 분석**: 80,000개 법률 데이터 활용
        """)
        
        st.subheader("🎯 특징")
        st.markdown("""
        - ✅ **80,000개** 한국어 법률 데이터
        - ✅ **AI 임베딩** 기반 유사도 검색
        - ✅ **실시간 검색** (빠른 응답)
        - ✅ **다양한 법률 분야** 커버
        """)
    
    with col2:
        st.subheader("📊 데이터셋 구성")
        
        dataset_info = hf_api.get_dataset_info()
        if dataset_info:
            # 데이터 타입별 파이 차트 (간단 버전)
            data_types = dataset_info['data_types']
            
            for data_type, count in data_types.items():
                percentage = (count / dataset_info['total_count']) * 100
                st.metric(
                    label=data_type.replace('_', ' '),
                    value=f"{count:,}개",
                    delta=f"{percentage:.1f}%"
                )
        
        st.subheader("🚀 빠른 시작")
        st.markdown("""
        1. **🔍 사례 검색** 탭에서 키워드 입력
        2. **AI가 유사 사례** 자동 검색
        3. **결과 확인** 및 상세 정보 열람
        """)

def show_case_search(hf_api):
    """사례 검색 페이지"""
    st.header("🔍 AI 기반 사례 검색")
    st.write("법률 질문이나 키워드를 입력하면 AI가 유사한 사례를 찾아드립니다.")
    
    # 검색 입력
    search_query = st.text_area(
        "검색할 내용을 입력하세요:",
        placeholder="예: 음주운전으로 인한 교통사고 손해배상\n예: 인터넷 명예훼손 사건\n예: 계약 위반에 따른 위자료",
        height=100
    )
    
    # 검색 옵션
    col1, col2, col3 = st.columns(3)
    
    with col1:
        case_type = st.selectbox(
            "사건 유형 필터:",
            ["전체", "해석례", "판결문", "결정례", "법령"]
        )
    
    with col2:
        num_results = st.slider("검색 결과 수", 1, 20, 5)
    
    with col3:
        search_button = st.button("🔍 검색 실행", type="primary")
    
    # 검색 실행
    if search_button and search_query.strip():
        with st.spinner("AI가 유사 사례를 검색 중입니다..."):
            try:
                # 검색 실행
                search_type = None if case_type == "전체" else case_type
                results = hf_api.search_similar_cases(
                    search_query, 
                    top_k=num_results,
                    case_type=search_type
                )
                
                if results:
                    st.success(f"✅ {len(results)}개의 유사 사례를 찾았습니다!")
                    
                    # 결과 표시
                    for i, result in enumerate(results, 1):
                        with st.expander(
                            f"🏛️ 사례 {i} - {result['case_type']} "
                            f"(유사도: {result['similarity_score']:.3f})"
                        ):
                            # 기본 정보
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**사건번호:** {result['case_number']}")
                                st.write(f"**사건명:** {result['case_name']}")
                                st.write(f"**법원:** {result['court_code']}")
                            
                            with col2:
                                st.write(f"**날짜:** {result['final_date']}")
                                st.write(f"**사건 유형:** {result['case_type']}")
                                st.metric("유사도", f"{result['similarity_score']:.3f}")
                            
                            # 내용
                            if result.get('query'):
                                st.markdown("**📋 질의/제목:**")
                                st.write(result['query'])
                            
                            if result.get('answer'):
                                st.markdown("**⚖️ 답변/판시사항:**")
                                st.write(result['answer'])
                            
                            # 추가 정보
                            if result.get('instruction'):
                                with st.expander("📖 추가 정보"):
                                    st.write(f"**지시사항:** {result['instruction']}")
                                    st.write(f"**출처:** {result['source']}")
                
                else:
                    st.warning("⚠️ 검색 조건에 맞는 결과가 없습니다.")
                    st.info("💡 다른 키워드나 더 일반적인 용어로 다시 검색해보세요.")
                
            except Exception as e:
                st.error(f"❌ 검색 중 오류가 발생했습니다: {e}")
    
    elif search_button and not search_query.strip():
        st.warning("⚠️ 검색할 내용을 입력해주세요.")

def show_comprehensive_analysis(hf_api):
    """종합 분석 페이지"""
    st.header("🚀 AI 기반 종합 사건 분석")
    st.write("사건 내용을 입력하면 AI가 분류, 유사 판례, 관련 법령을 종합 분석합니다.")
    
    # 사건 입력
    case_input = st.text_area(
        "사건 내용을 자세히 입력하세요:",
        placeholder="예: 피고인이 온라인 쇼핑몰에서 가짜 명품을 판매하여 소비자들에게 총 500만원의 피해를 입힌 사기 사건입니다...",
        height=150
    )
    
    if st.button("🔍 종합 분석 시작", type="primary"):
        if not case_input.strip():
            st.error("사건 내용을 입력해주세요.")
            return
        
        with st.spinner("AI가 종합 분석 중입니다..."):
            try:
                # 종합 분석 실행
                analysis_result = hf_api.get_enhanced_case_analysis(case_input)
                
                if 'error' in analysis_result:
                    st.error(f"분석 중 오류 발생: {analysis_result['error']}")
                    return
                
                # 결과 표시
                st.success("✅ 종합 분석 완료!")
                
                # 1. 사건 분류
                st.subheader("📋 사건 분류")
                classification = analysis_result.get('case_classification', 'Unknown')
                st.info(f"분류 결과: **{classification}**")
                
                # 2. 유사 판례
                similar_precedents = analysis_result.get('similar_precedents', [])
                if similar_precedents:
                    st.subheader("⚖️ 유사 판례")
                    
                    for i, case in enumerate(similar_precedents[:3], 1):
                        with st.expander(f"판례 {i} - 유사도: {case.get('similarity_score', 0):.3f}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**사건번호:** {case.get('case_number', 'N/A')}")
                                st.write(f"**사건명:** {case.get('case_name', 'N/A')}")
                                st.write(f"**법원:** {case.get('court_code', 'N/A')}")
                            
                            with col2:
                                st.write(f"**날짜:** {case.get('final_date', 'N/A')}")
                                st.write(f"**사건 유형:** {case.get('case_type', 'Unknown')}")
                                st.metric("유사도", f"{case.get('similarity_score', 0):.3f}")
                            
                            if case.get('query'):
                                st.write(f"**질의:** {case['query']}")
                            
                            if case.get('answer'):
                                st.write(f"**답변:** {case['answer']}")
                
                # 3. 관련 법령
                applicable_laws = analysis_result.get('applicable_laws', [])
                if applicable_laws:
                    st.subheader("📜 관련 법령")
                    
                    for law in applicable_laws[:3]:
                        with st.expander(f"법령 {law.get('case_name', '법령')}"):
                            st.write(f"**질의:** {law.get('query', '')}")
                            st.write(f"**답변:** {law.get('answer', '')}")
                            st.write(f"**유사도:** {law.get('similarity_score', 0):.3f}")
                
                # 4. 법률 해석
                interpretations = analysis_result.get('legal_interpretations', [])
                if interpretations:
                    st.subheader("🔍 법률 해석")
                    
                    for interp in interpretations:
                        with st.expander(f"해석례 - 유사도: {interp.get('similarity_score', 0):.3f}"):
                            st.write(f"**질의:** {interp.get('query', '')}")
                            st.write(f"**해석:** {interp.get('answer', '')}")
                
                # 5. 권고사항
                recommendations = analysis_result.get('recommendations', [])
                if recommendations:
                    st.subheader("💡 권고사항")
                    
                    for i, rec in enumerate(recommendations, 1):
                        st.write(f"{i}. {rec}")
                
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {e}")

def show_legal_qa(hf_api):
    """법률 Q&A 페이지"""
    st.header("❓ AI 법률 질의응답")
    st.write("법률 질문을 입력하시면 관련 해석례와 판례를 찾아서 답변해드립니다.")
    
    # 질문 입력
    legal_question = st.text_area(
        "법률 질문을 입력하세요:",
        placeholder="예: 임대차 계약에서 보증금 반환 의무는 언제까지인가요?\n예: 교통사고에서 과실비율은 어떻게 결정되나요?",
        height=100
    )
    
    if st.button("💬 질문하기", type="primary"):
        if not legal_question.strip():
            st.error("질문을 입력해주세요.")
            return
        
        with st.spinner("AI가 법률 데이터를 검색하고 답변을 준비 중입니다..."):
            try:
                # 법률 해석 검색
                interpretation = hf_api.get_legal_interpretation(legal_question)
                
                if interpretation.get('answer'):
                    st.success("✅ 관련 법률 해석을 찾았습니다!")
                    
                    # 답변 표시
                    st.subheader("📋 질문")
                    st.info(interpretation.get('question', legal_question))
                    
                    st.subheader("⚖️ 법률 해석")
                    st.write(interpretation.get('answer', ''))
                    
                    # 추가 정보
                    if interpretation.get('context'):
                        with st.expander("📚 관련 정보"):
                            st.write(interpretation['context'])
                    
                    # 신뢰도 정보
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric(
                            "유사도", 
                            f"{interpretation.get('similarity_score', 0):.3f}"
                        )
                    
                    with col2:
                        st.info(f"출처: {interpretation.get('source', 'Unknown')}")
                
                else:
                    st.warning("정확한 법률 해석을 찾지 못했습니다.")
                    
                    # 일반 검색으로 대체
                    st.subheader("🔍 관련 사례 검색")
                    results = hf_api.search_similar_cases(legal_question, top_k=3)
                    
                    if results:
                        for i, result in enumerate(results, 1):
                            with st.expander(f"관련 사례 {i} - 유사도: {result['similarity_score']:.3f}"):
                                st.write(f"**질의:** {result['query']}")
                                st.write(f"**답변:** {result['answer']}")
                                st.write(f"**사건:** {result['case_name']}")
                    else:
                        st.info("관련 사례를 찾지 못했습니다. 다른 키워드로 다시 시도해보세요.")
                
            except Exception as e:
                st.error(f"질의응답 처리 중 오류가 발생했습니다: {e}")

def show_dataset_info(hf_api):
    """데이터셋 정보 페이지"""
    st.header("📊 데이터셋 정보")
    
    dataset_info = hf_api.get_dataset_info()
    
    if not dataset_info:
        st.error("데이터셋 정보를 불러올 수 없습니다.")
        return
    
    # 전체 통계
    st.subheader("📈 전체 통계")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("전체 데이터", f"{dataset_info['total_count']:,}개")
    
    with col2:
        st.metric("데이터 타입", f"{len(dataset_info['data_types'])}종류")
    
    with col3:
        st.metric("기간", f"{dataset_info['date_range']['earliest']} ~ {dataset_info['date_range']['latest']}")
    
    # 데이터 타입별 분포
    st.subheader("📊 데이터 타입별 분포")
    
    data_types = dataset_info['data_types']
    
    # 테이블 형태로 표시
    df_display = pd.DataFrame([
        {
            '데이터 타입': data_type,
            '개수': f"{count:,}개",
            '비율': f"{(count/dataset_info['total_count']*100):.1f}%"
        }
        for data_type, count in data_types.items()
    ])
    
    st.dataframe(df_display, use_container_width=True)
    
    # 데이터 설명
    st.subheader("📋 데이터 설명")
    
    descriptions = {
        '결정례_QA': '헌법재판소 결정례 질의응답 데이터',
        '결정례_SUM': '헌법재판소 결정례 요약 데이터',
        '법령_QA': '법령 조문 질의응답 데이터',
        '판결문_QA': '법원 판결문 질의응답 데이터',
        '판결문_SUM': '법원 판결문 요약 데이터',
        '해석례_QA': '법령 해석례 질의응답 데이터',
        '해석례_SUM': '법령 해석례 요약 데이터'
    }
    
    for data_type, count in data_types.items():
        description = descriptions.get(data_type, '설명 없음')
        st.write(f"• **{data_type}** ({count:,}개): {description}")
    
    # 기술 정보
    st.subheader("🔧 기술 정보")
    
    st.write(f"• **데이터 소스**: {dataset_info['source']}")
    st.write("• **임베딩 모델**: snunlp/KR-SBERT-V40K-klueNLI")
    st.write("• **검색 방식**: 코사인 유사도 기반 벡터 검색")
    st.write("• **지원 언어**: 한국어")

if __name__ == "__main__":
    main() 