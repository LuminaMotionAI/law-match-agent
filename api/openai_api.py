import openai
from typing import List, Dict, Optional, Tuple
from config import Config
import json
import tiktoken

class OpenAIAPI:
    """OpenAI API를 사용한 법률 문서 분석 클래스"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.get_api_key("openai"))
        self.model = Config.OPENAI_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
    
    def get_completion(self, prompt: str, temperature: float = None) -> str:
        """
        간단한 completion을 위한 메서드
        
        Args:
            prompt: 요청할 프롬프트
            temperature: 온도 설정 (기본값: 클래스 기본값)
            
        Returns:
            AI 응답 텍스트
        """
        try:
            temp = temperature if temperature is not None else self.temperature
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=temp
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI completion 오류: {e}")
            return f"API 요청 실패: {e}"
        
    def summarize_precedent(self, precedent: Dict) -> str:
        """
        판례를 요약하는 메서드
        
        Args:
            precedent: 판례 정보 딕셔너리
            
        Returns:
            요약된 판례 문자열
        """
        try:
            prompt = f"""
다음 판례를 요약해주세요. 핵심 내용을 포함하여 간결하게 정리해주세요.

판례명: {precedent.get('title', '')}
사건번호: {precedent.get('case_number', '')}
법원: {precedent.get('court', '')}
선고일자: {precedent.get('date', '')}
요약: {precedent.get('summary', '')}
전문: {precedent.get('full_text', '')[:2000]}...
관련조문: {precedent.get('law_provisions', '')}
선고형량: {precedent.get('sentence', '')}

다음 형식으로 요약해주세요:
1. 사건 개요
2. 적용 법령
3. 판결 결과 (형량)
4. 주요 쟁점
5. 판결 의미
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"판례 요약 오류: {e}")
            return "요약 생성에 실패했습니다."
    
    def analyze_case(self, case_text: str) -> Dict:
        """
        사건을 분석하여 핵심 요소를 추출하는 메서드
        
        Args:
            case_text: 사건 설명 텍스트
            
        Returns:
            분석 결과 딕셔너리
        """
        try:
            prompt = f"""
다음 사건을 분석하여 핵심 요소를 추출해주세요:

사건 내용:
{case_text}

다음 JSON 형식으로 분석 결과를 제공해주세요:
{{
    "crime_types": ["추정되는 범죄 유형들"],
    "key_facts": ["주요 사실들"],
    "applicable_laws": ["적용 가능한 법령들"],
    "keywords": ["검색에 유용한 키워드들"],
    "victim_damages": ["피해 내용"],
    "evidence_needed": ["필요한 증거들"],
    "estimated_punishment": "예상 형량",
    "case_severity": "경중 판단 (경미/보통/중대)"
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"사건 분석 오류: {e}")
            return {
                "crime_types": [],
                "key_facts": [],
                "applicable_laws": [],
                "keywords": [],
                "victim_damages": [],
                "evidence_needed": [],
                "estimated_punishment": "분석 불가",
                "case_severity": "판단 불가"
            }
    
    def compare_cases(self, my_case: str, precedent: Dict) -> Dict:
        """
        내 사건과 판례를 비교하는 메서드
        
        Args:
            my_case: 내 사건 설명
            precedent: 판례 정보
            
        Returns:
            비교 결과 딕셔너리
        """
        try:
            prompt = f"""
다음 두 사건을 비교 분석해주세요:

내 사건:
{my_case}

판례:
- 판례명: {precedent.get('title', '')}
- 사건번호: {precedent.get('case_number', '')}
- 요약: {precedent.get('summary', '')}
- 선고형량: {precedent.get('sentence', '')}
- 관련조문: {precedent.get('law_provisions', '')}

다음 JSON 형식으로 비교 결과를 제공해주세요:
{{
    "similarity_score": "유사도 점수 (0-100)",
    "similarities": ["유사한 점들"],
    "differences": ["차이점들"],
    "applicable_precedent": "이 판례가 적용 가능한지 여부 (true/false)",
    "expected_outcome": "예상 결과",
    "legal_reasoning": "법적 근거",
    "recommendations": ["권고사항들"]
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"사건 비교 오류: {e}")
            return {
                "similarity_score": "0",
                "similarities": [],
                "differences": [],
                "applicable_precedent": False,
                "expected_outcome": "분석 불가",
                "legal_reasoning": "분석 실패",
                "recommendations": []
            }
    
    def generate_report(self, my_case: str, precedents: List[Dict], analysis: Dict) -> str:
        """
        종합 리포트를 생성하는 메서드
        
        Args:
            my_case: 내 사건 설명
            precedents: 관련 판례 리스트
            analysis: 사건 분석 결과
            
        Returns:
            종합 리포트 문자열
        """
        try:
            precedent_summaries = []
            for i, prec in enumerate(precedents[:3], 1):
                summary = f"""
판례 {i}:
- 판례명: {prec.get('title', '')}
- 사건번호: {prec.get('case_number', '')}
- 선고형량: {prec.get('sentence', '')}
- 요약: {prec.get('summary', '')[:200]}...
"""
                precedent_summaries.append(summary)
            
            prompt = f"""
다음 정보를 바탕으로 종합 분석 리포트를 작성해주세요:

내 사건:
{my_case}

사건 분석 결과:
- 추정 범죄 유형: {', '.join(analysis.get('crime_types', []))}
- 적용 가능한 법령: {', '.join(analysis.get('applicable_laws', []))}
- 예상 형량: {analysis.get('estimated_punishment', '')}
- 사건 경중: {analysis.get('case_severity', '')}

관련 판례들:
{''.join(precedent_summaries)}

다음 구조로 리포트를 작성해주세요:

# 🔍 사건 분석 결과

## 📋 사건 개요
[사건의 핵심 내용 요약]

## ⚖️ 적용 가능한 법령
[관련 법령들과 해당 조항들]

## 📊 유사 판례 분석
[각 판례별 유사도와 시사점]

## 🎯 예상 결과
[형량 예측과 근거]

## 💡 법적 조언
[권고사항과 대응 방안]

## 📈 위자료 관련
[위자료 청구 가능성과 예상 금액]

리포트는 구체적이고 실용적으로 작성해주세요.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"리포트 생성 오류: {e}")
            return "리포트 생성에 실패했습니다."
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        텍스트에서 법률 관련 키워드를 추출하는 메서드
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            키워드 리스트
        """
        try:
            prompt = f"""
다음 텍스트에서 법률 검색에 유용한 키워드들을 추출해주세요:

{text}

범죄 유형, 법령, 행위, 피해 등과 관련된 키워드를 JSON 배열 형태로 제공해주세요:
["키워드1", "키워드2", "키워드3", ...]
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            
            keywords = json.loads(response.choices[0].message.content)
            return keywords
            
        except Exception as e:
            print(f"키워드 추출 오류: {e}")
            return []
    
    def estimate_punishment(self, case_analysis: Dict, precedents: List[Dict]) -> Dict:
        """
        형량을 예측하는 메서드
        
        Args:
            case_analysis: 사건 분석 결과
            precedents: 관련 판례 리스트
            
        Returns:
            형량 예측 결과
        """
        try:
            precedent_info = []
            for prec in precedents:
                if prec.get('sentence'):
                    precedent_info.append(f"사건: {prec.get('title', '')}, 형량: {prec.get('sentence', '')}")
            
            prompt = f"""
다음 정보를 바탕으로 형량을 예측해주세요:

사건 분석:
- 범죄 유형: {', '.join(case_analysis.get('crime_types', []))}
- 사건 경중: {case_analysis.get('case_severity', '')}
- 적용 법령: {', '.join(case_analysis.get('applicable_laws', []))}

관련 판례 형량:
{chr(10).join(precedent_info)}

다음 JSON 형식으로 예측 결과를 제공해주세요:
{{
    "min_punishment": "최소 예상 형량",
    "max_punishment": "최대 예상 형량",
    "most_likely": "가장 가능성 높은 형량",
    "factors": ["형량에 영향을 미치는 요인들"],
    "mitigation_factors": ["감경 요인들"],
    "aggravation_factors": ["가중 요인들"],
    "confidence": "예측 신뢰도 (0-100)"
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"형량 예측 오류: {e}")
            return {
                "min_punishment": "예측 불가",
                "max_punishment": "예측 불가",
                "most_likely": "예측 불가",
                "factors": [],
                "mitigation_factors": [],
                "aggravation_factors": [],
                "confidence": "0"
            }
    
    def _count_tokens(self, text: str) -> int:
        """토큰 수를 계산하는 메서드"""
        try:
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4  # 대략적인 추정 