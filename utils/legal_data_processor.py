"""
형사법 LLM 데이터 처리 모듈
원천데이터와 라벨링데이터를 처리하여 법률 에이전트에서 활용 가능한 형태로 변환
"""

import pandas as pd
import json
import zipfile
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

class LegalDataProcessor:
    """형사법 LLM 데이터 처리 클래스"""
    
    def __init__(self, data_path: str = "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터"):
        self.data_path = Path(data_path)
        self.training_path = self.data_path / "3.개방데이터" / "1.데이터" / "Training"
        self.validation_path = self.data_path / "3.개방데이터" / "1.데이터" / "Validation"
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def extract_source_data(self, data_type: str = "해석례") -> List[Dict]:
        """
        원천데이터 추출 및 구조화
        
        Args:
            data_type: 데이터 타입 (해석례, 판결문, 결정례, 법령)
        
        Returns:
            구조화된 데이터 리스트
        """
        try:
            zip_path = self.training_path / "01.원천데이터" / f"TS_{data_type}.zip"
            
            if not zip_path.exists():
                self.logger.error(f"파일을 찾을 수 없습니다: {zip_path}")
                return []
            
            extracted_data = []
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    if file_name.endswith('.csv'):
                        with zip_ref.open(file_name) as csv_file:
                            df = pd.read_csv(csv_file, encoding='utf-8-sig')
                            
                            # 해석례 데이터 구조화
                            if data_type == "해석례":
                                case_data = self._process_interpretation_case(df)
                                if case_data:
                                    extracted_data.append(case_data)
                            
                            # 판결문 데이터 구조화
                            elif data_type == "판결문":
                                case_data = self._process_judgment_case(df)
                                if case_data:
                                    extracted_data.append(case_data)
            
            self.logger.info(f"{data_type} 데이터 {len(extracted_data)}건 추출 완료")
            return extracted_data
            
        except Exception as e:
            self.logger.error(f"{data_type} 데이터 추출 오류: {e}")
            return []
    
    def _process_interpretation_case(self, df: pd.DataFrame) -> Optional[Dict]:
        """해석례 데이터 구조화"""
        try:
            case_id = df['해석례일련번호'].iloc[0]
            
            # 구분별로 내용 정리
            query = ""
            answer = ""
            reasons = []
            
            for _, row in df.iterrows():
                if row['구분'] == '질의요지':
                    query = row['내용']
                elif row['구분'] == '회답':
                    answer = row['내용']
                elif row['구분'] == '이유':
                    reasons.append(row['내용'])
            
            return {
                'id': case_id,
                'type': '해석례',
                'query': query,
                'answer': answer,
                'reasons': ' '.join(reasons),
                'full_text': f"질의: {query}\n회답: {answer}\n이유: {' '.join(reasons)}"
            }
            
        except Exception as e:
            self.logger.error(f"해석례 데이터 처리 오류: {e}")
            return None
    
    def _process_judgment_case(self, df: pd.DataFrame) -> Optional[Dict]:
        """판결문 데이터 구조화"""
        try:
            # 판결문 데이터 구조에 따라 처리
            # (실제 구조에 맞게 수정 필요)
            case_id = df.iloc[0, 0] if len(df) > 0 else ""
            
            return {
                'id': case_id,
                'type': '판결문',
                'content': df.to_string(),
                'summary': ""  # 요약은 별도 처리
            }
            
        except Exception as e:
            self.logger.error(f"판결문 데이터 처리 오류: {e}")
            return None
    
    def extract_qa_data(self, data_type: str = "해석례") -> List[Dict]:
        """
        QA 라벨링데이터 추출
        
        Args:
            data_type: 데이터 타입
            
        Returns:
            QA 데이터 리스트
        """
        try:
            zip_path = self.training_path / "02.라벨링데이터" / f"TL_{data_type}_QA.zip"
            
            if not zip_path.exists():
                self.logger.error(f"파일을 찾을 수 없습니다: {zip_path}")
                return []
            
            qa_data = []
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    if file_name.endswith('.json'):
                        with zip_ref.open(file_name) as json_file:
                            data = json.load(json_file)
                            qa_data.extend(self._process_qa_json(data))
            
            self.logger.info(f"{data_type} QA 데이터 {len(qa_data)}건 추출 완료")
            return qa_data
            
        except Exception as e:
            self.logger.error(f"{data_type} QA 데이터 추출 오류: {e}")
            return []
    
    def _process_qa_json(self, data: Dict) -> List[Dict]:
        """QA JSON 데이터 처리"""
        qa_pairs = []
        
        try:
            # JSON 구조에 따라 Q&A 쌍 추출
            if isinstance(data, dict) and 'qa_pairs' in data:
                for qa in data['qa_pairs']:
                    qa_pairs.append({
                        'question': qa.get('question', ''),
                        'answer': qa.get('answer', ''),
                        'context': qa.get('context', ''),
                        'source': qa.get('source', '')
                    })
            
        except Exception as e:
            self.logger.error(f"QA JSON 처리 오류: {e}")
        
        return qa_pairs
    
    def create_knowledge_base(self) -> Dict[str, List[Dict]]:
        """
        통합 법률 지식베이스 생성
        
        Returns:
            데이터 타입별 지식베이스
        """
        knowledge_base = {
            '해석례': [],
            '판결문': [],
            '결정례': [],
            '법령': [],
            'qa_pairs': []
        }
        
        # 원천데이터 추출
        for data_type in ['해석례', '판결문', '결정례', '법령']:
            knowledge_base[data_type] = self.extract_source_data(data_type)
        
        # QA 데이터 추출
        for data_type in ['해석례', '판결문', '결정례', '법령']:
            qa_data = self.extract_qa_data(data_type)
            knowledge_base['qa_pairs'].extend(qa_data)
        
        return knowledge_base
    
    def save_knowledge_base(self, knowledge_base: Dict, output_path: str = "legal_knowledge_base.json"):
        """지식베이스를 JSON 파일로 저장"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"지식베이스 저장 완료: {output_path}")
            
        except Exception as e:
            self.logger.error(f"지식베이스 저장 오류: {e}")
    
    def get_embedding_data(self) -> List[Dict]:
        """벡터 임베딩을 위한 텍스트 데이터 준비"""
        knowledge_base = self.create_knowledge_base()
        embedding_data = []
        
        # 해석례 데이터
        for case in knowledge_base['해석례']:
            embedding_data.append({
                'id': f"interpretation_{case['id']}",
                'text': case['full_text'],
                'metadata': {
                    'type': '해석례',
                    'case_id': case['id'],
                    'query': case['query'],
                    'answer': case['answer']
                }
            })
        
        # 판결문 데이터
        for case in knowledge_base['판결문']:
            embedding_data.append({
                'id': f"judgment_{case['id']}",
                'text': case['content'],
                'metadata': {
                    'type': '판결문',
                    'case_id': case['id']
                }
            })
        
        # QA 데이터
        for i, qa in enumerate(knowledge_base['qa_pairs']):
            embedding_data.append({
                'id': f"qa_{i}",
                'text': f"질문: {qa['question']}\n답변: {qa['answer']}",
                'metadata': {
                    'type': 'QA',
                    'question': qa['question'],
                    'answer': qa['answer'],
                    'context': qa['context']
                }
            })
        
        return embedding_data


if __name__ == "__main__":
    # 테스트 실행
    processor = LegalDataProcessor()
    
    # 해석례 데이터 추출 테스트
    interpretation_data = processor.extract_source_data("해석례")
    print(f"추출된 해석례 데이터: {len(interpretation_data)}건")
    
    if interpretation_data:
        print("\n첫 번째 해석례 예시:")
        print(json.dumps(interpretation_data[0], ensure_ascii=False, indent=2)) 