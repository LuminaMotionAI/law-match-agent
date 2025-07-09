# Streamlit 클라우드 배포를 위한 진입점 파일
import streamlit as st
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 🔧 수정: app 모듈을 import하고 main() 함수 실행
# app.py 전체를 import하여 세션 상태 초기화가 포함되도록 함
import app

# main() 함수 실행
app.main() 