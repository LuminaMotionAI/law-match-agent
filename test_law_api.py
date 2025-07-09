#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
법률 API 테스트 스크립트
민법 제750조 검색 문제를 진단합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.law_api import LawAPI

def test_law_article_search():
    """법률 조항 검색 테스트"""
    print("🔍 법률 조항 검색 테스트 시작...")
    
    # LawAPI 초기화
    try:
        law_api = LawAPI()
        print("✅ LawAPI 초기화 성공")
    except Exception as e:
        print(f"❌ LawAPI 초기화 실패: {e}")
        return False
    
    # 민법 제750조 검색 테스트
    print("\n📖 민법 제750조 검색 중...")
    
    try:
        result = law_api.get_law_article("민법", "750")
        print(f"📊 검색 결과: {result}")
        
        if result.get('exists'):
            print("✅ 민법 제750조 검색 성공!")
            print(f"📋 조항명: {result.get('title')}")
            print(f"📖 내용: {result.get('content')}")
            print(f"🏷️ 법령번호: {result.get('law_number')}")
            return True
        else:
            print("❌ 민법 제750조 검색 실패!")
            print(f"💬 메시지: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ 검색 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_laws():
    """여러 법률 조항 테스트"""
    print("\n🔍 여러 법률 조항 테스트 시작...")
    
    law_api = LawAPI()
    
    test_cases = [
        ("민법", "750"),
        ("형법", "243"),
        ("형법", "347"),
        ("정보통신망법", "44의7")
    ]
    
    results = {}
    
    for law_name, article_number in test_cases:
        print(f"\n📖 {law_name} 제{article_number}조 검색...")
        try:
            result = law_api.get_law_article(law_name, article_number)
            results[f"{law_name}_{article_number}"] = result
            
            if result.get('exists'):
                print(f"✅ {law_name} 제{article_number}조 - {result.get('title')}")
            else:
                print(f"❌ {law_name} 제{article_number}조 - {result.get('message')}")
                
        except Exception as e:
            print(f"❌ {law_name} 제{article_number}조 검색 중 오류: {e}")
            results[f"{law_name}_{article_number}"] = {"error": str(e)}
    
    return results

def main():
    """메인 테스트 함수"""
    print("🚀 법률 API 종합 테스트 시작")
    print("=" * 50)
    
    # 1. 민법 제750조 단일 테스트
    success = test_law_article_search()
    
    # 2. 여러 법률 조항 테스트
    results = test_multiple_laws()
    
    # 3. 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    if success:
        print("✅ 민법 제750조 검색: 성공")
    else:
        print("❌ 민법 제750조 검색: 실패 - 이것이 주요 문제입니다!")
    
    success_count = 0
    total_count = len(results)
    
    for test_name, result in results.items():
        if result.get('exists'):
            print(f"✅ {test_name.replace('_', ' 제')}조: 성공")
            success_count += 1
        else:
            print(f"❌ {test_name.replace('_', ' 제')}조: 실패")
    
    print(f"\n📈 성공률: {success_count}/{total_count} ({(success_count/total_count*100):.1f}%)")
    
    if success_count < total_count:
        print("\n🔧 개선 필요 사항:")
        print("- 법률 데이터베이스 확장")
        print("- API 연결 개선") 
        print("- 실시간 법률 검색 API 연동")

if __name__ == "__main__":
    main() 