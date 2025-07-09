import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import faiss

class TextAnalyzer:
    """텍스트 분석 및 유사도 계산 클래스"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        텍스트 분석기 초기화
        
        Args:
            model_name: 사용할 sentence transformer 모델명
        """
        try:
            # 더 간단하고 안정적인 모델로 변경
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"SentenceTransformer 로딩 오류: {e}")
            print("기본 임베딩 모델을 사용합니다.")
            self.model = None
        
        self.index = None
        self.precedent_embeddings = None
        self.precedent_data = None
    
    def preprocess_text(self, text: str) -> str:
        """
        텍스트 전처리
        
        Args:
            text: 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        try:
            # 줄바꿈 문자 정리
            text = text.replace('\n', ' ').replace('\r', ' ')
            
            # 여러 공백을 하나로 통합
            text = re.sub(r'\s+', ' ', text)
            
            # 특수 문자 정리 (법률 문서에서 필요한 것들은 유지)
            text = re.sub(r'[^\w\s가-힣.,()[\]{}:;!?-]', ' ', text)
            
            # 앞뒤 공백 제거
            text = text.strip()
            
            return text
            
        except Exception as e:
            print(f"텍스트 전처리 오류: {e}")
            return text
    
    def extract_legal_terms(self, text: str) -> List[str]:
        """
        법률 용어 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            추출된 법률 용어 리스트
        """
        try:
            # 법률 용어 패턴들
            patterns = [
                r'(형법|민법|상법|행정법|형사소송법|민사소송법)\s*제?\s*(\d+조)',  # 법령 조문
                r'(징역|벌금|과료|구류|과태료|집행유예|선고유예)\s*(\d+년?\s*\d*개월?|\d+만원?)',  # 형량
                r'(고발|고소|기소|고발|체포|구속|영장|수사|재판|판결|선고)',  # 법적 절차
                r'(사기|절도|강도|살인|폭행|상해|협박|공갈|모욕|명예훼손|도박|음주운전)',  # 범죄 유형
                r'(위자료|손해배상|정신적피해|재산피해|피해보상)',  # 피해 관련
                r'(증거|증인|진술|자백|묵비권|변호사|검사|판사)',  # 법정 관련
            ]
            
            legal_terms = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        legal_terms.extend([term for term in match if term])
                    else:
                        legal_terms.append(match)
            
            # 중복 제거
            legal_terms = list(set(legal_terms))
            
            return legal_terms
            
        except Exception as e:
            print(f"법률 용어 추출 오류: {e}")
            return []
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트 간 유사도 계산
        
        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트
            
        Returns:
            유사도 점수 (0-1)
        """
        try:
            if self.model is None:
                # 기본 텍스트 기반 유사도 계산 (Jaccard 유사도)
                return self._calculate_basic_similarity(text1, text2)
            
            # 텍스트 전처리
            text1 = self.preprocess_text(text1)
            text2 = self.preprocess_text(text2)
            
            # 임베딩 생성
            embeddings = self.model.encode([text1, text2])
            
            # 코사인 유사도 계산
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            print(f"유사도 계산 오류: {e}")
            return self._calculate_basic_similarity(text1, text2)
    
    def build_precedent_index(self, precedents: List[Dict]):
        """
        판례 검색을 위한 인덱스 구축
        
        Args:
            precedents: 판례 데이터 리스트
        """
        try:
            if self.model is None:
                # 모델이 없으면 간단한 텍스트 기반 저장
                self.precedent_data = precedents
                print("텍스트 기반 판례 데이터 저장 완료")
                return
            
            # 판례 텍스트 추출 및 전처리
            texts = []
            for precedent in precedents:
                text = f"{precedent.get('title', '')} {precedent.get('summary', '')} {precedent.get('keywords', '')}"
                texts.append(self.preprocess_text(text))
            
            # 임베딩 생성
            embeddings = self.model.encode(texts)
            
            # FAISS 인덱스 생성
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # Inner Product (코사인 유사도)
            
            # 정규화 후 인덱스에 추가
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings.astype(np.float32))
            
            # 참조 데이터 저장
            self.precedent_embeddings = embeddings
            self.precedent_data = precedents
            
        except Exception as e:
            print(f"판례 인덱스 구축 오류: {e}")
            # 오류 발생 시 기본 저장
            self.precedent_data = precedents
    
    def search_similar_precedents(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        유사한 판례 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
            
        Returns:
            (판례, 유사도) 튜플 리스트
        """
        try:
            if self.precedent_data is None:
                print("판례 데이터가 구축되지 않았습니다.")
                return []
            
            if self.model is None or self.index is None:
                # 기본 텍스트 기반 검색
                return self._search_precedents_basic(query, top_k)
            
            # 쿼리 전처리 및 임베딩
            query = self.preprocess_text(query)
            query_embedding = self.model.encode([query])
            
            # 정규화
            faiss.normalize_L2(query_embedding)
            
            # 검색 수행
            scores, indices = self.index.search(query_embedding.astype(np.float32), top_k)
            
            # 결과 구성
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.precedent_data):
                    results.append((self.precedent_data[idx], float(score)))
            
            return results
            
        except Exception as e:
            print(f"판례 검색 오류: {e}")
            return self._search_precedents_basic(query, top_k)
    
    def extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """
        핵심 구문 추출
        
        Args:
            text: 분석할 텍스트
            max_phrases: 최대 추출할 구문 수
            
        Returns:
            핵심 구문 리스트
        """
        try:
            # 문장 분리
            sentences = re.split(r'[.!?]', text)
            
            # 짧은 문장들 제거
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            if not sentences:
                return []
            
            if self.model is None:
                # 기본 방식: 법률 용어가 많은 문장을 우선
                return self._extract_key_phrases_basic(sentences, max_phrases)
            
            # 문장 임베딩 생성
            embeddings = self.model.encode(sentences)
            
            # 문서 전체 임베딩 생성
            doc_embedding = self.model.encode([text])
            
            # 각 문장과 문서 간 유사도 계산
            similarities = cosine_similarity(embeddings, doc_embedding).flatten()
            
            # 유사도가 높은 순으로 정렬
            top_indices = np.argsort(similarities)[::-1][:max_phrases]
            
            # 상위 문장들 반환
            key_phrases = [sentences[i] for i in top_indices]
            
            return key_phrases
            
        except Exception as e:
            print(f"핵심 구문 추출 오류: {e}")
            return self._extract_key_phrases_basic(sentences, max_phrases) if sentences else []
    
    def analyze_text_structure(self, text: str) -> Dict:
        """
        텍스트 구조 분석
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            구조 분석 결과
        """
        try:
            # 기본 통계
            word_count = len(text.split())
            char_count = len(text)
            sentence_count = len(re.split(r'[.!?]', text))
            
            # 법률 용어 분석
            legal_terms = self.extract_legal_terms(text)
            
            # 숫자 패턴 분석
            numbers = re.findall(r'\d+', text)
            dates = re.findall(r'\d{4}[년.-]\d{1,2}[월.-]\d{1,2}[일]?', text)
            
            # 문장 길이 분석
            sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            
            return {
                'word_count': word_count,
                'char_count': char_count,
                'sentence_count': sentence_count,
                'legal_terms': legal_terms,
                'legal_term_count': len(legal_terms),
                'numbers': numbers,
                'dates': dates,
                'avg_sentence_length': avg_sentence_length,
                'complexity_score': self._calculate_complexity(text)
            }
            
        except Exception as e:
            print(f"텍스트 구조 분석 오류: {e}")
            return {}
    
    def _calculate_complexity(self, text: str) -> float:
        """
        텍스트 복잡도 계산
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            복잡도 점수 (0-1)
        """
        try:
            # 문장 길이 분석
            sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
            if not sentences:
                return 0.0
            
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            
            # 어휘 다양성 분석
            words = text.split()
            unique_words = set(words)
            lexical_diversity = len(unique_words) / len(words) if words else 0
            
            # 법률 용어 밀도
            legal_terms = self.extract_legal_terms(text)
            legal_term_density = len(legal_terms) / len(words) if words else 0
            
            # 복잡도 계산 (가중 평균)
            complexity = (
                (avg_sentence_length / 50) * 0.4 +  # 문장 길이 (최대 50단어 가정)
                lexical_diversity * 0.3 +  # 어휘 다양성
                legal_term_density * 0.3  # 법률 용어 밀도
            )
            
            return min(complexity, 1.0)
            
        except Exception as e:
            print(f"복잡도 계산 오류: {e}")
            return 0.0
    
    def find_similar_patterns(self, texts: List[str], threshold: float = 0.7) -> List[List[int]]:
        """
        유사한 패턴을 가진 텍스트 그룹 찾기
        
        Args:
            texts: 텍스트 리스트
            threshold: 유사도 임계값
            
        Returns:
            유사한 텍스트들의 인덱스 그룹
        """
        try:
            if len(texts) < 2:
                return []
            
            if self.model is None:
                # 기본 텍스트 기반 그룹핑
                return self._find_similar_patterns_basic(texts, threshold)
            
            # 임베딩 생성
            embeddings = self.model.encode(texts)
            
            # 유사도 행렬 계산
            similarity_matrix = cosine_similarity(embeddings)
            
            # 유사한 그룹 찾기
            groups = []
            visited = set()
            
            for i in range(len(texts)):
                if i in visited:
                    continue
                
                group = [i]
                visited.add(i)
                
                for j in range(i + 1, len(texts)):
                    if j not in visited and similarity_matrix[i][j] >= threshold:
                        group.append(j)
                        visited.add(j)
                
                if len(group) > 1:
                    groups.append(group)
            
            return groups
            
        except Exception as e:
            print(f"유사 패턴 찾기 오류: {e}")
            return self._find_similar_patterns_basic(texts, threshold)
    
    def _calculate_basic_similarity(self, text1: str, text2: str) -> float:
        """
        기본 텍스트 유사도 계산 (모델이 없을 때 사용)
        
        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트
            
        Returns:
            유사도 점수 (0-1)
        """
        try:
            # 텍스트 전처리
            text1 = self.preprocess_text(text1.lower())
            text2 = self.preprocess_text(text2.lower())
            
            # 단어 집합 생성
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            # Jaccard 유사도 계산
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            if union == 0:
                return 0.0
            
            jaccard_similarity = intersection / union
            
            # 법률 용어 가중치 적용
            legal_terms1 = set(self.extract_legal_terms(text1))
            legal_terms2 = set(self.extract_legal_terms(text2))
            legal_intersection = len(legal_terms1.intersection(legal_terms2))
            
            if legal_intersection > 0:
                # 법률 용어가 일치하면 가중치 추가
                jaccard_similarity += 0.2 * (legal_intersection / max(len(legal_terms1), len(legal_terms2), 1))
            
            return min(jaccard_similarity, 1.0)
            
        except Exception as e:
            print(f"기본 유사도 계산 오류: {e}")
            return 0.0
    
    def _search_precedents_basic(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        기본 텍스트 기반 판례 검색 (모델이 없을 때 사용)
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
            
        Returns:
            (판례, 유사도) 튜플 리스트
        """
        try:
            if not self.precedent_data:
                return []
            
            query = self.preprocess_text(query.lower())
            query_words = set(query.split())
            query_legal_terms = set(self.extract_legal_terms(query))
            
            results = []
            
            for precedent in self.precedent_data:
                # 판례 텍스트 생성
                prec_text = f"{precedent.get('title', '')} {precedent.get('summary', '')} {precedent.get('keywords', '')}"
                prec_text = self.preprocess_text(prec_text.lower())
                prec_words = set(prec_text.split())
                prec_legal_terms = set(self.extract_legal_terms(prec_text))
                
                # 기본 단어 매칭 점수
                word_intersection = len(query_words.intersection(prec_words))
                word_union = len(query_words.union(prec_words))
                word_score = word_intersection / word_union if word_union > 0 else 0
                
                # 법률 용어 매칭 점수 (가중치 적용)
                legal_intersection = len(query_legal_terms.intersection(prec_legal_terms))
                legal_score = legal_intersection / max(len(query_legal_terms), 1) if legal_intersection > 0 else 0
                
                # 제목 매칭 보너스
                title_score = 0
                if precedent.get('title'):
                    title_words = set(precedent['title'].lower().split())
                    title_intersection = len(query_words.intersection(title_words))
                    title_score = title_intersection / len(title_words) if title_words else 0
                
                # 종합 점수 계산
                total_score = (word_score * 0.4) + (legal_score * 0.4) + (title_score * 0.2)
                
                if total_score > 0:
                    results.append((precedent, total_score))
            
            # 점수 순으로 정렬하고 상위 k개 반환
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            print(f"기본 판례 검색 오류: {e}")
            return []
    
    def _extract_key_phrases_basic(self, sentences: List[str], max_phrases: int = 10) -> List[str]:
        """
        기본 핵심 구문 추출 (모델이 없을 때 사용)
        
        Args:
            sentences: 문장 리스트
            max_phrases: 최대 추출할 구문 수
            
        Returns:
            핵심 구문 리스트
        """
        try:
            scored_sentences = []
            
            for sentence in sentences:
                score = 0
                
                # 법률 용어 점수
                legal_terms = self.extract_legal_terms(sentence)
                score += len(legal_terms) * 2
                
                # 문장 길이 점수 (너무 짧거나 길지 않은 문장 선호)
                length = len(sentence.split())
                if 5 <= length <= 30:
                    score += 1
                
                # 숫자나 날짜 포함 점수 (법률 문서에서 중요할 수 있음)
                if re.search(r'\d+', sentence):
                    score += 1
                
                # 특정 키워드 포함 점수
                important_keywords = ['판결', '선고', '형량', '벌금', '징역', '피고인', '피해자', '법원', '조항']
                for keyword in important_keywords:
                    if keyword in sentence:
                        score += 1
                
                scored_sentences.append((sentence, score))
            
            # 점수 순으로 정렬
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 문장들 반환
            return [sentence for sentence, _ in scored_sentences[:max_phrases]]
            
        except Exception as e:
            print(f"기본 핵심 구문 추출 오류: {e}")
            return sentences[:max_phrases] if sentences else []
    
    def _find_similar_patterns_basic(self, texts: List[str], threshold: float = 0.7) -> List[List[int]]:
        """
        기본 텍스트 유사 패턴 찾기 (모델이 없을 때 사용)
        
        Args:
            texts: 텍스트 리스트
            threshold: 유사도 임계값
            
        Returns:
            유사한 텍스트들의 인덱스 그룹
        """
        try:
            if len(texts) < 2:
                return []
            
            groups = []
            visited = set()
            
            for i in range(len(texts)):
                if i in visited:
                    continue
                
                group = [i]
                visited.add(i)
                
                for j in range(i + 1, len(texts)):
                    if j not in visited:
                        similarity = self._calculate_basic_similarity(texts[i], texts[j])
                        if similarity >= threshold:
                            group.append(j)
                            visited.add(j)
                
                if len(group) > 1:
                    groups.append(group)
            
            return groups
            
        except Exception as e:
            print(f"기본 유사 패턴 찾기 오류: {e}")
            return [] 