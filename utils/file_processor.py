import os
import io
from typing import Optional, List, Dict
from pathlib import Path
import PyPDF2
from docx import Document
from config import Config

class FileProcessor:
    """파일 처리 클래스"""
    
    def __init__(self):
        self.upload_folder = Config.UPLOAD_FOLDER
        self.max_file_size = Config.MAX_FILE_SIZE
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
        
        # 업로드 폴더 생성
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def is_allowed_file(self, filename: str) -> bool:
        """
        허용된 파일 확장자인지 확인
        
        Args:
            filename: 파일명
            
        Returns:
            허용 여부
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def is_valid_file_size(self, file_size: int) -> bool:
        """
        파일 크기가 허용 범위인지 확인
        
        Args:
            file_size: 파일 크기 (bytes)
            
        Returns:
            허용 여부
        """
        return file_size <= self.max_file_size
    
    def save_uploaded_file(self, file_data: bytes, filename: str) -> str:
        """
        업로드된 파일을 저장
        
        Args:
            file_data: 파일 데이터
            filename: 파일명
            
        Returns:
            저장된 파일 경로
        """
        try:
            # 안전한 파일명 생성
            safe_filename = self._make_safe_filename(filename)
            file_path = os.path.join(self.upload_folder, safe_filename)
            
            # 파일 저장
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            return file_path
            
        except Exception as e:
            print(f"파일 저장 오류: {e}")
            return None
    
    def read_text_file(self, file_path: str) -> Optional[str]:
        """
        텍스트 파일 읽기
        
        Args:
            file_path: 파일 경로
            
        Returns:
            파일 내용
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # UTF-8로 읽기 실패시 다른 인코딩 시도
            try:
                with open(file_path, 'r', encoding='cp949') as f:
                    return f.read()
            except Exception as e:
                print(f"텍스트 파일 읽기 오류: {e}")
                return None
        except Exception as e:
            print(f"텍스트 파일 읽기 오류: {e}")
            return None
    
    def read_pdf_file(self, file_path: str) -> Optional[str]:
        """
        PDF 파일 읽기
        
        Args:
            file_path: 파일 경로
            
        Returns:
            추출된 텍스트
        """
        try:
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # 모든 페이지에서 텍스트 추출
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"PDF 파일 읽기 오류: {e}")
            return None
    
    def read_docx_file(self, file_path: str) -> Optional[str]:
        """
        DOCX 파일 읽기
        
        Args:
            file_path: 파일 경로
            
        Returns:
            추출된 텍스트
        """
        try:
            doc = Document(file_path)
            text = ""
            
            # 모든 문단에서 텍스트 추출
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"DOCX 파일 읽기 오류: {e}")
            return None
    
    def read_file(self, file_path: str) -> Optional[str]:
        """
        파일 형식에 따라 적절한 방법으로 파일 읽기
        
        Args:
            file_path: 파일 경로
            
        Returns:
            파일 내용
        """
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.txt':
                return self.read_text_file(file_path)
            elif file_ext == '.pdf':
                return self.read_pdf_file(file_path)
            elif file_ext == '.docx':
                return self.read_docx_file(file_path)
            else:
                print(f"지원하지 않는 파일 형식: {file_ext}")
                return None
                
        except Exception as e:
            print(f"파일 읽기 오류: {e}")
            return None
    
    def process_uploaded_file(self, file_data: bytes, filename: str) -> Dict:
        """
        업로드된 파일을 처리하여 텍스트 추출
        
        Args:
            file_data: 파일 데이터
            filename: 파일명
            
        Returns:
            처리 결과 딕셔너리
        """
        try:
            # 파일 검증
            if not self.is_allowed_file(filename):
                return {
                    'success': False,
                    'error': f'허용되지 않는 파일 형식입니다. 허용 형식: {", ".join(self.allowed_extensions)}'
                }
            
            if not self.is_valid_file_size(len(file_data)):
                return {
                    'success': False,
                    'error': f'파일 크기가 너무 큽니다. 최대 크기: {self.max_file_size / (1024*1024):.1f}MB'
                }
            
            # 파일 저장
            file_path = self.save_uploaded_file(file_data, filename)
            if not file_path:
                return {
                    'success': False,
                    'error': '파일 저장에 실패했습니다.'
                }
            
            # 텍스트 추출
            content = self.read_file(file_path)
            if not content:
                return {
                    'success': False,
                    'error': '파일 내용을 읽을 수 없습니다.'
                }
            
            # 임시 파일 삭제
            try:
                os.remove(file_path)
            except:
                pass
            
            return {
                'success': True,
                'content': content,
                'filename': filename,
                'file_size': len(file_data)
            }
            
        except Exception as e:
            print(f"파일 처리 오류: {e}")
            return {
                'success': False,
                'error': f'파일 처리 중 오류가 발생했습니다: {str(e)}'
            }
    
    def _make_safe_filename(self, filename: str) -> str:
        """
        안전한 파일명 생성
        
        Args:
            filename: 원본 파일명
            
        Returns:
            안전한 파일명
        """
        import re
        import time
        
        # 위험한 문자 제거
        safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # 타임스탬프 추가하여 중복 방지
        timestamp = str(int(time.time()))
        name_parts = safe_name.rsplit('.', 1)
        
        if len(name_parts) == 2:
            return f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
        else:
            return f"{safe_name}_{timestamp}"
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        오래된 임시 파일 정리
        
        Args:
            max_age_hours: 삭제할 파일의 최대 나이 (시간)
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        print(f"오래된 파일 삭제: {filename}")
                        
        except Exception as e:
            print(f"파일 정리 오류: {e}")
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        파일 정보 조회
        
        Args:
            file_path: 파일 경로
            
        Returns:
            파일 정보 딕셔너리
        """
        try:
            stat = os.stat(file_path)
            return {
                'filename': os.path.basename(file_path),
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'extension': Path(file_path).suffix.lower(),
                'is_supported': self.is_allowed_file(file_path)
            }
        except Exception as e:
            print(f"파일 정보 조회 오류: {e}")
            return {} 