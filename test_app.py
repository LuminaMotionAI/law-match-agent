#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
판례 검색 & 사건 분석 에이전트 테스트 스크립트
"""

import sys
import os
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """설정 모듈 테스트"""
    print("🔧 설정 모듈 테스트...")
    try:
        from config import Config
        print("✅ Config 모듈 임포트 성공")
        
        # 설정 검증
        if Config.OPENAI_API_KEY:
            print("✅ OpenAI API 키 설정됨")
        else:
            print("⚠️ OpenAI API 키가 설정되지 않음")
        
        print(f"📋 설정값:")
        print(f"  - 모델: {Config.OPENAI_MODEL}")
        print(f"  - 최대 토큰: {Config.MAX_TOKENS}")
        print(f"  - 온도: {Config.TEMPERATURE}")
        print(f"  - 최대 검색 결과: {Config.MAX_SEARCH_RESULTS}")
        
        return True
        
    except Exception as e:
        print(f"❌ 설정 모듈 테스트 실패: {e}")
        return False

def test_api_modules():
    """API 모듈 테스트"""
    print("\n🔌 API 모듈 테스트...")
    try:
        from api import LawAPI, OpenAIAPI
        print("✅ API 모듈 임포트 성공")
        
        # LawAPI 테스트
        law_api = LawAPI()
        print("✅ LawAPI 인스턴스 생성 성공")
        
        # OpenAI API 테스트 (키가 있는 경우만)
        from config import Config
        if Config.OPENAI_API_KEY:
            openai_api = OpenAIAPI()
            print("✅ OpenAI API 인스턴스 생성 성공")
            
            # 간단한 키워드 추출 테스트
            test_text = "이것은 간단한 테스트 텍스트입니다. 사기죄와 관련된 내용입니다."
            keywords = openai_api.extract_keywords(test_text)
            print(f"✅ 키워드 추출 테스트 완료: {keywords}")
        else:
            print("⚠️ OpenAI API 키가 없어 OpenAI API 테스트 생략")
        
        return True
        
    except Exception as e:
        print(f"❌ API 모듈 테스트 실패: {e}")
        return False

def test_utils_modules():
    """유틸리티 모듈 테스트"""
    print("\n🔨 유틸리티 모듈 테스트...")
    try:
        from utils import FileProcessor, TextAnalyzer
        print("✅ 유틸리티 모듈 임포트 성공")
        
        # FileProcessor 테스트
        file_processor = FileProcessor()
        print("✅ FileProcessor 인스턴스 생성 성공")
        
        # 간단한 파일 확장자 테스트
        test_files = ["test.txt", "test.pdf", "test.docx", "test.exe"]
        for file in test_files:
            is_allowed = file_processor.is_allowed_file(file)
            status = "✅" if is_allowed else "❌"
            print(f"  {status} {file}: {is_allowed}")
        
        # TextAnalyzer 테스트
        print("📊 TextAnalyzer 초기화 중...")
        text_analyzer = TextAnalyzer()
        print("✅ TextAnalyzer 인스턴스 생성 성공")
        
        # 간단한 텍스트 분석 테스트
        test_text = "이것은 사기죄와 관련된 테스트 문서입니다. 피고인은 허위 사실을 이용하여 피해자를 속였습니다."
        
        # 텍스트 전처리 테스트
        processed_text = text_analyzer.preprocess_text(test_text)
        print(f"✅ 텍스트 전처리 완료: {processed_text[:50]}...")
        
        # 법률 용어 추출 테스트
        legal_terms = text_analyzer.extract_legal_terms(test_text)
        print(f"✅ 법률 용어 추출 완료: {legal_terms}")
        
        # 텍스트 구조 분석 테스트
        structure = text_analyzer.analyze_text_structure(test_text)
        print(f"✅ 텍스트 구조 분석 완료: 단어 수 {structure.get('word_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 유틸리티 모듈 테스트 실패: {e}")
        return False

def test_dependencies():
    """의존성 모듈 테스트"""
    print("\n📦 의존성 모듈 테스트...")
    
    required_modules = [
        'streamlit',
        'openai',
        'requests',
        'beautifulsoup4',
        'python-dotenv',
        'pandas',
        'numpy',
        'xmltodict',
        'PyPDF2',
        'python-docx',
        'sentence-transformers',
        'faiss-cpu',
        'tiktoken'
    ]
    
    success_count = 0
    total_count = len(required_modules)
    
    for module in required_modules:
        try:
            if module == 'python-dotenv':
                import dotenv
            elif module == 'python-docx':
                import docx
            elif module == 'beautifulsoup4':
                import bs4
            elif module == 'sentence-transformers':
                import sentence_transformers
            elif module == 'faiss-cpu':
                import faiss
            else:
                __import__(module)
            
            print(f"✅ {module}")
            success_count += 1
            
        except ImportError:
            print(f"❌ {module} - 설치 필요")
    
    print(f"\n📊 의존성 테스트 결과: {success_count}/{total_count} 성공")
    return success_count == total_count

def test_streamlit_app():
    """Streamlit 앱 테스트"""
    print("\n🌐 Streamlit 앱 테스트...")
    try:
        import streamlit as st
        print("✅ Streamlit 임포트 성공")
        
        # app.py 파일 존재 확인
        if os.path.exists("app.py"):
            print("✅ app.py 파일 존재")
            
            # 기본 구문 검사
            with open("app.py", "r", encoding="utf-8") as f:
                content = f.read()
            
            if "def main():" in content:
                print("✅ 메인 함수 존재")
            
            if "st.title" in content:
                print("✅ Streamlit 컴포넌트 사용 확인")
            
            print("💡 앱 실행 방법: streamlit run app.py")
            return True
        else:
            print("❌ app.py 파일이 없습니다")
            return False
            
    except Exception as e:
        print(f"❌ Streamlit 앱 테스트 실패: {e}")
        return False

def test_directory_structure():
    """디렉토리 구조 테스트"""
    print("\n📁 디렉토리 구조 테스트...")
    
    required_dirs = ["api", "utils", "models", "uploads"]
    required_files = ["app.py", "config.py", "requirements.txt", "README.md"]
    
    # 디렉토리 확인
    for dir_name in required_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            print(f"✅ {dir_name}/ 디렉토리 존재")
        else:
            print(f"❌ {dir_name}/ 디렉토리 없음")
    
    # 파일 확인
    for file_name in required_files:
        if os.path.exists(file_name) and os.path.isfile(file_name):
            print(f"✅ {file_name} 파일 존재")
        else:
            print(f"❌ {file_name} 파일 없음")
    
    return True

def run_all_tests():
    """모든 테스트 실행"""
    print("🚀 판례 검색 & 사건 분석 에이전트 테스트 시작")
    print("=" * 50)
    
    tests = [
        ("디렉토리 구조", test_directory_structure),
        ("의존성 모듈", test_dependencies),
        ("설정 모듈", test_config),
        ("API 모듈", test_api_modules),
        ("유틸리티 모듈", test_utils_modules),
        ("Streamlit 앱", test_streamlit_app),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 오류 발생: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    success_count = 0
    for test_name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{status} {test_name}")
        if result:
            success_count += 1
    
    print(f"\n🎯 전체 결과: {success_count}/{len(tests)} 테스트 통과")
    
    if success_count == len(tests):
        print("🎉 모든 테스트가 성공했습니다! 애플리케이션을 실행할 준비가 되었습니다.")
        print("📝 실행 방법:")
        print("   1. .env 파일에 OpenAI API 키를 설정하세요")
        print("   2. streamlit run app.py 명령어로 앱을 실행하세요")
        print("   3. 브라우저에서 http://localhost:8501 에 접속하세요")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 위의 오류 메시지를 확인하고 필요한 설정을 완료하세요.")
    
    return success_count == len(tests)

if __name__ == "__main__":
    print(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = run_all_tests()
    print(f"테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 종료 코드 설정
    sys.exit(0 if success else 1) 