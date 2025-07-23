"""
허깅페이스 데이터셋을 사용하는 API 클래스
"""

import os
from typing import List, Dict, Optional
from datasets import load_dataset
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class HuggingFaceAPI:
    """허깅페이스 데이터셋을 사용하는 법률 검색 API"""
    
    def __init__(self, dataset_name="LuminaMotionAI/korean-legal-dataset"):
        """
        Args:
            dataset_name: 허깅페이스 데이터셋 이름
        """
        self.dataset_name = dataset_name
        self.dataset = None
        self.encoder = None
        self.embeddings_cache = {}
        
        # 모델 초기화
        self._initialize_encoder()
        
        # 데이터셋 로드
        self._load_dataset()
    
    def _initialize_encoder(self):
        """한국어 문장 임베딩 모델 초기화"""
        try:
            self.encoder = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI')
            print("✅ 한국어 SBERT 모델 로드 완료")
        except Exception as e:
            print(f"❌ 임베딩 모델 로드 실패: {e}")
            self.encoder = None
    
    def _load_dataset(self):
        """허깅페이스에서 데이터셋 로드"""
        try:
            print(f"📥 허깅페이스에서 데이터셋 로딩: {self.dataset_name}")
            self.dataset = load_dataset(self.dataset_name)
            print(f"✅ 데이터셋 로드 완료: {len(self.dataset['all'])}개 데이터")
            
            # 데이터프레임으로 변환 (검색 성능 향상)
            self.df = self.dataset['all'].to_pandas()
            print(f"✅ 데이터프레임 변환 완료")
            
        except Exception as e:
            print(f"❌ 데이터셋 로드 실패: {e}")
            print("💡 로컬 데이터셋을 사용합니다...")
            self._load_local_dataset()
    
    def _load_local_dataset(self):
        """로컬 데이터셋 로드 (백업)"""
        try:
            from datasets import load_from_disk
            self.dataset = load_from_disk("korean_legal_dataset")
            self.df = self.dataset['all'].to_pandas()
            print(f"✅ 로컬 데이터셋 로드 완료: {len(self.df)}개 데이터")
        except Exception as e:
            print(f"❌ 로컬 데이터셋 로드도 실패: {e}")
            self.dataset = None
            self.df = pd.DataFrame()
    
    def search_similar_cases(self, query: str, top_k: int = 5, case_type: str = None) -> List[Dict]:
        """유사한 사례 검색"""
        if self.df.empty or self.encoder is None:
            return []
        
        try:
            # 쿼리 임베딩
            query_embedding = self.encoder.encode([query])
            
            # 데이터 필터링
            search_df = self.df.copy()
            if case_type and case_type != "전체":
                case_type_map = {
                    "해석례": "해석례_QA",
                    "판결문": "판결문_QA", 
                    "결정례": "결정례_QA",
                    "법령": "법령_QA"
                }
                if case_type in case_type_map:
                    search_df = search_df[search_df['data_type'].str.contains(case_type_map[case_type])]
            
            if search_df.empty:
                return []
            
            # 텍스트 임베딩 (캐시 사용)
            text_embeddings = []
            for idx, row in search_df.iterrows():
                text = f"{row['input']} {row['output']}"
                cache_key = f"{row['id']}_{row['data_type']}"
                
                if cache_key in self.embeddings_cache:
                    embedding = self.embeddings_cache[cache_key]
                else:
                    embedding = self.encoder.encode([text])[0]
                    self.embeddings_cache[cache_key] = embedding
                
                text_embeddings.append(embedding)
            
            # 유사도 계산
            text_embeddings = np.array(text_embeddings)
            similarities = cosine_similarity(query_embedding, text_embeddings)[0]
            
            # 상위 결과 선택
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                row = search_df.iloc[idx]
                result = {
                    'case_id': row['id'],
                    'case_number': row['case_number'],
                    'case_name': row['case_name'],
                    'court_code': row['court_code'],
                    'final_date': row['final_date'],
                    'case_type': row['data_type'],
                    'query': row['input'],
                    'answer': row['output'],
                    'instruction': row['instruction'],
                    'similarity_score': float(similarities[idx]),
                    'source': 'HuggingFace Dataset',
                    'rank': len(results) + 1
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ 검색 중 오류: {e}")
            return []
    
    def get_legal_interpretation(self, query: str) -> Dict:
        """법률 해석 검색"""
        # 해석례 데이터만 검색
        results = self.search_similar_cases(query, top_k=1, case_type="해석례")
        
        if results:
            result = results[0]
            return {
                'question': result['query'],
                'answer': result['answer'],
                'context': f"사건명: {result['case_name']}\n법원: {result['court_code']}\n날짜: {result['final_date']}",
                'similarity_score': result['similarity_score'],
                'source': result['source']
            }
        else:
            return {}
    
    def get_enhanced_case_analysis(self, case_description: str) -> Dict:
        """종합 사건 분석"""
        try:
            # 1. 사건 분류 (데이터 타입별 유사도 확인)
            case_classification = self._classify_case(case_description)
            
            # 2. 유사 판례 검색
            similar_precedents = self.search_similar_cases(case_description, top_k=5)
            
            # 3. 관련 법령 검색
            applicable_laws = self.search_similar_cases(case_description, top_k=3, case_type="법령")
            
            # 4. 법률 해석
            legal_interpretations = self.search_similar_cases(case_description, top_k=2, case_type="해석례")
            
            # 5. 데이터 소스 정보
            data_sources = ["허깅페이스 한국어 법률 데이터셋", "형사법 LLM 사전학습 데이터"]
            
            return {
                'case_classification': case_classification,
                'similar_precedents': similar_precedents,
                'applicable_laws': applicable_laws,
                'legal_interpretations': legal_interpretations,
                'data_sources': data_sources,
                'recommendations': [
                    "유사 판례를 참고하여 변호 전략을 수립하세요.",
                    "관련 법령을 자세히 검토하세요.",
                    "전문가와 상담을 받으시길 권합니다."
                ]
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _classify_case(self, case_description: str) -> str:
        """사건 분류"""
        try:
            # 각 데이터 타입별로 유사도 계산
            data_types = ['결정례_QA', '법령_QA', '판결문_QA', '해석례_QA']
            type_scores = {}
            
            for data_type in data_types:
                results = self.search_similar_cases(case_description, top_k=1, case_type=data_type.split('_')[0])
                if results:
                    type_scores[data_type] = results[0]['similarity_score']
                else:
                    type_scores[data_type] = 0
            
            # 가장 높은 점수의 타입 반환
            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                return best_type.replace('_QA', '').replace('_SUM', '')
            else:
                return "분류 불가"
                
        except Exception as e:
            return f"분류 오류: {e}"
    
    def get_dataset_info(self) -> Dict:
        """데이터셋 정보 반환"""
        if self.df.empty:
            return {}
        
        info = {
            'total_count': len(self.df),
            'data_types': self.df['data_type'].value_counts().to_dict(),
            'date_range': {
                'earliest': self.df['final_date'].min(),
                'latest': self.df['final_date'].max()
            },
            'source': self.dataset_name
        }
        
        return info 