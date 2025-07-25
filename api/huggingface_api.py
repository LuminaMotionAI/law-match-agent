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
import json

class HuggingFaceAPI:
    """허깅페이스 데이터셋을 사용하는 법률 검색 API"""
    
    def __init__(self, dataset_name=None):
        """
        Args:
            dataset_name: 허깅페이스 데이터셋 이름
        """
        # Streamlit secrets 또는 환경변수에서 설정 읽기
        self.dataset_name = dataset_name or self._get_dataset_name()
        self.hf_token = self._get_hf_token()
        self.dataset = None
        self.encoder = None
        self.embeddings_cache = {}
        
        # 데이터프레임들 (복수 소스)
        self.df = pd.DataFrame()
        self.curated_df = pd.DataFrame()
        
        # 모델 초기화
        self._initialize_encoder()
        
        # 데이터셋 로드
        self._load_dataset()
        self._load_curated_dataset()
    
    def _get_dataset_name(self):
        """데이터셋 이름을 Streamlit secrets 또는 환경변수에서 가져오기"""
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'huggingface' in st.secrets:
                return st.secrets['huggingface']['dataset_name']
        except:
            pass
        
        return os.getenv('HUGGINGFACE_DATASET_NAME', 'LuminaMotionAI/korean-legal-dataset')
    
    def _get_hf_token(self):
        """허깅페이스 토큰을 Streamlit secrets 또는 환경변수에서 가져오기"""
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'huggingface' in st.secrets:
                return st.secrets['huggingface']['api_token']
        except:
            pass
        
        return os.getenv('HUGGINGFACE_API_TOKEN', None)

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
    
    def _load_curated_dataset(self):
        """큐레이티드 법률 데이터셋 로드"""
        try:
            curated_file = "curated_legal_dataset.json"
            if not os.path.exists(curated_file):
                print("⚠️ 큐레이티드 데이터셋을 찾을 수 없습니다.")
                return
            
            print("📥 큐레이티드 법률 데이터셋 로딩...")
            
            with open(curated_file, 'r', encoding='utf-8') as f:
                curated_data = json.load(f)
            
            # 큐레이티드 데이터를 검색 가능한 형태로 변환
            curated_records = []
            
            for case_id, case_data in curated_data.get('precedents', {}).items():
                record = {
                    'id': case_id,
                    'case_number': case_id,
                    'case_name': case_data.get('title', ''),
                    'court_code': case_data.get('court', ''),
                    'final_date': case_data.get('date', ''),
                    'input': f"{case_data.get('title', '')} {case_data.get('summary', '')}",
                    'output': f"판결 요지: {case_data.get('summary', '')}\n"
                             f"핵심 법리: {'; '.join(case_data.get('key_legal_points', []))}\n"
                             f"적용 법령: {'; '.join(case_data.get('applicable_laws', []))}\n"
                             f"형량: {case_data.get('sentence', '')}\n"
                             f"손해배상: {case_data.get('compensation', '')}",
                    'data_type': f"큐레이티드_{case_data.get('category', '일반')}",
                    'law_class': case_data.get('category', ''),
                    'importance': case_data.get('importance', '보통'),
                    'applicable_laws': case_data.get('applicable_laws', []),
                    'key_legal_points': case_data.get('key_legal_points', [])
                }
                curated_records.append(record)
            
            self.curated_df = pd.DataFrame(curated_records)
            print(f"✅ 큐레이티드 데이터셋 로드 완료: {len(self.curated_df)}개 고품질 판례")
            
        except Exception as e:
            print(f"❌ 큐레이티드 데이터셋 로드 실패: {e}")
            self.curated_df = pd.DataFrame()
    
    def search_similar_cases(self, query: str, top_k: int = 5, case_type: str = None) -> List[Dict]:
        """유사한 사례 검색 (큐레이티드 + 허깅페이스 데이터 통합)"""
        all_results = []
        
        # 1. 큐레이티드 고품질 데이터에서 먼저 검색
        if not self.curated_df.empty:
            curated_results = self._search_in_dataframe(
                self.curated_df, query, top_k//2 + 1, case_type, source="큐레이티드"
            )
            all_results.extend(curated_results)
        
        # 2. 허깅페이스 대용량 데이터에서 검색
        if not self.df.empty:
            hf_results = self._search_in_dataframe(
                self.df, query, top_k, case_type, source="허깅페이스"
            )
            all_results.extend(hf_results)
        
        # 3. 결과 통합 및 중복 제거
        seen_cases = set()
        final_results = []
        
        # 큐레이티드 결과를 우선순위로 처리
        for result in all_results:
            case_key = f"{result['case_number']}_{result['case_name']}"
            if case_key not in seen_cases:
                seen_cases.add(case_key)
                final_results.append(result)
                
                if len(final_results) >= top_k:
                    break
        
        # 순위 재조정
        for i, result in enumerate(final_results):
            result['rank'] = i + 1
        
        return final_results
    
    def _search_in_dataframe(self, df: pd.DataFrame, query: str, top_k: int, case_type: str = None, source: str = "Unknown") -> List[Dict]:
        """특정 데이터프레임에서 검색 수행"""
        if df.empty or self.encoder is None:
            return []
        
        try:
            # 데이터 필터링
            search_df = df.copy()
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
            
            # 1단계: 키워드 기반 필터링 (빠른 검색)
            query_lower = query.lower()
            keyword_matches = []
            
            for idx, row in search_df.iterrows():
                input_text = str(row['input']).lower()
                output_text = str(row['output']).lower()
                case_name = str(row['case_name']).lower()
                
                # 키워드 매칭 점수
                keyword_score = 0
                if query_lower in input_text or query_lower in output_text or query_lower in case_name:
                    keyword_score += 3
                
                # 부분 키워드 매칭
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 1:  # 한 글자는 제외
                        if word in input_text or word in output_text:
                            keyword_score += 1
                
                # 특별 키워드 가중치 (법률 용어)
                legal_keywords = ['조', '항', '호', '법', '죄', '형법', '민법', '상법', '스토킹', '성범죄', '사기']
                for keyword in legal_keywords:
                    if keyword in query_lower and keyword in input_text or keyword in output_text:
                        keyword_score += 2
                
                if keyword_score > 0:
                    keyword_matches.append((idx, keyword_score))
            
            # 2단계: 키워드 매칭된 것이 있으면 우선 처리
            if keyword_matches:
                # 키워드 점수 순으로 정렬
                keyword_matches.sort(key=lambda x: x[1], reverse=True)
                selected_indices = [idx for idx, score in keyword_matches[:top_k*3]]  # 더 많이 선택
                filtered_df = search_df.loc[selected_indices]
            else:
                # 키워드 매칭이 없으면 전체 데이터 사용 (큐레이티드는 작으니까 전체, 허깅페이스는 샘플링)
                if source == "큐레이티드":
                    filtered_df = search_df
                else:
                    filtered_df = search_df.sample(min(1000, len(search_df)))  # 성능을 위해 샘플링
            
            # 3단계: 임베딩 기반 유사도 검색
            query_embedding = self.encoder.encode([query])
            
            text_embeddings = []
            valid_indices = []
            
            for idx, row in filtered_df.iterrows():
                text = f"{row['input']} {row['output']}"
                cache_key = f"{row['id']}_{row['data_type']}_{source}"
                
                if cache_key in self.embeddings_cache:
                    embedding = self.embeddings_cache[cache_key]
                else:
                    embedding = self.encoder.encode([text])[0]
                    self.embeddings_cache[cache_key] = embedding
                
                text_embeddings.append(embedding)
                valid_indices.append(idx)
            
            if not text_embeddings:
                return []
            
            # 유사도 계산
            text_embeddings = np.array(text_embeddings)
            similarities = cosine_similarity(query_embedding, text_embeddings)[0]
            
            # 상위 결과 선택
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            results = []
            for i, embedding_idx in enumerate(top_indices):
                original_idx = valid_indices[embedding_idx]
                row = search_df.loc[original_idx]
                similarity_score = similarities[embedding_idx]
                
                # 최소 유사도 필터링 (큐레이티드는 더 관대하게)
                min_similarity = 0.05 if source == "큐레이티드" else 0.1
                if similarity_score < min_similarity:
                    continue
                
                result = {
                    'case_id': row['id'],
                    'case_number': row['case_number'],
                    'case_name': row['case_name'],
                    'court_code': row['court_code'],
                    'final_date': row['final_date'],
                    'input': row['input'],
                    'output': row['output'],
                    'data_type': row['data_type'],
                    'similarity': similarity_score,
                    'source': source,
                    'rank': i + 1
                }
                
                # 큐레이티드 데이터에서 추가 정보 포함
                if source == "큐레이티드" and 'applicable_laws' in row:
                    result['applicable_laws'] = row.get('applicable_laws', [])
                    result['key_legal_points'] = row.get('key_legal_points', [])
                    result['importance'] = row.get('importance', '보통')
                
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ {source} 검색 오류: {e}")
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
        """데이터셋 정보 반환 (허깅페이스 + 큐레이티드 통합)"""
        total_hf = len(self.df) if not self.df.empty else 0
        total_curated = len(self.curated_df) if not self.curated_df.empty else 0
        total_count = total_hf + total_curated
        
        if total_count == 0:
            return {}
        
        # 데이터 타입 통계
        data_types = {}
        
        # 허깅페이스 데이터 타입
        if not self.df.empty:
            hf_types = self.df['data_type'].value_counts().to_dict()
            for dtype, count in hf_types.items():
                data_types[f"HF_{dtype}"] = count
        
        # 큐레이티드 데이터 타입
        if not self.curated_df.empty:
            curated_types = self.curated_df['data_type'].value_counts().to_dict()
            for dtype, count in curated_types.items():
                data_types[dtype] = count
        
        # 날짜 범위
        all_dates = []
        if not self.df.empty:
            all_dates.extend(self.df['final_date'].dropna().tolist())
        if not self.curated_df.empty:
            all_dates.extend(self.curated_df['final_date'].dropna().tolist())
        
        date_range = {'earliest': 'Unknown', 'latest': 'Unknown'}
        if all_dates:
            all_dates = [d for d in all_dates if d and d != '']
            if all_dates:
                date_range = {
                    'earliest': min(all_dates),
                    'latest': max(all_dates)
                }
        
        info = {
            'total_count': total_count,
            'huggingface_count': total_hf,
            'curated_count': total_curated,
            'data_types': data_types,
            'date_range': date_range,
            'source': f"{self.dataset_name} + 큐레이티드 데이터",
            'data_quality': f"대용량 데이터 {total_hf:,}개 + 고품질 데이터 {total_curated}개"
        }
        
        return info 