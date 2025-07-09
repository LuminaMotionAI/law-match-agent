import os
from dotenv import load_dotenv
import streamlit as st

# .env 파일 로드
load_dotenv()

# Streamlit secrets 지원
def get_secret(key, default=""):
    """환경변수 또는 Streamlit secrets에서 값을 가져오는 함수"""
    # 1. 환경변수에서 확인
    value = os.getenv(key, default)
    
    # 2. Streamlit secrets에서 확인 (Streamlit 클라우드 배포 시)
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            value = st.secrets[key]
    except:
        pass
    
    return value

class Config:
    # OpenAI API 설정
    OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-4"
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7
    
    # 국가법령정보센터 API 설정
    LAW_API_KEY = get_secret("LAW_API_KEY", "")
    LAW_API_URL = get_secret("LAW_API_URL", "https://www.law.go.kr/DRF/lawService.do")
    
    # 판례검색 API 설정
    CASE_SEARCH_API_KEY = get_secret("CASE_SEARCH_API_KEY", "")
    CASE_SEARCH_API_URL = get_secret("CASE_SEARCH_API_URL", "https://www.law.go.kr/DRF/precService.do")
    
    # 카카오 API 설정 (주소 검색용)
    KAKAO_REST_API_KEY = get_secret("KAKAO_REST_API_KEY", "")
    
    # 대법원 관련 API (레거시)
    SUPREME_COURT_API_URL = "https://www.courtnet.go.kr/OpenAPI/"
    SCOURT_API_KEY = get_secret("SCOURT_API_KEY", "")
    
    # 레거시 호환성
    LAWINFO_API_KEY = LAW_API_KEY
    LAWINFO_API_URL = LAW_API_URL
    
    # 서버 설정
    STREAMLIT_SERVER_PORT = int(get_secret("STREAMLIT_SERVER_PORT", "8501"))
    STREAMLIT_SERVER_HOST = get_secret("STREAMLIT_SERVER_HOST", "localhost")
    
    # 검색 설정
    MAX_SEARCH_RESULTS = 10
    SIMILARITY_THRESHOLD = 0.7
    
    # 파일 업로드 설정
    UPLOAD_FOLDER = "uploads"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}
    
    # 기타 설정
    DEBUG = get_secret("DEBUG", "false").lower() == "true"
    LOG_LEVEL = get_secret("LOG_LEVEL", "INFO")
    DATABASE_URL = get_secret("DATABASE_URL", "sqlite:///law_match.db")
    
    @staticmethod
    def get_api_key(service):
        """API 키를 안전하게 가져오는 메서드"""
        api_keys = {
            "openai": Config.OPENAI_API_KEY,
            "lawinfo": Config.LAW_API_KEY,
            "law": Config.LAW_API_KEY,
            "case_search": Config.CASE_SEARCH_API_KEY,
            "kakao": Config.KAKAO_REST_API_KEY,
            "scourt": Config.SCOURT_API_KEY
        }
        return api_keys.get(service)
    
    @staticmethod
    def is_api_configured(service):
        """API가 설정되었는지 확인"""
        api_key = Config.get_api_key(service)
        return api_key and api_key.startswith("sk-") if service == "openai" else (api_key and len(api_key) > 10)
    
    @staticmethod
    def get_data_sources():
        """현재 설정된 데이터 소스 목록 반환"""
        sources = ["로컬 데이터베이스"]
        
        if Config.is_api_configured("openai"):
            sources.append("OpenAI API (실시간 검색)")
        
        if Config.is_api_configured("law"):
            sources.append("국가법령정보센터 API")
            
        if Config.is_api_configured("case_search"):
            sources.append("판례검색 API")
            
        if Config.is_api_configured("kakao"):
            sources.append("카카오 로컬 API")
            
        return sources
    
    @staticmethod
    def validate_config():
        """필수 설정 검증"""
        if not Config.OPENAI_API_KEY:
            raise ValueError("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        
        if not Config.is_api_configured("openai"):
            raise ValueError("❌ OpenAI API 키가 올바르지 않습니다.")
            
        return True 