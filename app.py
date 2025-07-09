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

# PyTorch 관련 경고 억제
import sys
if 'torch' in sys.modules:
    import torch
    torch.set_num_threads(1)

# 커스텀 모듈 임포트
from config import Config
from api import LawAPI, OpenAIAPI
from utils import FileProcessor, TextAnalyzer

# 페이지 설정
st.set_page_config(
    page_title="판례 검색 & 사건 분석 에이전트",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 전역 변수
@st.cache_resource
def init_components():
    """컴포넌트 초기화"""
    try:
        Config.validate_config()
        law_api = LawAPI()
        openai_api = OpenAIAPI()
        file_processor = FileProcessor()
        text_analyzer = TextAnalyzer()
        return law_api, openai_api, file_processor, text_analyzer
    except Exception as e:
        st.error(f"초기화 오류: {e}")
        return None, None, None, None

# 세션 상태 초기화
if 'case_analysis' not in st.session_state:
    st.session_state.case_analysis = None
if 'precedents' not in st.session_state:
    st.session_state.precedents = []
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

def main():
    """메인 애플리케이션"""
    
    # 타이틀
    st.title("⚖️ 판례 검색 & 사건 분석 에이전트")
    st.markdown("---")
    
    # 컴포넌트 초기화
    law_api, openai_api, file_processor, text_analyzer = init_components()
    
    if not all([law_api, openai_api, file_processor, text_analyzer]):
        st.error("시스템 초기화에 실패했습니다. 설정을 확인해주세요.")
        return
    
    # 사이드바 메뉴
    with st.sidebar:
        st.header("🔧 메뉴")
        menu = st.radio(
            "기능 선택",
            ["🏠 홈", "📄 사건 분석", "🔍 판례 검색", "✅ 법률 정보 검증", "📊 종합 리포트", "⚙️ 설정"]
        )
        
        st.markdown("---")
        
        # API 키 상태 표시
        st.subheader("🔑 API 상태")
        if Config.OPENAI_API_KEY:
            st.success("✅ OpenAI API 연결됨")
        else:
            st.error("❌ OpenAI API 키 필요")
            
        st.markdown("---")
        
        # 빠른 액션
        st.subheader("🚀 빠른 액션")
        if st.button("🗑️ 세션 초기화"):
            st.session_state.clear()
            st.rerun()
    
    # 메인 컨텐츠
    if menu == "🏠 홈":
        show_home()
    elif menu == "📄 사건 분석":
        show_case_analysis(openai_api, file_processor, text_analyzer)
    elif menu == "🔍 판례 검색":
        show_precedent_search(law_api, openai_api, text_analyzer)
    elif menu == "✅ 법률 정보 검증":
        show_legal_verification(law_api, openai_api)
    elif menu == "📊 종합 리포트":
        show_comprehensive_report(openai_api)
    elif menu == "⚙️ 설정":
        show_settings()

def show_home():
    """홈 페이지"""
    st.header("🏠 판례 검색 & 사건 분석 에이전트")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 주요 기능")
        st.markdown("""
        - **🔍 판례 검색**: 키워드로 관련 판례 찾기
        - **📄 사건 분석**: 사건 내용 자동 분석
        - **📊 유사도 분석**: 내 사건과 판례 비교
        - **📈 형량 예측**: AI 기반 형량 예측
        - **📋 종합 리포트**: 분석 결과 종합 정리
        """)
    
    with col2:
        st.subheader("🚀 사용 방법")
        st.markdown("""
        1. **사건 분석** 탭에서 사건 내용 입력
        2. **판례 검색** 탭에서 관련 판례 찾기
        3. **종합 리포트** 탭에서 결과 확인
        """)
    
    st.markdown("---")
    
    # 최근 검색 기록
    if st.session_state.search_history:
        st.subheader("📜 최근 검색 기록")
        for i, search in enumerate(st.session_state.search_history[-5:]):
            with st.expander(f"🔍 {search['query']} ({search['timestamp']})"):
                st.write(f"**검색어**: {search['query']}")
                st.write(f"**결과 수**: {search['result_count']}")
                st.write(f"**검색 시간**: {search['timestamp']}")

def show_case_analysis(openai_api, file_processor, text_analyzer):
    """사건 분석 페이지"""
    st.header("📄 사건 분석")
    
    # 입력 방법 선택
    input_method = st.radio(
        "사건 정보 입력 방법",
        ["📝 직접 입력", "📁 파일 업로드"]
    )
    
    case_text = ""
    
    if input_method == "📝 직접 입력":
        case_text = st.text_area(
            "사건 내용을 입력하세요",
            height=300,
            placeholder="예: 온라인 게임에서 다른 사용자의 계정을 해킹하여 게임 아이템을 훔쳤습니다..."
        )
    
    elif input_method == "📁 파일 업로드":
        uploaded_file = st.file_uploader(
            "사건 관련 문서 업로드",
            type=['txt', 'pdf', 'docx'],
            help="고소장, 진술서, 사건 요약서 등을 업로드하세요."
        )
        
        if uploaded_file is not None:
            # 파일 처리
            file_data = uploaded_file.read()
            result = file_processor.process_uploaded_file(file_data, uploaded_file.name)
            
            if result['success']:
                case_text = result['content']
                st.success(f"✅ 파일 처리 완료: {uploaded_file.name}")
                st.text_area("추출된 내용", case_text, height=200)
            else:
                st.error(f"❌ 파일 처리 실패: {result['error']}")
    
    # 분석 실행
    if case_text and st.button("🔍 사건 분석 실행"):
        with st.spinner("사건을 분석 중입니다..."):
            try:
                # AI 분석
                analysis = openai_api.analyze_case(case_text)
                
                # 텍스트 구조 분석
                structure_analysis = text_analyzer.analyze_text_structure(case_text)
                
                # 키워드 추출
                keywords = openai_api.extract_keywords(case_text)
                
                # 결과 저장
                st.session_state.case_analysis = {
                    'text': case_text,
                    'ai_analysis': analysis,
                    'structure_analysis': structure_analysis,
                    'keywords': keywords,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                st.success("✅ 분석이 완료되었습니다!")
                
            except Exception as e:
                st.error(f"❌ 분석 중 오류가 발생했습니다: {e}")
    
    # 분석 결과 표시
    if st.session_state.case_analysis:
        st.markdown("---")
        st.subheader("📊 분석 결과")
        
        analysis = st.session_state.case_analysis['ai_analysis']
        
        # 탭으로 결과 구분
        tab1, tab2, tab3, tab4 = st.tabs(["🎯 핵심 분석", "📈 통계", "🔍 키워드", "📋 상세"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🔴 추정 범죄 유형**")
                for crime in analysis.get('crime_types', []):
                    st.write(f"• {crime}")
                
                st.markdown("**⚖️ 적용 가능한 법령**")
                for law in analysis.get('applicable_laws', []):
                    st.write(f"• {law}")
            
            with col2:
                st.markdown("**⚡ 예상 형량**")
                st.write(analysis.get('estimated_punishment', '분석 불가'))
                
                st.markdown("**📊 사건 경중**")
                severity = analysis.get('case_severity', '판단 불가')
                if severity == '경미':
                    st.success(f"🟢 {severity}")
                elif severity == '보통':
                    st.warning(f"🟡 {severity}")
                else:
                    st.error(f"🔴 {severity}")
        
        with tab2:
            structure = st.session_state.case_analysis['structure_analysis']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("단어 수", structure.get('word_count', 0))
                st.metric("문장 수", structure.get('sentence_count', 0))
            
            with col2:
                st.metric("법률 용어 수", structure.get('legal_term_count', 0))
                st.metric("평균 문장 길이", f"{structure.get('avg_sentence_length', 0):.1f}")
            
            with col3:
                complexity = structure.get('complexity_score', 0)
                st.metric("복잡도", f"{complexity:.2f}")
                
                if complexity < 0.3:
                    st.success("🟢 단순")
                elif complexity < 0.7:
                    st.warning("🟡 보통")
                else:
                    st.error("🔴 복잡")
        
        with tab3:
            st.markdown("**🔍 추출된 키워드**")
            keywords = st.session_state.case_analysis['keywords']
            
            if keywords:
                # 키워드를 태그 형태로 표시
                keyword_html = ""
                for keyword in keywords:
                    keyword_html += f'<span style="background-color: #e1f5fe; padding: 2px 8px; margin: 2px; border-radius: 12px; font-size: 12px;">{keyword}</span> '
                
                st.markdown(keyword_html, unsafe_allow_html=True)
            else:
                st.write("키워드를 추출하지 못했습니다.")
        
        with tab4:
            st.markdown("**📋 주요 사실**")
            for fact in analysis.get('key_facts', []):
                st.write(f"• {fact}")
            
            st.markdown("**💔 피해 내용**")
            for damage in analysis.get('victim_damages', []):
                st.write(f"• {damage}")
            
            st.markdown("**📑 필요한 증거**")
            for evidence in analysis.get('evidence_needed', []):
                st.write(f"• {evidence}")

def show_precedent_search(law_api, openai_api, text_analyzer):
    """판례 검색 페이지"""
    st.header("🔍 판례 검색")
    
    # 검색 방법 선택
    search_method = st.radio(
        "검색 방법",
        ["🔍 키워드 검색", "🎯 사건 기반 검색", "📂 범죄 유형별 검색"]
    )
    
    search_query = ""
    
    if search_method == "🔍 키워드 검색":
        search_query = st.text_input(
            "검색 키워드 입력",
            placeholder="예: 사기죄, 명의도용, 위자료 등"
        )
    
    elif search_method == "🎯 사건 기반 검색":
        if st.session_state.case_analysis:
            st.success("✅ 분석된 사건을 기반으로 검색합니다.")
            
            # 분석된 사건에서 키워드 추출
            analysis = st.session_state.case_analysis['ai_analysis']
            keywords = analysis.get('keywords', [])
            crime_types = analysis.get('crime_types', [])
            
            # 검색 쿼리 구성
            search_query = ' '.join(keywords[:3] + crime_types[:2])
            
            st.info(f"🔍 검색 쿼리: {search_query}")
            
        else:
            st.warning("⚠️ 먼저 사건 분석을 진행해주세요.")
    
    elif search_method == "📂 범죄 유형별 검색":
        crime_type = st.selectbox(
            "범죄 유형 선택",
            ["사기", "절도", "강도", "폭행", "상해", "협박", "공갈", "모욕", "명예훼손", "음주운전", "도박"]
        )
        search_query = crime_type
    
    # 검색 옵션
    col1, col2 = st.columns(2)
    with col1:
        max_results = st.slider("최대 검색 결과 수", 5, 20, 10)
    with col2:
        sort_by = st.selectbox("정렬 기준", ["관련도", "날짜", "법원"])
    
    # 검색 실행
    if search_query and st.button("🔍 판례 검색"):
        with st.spinner("판례를 검색 중입니다..."):
            try:
                # 1. 국가법령정보센터 API에서 판례 검색
                precedents = law_api.search_precedents_with_openlaw_api(search_query, max_results)
                
                # 2. 국가법령정보센터에서 결과가 없으면 기존 API 사용
                if not precedents:
                    precedents = law_api.search_precedents(search_query, max_results)
                
                if precedents:
                    st.session_state.precedents = precedents
                    
                    # 검색 기록 저장
                    st.session_state.search_history.append({
                        'query': search_query,
                        'result_count': len(precedents),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    st.success(f"✅ {len(precedents)}개의 판례를 찾았습니다!")
                    
                    # 유사도 분석 (사건 분석이 있는 경우)
                    if st.session_state.case_analysis:
                        case_text = st.session_state.case_analysis['text']
                        
                        # 각 판례와 유사도 계산
                        for precedent in precedents:
                            prec_text = f"{precedent.get('title', '')} {precedent.get('summary', '')}"
                            similarity = text_analyzer.calculate_similarity(case_text, prec_text)
                            precedent['similarity'] = similarity
                        
                        # 유사도 순으로 정렬
                        precedents.sort(key=lambda x: x.get('similarity', 0), reverse=True)
                        st.session_state.precedents = precedents
                    
                else:
                    st.warning("⚠️ 검색 결과가 없습니다.")
                    
            except Exception as e:
                st.error(f"❌ 검색 중 오류가 발생했습니다: {e}")
    
    # 검색 결과 표시
    if st.session_state.precedents:
        st.markdown("---")
        st.subheader("📊 검색 결과")
        
        for i, precedent in enumerate(st.session_state.precedents, 1):
            with st.expander(f"📋 {i}. {precedent.get('title', '제목 없음')}", expanded=(i <= 3)):
                
                # 기본 정보
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**사건번호**: {precedent.get('case_number', '정보 없음')}")
                    st.write(f"**법원**: {precedent.get('court', '정보 없음')}")
                    st.write(f"**선고일자**: {precedent.get('date', '정보 없음')}")
                
                with col2:
                    st.write(f"**선고형량**: {precedent.get('sentence', '정보 없음')}")
                    st.write(f"**위자료**: {precedent.get('compensation', '정보 없음')}")
                    
                    # 유사도 표시
                    if 'similarity' in precedent:
                        similarity = precedent['similarity']
                        st.metric("유사도", f"{similarity:.2f}")
                
                # 요약
                if precedent.get('summary'):
                    st.markdown("**📝 요약**")
                    st.write(precedent['summary'])
                
                # 관련 조문
                if precedent.get('law_provisions'):
                    st.markdown("**⚖️ 관련 조문**")
                    st.write(precedent['law_provisions'])
                
                # AI 요약 버튼
                if st.button(f"🤖 AI 요약", key=f"summarize_{i}"):
                    with st.spinner("AI가 판례를 요약하고 있습니다..."):
                        try:
                            summary = openai_api.summarize_precedent(precedent)
                            st.markdown("**🤖 AI 요약**")
                            st.write(summary)
                        except Exception as e:
                            st.error(f"AI 요약 실패: {e}")

def show_legal_verification(law_api, openai_api):
    """법률 정보 검증 페이지"""
    st.header("✅ 법률 정보 검증")
    
    st.markdown("""
    판례 번호, 법률 조항, 법률 인용 등이 정확한지 확인해보세요.
    """)
    
    # 검증 방법 선택
    verification_type = st.selectbox(
        "검증 유형 선택",
        ["📋 판례 번호 검증", "📖 법률 조항 검증", "🔍 종합 법률 인용 검증", "🔎 키워드 법률 검색"]
    )
    
    st.markdown("---")
    
    if verification_type == "📋 판례 번호 검증":
        st.subheader("📋 판례 번호 검증")
        
        # 입력 예시
        st.info("📌 **입력 예시**: 2019도11772, 2022고합57, 2020도5432, 2021도3456")
        
        # AI 검색 옵션
        use_ai_search = st.checkbox(
            "🤖 AI 실시간 검색 사용 (OpenAI API 필요)",
            value=True,
            help="체크하면 로컬 데이터에 없는 판례도 AI를 통해 실시간으로 검색합니다."
        )
        
        case_number = st.text_input(
            "판례 번호를 입력하세요",
            placeholder="예: 2019도11772 또는 2022고합57"
        )
        
        if st.button("🔍 판례 번호 검증"):
            if case_number:
                if use_ai_search:
                    with st.spinner("AI를 사용하여 판례를 검색 중입니다... (시간이 조금 걸릴 수 있습니다)"):
                        result = law_api.verify_case_number(case_number, use_ai_search=True)
                else:
                    with st.spinner("로컬 데이터에서 판례를 검색 중입니다..."):
                        result = law_api.verify_case_number(case_number, use_ai_search=False)
                    
                    if result.get('exists'):
                        # 검색 소스 표시
                        if result.get('source') == '대법원 포털 API':
                            st.success(f"✅ 판례 번호 '{case_number}'가 존재합니다! 🏛️ (대법원 포털 API)")
                            st.info("💡 이 결과는 대법원 포털 API를 통해 검색된 공식 정보입니다.")
                        elif result.get('source') == 'AI 검색':
                            st.success(f"✅ 판례 번호 '{case_number}'가 존재합니다! 🤖 (AI 검색)")
                            st.info("💡 이 결과는 AI를 통해 실시간으로 검색된 정보입니다. 정확성을 위해 공식 법원 사이트에서도 확인해보세요.")
                        else:
                            st.success(f"✅ 판례 번호 '{case_number}'가 존재합니다! 📚 (로컬 데이터)")
                        
                        # 판례 정보 표시
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("법원", result.get('court', '정보 없음'))
                            st.metric("사건 유형", result.get('case_type', '정보 없음'))
                            st.metric("판결일", result.get('date', '정보 없음'))
                        
                        with col2:
                            st.metric("제목", result.get('title', '정보 없음'))
                            st.metric("판결 결과", result.get('verdict', '정보 없음'))
                            if result.get('source'):
                                st.metric("정보 출처", result.get('source', '정보 없음'))
                        
                        # 상세 정보
                        st.markdown("---")
                        st.subheader("📄 판례 상세 정보")
                        
                        st.markdown(f"**📋 사건 개요**")
                        st.write(result.get('summary', '정보 없음'))
                        
                        st.markdown(f"**🔍 주요 쟁점**")
                        st.write(result.get('main_issue', '정보 없음'))
                        
                        # 적용 법률
                        if result.get('applicable_law'):
                            st.markdown("**⚖️ 적용 법률**")
                            for law in result['applicable_law']:
                                st.write(f"• {law}")
                        
                        # 키워드
                        if result.get('keywords'):
                            st.markdown("**🏷️ 키워드**")
                            st.write(", ".join(result['keywords']))
                        
                    else:
                        if result.get('source') == '대법원 포털 API':
                            st.error(f"❌ 판례 번호 '{case_number}'를 대법원 포털 API에서 찾을 수 없습니다.")
                            st.warning("🏛️ 대법원 포털 API에서 해당 판례를 찾지 못했습니다. 판례 번호가 정확한지 확인하거나, 아래 공식 사이트에서 직접 검색해보세요.")
                        elif use_ai_search and result.get('source') == 'AI 검색':
                            st.error(f"❌ 판례 번호 '{case_number}'를 AI 검색에서도 찾을 수 없습니다.")
                            st.warning("🤖 AI 검색을 시도했지만 해당 판례를 찾지 못했습니다. 판례 번호가 정확한지 확인하거나, 아래 공식 사이트에서 직접 검색해보세요.")
                        else:
                            st.error(f"❌ 판례 번호 '{case_number}'를 로컬 데이터에서 찾을 수 없습니다.")
                            if not use_ai_search:
                                st.info("💡 AI 실시간 검색을 활성화하면 더 많은 판례를 찾을 수 있습니다.")
                        
                        st.write(result.get('message', '알 수 없는 오류'))
                        
                        if result.get('suggestion'):
                            st.info(f"💡 {result['suggestion']}")
                        
                        # 에러 정보 표시 (AI 검색 실패 시)
                        if result.get('error') and use_ai_search:
                            with st.expander("🔧 기술적 세부사항"):
                                st.write(f"오류 내용: {result['error']}")
                        
                        # 검색 링크 제공
                        if result.get('search_links'):
                            st.markdown("---")
                            st.subheader("🔍 직접 검색해보기")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown(f"[🏛️ 대법원 판례]({result['search_links']['대법원']})")
                            
                            with col2:
                                st.markdown(f"[📖 종합법률정보]({result['search_links']['종합법률정보']})")
                            
                            with col3:
                                st.markdown(f"[⚖️ 케이스노트]({result['search_links']['케이스노트']})")
            else:
                st.warning("⚠️ 판례 번호를 입력해주세요.")
    
    elif verification_type == "📖 법률 조항 검증":
        st.subheader("📖 법률 조항 검증")
        
        # 입력 예시
        st.info("📌 **입력 예시**: 형법 제243조, 민법 제750조, 정보통신망법 제44조의7")
        
        col1, col2 = st.columns(2)
        
        with col1:
            law_name = st.text_input(
                "법률명을 입력하세요",
                placeholder="예: 형법"
            )
        
        with col2:
            article_number = st.text_input(
                "조항 번호를 입력하세요",
                placeholder="예: 243 또는 44의7"
            )
        
        if st.button("🔍 법률 조항 검증"):
            if law_name and article_number:
                with st.spinner("법률 조항을 검증 중입니다..."):
                    result = law_api.get_law_article(law_name, article_number)
                    
                    if result.get('exists'):
                        st.success(f"✅ {law_name} 제{article_number}조가 존재합니다!")
                        
                        # 조항 정보 표시
                        st.markdown("---")
                        st.subheader("📜 조항 내용")
                        
                        st.markdown(f"**📋 조항명**: {result.get('title', '정보 없음')}")
                        st.markdown(f"**📖 조항 내용**")
                        st.write(result.get('content', '정보 없음'))
                        
                        # 분류 정보
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("대분류", result.get('category', '정보 없음'))
                        with col2:
                            st.metric("소분류", result.get('subcategory', '정보 없음'))
                        
                        # 관련 법률 검색
                        st.markdown("---")
                        st.subheader("🔗 관련 법률")
                        
                        law_reference = f"{law_name} 제{article_number}조"
                        related_laws = law_api.get_related_laws(law_reference)
                        
                        if related_laws:
                            for related in related_laws:
                                with st.expander(f"📖 {related['law_name']} 제{related['article']}조 - {related['title']}"):
                                    st.write(f"**관련성**: {related['relation']}")
                        else:
                            st.info("관련 법률 정보가 없습니다.")
                        
                    else:
                        st.error(f"❌ {law_name} 제{article_number}조를 찾을 수 없습니다.")
                        st.write(result.get('message', '알 수 없는 오류'))
            else:
                st.warning("⚠️ 법률명과 조항 번호를 모두 입력해주세요.")
    
    elif verification_type == "🔍 종합 법률 인용 검증":
        st.subheader("🔍 종합 법률 인용 검증")
        
        # 입력 예시
        st.info("📌 **입력 예시**: 형법 제243조, 대법원 2019도11772")
        
        citation = st.text_input(
            "법률 인용을 입력하세요",
            placeholder="예: 형법 제243조 또는 대법원 2019도11772"
        )
        
        if st.button("🔍 법률 인용 검증"):
            if citation:
                with st.spinner("법률 인용을 검증 중입니다..."):
                    result = law_api.validate_legal_citation(citation)
                    
                    if result.get('is_valid'):
                        st.success(f"✅ '{citation}' 인용이 올바릅니다!")
                        
                        # 인용 유형별 정보 표시
                        citation_type = result.get('type')
                        details = result.get('details', {})
                        
                        st.markdown("---")
                        st.subheader("📋 인용 정보")
                        
                        if citation_type == "law_article":
                            st.markdown(f"**📖 유형**: 법률 조항")
                            st.markdown(f"**📋 법률명**: {details.get('law_name', '정보 없음')}")
                            st.markdown(f"**📄 조항번호**: {details.get('article_number', '정보 없음')}")
                            st.markdown(f"**📜 조항명**: {details.get('title', '정보 없음')}")
                            st.markdown(f"**📖 내용**:")
                            st.write(details.get('content', '정보 없음'))
                            
                        elif citation_type == "case_number":
                            st.markdown(f"**📋 유형**: 판례 번호")
                            st.markdown(f"**🏛️ 법원**: {details.get('court', '정보 없음')}")
                            st.markdown(f"**📅 연도**: {details.get('year', '정보 없음')}")
                            st.markdown(f"**📋 사건유형**: {details.get('case_type', '정보 없음')}")
                            st.markdown(f"**📄 제목**: {details.get('title', '정보 없음')}")
                            st.markdown(f"**📖 요약**:")
                            st.write(details.get('summary', '정보 없음'))
                        
                    else:
                        st.error(f"❌ '{citation}' 인용을 확인할 수 없습니다.")
                        st.write(result.get('details', {}).get('error', '알 수 없는 오류'))
                        
                        # 형식 안내
                        st.markdown("---")
                        st.subheader("📝 올바른 형식")
                        st.markdown("""
                        **판례 번호**: 2019도11772, 2020도5432
                        **법률 조항**: 형법 제243조, 민법 제750조
                        """)
            else:
                st.warning("⚠️ 법률 인용을 입력해주세요.")
    
    elif verification_type == "🔎 키워드 법률 검색":
        st.subheader("🔎 키워드 법률 검색")
        
        col1, col2 = st.columns(2)
        
        with col1:
            keyword = st.text_input(
                "검색 키워드를 입력하세요",
                placeholder="예: 음란물, 사기, 불법행위"
            )
        
        with col2:
            law_type = st.selectbox(
                "법률 유형 선택",
                ["all", "criminal", "civil", "administrative"],
                format_func=lambda x: {"all": "전체", "criminal": "형사법", "civil": "민사법", "administrative": "행정법"}[x]
            )
        
        if st.button("🔍 법률 검색"):
            if keyword:
                with st.spinner("관련 법률을 검색 중입니다..."):
                    results = law_api.search_law_by_keyword(keyword, law_type)
                    
                    if results:
                        st.success(f"✅ '{keyword}' 관련 법률 {len(results)}개를 찾았습니다!")
                        
                        for i, law in enumerate(results):
                            with st.expander(f"📖 {law['law_name']} 제{law['article']}조 - {law['title']}"):
                                st.markdown(f"**📋 법률명**: {law['law_name']}")
                                st.markdown(f"**📄 조항**: 제{law['article']}조")
                                st.markdown(f"**📜 제목**: {law['title']}")
                                st.markdown(f"**📖 내용**:")
                                st.write(law['content'])
                                st.markdown(f"**🏷️ 유형**: {law['type']}")
                                st.markdown(f"**🔖 키워드**: {', '.join(law['keywords'])}")
                    else:
                        st.warning(f"⚠️ '{keyword}' 관련 법률을 찾을 수 없습니다.")
                        st.info("💡 다른 키워드로 검색해보세요.")
            else:
                st.warning("⚠️ 검색 키워드를 입력해주세요.")
    
    # 사용 팁
    st.markdown("---")
    st.subheader("💡 사용 팁")
    
    with st.expander("📋 판례 번호 형식 안내"):
        st.markdown("""
        **판례 번호 형식**: YYYY + 사건유형 + 번호
        - **연도**: 4자리 (예: 2019, 2020, 2022)
        - **사건유형**: 
          - 도(형사), 바(행정), 노(민사), 마(가사)
          - 고합(중죄), 고단(단독), 합(합의), 단(단독)
          - 초기, 재, 전, 누, 구, 나, 가 등
        - **번호**: 순서 번호 (예: 11772, 57, 5432)
        
        **예시**:
        - 2019도11772 (2019년 형사 11772번)
        - 2022고합57 (2022년 합의부 중죄 57번)
        - 2020바5432 (2020년 행정 5432번)
        - 2021고단123 (2021년 단독 123번)
        """)
    
    with st.expander("📖 법률 조항 검색 안내"):
        st.markdown("""
        **지원하는 법률**:
        - 형법 (제243조, 제347조 등)
        - 민법 (제750조 등)
        - 정보통신망법 (제44조의7 등)
        
        **입력 형식**:
        - 법률명: 형법, 민법, 정보통신망법 등
        - 조항번호: 243, 347, 44의7 등
        """)

def show_comprehensive_report(openai_api):
    """종합 리포트 페이지"""
    st.header("📊 종합 리포트")
    
    if not st.session_state.case_analysis:
        st.warning("⚠️ 먼저 사건 분석을 진행해주세요.")
        return
    
    if not st.session_state.precedents:
        st.warning("⚠️ 먼저 판례 검색을 진행해주세요.")
        return
    
    # 리포트 생성
    if st.button("📋 종합 리포트 생성"):
        with st.spinner("종합 리포트를 생성 중입니다..."):
            try:
                case_text = st.session_state.case_analysis['text']
                analysis = st.session_state.case_analysis['ai_analysis']
                precedents = st.session_state.precedents[:5]  # 상위 5개 판례만 사용
                
                # 종합 리포트 생성
                report = openai_api.generate_report(case_text, precedents, analysis)
                
                # 형량 예측
                punishment_prediction = openai_api.estimate_punishment(analysis, precedents)
                
                st.success("✅ 종합 리포트가 생성되었습니다!")
                
                # 리포트 표시
                st.markdown("---")
                st.markdown(report)
                
                # 형량 예측 표시
                st.markdown("---")
                st.subheader("⚖️ 형량 예측")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("최소 예상 형량", punishment_prediction.get('min_punishment', '예측 불가'))
                
                with col2:
                    st.metric("최대 예상 형량", punishment_prediction.get('max_punishment', '예측 불가'))
                
                with col3:
                    st.metric("가장 가능성 높은 형량", punishment_prediction.get('most_likely', '예측 불가'))
                
                # 신뢰도 표시
                confidence = punishment_prediction.get('confidence', '0')
                st.progress(int(confidence) / 100)
                st.write(f"예측 신뢰도: {confidence}%")
                
                # 영향 요인들
                if punishment_prediction.get('factors'):
                    st.markdown("**📊 형량 영향 요인**")
                    for factor in punishment_prediction['factors']:
                        st.write(f"• {factor}")
                
                # 감경/가중 요인
                col1, col2 = st.columns(2)
                
                with col1:
                    if punishment_prediction.get('mitigation_factors'):
                        st.markdown("**🟢 감경 요인**")
                        for factor in punishment_prediction['mitigation_factors']:
                            st.write(f"• {factor}")
                
                with col2:
                    if punishment_prediction.get('aggravation_factors'):
                        st.markdown("**🔴 가중 요인**")
                        for factor in punishment_prediction['aggravation_factors']:
                            st.write(f"• {factor}")
                
                # 다운로드 버튼
                st.markdown("---")
                
                # 리포트 텍스트 생성
                full_report = f"""
판례 검색 & 사건 분석 리포트
==============================

생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{report}

형량 예측 결과:
- 최소 예상 형량: {punishment_prediction.get('min_punishment', '예측 불가')}
- 최대 예상 형량: {punishment_prediction.get('max_punishment', '예측 불가')}
- 가장 가능성 높은 형량: {punishment_prediction.get('most_likely', '예측 불가')}
- 예측 신뢰도: {confidence}%

"""
                
                st.download_button(
                    label="📥 리포트 다운로드",
                    data=full_report,
                    file_name=f"case_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ 리포트 생성 중 오류가 발생했습니다: {e}")

def show_settings():
    """설정 페이지"""
    st.header("⚙️ 설정")
    
    # API 키 설정
    st.subheader("🔑 API 키 설정")
    
    # OpenAI API 키
    openai_key = st.text_input(
        "OpenAI API 키",
        type="password",
        value="*" * 20 if Config.OPENAI_API_KEY else "",
        help="OpenAI API 키를 입력하세요."
    )
    
    # 법령 정보 API 키
    law_key = st.text_input(
        "법령 정보 API 키",
        type="password",
        value="*" * 20 if Config.LAWINFO_API_KEY else "",
        help="법령 정보 서비스 API 키를 입력하세요."
    )
    
    # 모델 설정
    st.subheader("🤖 모델 설정")
    
    model_name = st.selectbox(
        "OpenAI 모델 선택",
        ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
        index=0
    )
    
    temperature = st.slider(
        "Temperature (창의성)",
        0.0, 1.0, 0.7, 0.1
    )
    
    max_tokens = st.slider(
        "최대 토큰 수",
        1000, 8000, 4000, 500
    )
    
    # 검색 설정
    st.subheader("🔍 검색 설정")
    
    max_search_results = st.slider(
        "최대 검색 결과 수",
        5, 50, 10, 5
    )
    
    similarity_threshold = st.slider(
        "유사도 임계값",
        0.0, 1.0, 0.7, 0.1
    )
    
    # 파일 업로드 설정
    st.subheader("📁 파일 업로드 설정")
    
    max_file_size = st.slider(
        "최대 파일 크기 (MB)",
        1, 50, 10, 1
    )
    
    # 저장 버튼
    if st.button("💾 설정 저장"):
        st.success("✅ 설정이 저장되었습니다!")
        st.info("ℹ️ 일부 설정은 애플리케이션을 재시작해야 적용됩니다.")
    
    # 시스템 정보
    st.markdown("---")
    st.subheader("📊 시스템 정보")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**현재 설정**")
        st.write(f"• 모델: {Config.OPENAI_MODEL}")
        st.write(f"• 최대 토큰: {Config.MAX_TOKENS}")
        st.write(f"• Temperature: {Config.TEMPERATURE}")
    
    with col2:
        st.write("**세션 상태**")
        st.write(f"• 사건 분석 완료: {'✅' if st.session_state.case_analysis else '❌'}")
        st.write(f"• 판례 검색 완료: {'✅' if st.session_state.precedents else '❌'}")
        st.write(f"• 검색 기록: {len(st.session_state.search_history)}개")
    
    # 데이터 소스 정보
    st.markdown("---")
    st.subheader("🔍 현재 데이터 소스")
    
    data_sources = Config.get_data_sources()
    for i, source in enumerate(data_sources, 1):
        if "OpenAI" in source:
            st.write(f"{i}. 🤖 {source}")
        elif "국가법령정보센터" in source:
            st.write(f"{i}. 🏛️ {source}")
        elif "로컬" in source:
            st.write(f"{i}. 📚 {source}")
        else:
            st.write(f"{i}. 🔗 {source}")
    
    # API 연결 상태
    st.markdown("---")
    st.subheader("📡 API 연결 상태")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # OpenAI API 상태
        openai_status = "✅ 연결됨" if Config.is_api_configured("openai") else "❌ 미연결"
        st.write(f"**OpenAI API**: {openai_status}")
        
        # 국가법령정보센터 API 상태
        law_status = "✅ 연결됨" if Config.is_api_configured("law") else "❌ 미연결"
        st.write(f"**국가법령정보센터**: {law_status}")
    
    with col2:
        # 판례검색 API 상태
        case_status = "✅ 연결됨" if Config.is_api_configured("case_search") else "❌ 미연결"
        st.write(f"**판례검색 API**: {case_status}")
        
        # 카카오 API 상태
        kakao_status = "✅ 연결됨" if Config.is_api_configured("kakao") else "❌ 미연결"
        st.write(f"**카카오 API**: {kakao_status}")
    
    # API 설정 안내
    if not Config.is_api_configured("openai"):
        st.warning("⚠️ OpenAI API가 설정되지 않았습니다. env_template.txt 파일을 참고하여 .env 파일을 설정하세요.")
        
        with st.expander("🔧 API 설정 방법"):
            st.markdown("""
            **1. env_template.txt 파일을 .env로 복사**
            ```bash
            copy env_template.txt .env
            ```
            
            **2. .env 파일에서 API 키 설정**
            - OPENAI_API_KEY: OpenAI API 키 (필수)
            - LAW_API_KEY: 국가법령정보센터 API 키 (선택)
            - CASE_SEARCH_API_KEY: 판례검색 API 키 (선택)
            - KAKAO_REST_API_KEY: 카카오 API 키 (선택)
            
            **3. 애플리케이션 재시작**
            """)

if __name__ == "__main__":
    main() 