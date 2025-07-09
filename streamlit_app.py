# Streamlit 클라우드 배포를 위한 진입점 파일
import streamlit as st
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 메인 애플리케이션 실행
if __name__ == "__main__":
    # app.py의 main 함수 실행
    from app import main
    main() 