"""
고급 법률 벡터 데이터베이스 구축 스크립트
형사법 LLM 데이터를 활용한 정확도 높은 유사 사례 검색 시스템
"""

import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from utils.legal_data_processor import LegalDataProcessor
import pickle
import logging
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

class AdvancedLegalVectorDB:
    """고급 법률 벡터 데이터베이스 클래스"""
    
    def __init__(self, 
                 model_name: str = "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
                 index_path: str = "legal_vector.index",
                 metadata_path: str = "legal_metadata.pkl"):
        
        self.model_name = model_name
        self.index_path = index_path
        self.metadata_path = metadata_path
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 모델 초기화
        try:
            self.model = SentenceTransformer(model_name)
            self.logger.info(f"모델 로드 성공: {model_name}")
        except Exception as e:
            self.logger.warning(f"기본 모델 로드 실패: {e}")
            try:
                self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                self.logger.info("대체 모델 사용: all-MiniLM-L6-v2")
            except Exception as e2:
                self.logger.error(f"모델 로드 완전 실패: {e2}")
                self.model = None
        
        self.index = None
        self.metadata = []
        self.dimension = 384  # 기본 임베딩 차원
    
    def build_knowledge_base(self) -> Dict:
        """형사법 LLM 데이터로부터 지식베이스 구축"""
        self.logger.info("형사법 LLM 데이터 처리 시작...")
        
        processor = LegalDataProcessor()
        
        try:
            # 지식베이스 생성
            knowledge_base = processor.create_knowledge_base()
            
            # 임베딩용 데이터 준비
            embedding_data = processor.get_embedding_data()
            
            self.logger.info(f"총 {len(embedding_data)}개의 문서 준비 완료")
            
            # 지식베이스 저장
            processor.save_knowledge_base(knowledge_base, "enhanced_legal_knowledge_base.json")
            
            return knowledge_base, embedding_data
            
        except Exception as e:
            self.logger.error(f"지식베이스 구축 오류: {e}")
            return {}, []
    
    def create_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """텍스트 리스트를 벡터 임베딩으로 변환"""
        if self.model is None:
            self.logger.error("모델이 로드되지 않음")
            return np.array([])
        
        embeddings = []
        
        try:
            # 배치 단위로 임베딩 생성
            for i in tqdm(range(0, len(texts), batch_size), desc="임베딩 생성"):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch_texts,
                    convert_to_tensor=False,
                    show_progress_bar=False
                )
                embeddings.extend(batch_embeddings)
            
            embeddings_array = np.array(embeddings).astype('float32')
            self.dimension = embeddings_array.shape[1]
            
            self.logger.info(f"임베딩 생성 완료: {embeddings_array.shape}")
            return embeddings_array
            
        except Exception as e:
            self.logger.error(f"임베딩 생성 오류: {e}")
            return np.array([])
    
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """FAISS 인덱스 구축"""
        try:
            # IVF + PQ 인덱스 (대용량 데이터에 효율적)
            if len(embeddings) > 1000:
                nlist = min(int(np.sqrt(len(embeddings))), 100)  # 클러스터 수
                quantizer = faiss.IndexFlatIP(self.dimension)  # Inner Product (코사인 유사도)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
                
                # 훈련
                index.train(embeddings)
                index.add(embeddings)
                index.nprobe = min(10, nlist)  # 검색 시 탐색할 클러스터 수
                
                self.logger.info(f"IVF 인덱스 구축 완료: {len(embeddings)}개 벡터, {nlist}개 클러스터")
                
            else:
                # 작은 데이터셋의 경우 Flat 인덱스
                index = faiss.IndexFlatIP(self.dimension)
                index.add(embeddings)
                
                self.logger.info(f"Flat 인덱스 구축 완료: {len(embeddings)}개 벡터")
            
            return index
            
        except Exception as e:
            self.logger.error(f"FAISS 인덱스 구축 오류: {e}")
            return None
    
    def build_vector_db(self):
        """전체 벡터 데이터베이스 구축 프로세스"""
        self.logger.info("🚀 고급 법률 벡터 데이터베이스 구축 시작")
        
        # 1. 지식베이스 구축
        knowledge_base, embedding_data = self.build_knowledge_base()
        
        if not embedding_data:
            self.logger.error("임베딩 데이터가 없습니다.")
            return False
        
        # 2. 텍스트 추출
        texts = [item['text'] for item in embedding_data]
        
        # 3. 임베딩 생성
        self.logger.info("벡터 임베딩 생성 중...")
        embeddings = self.create_embeddings(texts)
        
        if embeddings.size == 0:
            self.logger.error("임베딩 생성 실패")
            return False
        
        # 4. FAISS 인덱스 구축
        self.logger.info("FAISS 인덱스 구축 중...")
        self.index = self.build_faiss_index(embeddings)
        
        if self.index is None:
            self.logger.error("인덱스 구축 실패")
            return False
        
        # 5. 메타데이터 저장
        self.metadata = embedding_data
        
        # 6. 파일 저장
        self.save_index()
        self.save_metadata()
        
        self.logger.info("✅ 벡터 데이터베이스 구축 완료!")
        return True
    
    def save_index(self):
        """FAISS 인덱스 저장"""
        try:
            faiss.write_index(self.index, self.index_path)
            self.logger.info(f"인덱스 저장 완료: {self.index_path}")
        except Exception as e:
            self.logger.error(f"인덱스 저장 오류: {e}")
    
    def save_metadata(self):
        """메타데이터 저장"""
        try:
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
            self.logger.info(f"메타데이터 저장 완료: {self.metadata_path}")
        except Exception as e:
            self.logger.error(f"메타데이터 저장 오류: {e}")
    
    def load_index(self) -> bool:
        """저장된 인덱스 로드"""
        try:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                self.logger.info(f"인덱스 로드 완료: {self.index_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"인덱스 로드 오류: {e}")
            return False
    
    def load_metadata(self) -> bool:
        """저장된 메타데이터 로드"""
        try:
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                self.logger.info(f"메타데이터 로드 완료: {self.metadata_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"메타데이터 로드 오류: {e}")
            return False
    
    def search_similar_cases(self, 
                           query: str, 
                           top_k: int = 5, 
                           case_type: Optional[str] = None) -> List[Dict]:
        """유사 사례 검색"""
        if self.model is None or self.index is None:
            self.logger.error("모델 또는 인덱스가 준비되지 않음")
            return []
        
        try:
            # 쿼리 임베딩
            query_embedding = self.model.encode([query], convert_to_tensor=False)
            query_embedding = np.array(query_embedding).astype('float32')
            
            # 유사도 검색
            scores, indices = self.index.search(query_embedding, top_k * 2)  # 여유분 확보
            
            results = []
            added_cases = set()  # 중복 제거용
            
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= len(self.metadata):
                    continue
                
                case_data = self.metadata[idx].copy()
                case_data['similarity_score'] = float(score)
                case_data['rank'] = i + 1
                
                # 사건 유형 필터링
                if case_type and case_data.get('metadata', {}).get('type') != case_type:
                    continue
                
                # 중복 제거 (같은 사건 ID)
                case_id = case_data.get('metadata', {}).get('case_id', '')
                if case_id and case_id in added_cases:
                    continue
                
                results.append(case_data)
                if case_id:
                    added_cases.add(case_id)
                
                if len(results) >= top_k:
                    break
            
            self.logger.info(f"유사 사례 검색 완료: {len(results)}건 반환")
            return results
            
        except Exception as e:
            self.logger.error(f"유사 사례 검색 오류: {e}")
            return []
    
    def get_case_statistics(self) -> Dict:
        """데이터베이스 통계 정보"""
        if not self.metadata:
            return {}
        
        stats = {
            'total_cases': len(self.metadata),
            'case_types': {},
            'avg_text_length': 0
        }
        
        text_lengths = []
        
        for item in self.metadata:
            # 사건 유형별 통계
            case_type = item.get('metadata', {}).get('type', 'Unknown')
            stats['case_types'][case_type] = stats['case_types'].get(case_type, 0) + 1
            
            # 텍스트 길이 통계
            text_length = len(item.get('text', ''))
            text_lengths.append(text_length)
        
        if text_lengths:
            stats['avg_text_length'] = sum(text_lengths) / len(text_lengths)
            stats['min_text_length'] = min(text_lengths)
            stats['max_text_length'] = max(text_lengths)
        
        return stats


def main():
    """메인 실행 함수"""
    print("🏛️  고급 형사법 벡터 데이터베이스 구축 시스템")
    print("=" * 60)
    
    # 벡터 DB 인스턴스 생성
    vector_db = AdvancedLegalVectorDB()
    
    # 기존 인덱스 확인
    if vector_db.load_index() and vector_db.load_metadata():
        print("✅ 기존 인덱스 발견됨")
        
        rebuild = input("새로 구축하시겠습니까? (y/N): ").strip().lower()
        if rebuild != 'y':
            print("기존 인덱스를 사용합니다.")
            
            # 통계 정보 출력
            stats = vector_db.get_case_statistics()
            print(f"\n📊 데이터베이스 통계:")
            print(f"전체 사례: {stats.get('total_cases', 0)}건")
            print(f"사건 유형별:")
            for case_type, count in stats.get('case_types', {}).items():
                print(f"  - {case_type}: {count}건")
            
            # 검색 테스트
            test_query = input("\n검색할 질의를 입력하세요 (엔터 시 기본 예시): ").strip()
            if not test_query:
                test_query = "교통사고로 인한 손해배상책임은 어떻게 되나요?"
            
            print(f"\n🔍 검색 질의: {test_query}")
            results = vector_db.search_similar_cases(test_query, top_k=3)
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. 유사도: {result['similarity_score']:.4f}")
                print(f"   유형: {result.get('metadata', {}).get('type', 'Unknown')}")
                print(f"   내용: {result.get('text', '')[:200]}...")
            
            return
    
    # 새로 구축
    print("🚀 새로운 벡터 데이터베이스 구축을 시작합니다...")
    
    success = vector_db.build_vector_db()
    
    if success:
        print("\n🎉 벡터 데이터베이스 구축 성공!")
        
        # 통계 정보 출력
        stats = vector_db.get_case_statistics()
        print(f"\n📊 구축된 데이터베이스 통계:")
        print(f"전체 사례: {stats.get('total_cases', 0)}건")
        print(f"평균 텍스트 길이: {stats.get('avg_text_length', 0):.0f}자")
        print(f"사건 유형별:")
        for case_type, count in stats.get('case_types', {}).items():
            print(f"  - {case_type}: {count}건")
        
    else:
        print("❌ 벡터 데이터베이스 구축 실패")


if __name__ == "__main__":
    main() 