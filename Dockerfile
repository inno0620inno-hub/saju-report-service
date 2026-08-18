# 사주 리포트 서비스 배포용 Dockerfile
# Railway가 이 파일을 보고 자동으로 서버 환경을 만들어줍니다.

FROM python:3.12-slim

# PDF 생성에 필요한 프로그램(wkhtmltopdf)과 한글 폰트를 설치
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 파이썬 패키지 설치
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 전체 복사
COPY . .

# 생성된 PDF를 저장할 폴더 (server.py가 webapp 폴더에서 실행되므로 여기 생성)
RUN mkdir -p /app/webapp/generated_reports

WORKDIR /app/webapp

# Railway는 PORT 환경변수로 포트를 알려주므로 그걸 사용
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
