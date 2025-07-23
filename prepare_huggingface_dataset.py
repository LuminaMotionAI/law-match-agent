#!/usr/bin/env python3
"""
형사법 LLM 데이터를 허깅페이스 데이터셋으로 변환하는 스크립트
"""

import json
import os
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi, create_repo

def load_json_files(data_dir):
    """JSON 파일들을 로드하고 통합된 데이터셋 생성"""
    all_data = []
    data_types = ['결정례_QA', '결정례_SUM', '법령_QA', '판결문_QA', '판결문_SUM', '해석례_QA', '해석례_SUM']
    
    print(f"📂 데이터 디렉토리: {data_dir}")
    
    for data_type in data_types:
        # Training 데이터
        train_dir = Path(data_dir) / "Training" / "02.라벨링데이터" / f"TL_{data_type}"
        if train_dir.exists():
            print(f"📄 {data_type} Training 데이터 로딩...")
            load_from_directory(train_dir, all_data, "train", data_type)
        
        # Validation 데이터 (압축파일이므로 스킵)
        # val_dir = Path(data_dir) / "Validation" / "02.라벨링데이터" / f"VL_{data_type}"
    
    print(f"✅ 총 {len(all_data)}개의 데이터 로드 완료")
    return all_data

def load_from_directory(directory, all_data, split, data_type):
    """특정 디렉토리에서 JSON 파일들을 로드"""
    json_files = list(directory.glob("*.json"))
    print(f"   - {len(json_files)}개 파일 발견")
    
    for json_file in tqdm(json_files, desc=f"Loading {data_type}"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 데이터 구조 변환
                processed_data = {
                    'id': data.get('info', {}).get('determintId', ''),
                    'case_number': data.get('info', {}).get('caseNum', ''),
                    'case_name': data.get('info', {}).get('caseName', ''),
                    'court_code': data.get('info', {}).get('courtCode', ''),
                    'final_date': data.get('info', {}).get('finalDate', ''),
                    'law_class': data.get('info', {}).get('lawClass', ''),
                    'docu_type': data.get('info', {}).get('DocuType', ''),
                    'case_code': data.get('info', {}).get('caseCode', ''),
                    'instruction': data.get('label', {}).get('instruction', ''),
                    'input': data.get('label', {}).get('input', ''),
                    'output': data.get('label', {}).get('output', ''),
                    'origin_word_count': data.get('label', {}).get('originwordCnt', ''),
                    'label_word_count': data.get('label', {}).get('labelwordCnt', ''),
                    'data_type': data_type,
                    'split': split,
                    'file_name': json_file.name
                }
                
                all_data.append(processed_data)
                
        except Exception as e:
            print(f"❌ {json_file} 로드 실패: {e}")
            continue

def create_huggingface_dataset(all_data):
    """허깅페이스 데이터셋 형식으로 변환"""
    print("🔄 데이터셋 변환 중...")
    
    # 데이터타입별로 분류
    datasets = {}
    
    for data_type in ['결정례_QA', '결정례_SUM', '법령_QA', '판결문_QA', '판결문_SUM', '해석례_QA', '해석례_SUM']:
        filtered_data = [item for item in all_data if item['data_type'] == data_type]
        if filtered_data:
            datasets[data_type] = Dataset.from_list(filtered_data)
            print(f"✅ {data_type}: {len(filtered_data)}개 데이터")
    
    # 전체 통합 데이터셋
    datasets['all'] = Dataset.from_list(all_data)
    print(f"✅ 전체: {len(all_data)}개 데이터")
    
    return DatasetDict(datasets)

def upload_to_huggingface(dataset_dict, repo_name, token=None):
    """허깅페이스에 데이터셋 업로드"""
    print(f"🚀 허깅페이스에 업로드: {repo_name}")
    
    if not token:
        print("❌ 허깅페이스 토큰이 필요합니다.")
        print("https://huggingface.co/settings/tokens 에서 토큰을 생성하세요.")
        return False
    
    try:
        # 레포지토리 생성
        api = HfApi(token=token)
        create_repo(
            repo_id=repo_name,
            token=token,
            repo_type="dataset",
            exist_ok=True
        )
        
        # 데이터셋 업로드
        dataset_dict.push_to_hub(
            repo_id=repo_name,
            token=token
        )
        
        print(f"✅ 업로드 완료: https://huggingface.co/datasets/{repo_name}")
        return True
        
    except Exception as e:
        print(f"❌ 업로드 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 형사법 LLM 데이터셋 허깅페이스 준비 시작...")
    
    # 데이터 디렉토리 경로
    data_dir = "04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터"
    
    if not os.path.exists(data_dir):
        print(f"❌ 데이터 디렉토리를 찾을 수 없습니다: {data_dir}")
        return
    
    # 1. 데이터 로드
    all_data = load_json_files(data_dir)
    
    if not all_data:
        print("❌ 로드된 데이터가 없습니다.")
        return
    
    # 2. 허깅페이스 데이터셋으로 변환
    dataset_dict = create_huggingface_dataset(all_data)
    
    # 3. 로컬 저장 (선택사항)
    print("💾 로컬에 데이터셋 저장...")
    dataset_dict.save_to_disk("korean_legal_dataset")
    
    # 4. 데이터셋 정보 출력
    print("\n📊 데이터셋 정보:")
    for key, dataset in dataset_dict.items():
        print(f"  - {key}: {len(dataset)}개 샘플")
        if len(dataset) > 0:
            print(f"    컬럼: {list(dataset.column_names)}")
    
    # 5. 샘플 데이터 확인
    if len(dataset_dict['all']) > 0:
        print(f"\n📋 샘플 데이터:")
        sample = dataset_dict['all'][0]
        for key, value in sample.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    
    print("\n🎉 데이터셋 준비 완료!")
    print("\n📝 다음 단계:")
    print("1. 허깅페이스 계정 생성: https://huggingface.co/join")
    print("2. 토큰 생성: https://huggingface.co/settings/tokens")
    print("3. 업로드 실행:")
    print("   python prepare_huggingface_dataset.py --upload --token YOUR_TOKEN --repo YOUR_USERNAME/korean-legal-dataset")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="형사법 LLM 데이터셋 허깅페이스 준비")
    parser.add_argument("--upload", action="store_true", help="허깅페이스에 업로드")
    parser.add_argument("--token", type=str, help="허깅페이스 토큰")
    parser.add_argument("--repo", type=str, default="korean-legal-dataset", help="레포지토리 이름")
    
    args = parser.parse_args()
    
    if args.upload:
        if not args.token:
            print("❌ --token 옵션이 필요합니다.")
        else:
            # 업로드 모드
            main()
            
            # 데이터셋 로드 후 업로드
            from datasets import load_from_disk
            dataset_dict = load_from_disk("korean_legal_dataset")
            upload_to_huggingface(dataset_dict, args.repo, args.token)
    else:
        # 준비만 실행
        main() 