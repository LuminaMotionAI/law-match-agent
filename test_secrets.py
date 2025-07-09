import streamlit as st
import os

st.title("🔑 Secrets 테스트 앱")

st.subheader("Secrets 상태 확인")

# 1. 환경변수에서 확인
env_key = os.getenv("OPENAI_API_KEY", "")
st.write(f"**환경변수**: {'✅ 있음' if env_key else '❌ 없음'}")

# 2. Streamlit secrets에서 확인
try:
    secrets_key = st.secrets.get("OPENAI_API_KEY", "")
    st.write(f"**Streamlit Secrets**: {'✅ 있음' if secrets_key else '❌ 없음'}")
    
    if secrets_key:
        # 키의 일부만 표시 (보안상)
        masked_key = secrets_key[:10] + "..." + secrets_key[-10:] if len(secrets_key) > 20 else "짧은 키"
        st.write(f"**키 확인**: {masked_key}")
        
    # LAW_OC_CODE도 확인
    law_oc = st.secrets.get("LAW_OC_CODE", "")
    st.write(f"**LAW_OC_CODE**: {law_oc if law_oc else '❌ 없음'}")
    
except Exception as e:
    st.error(f"Secrets 접근 오류: {e}")

st.subheader("전체 Secrets 키 목록")
try:
    available_keys = list(st.secrets.keys())
    st.write(f"**사용 가능한 키들**: {available_keys}")
except Exception as e:
    st.error(f"키 목록 확인 오류: {e}")

st.markdown("---")
st.info("이 테스트가 성공하면 메인 앱도 작동해야 합니다!") 