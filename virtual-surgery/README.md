# 가상 성형 시뮬레이터 (virtual-surgery)

사진을 업로드하고 눈/코/턱선/광대/입술/피부 중 원하는 항목을 고르면,
Google Gemini 이미지 편집 모델(`gemini-2.5-flash-image`)이 "시술을 받았다면
이런 느낌일까?"를 재미로 보여주는 독립 웹앱입니다. 의학적으로 정확한
시뮬레이션이 아니며, 사주 리포트 서비스(`webapp/`)와는 코드/DB를 공유하지
않는 완전히 별개의 앱입니다.

## 실행 방법

```bash
cd virtual-surgery
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY 채워넣기
uvicorn server:app --host 0.0.0.0 --port 8010 --reload
```

브라우저에서 `http://localhost:8010` 접속.

## 동작 방식

1. 사용자가 사진 업로드 + 시술 항목(복수 선택) + 강도(약하게/보통/강하게) 선택
2. `POST /api/simulate` 로 사진과 옵션 전송
3. 서버가 선택 항목을 자연어 편집 프롬프트로 조합해 Gemini에 이미지+텍스트로 전달
4. Gemini가 생성한 결과 이미지를 base64로 응답 → 프론트에서 원본과 비교 슬라이더로 표시

업로드된 사진과 생성 결과는 디스크에 저장하지 않고 요청 처리 중에만 메모리에서
다루며, 응답 후 즉시 폐기됩니다.

## 주의사항

- 본인 동의 하에 촬영/보유한 사진만 업로드하도록 안내하는 문구를 넣었습니다.
- 결과는 AI가 생성한 이미지이며 실제 시술 결과를 보장하지 않는다는 점을
  화면에 명시했습니다. 의료 광고/오인 소지가 없도록 실제 배포 전에 문구를
  검토하세요.
