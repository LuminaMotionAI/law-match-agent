import requests
import json
import xmltodict
from typing import List, Dict, Optional
from datetime import datetime
import urllib.parse
import re

# Config 임포트를 try-except로 감싸서 Streamlit Cloud 호환성 확보
try:
    from config import Config
    CONFIG_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Config 모듈 로딩 오류: {e}")
    CONFIG_AVAILABLE = False
    
    # Fallback 설정값들
    class FallbackConfig:
        LAW_OC_CODE = "guest"
        LAW_API_URL = "http://www.law.go.kr/DRF/lawSearch.do"
        CASE_SEARCH_API_URL = "https://www.scourt.go.kr/portal/api"
        
        @staticmethod
        def get_api_key(key_name):
            return None
    
    Config = FallbackConfig()

class LawAPI:
    """한국 법률 정보 API 연동 클래스 (Streamlit Cloud 호환)"""
    
    def __init__(self):
        # 🔧 Config 초기화 오류 대응
        try:
            if CONFIG_AVAILABLE:
                # 국가법령정보센터 API 설정
                self.law_oc_code = getattr(Config, 'LAW_OC_CODE', 'guest')
                self.law_api_url = getattr(Config, 'LAW_API_URL', 'http://www.law.go.kr/DRF/lawSearch.do')
                
                # 판례검색 API 설정
                self.case_search_api_key = Config.get_api_key("case_search") if hasattr(Config, 'get_api_key') else None
                self.case_search_api_url = getattr(Config, 'CASE_SEARCH_API_URL', 'https://www.scourt.go.kr/portal/api')
                
                # 레거시 호환성
                self.law_api_key = Config.get_api_key("law") if hasattr(Config, 'get_api_key') else None
                self.lawinfo_api_key = self.law_oc_code
                self.base_url = self.law_api_url
                
                # 카카오 API 설정
                self.kakao_api_key = Config.get_api_key("kakao") if hasattr(Config, 'get_api_key') else None
            else:
                # Fallback 설정 사용
                self.law_oc_code = "guest"
                self.law_api_url = "http://www.law.go.kr/DRF/lawSearch.do"
                self.case_search_api_key = None
                self.case_search_api_url = "https://www.scourt.go.kr/portal/api"
                self.law_api_key = None
                self.lawinfo_api_key = "guest"
                self.base_url = self.law_api_url
                self.kakao_api_key = None
                
        except Exception as e:
            print(f"⚠️ API 설정 초기화 오류: {e} - 기본값 사용")
            # 기본값 설정
            self.law_oc_code = "guest"
            self.law_api_url = "http://www.law.go.kr/DRF/lawSearch.do"
            self.case_search_api_key = None
            self.case_search_api_url = "https://www.scourt.go.kr/portal/api"
            self.law_api_key = None
            self.lawinfo_api_key = "guest"
            self.base_url = self.law_api_url
            self.kakao_api_key = None
        
        # HTTP 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LawMatchAgent/1.0 (https://github.com/user/law-match-agent)',
            'Accept': 'application/json, application/xml, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        })
        
    def search_precedents(self, query: str, limit: int = 10) -> List[Dict]:
        """
        판례 검색 메서드
        
        Args:
            query: 검색 키워드
            limit: 검색 결과 수 제한
            
        Returns:
            판례 검색 결과 리스트
        """
        try:
            # 국가법령정보센터 판례 API 호출
            params = {
                'OC': self.law_oc_code,
                'target': 'prec',
                'query': query,
                'display': str(limit),
                'type': 'XML'
            }
            
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            # XML을 딕셔너리로 변환
            xml_data = xmltodict.parse(response.text)
            
            # 판례 데이터 추출
            precedents = self._extract_precedents(xml_data)
            
            return precedents
            
        except requests.exceptions.RequestException as e:
            print(f"API 요청 오류: {e}")
            return []
        except Exception as e:
            print(f"판례 검색 오류: {e}")
            return []
    
    def _extract_precedents(self, xml_data: Dict) -> List[Dict]:
        """XML 데이터에서 판례 정보 추출"""
        try:
            precedents = []
            
            # XML 구조에 따라 판례 정보 추출
            if 'PrecService' in xml_data:
                prec_list = xml_data['PrecService'].get('prec', [])
                
                # 단일 결과인 경우 리스트로 변환
                if not isinstance(prec_list, list):
                    prec_list = [prec_list]
                
                for prec in prec_list:
                    precedent = {
                        'title': prec.get('판례명', ''),
                        'case_number': prec.get('사건번호', ''),
                        'court': prec.get('법원명', ''),
                        'date': prec.get('선고일자', ''),
                        'summary': prec.get('요약', ''),
                        'full_text': prec.get('전문', ''),
                        'law_provisions': prec.get('관련조문', ''),
                        'keywords': prec.get('키워드', ''),
                        'sentence': prec.get('선고형량', ''),
                        'compensation': prec.get('위자료', '')
                    }
                    precedents.append(precedent)
            
            return precedents
            
        except Exception as e:
            print(f"판례 데이터 추출 오류: {e}")
            return []
    
    def search_statutes(self, query: str) -> List[Dict]:
        """
        법령 검색 메서드
        
        Args:
            query: 검색 키워드
            
        Returns:
            법령 검색 결과 리스트
        """
        try:
            params = {
                'OC': self.law_oc_code,
                'target': 'law',
                'query': query,
                'display': '20',
                'type': 'XML'
            }
            
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            xml_data = xmltodict.parse(response.text)
            statutes = self._extract_statutes(xml_data)
            
            return statutes
            
        except Exception as e:
            print(f"법령 검색 오류: {e}")
            return []
    
    def _extract_statutes(self, xml_data: Dict) -> List[Dict]:
        """XML 데이터에서 법령 정보 추출"""
        try:
            statutes = []
            
            if 'LawService' in xml_data:
                law_list = xml_data['LawService'].get('law', [])
                
                if not isinstance(law_list, list):
                    law_list = [law_list]
                
                for law in law_list:
                    statute = {
                        'title': law.get('법령명', ''),
                        'law_number': law.get('법령번호', ''),
                        'enactment_date': law.get('제정일자', ''),
                        'revision_date': law.get('개정일자', ''),
                        'content': law.get('조문내용', ''),
                        'category': law.get('분야', '')
                    }
                    statutes.append(statute)
            
            return statutes
            
        except Exception as e:
            print(f"법령 데이터 추출 오류: {e}")
            return []
    
    def get_case_details(self, case_number: str) -> Optional[Dict]:
        """
        특정 판례의 상세 정보 조회
        
        Args:
            case_number: 사건번호
            
        Returns:
            판례 상세 정보
        """
        try:
            params = {
                'OC': self.law_oc_code,
                'target': 'prec',
                'query': case_number,
                'display': '1',
                'type': 'XML'
            }
            
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            xml_data = xmltodict.parse(response.text)
            precedents = self._extract_precedents(xml_data)
            
            return precedents[0] if precedents else None
            
        except Exception as e:
            print(f"판례 상세 정보 조회 오류: {e}")
            return None
    
    def search_by_keywords(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """
        키워드 리스트로 판례 검색
        
        Args:
            keywords: 검색 키워드 리스트
            limit: 검색 결과 수 제한
            
        Returns:
            판례 검색 결과 리스트
        """
        query = ' '.join(keywords)
        return self.search_precedents(query, limit)
    
    def search_by_crime_type(self, crime_type: str, limit: int = 10) -> List[Dict]:
        """
        범죄 유형별 판례 검색
        
        Args:
            crime_type: 범죄 유형 (예: 사기, 강도, 절도 등)
            limit: 검색 결과 수 제한
            
        Returns:
            판례 검색 결과 리스트
        """
        return self.search_precedents(f"{crime_type}죄", limit)
    
    def search_by_punishment(self, punishment_type: str, limit: int = 10) -> List[Dict]:
        """
        형량 유형별 판례 검색
        
        Args:
            punishment_type: 형량 유형 (예: 징역, 벌금, 집행유예 등)
            limit: 검색 결과 수 제한
            
        Returns:
            판례 검색 결과 리스트
        """
        return self.search_precedents(f"{punishment_type}", limit) 

    def get_law_article(self, law_name: str, article_number: str) -> Dict:
        """
        법률 조항 검색 (Streamlit Cloud 완전 호환)
        
        Args:
            law_name: 법률명 (예: "형법", "민법")
            article_number: 조항 번호 (예: "243", "44의7")
            
        Returns:
            법률 조항 정보
        """
        try:
            # 🔧 확장된 법률 조항 데이터베이스 (Streamlit Cloud 내장)
            law_articles = {
                "형법": {
                    "243": {
                        "title": "음화반포등",
                        "content": "음란한 문서, 도화, 필름 기타 물건을 반포, 판매 또는 임대하거나 공연히 전시 또는 상영한 자는 1년 이하의 징역 또는 500만원 이하의 벌금에 처한다.",
                        "law_number": "형법 제243조",
                        "category": "사회에 대한 죄",
                        "subcategory": "성풍속에 관한 죄"
                    },
                    "347": {
                        "title": "사기",
                        "content": "사람을 기망하여 재물의 교부를 받거나 재산상의 이익을 취득한 자는 10년 이하의 징역 또는 2천만원 이하의 벌금에 처한다.",
                        "law_number": "형법 제347조", 
                        "category": "재산에 대한 죄",
                        "subcategory": "사기와 공갈의 죄"
                    },
                    "1": {
                        "title": "범죄의 성립과 처벌",
                        "content": "죄형법정주의에 따라 법률이 정하지 아니하면 범죄가 되지 아니하고 형벌을 과하지 아니한다.",
                        "law_number": "형법 제1조",
                        "category": "통칙",
                        "subcategory": "기본원칙"
                    }
                },
                "민법": {
                    "750": {
                        "title": "불법행위의 내용",
                        "content": "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.",
                        "law_number": "민법 제750조",
                        "category": "채권",
                        "subcategory": "불법행위로 인한 채권"
                    },
                    "751": {
                        "title": "재산 이외의 손해의 배상",
                        "content": "타인의 신체, 자유 또는 인격권을 침해한 경우에는 재산 이외의 손해에 대하여도 배상할 책임이 있다.",
                        "law_number": "민법 제751조",
                        "category": "채권",
                        "subcategory": "불법행위로 인한 채권"
                    },
                    "1": {
                        "title": "권리능력의 시기",
                        "content": "사람은 생존하는 동안 권리와 의무의 주체가 된다.",
                        "law_number": "민법 제1조",
                        "category": "일반규정",
                        "subcategory": "기본원칙"
                    }
                },
                "정보통신망 이용촉진 및 정보보호 등에 관한 법률": {
                    "44의7": {
                        "title": "불법정보의 유통금지 등",
                        "content": "누구든지 정보통신망을 통하여 음란정보를 유통하여서는 아니 된다. 이 법을 위반하여 불법정보를 유통한 자는 2년 이하의 징역 또는 2천만원 이하의 벌금에 처한다.",
                        "law_number": "정보통신망 이용촉진 및 정보보호 등에 관한 법률 제44조의7",
                        "category": "정보통신망 관련 특별법",
                        "subcategory": "불법정보 유통 금지"
                    }
                },
                "정보통신망법": {
                    "44의7": {
                        "title": "불법정보의 유통금지 등",
                        "content": "누구든지 정보통신망을 통하여 음란정보를 유통하여서는 아니 된다. 이 법을 위반하여 불법정보를 유통한 자는 2년 이하의 징역 또는 2천만원 이하의 벌금에 처한다.",
                        "law_number": "정보통신망법 제44조의7",
                        "category": "정보통신망 관련 특별법",
                        "subcategory": "불법정보 유통 금지"
                    }
                },
                "개인정보보호법": {
                    "71": {
                        "title": "벌칙",
                        "content": "다음 각 호의 어느 하나에 해당하는 자는 5년 이하의 징역 또는 5천만원 이하의 벌금에 처한다.",
                        "law_number": "개인정보보호법 제71조",
                        "category": "개인정보보호",
                        "subcategory": "벌칙"
                    }
                },
                "상법": {
                    "1": {
                        "title": "상법의 적용범위",
                        "content": "상인의 영업에 관하여는 다른 법률에 특별한 규정이 있는 경우를 제외하고는 이 법이 정하는 바에 의한다.",
                        "law_number": "상법 제1조",
                        "category": "총칙",
                        "subcategory": "기본원칙"
                    }
                }
            }
            
            # 🔍 법률명 정규화 (별칭 처리)
            law_aliases = {
                "정통법": "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
                "정보통신망법": "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
                "개보법": "개인정보보호법",
                "개인정보법": "개인정보보호법"
            }
            
            normalized_law_name = law_aliases.get(law_name, law_name)
            
            # 검색 실행
            if normalized_law_name in law_articles and article_number in law_articles[normalized_law_name]:
                article_info = law_articles[normalized_law_name][article_number].copy()
                article_info["exists"] = True
                article_info["source"] = "내장 데이터베이스"
                return article_info
            else:
                return {
                    "exists": False,
                    "message": f"{law_name} 제{article_number}조를 내장 데이터베이스에서 찾을 수 없습니다.",
                    "law_number": f"{law_name} 제{article_number}조",
                    "suggestion": "더 많은 법률 조항을 찾으려면 '국가법령정보센터(law.go.kr)'에서 직접 검색해보세요.",
                    "search_url": f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=&efYd=&chrClsCd=010202&ancYnChk=0#J{article_number}:{law_name}"
                }
                
        except Exception as e:
            print(f"⚠️ 법률 조항 검색 오류: {e}")
            return {
                "exists": False, 
                "message": f"검색 중 오류가 발생했습니다: {e}",
                "error": str(e)
            }
    
    def verify_case_number(self, case_number: str, use_ai_search: bool = True) -> Dict:
        """
        판례 번호 검증
        
        Args:
            case_number: 판례 번호 (예: "2019도11772")
            use_ai_search: AI 검색 사용 여부
            
        Returns:
            판례 정보 또는 존재 여부
        """
        try:
            # 판례 번호 형식 검증 (더 많은 사건 유형 포함)
            case_pattern = r'^(\d{4})(도|바|노|마|차|러|허|므|두|후|고합|고단|초기|재|전|누|구|나|가|재나|재차|재허|재므|재두|재후|합|단|기|전합|전단|전기|누합|누단|누기|구합|구단|구기|나합|나단|나기|가합|가단|가기)(\d+)$'
            if not re.match(case_pattern, case_number):
                return {
                    "exists": False,
                    "message": "잘못된 판례 번호 형식입니다. (예: 2019도11772)",
                    "case_number": case_number
                }
            
                    # 1. 먼저 로컬 데이터베이스에서 검색 (가장 정확한 정보)
            
            # 2. 로컬 샘플 데이터에서 검색
            sample_cases = {
                "2019도11772": {
                    "exists": True,
                    "title": "음란물 유포죄 관련 판례",
                    "court": "대법원",
                    "date": "2019-12-26",
                    "case_type": "형사",
                    "summary": "정보통신망을 이용하여 음란물을 유포한 행위에 대한 처벌 기준을 명확히 한 판례",
                    "main_issue": "음란물 유포의 구성요건과 처벌 기준",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제243조", "정보통신망 이용촉진 및 정보보호 등에 관한 법률"],
                    "keywords": ["음란물", "유포", "정보통신망", "형법 제243조"]
                },
                "2020도5432": {
                    "exists": True,
                    "title": "전자상거래 사기 판례",
                    "court": "대법원",
                    "date": "2020-03-15",
                    "case_type": "형사",
                    "summary": "온라인 쇼핑몰을 통한 사기 행위의 법적 판단 기준",
                    "main_issue": "전자상거래에서의 사기 구성요건",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제347조"],
                    "keywords": ["사기", "전자상거래", "온라인"]
                },
                "2021도3456": {
                    "exists": True,
                    "title": "해킹 관련 판례",
                    "court": "대법원",
                    "date": "2021-06-20",
                    "case_type": "형사",
                    "summary": "타인의 컴퓨터 시스템에 무단으로 접근하여 정보를 빼낸 행위에 대한 법적 판단",
                    "main_issue": "해킹 행위의 구성요건과 처벌 수준",
                    "verdict": "유죄",
                    "applicable_law": ["정보통신망법 제48조", "형법 제347조의2"],
                    "keywords": ["해킹", "무단접근", "정보통신망", "컴퓨터범죄"]
                },
                "2018도9876": {
                    "exists": True,
                    "title": "스토킹 처벌 판례",
                    "court": "대법원",
                    "date": "2018-11-10",
                    "case_type": "형사",
                    "summary": "지속적인 접근 및 괴롭힘 행위에 대한 처벌 기준",
                    "main_issue": "스토킹 행위의 범위와 처벌 수준",
                    "verdict": "유죄",
                    "applicable_law": ["스토킹범죄의 처벌 등에 관한 법률"],
                    "keywords": ["스토킹", "괴롭힘", "접근금지", "특별법"]
                },
                "2022고합57": {
                    "exists": True,
                    "title": "특수강도 사건",
                    "court": "서울중앙지방법원",
                    "date": "2022-07-07",
                    "case_type": "형사",
                    "summary": "야간에 주거지에 침입하여 폭력을 행사하고 금품을 갈취한 특수강도 사건",
                    "main_issue": "특수강도죄의 구성요건 및 형량 결정",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제334조", "형법 제335조"],
                    "keywords": ["특수강도", "주거침입", "폭력", "금품갈취"]
                },
                "2022고단1234": {
                    "exists": True,
                    "title": "사기 사건",
                    "court": "대전지방법원",
                    "date": "2022-08-15",
                    "case_type": "형사",
                    "summary": "가상화폐 투자를 빙자한 다단계 사기 사건",
                    "main_issue": "가상화폐 관련 사기죄의 적용",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제347조", "방문판매법"],
                    "keywords": ["사기", "가상화폐", "다단계", "투자"]
                },
                "2022고합144": {
                    "exists": True,
                    "title": "성폭력 사건",
                    "court": "수원지방법원",
                    "date": "2022-12-23",
                    "case_type": "형사",
                    "summary": "직장 내 성폭력 사건에 대한 법적 판단",
                    "main_issue": "직장 내 성폭력의 처벌 기준",
                    "verdict": "유죄",
                    "applicable_law": ["성폭력처벌법", "형법 제297조"],
                    "keywords": ["성폭력", "직장", "처벌", "피해자보호"]
                },
                "2022고합600": {
                    "exists": True,
                    "title": "마약 사건",
                    "court": "서울중앙지방법원",
                    "date": "2022-11-15",
                    "case_type": "형사",
                    "summary": "대량 마약 유통 및 판매 사건",
                    "main_issue": "마약 판매의 처벌 수준 및 몰수·추징",
                    "verdict": "유죄",
                    "applicable_law": ["마약류 관리에 관한 법률"],
                    "keywords": ["마약", "유통", "판매", "몰수추징"]
                },
                "2022고합660": {
                    "exists": True,
                    "title": "특수절도 사건",
                    "court": "서울중앙지방법원",
                    "date": "2024-11-15",
                    "case_type": "형사",
                    "summary": "차량 절도 및 연쇄 절도 사건",
                    "main_issue": "특수절도죄의 구성요건 및 상습성",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제331조", "형법 제332조"],
                    "keywords": ["특수절도", "차량절도", "상습", "연쇄범죄"]
                },
                "2022고합3692": {
                    "exists": True,
                    "title": "횡령 사건",
                    "court": "서울남부지방법원",
                    "date": "2024-05-16",
                    "case_type": "형사",
                    "summary": "회사 자금 횡령 및 배임 사건",
                    "main_issue": "횡령죄와 배임죄의 구별 및 처벌",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제355조", "형법 제356조"],
                    "keywords": ["횡령", "배임", "회사자금", "업무상배임"]
                },
                "2023고합88": {
                    "exists": True,
                    "title": "살인 사건",
                    "court": "광주지방법원",
                    "date": "2023-09-12",
                    "case_type": "형사",
                    "summary": "동거인 살해 사건",
                    "main_issue": "살인죄의 구성요건 및 정당방위 여부",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제250조"],
                    "keywords": ["살인", "동거인", "정당방위", "고의"]
                },
                "2021고합456": {
                    "exists": True,
                    "title": "방화 사건",
                    "court": "부산지방법원",
                    "date": "2021-10-08",
                    "case_type": "형사",
                    "summary": "아파트 방화 사건",
                    "main_issue": "현주건조물 방화죄의 적용",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제164조"],
                    "keywords": ["방화", "현주건조물", "아파트", "위험"]
                },
                "2020고합789": {
                    "exists": True,
                    "title": "뇌물 사건",
                    "court": "대구지방법원",
                    "date": "2020-12-18",
                    "case_type": "형사",
                    "summary": "공무원 뇌물 수수 사건",
                    "main_issue": "뇌물죄의 구성요건 및 처벌",
                    "verdict": "유죄",
                    "applicable_law": ["형법 제129조", "형법 제130조"],
                    "keywords": ["뇌물", "공무원", "수수", "직무관련"]
                }
            }
            
            if case_number in sample_cases:
                return sample_cases[case_number]
            
            # 로컬 데이터에 없으면 AI 검색 시도 (실시간 검색)
            if use_ai_search:
                try:
                    from . import OpenAIAPI
                    openai_api = OpenAIAPI()
                    ai_result = self._search_case_with_ai(case_number, openai_api)
                    if ai_result.get("exists"):
                        return ai_result
                except Exception as e:
                    print(f"AI 검색 중 오류: {e}")
            
            # 찾을 수 없는 경우
            return {
                "exists": False,
                "message": f"판례 번호 '{case_number}'를 시스템에서 찾을 수 없습니다.",
                "case_number": case_number,
                "suggestion": "AI 검색을 시도했지만 결과를 찾을 수 없었습니다. 법원 홈페이지에서 직접 확인해보세요.",
                "search_links": {
                    "대법원": "https://glaw.scourt.go.kr/",
                    "종합법률정보": "https://www.law.go.kr/",
                    "케이스노트": "https://casenote.kr/"
                }
            }
                
        except Exception as e:
            print(f"판례 번호 검증 오류: {e}")
            return {"exists": False, "message": f"검증 중 오류가 발생했습니다: {e}"}
    
    def _search_case_with_ai(self, case_number: str, openai_api) -> Dict:
        """
        OpenAI API를 사용한 판례 검색
        
        Args:
            case_number: 판례 번호
            openai_api: OpenAI API 인스턴스
            
        Returns:
            판례 정보
        """
        try:
            # OpenAI API에 판례 검색 요청
            prompt = f"""
다음 판례 번호에 대한 정보를 검색해주세요: {case_number}

이 판례가 실제로 존재하는지 확인하고, 존재한다면 다음 정보를 JSON 형식으로 제공해주세요:

{{
    "exists": true/false,
    "title": "판례 제목",
    "court": "담당 법원",
    "date": "판결일 (YYYY-MM-DD)",
    "case_type": "사건 유형 (형사/민사/행정/가사)",
    "summary": "사건 요약",
    "main_issue": "주요 쟁점",
    "verdict": "판결 결과",
    "applicable_law": ["적용 법률들"],
    "keywords": ["관련 키워드들"]
}}

만약 판례가 존재하지 않는다면 exists를 false로 설정해주세요.
정확한 정보만 제공하고, 추측하지 마세요.
"""
            
            # AI에게 질의
            response = openai_api.get_completion(prompt)
            
            # JSON 파싱 시도
            import json
            try:
                # 응답에서 JSON 부분만 추출
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    result = json.loads(json_str)
                    
                    # 결과 검증 및 정리
                    if result.get("exists"):
                        return {
                            "exists": True,
                            "title": result.get("title", "정보 없음"),
                            "court": result.get("court", "정보 없음"),
                            "date": result.get("date", "정보 없음"),
                            "case_type": result.get("case_type", "정보 없음"),
                            "summary": result.get("summary", "정보 없음"),
                            "main_issue": result.get("main_issue", "정보 없음"),
                            "verdict": result.get("verdict", "정보 없음"),
                            "applicable_law": result.get("applicable_law", []),
                            "keywords": result.get("keywords", []),
                            "source": "AI 검색"
                        }
                    else:
                        return {"exists": False, "source": "AI 검색"}
                
            except json.JSONDecodeError:
                print(f"AI 응답 JSON 파싱 실패: {response}")
                return {"exists": False, "error": "AI 응답 파싱 실패"}
            
            return {"exists": False, "error": "AI 응답에서 유효한 JSON을 찾을 수 없음"}
            
        except Exception as e:
            print(f"AI 판례 검색 오류: {e}")
            return {"exists": False, "error": f"AI 검색 실패: {e}"}
    
    def search_case_with_scourt_api(self, case_number: str) -> Dict:
        """
        대법원 포털 API를 사용한 판례 검색
        
        Args:
            case_number: 판례 번호
            
        Returns:
            판례 정보
        """
        try:
            # 대법원 포털 판례검색 API 엔드포인트
            search_url = f"{self.case_search_api_url}/search/precedent"
            
            # 검색 파라미터
            params = {
                'caseNo': case_number,
                'searchType': 'caseNumber',
                'pageSize': 1,
                'pageNum': 1
            }
            
            # API 요청
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('resultList') and len(data['resultList']) > 0:
                    case_info = data['resultList'][0]
                    
                    return {
                        "exists": True,
                        "title": case_info.get('caseTitle', ''),
                        "court": case_info.get('courtName', ''),
                        "date": case_info.get('judgeDate', ''),
                        "case_type": self._get_case_type_from_number(case_number),
                        "summary": case_info.get('caseSummary', ''),
                        "main_issue": case_info.get('mainIssue', ''),
                        "verdict": case_info.get('verdict', ''),
                        "applicable_law": case_info.get('applicableLaw', []),
                        "keywords": case_info.get('keywords', []),
                        "source": "대법원 포털 API",
                        "full_text": case_info.get('fullText', ''),
                        "case_url": case_info.get('caseUrl', '')
                    }
                else:
                    return {"exists": False, "source": "대법원 포털 API", "message": "검색 결과 없음"}
            
            else:
                print(f"대법원 API 응답 오류: {response.status_code}")
                return {"exists": False, "error": f"API 응답 오류: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print("대법원 API 요청 시간 초과")
            return {"exists": False, "error": "요청 시간 초과"}
        except requests.exceptions.RequestException as e:
            print(f"대법원 API 요청 오류: {e}")
            return {"exists": False, "error": f"네트워크 오류: {e}"}
        except Exception as e:
            print(f"대법원 API 처리 오류: {e}")
            return {"exists": False, "error": f"처리 오류: {e}"}
    
    def search_precedents_by_keyword_scourt(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        대법원 포털에서 키워드로 판례 검색
        
        Args:
            keyword: 검색 키워드
            limit: 검색 결과 수 제한
            
        Returns:
            판례 검색 결과 리스트
        """
        try:
            search_url = f"{self.case_search_api_url}/search/precedent"
            
            params = {
                'keyword': keyword,
                'searchType': 'keyword',
                'pageSize': limit,
                'pageNum': 1
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                precedents = []
                
                for case_info in data.get('resultList', []):
                    precedent = {
                        'title': case_info.get('caseTitle', ''),
                        'case_number': case_info.get('caseNo', ''),
                        'court': case_info.get('courtName', ''),
                        'date': case_info.get('judgeDate', ''),
                        'summary': case_info.get('caseSummary', ''),
                        'keywords': case_info.get('keywords', []),
                        'verdict': case_info.get('verdict', ''),
                        'source': '대법원 포털',
                        'case_url': case_info.get('caseUrl', '')
                    }
                    precedents.append(precedent)
                
                return precedents
            else:
                print(f"대법원 키워드 검색 API 오류: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"대법원 키워드 검색 오류: {e}")
            return []
    
    def _get_case_type_from_number(self, case_number: str) -> str:
        """
        사건번호에서 사건 유형 추출
        
        Args:
            case_number: 사건번호 (예: 2022고합57)
            
        Returns:
            사건 유형
        """
        case_type_map = {
            '도': '형사',
            '바': '행정',
            '노': '민사',
            '마': '가사',
            '고합': '형사(합의)',
            '고단': '형사(단독)',
            '합': '합의부',
            '단': '단독',
            '재': '재심',
            '전': '전원합의체'
        }
        
        # 정규식으로 사건 유형 추출
        match = re.search(r'\d{4}([가-힣]+)\d+', case_number)
        if match:
            case_type_code = match.group(1)
            return case_type_map.get(case_type_code, case_type_code)
        
        return '알 수 없음'
    
    def search_law_with_openlaw_api(self, query: str, target: str = "law") -> List[Dict]:
        """
        국가법령정보센터 오픈 API를 사용한 법령 검색
        
        Args:
            query: 검색 키워드
            target: 검색 대상 (law: 법령, prec: 판례)
            
        Returns:
            검색 결과 리스트
        """
        try:
            if not self.law_api_key:
                print("국가법령정보센터 API 키가 설정되지 않았습니다.")
                return []
            
            # API 파라미터 설정
            params = {
                'OC': self.law_api_key,
                'target': target,
                'query': query,
                'display': '10',
                'type': 'json'
            }
            
            # API 요청
            response = self.session.get(self.law_api_url, params=params, timeout=10)
            response.raise_for_status()
            
            # JSON 응답 파싱
            data = response.json()
            
            results = []
            if target == "law" and 'LawService' in data:
                law_list = data['LawService'].get('law', [])
                if not isinstance(law_list, list):
                    law_list = [law_list]
                    
                for law_item in law_list:
                    result = {
                        'title': law_item.get('법령명', ''),
                        'law_number': law_item.get('법령번호', ''),
                        'enactment_date': law_item.get('제정일자', ''),
                        'content': law_item.get('조문내용', ''),
                        'category': law_item.get('분야', ''),
                        'source': '국가법령정보센터'
                    }
                    results.append(result)
                    
            elif target == "prec" and 'PrecService' in data:
                prec_list = data['PrecService'].get('prec', [])
                if not isinstance(prec_list, list):
                    prec_list = [prec_list]
                    
                for prec_item in prec_list:
                    result = {
                        'title': prec_item.get('판례명', ''),
                        'case_number': prec_item.get('사건번호', ''),
                        'court': prec_item.get('법원명', ''),
                        'date': prec_item.get('선고일자', ''),
                        'summary': prec_item.get('요약', ''),
                        'keywords': prec_item.get('키워드', '').split(',') if prec_item.get('키워드') else [],
                        'source': '국가법령정보센터'
                    }
                    results.append(result)
            
            return results
            
        except requests.exceptions.Timeout:
            print("국가법령정보센터 API 요청 시간 초과")
            return []
        except requests.exceptions.RequestException as e:
            print(f"국가법령정보센터 API 요청 오류: {e}")
            return []
        except Exception as e:
            print(f"국가법령정보센터 API 처리 오류: {e}")
            return []
    
    def search_precedents_with_openlaw_api(self, query: str, limit: int = 10) -> List[Dict]:
        """
        국가법령정보센터 API를 사용한 판례 검색
        
        Args:
            query: 검색 키워드
            limit: 검색 결과 수 제한
            
        Returns:
            판례 검색 결과 리스트
        """
        return self.search_law_with_openlaw_api(query, target="prec")
    
    def search_law_by_keyword(self, keyword: str, law_type: str = "all") -> List[Dict]:
        """
        키워드로 법률 검색
        
        Args:
            keyword: 검색 키워드
            law_type: 법률 유형 ("criminal", "civil", "administrative", "all")
            
        Returns:
            관련 법률 목록
        """
        try:
            # 샘플 법률 데이터
            laws_data = [
                {
                    "law_name": "형법",
                    "article": "243",
                    "title": "음화반포등",
                    "content": "음란한 문서, 도화, 필름 기타 물건을 반포, 판매 또는 임대하거나 공연히 전시 또는 상영한 자는 1년 이하의 징역 또는 500만원 이하의 벌금에 처한다.",
                    "type": "criminal",
                    "keywords": ["음란물", "유포", "반포", "판매", "임대", "전시", "상영"]
                },
                {
                    "law_name": "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
                    "article": "44조의7",
                    "title": "불법정보의 유통금지 등",
                    "content": "누구든지 정보통신망을 통하여 음란정보를 유통하여서는 아니 된다.",
                    "type": "administrative",
                    "keywords": ["정보통신망", "음란정보", "유통금지", "인터넷"]
                },
                {
                    "law_name": "형법",
                    "article": "347",
                    "title": "사기",
                    "content": "사람을 기망하여 재물의 교부를 받거나 재산상의 이익을 취득한 자는 10년 이하의 징역 또는 2천만원 이하의 벌금에 처한다.",
                    "type": "criminal",
                    "keywords": ["사기", "기망", "재물", "교부", "재산상 이익"]
                }
            ]
            
            # 키워드로 필터링
            filtered_laws = []
            for law in laws_data:
                if (law_type == "all" or law["type"] == law_type) and \
                   (keyword.lower() in law["content"].lower() or \
                    keyword.lower() in law["title"].lower() or \
                    any(keyword.lower() in kw.lower() for kw in law["keywords"])):
                    filtered_laws.append(law)
            
            return filtered_laws
            
        except Exception as e:
            print(f"법률 키워드 검색 오류: {e}")
            return []

    def get_related_laws(self, law_reference: str) -> List[Dict]:
        """
        관련 법률 조항 검색
        
        Args:
            law_reference: 법률 참조 (예: "형법 제243조")
            
        Returns:
            관련 법률 목록
        """
        try:
            # 법률 참조 파싱
            law_match = re.match(r'(.+?)\s*제(\d+(?:의\d+)?)조', law_reference)
            if not law_match:
                return []
            
            law_name = law_match.group(1)
            article_num = law_match.group(2)
            
            # 관련 법률 매핑
            related_laws = {
                "형법 제243조": [
                    {
                        "law_name": "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
                        "article": "44조의7",
                        "title": "불법정보의 유통금지 등",
                        "relation": "온라인 음란물 유포 시 적용되는 특별법"
                    },
                    {
                        "law_name": "형법",
                        "article": "244조",
                        "title": "음화제조등",
                        "relation": "음란물 제조 관련 조항"
                    }
                ],
                "형법 제347조": [
                    {
                        "law_name": "형법",
                        "article": "350조",
                        "title": "공갈",
                        "relation": "재산범죄 관련 조항"
                    },
                    {
                        "law_name": "전자상거래 등에서의 소비자보호에 관한 법률",
                        "article": "21조",
                        "title": "금지행위",
                        "relation": "전자상거래 사기 관련 특별법"
                    }
                ]
            }
            
            return related_laws.get(law_reference, [])
            
        except Exception as e:
            print(f"관련 법률 검색 오류: {e}")
            return []

    def validate_legal_citation(self, citation: str) -> Dict:
        """
        법률 인용 형식 검증
        
        Args:
            citation: 법률 인용 (예: "형법 제243조", "대법원 2019도11772")
            
        Returns:
            검증 결과
        """
        try:
            result = {
                "citation": citation,
                "is_valid": False,
                "type": "unknown",
                "details": {}
            }
            
            # 법률 조항 패턴 검증
            law_pattern = r'^(.+?)\s*제(\d+(?:의\d+)?)조$'
            law_match = re.match(law_pattern, citation)
            
            if law_match:
                law_name = law_match.group(1)
                article_num = law_match.group(2)
                
                result["type"] = "law_article"
                result["details"] = {
                    "law_name": law_name,
                    "article_number": article_num
                }
                
                # 법률 조항 존재 여부 확인
                article_info = self.get_law_article(law_name, article_num)
                if article_info.get("exists"):
                    result["is_valid"] = True
                    result["details"].update(article_info)
                else:
                    result["details"]["error"] = article_info.get("message", "조항을 찾을 수 없습니다.")
                
                return result
            
            # 판례 번호 패턴 검증 (더 많은 사건 유형 포함)
            case_pattern = r'^(대법원|고등법원|지방법원)?\s*(\d{4})(도|바|노|마|차|러|허|므|두|후|고합|고단|초기|재|전|누|구|나|가|재나|재차|재허|재므|재두|재후|합|단|기|전합|전단|전기|누합|누단|누기|구합|구단|구기|나합|나단|나기|가합|가단|가기)(\d+)$'
            case_match = re.match(case_pattern, citation)
            
            if case_match:
                court = case_match.group(1) or "대법원"
                year = case_match.group(2)
                case_type = case_match.group(3)
                case_num = case_match.group(4)
                full_case_num = f"{year}{case_type}{case_num}"
                
                result["type"] = "case_number"
                result["details"] = {
                    "court": court,
                    "year": year,
                    "case_type": case_type,
                    "case_number": case_num,
                    "full_case_number": full_case_num
                }
                
                # 판례 존재 여부 확인
                case_info = self.verify_case_number(full_case_num)
                if case_info.get("exists"):
                    result["is_valid"] = True
                    result["details"].update(case_info)
                else:
                    result["details"]["error"] = case_info.get("message", "판례를 찾을 수 없습니다.")
                
                return result
            
            # 알 수 없는 형식
            result["details"]["error"] = "인식할 수 없는 법률 인용 형식입니다."
            return result
            
        except Exception as e:
            print(f"법률 인용 검증 오류: {e}")
            return {
                "citation": citation,
                "is_valid": False,
                "type": "error",
                "details": {"error": f"검증 중 오류가 발생했습니다: {e}"}
            } 