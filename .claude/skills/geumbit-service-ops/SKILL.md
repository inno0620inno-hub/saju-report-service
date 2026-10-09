---
name: geumbit-service-ops
description: 금빛사주명식 서비스(PDF 리포트·Gemini·Railway 배포·테스트 발송) 운영 워크플로우와 함정. "금빛사주명식 PDF/서버/배포/샘플 발송/Gemini" 때 사용
---

# 금빛사주명식 서비스 운영 워크플로우 (2026-10-09)

## 구조
- 소스: `C:\Users\hyeji\OneDrive\바탕 화면\saju-report-service` (루트가 git, GitHub inno0620inno-hub/saju-report-service, main 푸시 → Railway 자동 배포). 안의 `saju-report-service/` 하위 폴더는 중복 복제본이라 건드리지 않는다(커밋 제외).
- 주요 파일: `generate_report.py`(AI 호출·파이프라인), `build_report.py`(PDF 조립·삽화·마크다운 제거), `report_assets/`(template_body/cover.html, bg_stripes.png, fonts/Cafe24Danjunghae.ttf, illustrations/ + pool.json), `webapp/server.py`(FastAPI, /admin, /admin/test-send), `report_prompts.py`.
- 도메인: 금빛사주명식.store (= xn--jj0bw0vf2c1zcg0du2m.store) → Railway. 예비 주소 saju-report-service-production.up.railway.app.

## AI = Gemini 무료 API
- 환경변수 `GEMINI_API_KEY`(없으면 ANTHROPIC_API_KEY로 폴백 — Claude 크레딧이 소진돼 실패한 적 있음). 모델 gemini-3.5-flash → 3.6 → 3.7 순 폴백(2.5 계열은 신규 키에서 404). 429/503 재시도 내장. **키는 파일·코드에 저장하지 않는다.**

## Railway 규칙 (2026-10-09 사용자 확정)
**사주(금빛사주명식)는 Railway 프로젝트 `pleasant-insight`(프로젝트 9e279feb-c7cf-4f19-b34a-99e3dabb91cb / 서비스 5c91cc52-60c1-4f3b-a3b4-c92d681511f0, 도메인 금빛사주명식.store 연결)만 쓴다. 다른 Railway 프로젝트·서비스는 새로 만들지 않는다.** (2026-10-09 사용자가 A안으로 통일 결정, 변수는 optimistic-flexibility에서 복사 완료)

## Railway 함정 (중요)
- 프로젝트가 4개이고 이름이 자동 생성(believable-elegance, harmonious-optimism, pleasant-insight, optimistic-flexibility). **실제 운영 = `pleasant-insight`**(고객 도메인 연결). `optimistic-flexibility`(railway.app 주소만)는 변수의 원본이었고 통일 후 불필요, `harmonious-optimism`·`believable-elegance`는 빈 중복본.
- 변수 추가 흐름: 서비스 → Variables → New Variable → 저장하면 "Apply N change" 바가 뜨고 **Deploy를 눌러야 적용**됨. API 키 입력은 사용자가 직접(Claude는 입력하지 않음).
- 로그: 서비스 → Deployments → View logs → Deploy Logs. 오류 예: "credit balance is too low" = Anthropic 크레딧 소진.

## 샘플 PDF 테스트 발송 (10/9 검증 완료 — 사용자가 PDF 수신 확인)
- `도메인/admin`(기본 인증 — 브라우저 비밀번호 창, Claude는 비밀번호를 입력하지 않음; 사용자가 직접 로그인) 하단 "테스트 발송" 폼 = POST `/admin/test-send` (name, birth_date YYYY-MM-DD, birth_time HH:MM, gender M/F, product_id, email). 응답이 `alert()` 스크립트라 **폼을 직접 제출하면 브라우저가 멈춤 → 페이지 JS에서 `fetch('/admin/test-send',{method:'POST',body:FormData})`로 보내고 status만 읽는다.** 이메일은 사용자가 정한 주소(godsaveme777777701@gmail.com 또는 inno0620inno@gmail.com). 워터마크 "SAMPLE · 미리보기" PDF가 1~3분 뒤 도착.

## PDF 디자인 규칙
- 검정+금 아트데코(세로 줄무늬 배경, 금 링/단상 장식, 표지 아치), 글씨체 카페24 단정해체(번들), wkhtmltopdf는 linear-gradient·CSS 변수 미지원 → 단색 hex만.
- 삽화: 장 머리마다 `illustrations/pool.json` 테마 풀에서 랜덤(한 PDF 내 중복 없음) + 금빛도사 말풍선, 긴 풀이문(문단 10개↑)은 중간에 1장 더. 새 그림은 1000x640 jpg로 폴더에 넣고 pool.json에 이름 추가.
- 풀이문 마크다운(###, ---, **)은 `_strip_markdown`이 제거.
- 로컬에는 wkhtmltopdf가 없어 크롬 headless 스크린샷으로 미리보기(`chrome --headless=new --window-size=832,… --screenshot`); 최종 모양은 서버 샘플 PDF로 확인.

## 이미지 보관
`바탕 화면\금빛사주명식_이미지\`(쇼츠_띠마스코트, 쇼츠_후킹이미지, PDF_삽화, 참고_템플릿).
