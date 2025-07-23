# Streamlit 클라우드 배포를 위한 진입점 파일
import streamlit as st
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 🔧 수정: 가벼운 버전의 앱 사용
# 허깅페이스 없이 로컬 데이터를 사용하는 버전
import app_lightweight

# main() 함수 실행
if __name__ == "__main__":
    app_lightweight.main() 