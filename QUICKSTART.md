# Quick Start Guide

## 🚀 빠른 시작

### 필수 요구사항
- Python 3.8 이상
- pip (Python 패키지 관리자)

### 1단계: 백엔드 의존성 설치

```bash
# Python이 설치되어 있는지 확인
python --version
# 또는
python3 --version

# 의존성 설치
python -m pip install -r backend/requirements.txt
# 또는
python3 -m pip install -r backend/requirements.txt
```

### 2단계: 서버 실행

**방법 1: uvicorn 직접 실행**
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**방법 2: main.py 실행**
```bash
cd backend
python main.py
```

**방법 3: 프로젝트 루트에서 실행**
```bash
python -m backend.main
```

### 3단계: 브라우저에서 접속

```
http://localhost:8000
```

## 🔧 문제 해결

### Python을 찾을 수 없는 경우

1. **Python 설치 확인**
   - Windows: Microsoft Store에서 Python 설치
   - 또는 https://www.python.org/downloads/ 에서 다운로드

2. **PATH 환경변수 확인**
   - Python 설치 시 "Add Python to PATH" 체크

3. **가상환경 사용 (권장)**
   ```bash
   # 가상환경 생성
   python -m venv venv
   
   # 가상환경 활성화 (Windows)
   venv\Scripts\activate
   
   # 가상환경 활성화 (Mac/Linux)
   source venv/bin/activate
   
   # 의존성 설치
   pip install -r backend/requirements.txt
   ```

### 포트가 이미 사용 중인 경우

다른 포트 사용:
```bash
python -m uvicorn backend.main:app --reload --port 8080
```

## 📚 API 문서

서버 실행 후 자동 생성된 API 문서 확인:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🎯 다음 단계

1. 브라우저에서 http://localhost:8000 접속
2. 날짜와 설정 입력
3. "🚀 실행하기" 버튼 클릭
4. 실시간 진행상황 확인
5. 결과 탭에서 요약, 이미지, TTS, 쇼츠 확인
