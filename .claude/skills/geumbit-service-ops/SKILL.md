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
- (10/13 이후) 배경은 **미리 구워 둔 아트 PDF를 글자 층 밑에 깔아 합성**한다(아래 'PDF 배경 아트 합성' 절). 글씨체는 카페24 단정해체(번들).
- wkhtmltopdf(0.12.6 patched qt) 실측: **표준 `linear-gradient()`·CSS 변수 `var()`·SVG blur 필터·✦❖☰ 같은 특수기호는 안 됨**, `-webkit-gradient/-webkit-linear-gradient/-webkit-radial-gradient`·`border-image`(9분할)·PNG 알파·rgba·box/text-shadow·인라인 SVG(다각형·그라데이션)는 됨. 배경을 안 칠한 곳은 PDF가 **투명**(알파 0).
- 삽화: 장 머리마다 `illustrations/pool.json` 테마 풀에서 랜덤(한 PDF 내 중복 없음) + 금빛도사 말풍선, 긴 풀이문(문단 10개↑)은 중간에 1장 더. 새 그림은 1000x640 jpg로 폴더에 넣고 pool.json에 이름 추가.
- **페이지 위·아래 흰 띠 해결(10/9 사용자 확인 완료):** 본문 위·아래 여백 22mm는 wkhtmltopdf 특성상 배경이 안 칠해져 흰 띠가 생김 → `report_assets/header.html`(빈 머리글)과 `footer.html`(페이지 번호 바닥글)에 본문과 같은 `#0B0A09 + bg_stripes.png` 배경을 주고 `--header-html/--footer-html` + `--header-spacing 0 --footer-spacing 0`으로 여백 영역을 칠한다(build_report.py의 본문 렌더 2곳). 여백을 줄이거나 body padding으로 해결하려 하지 말 것(페이지마다 반복 안 됨).
- 풀이문 마크다운(###, ---, **)은 `_strip_markdown`이 제거.
- 로컬에는 wkhtmltopdf가 없어 크롬 headless 스크린샷으로 미리보기(`chrome --headless=new --window-size=832,… --screenshot`); 최종 모양은 서버 샘플 PDF로 확인.

## 이미지 보관
`바탕 화면\금빛사주명식_이미지\`(쇼츠_띠마스코트, 쇼츠_후킹이미지, PDF_삽화, 참고_템플릿).

## PDF 배경 아트 합성 (10/13 개편 — '더 화려하게')
- **구조**: wkhtmltopdf는 글자 층만 투명 PDF로 만들고(`{{BG_CSS}}`=`background:transparent`), `build_report._compose_with_art`가 pypdf로 `report_assets/art/{cover,page,opener}.pdf`(Chrome으로 구운 JPG 1장짜리 PDF)를 **페이지 밑**에 깔아 합친다. 표지=cover, 장(章) 시작 쪽=opener(마법진 워터마크+보랏빛 글로우), 나머지=page. 장 시작 쪽은 pass1의 마커 위치로 판별.
- **자동 폴백**: 아트 파일/`pypdf`가 없거나 합성 중 예외가 나면 `build_report()`가 **기본 모드**(예전 검정 줄무늬 CSS 배경 + pdfunite)로 다시 만든다 → 고객이 PDF를 못 받는 일은 없음. 서버 의존성: `webapp/requirements.txt`의 `pypdf>=5.0,<7`.
- **글자 층 장식 PNG**: `report_assets/orn/{divider,medal,frame,end}.png` (frame은 `border-image` 9분할: 삽화·콜아웃 액자). 장 머리=메달(장 번호)+영문 라벨+제목+부제+구분선, 사주 원국 장은 3쪽(도입 / 카드+일간 해설+오행 레이더 / 오행 막대+해설)으로 여유 있게 구성, 오행 레이더는 인라인 SVG(`render_oheng_radar`).
- **좌표 함정(실측, 서버=로컬 동일)**: wkhtmltopdf는 **CSS 1px = 0.6pt**(확대율 0.8)로 그린다 → `mm`는 물리 mm가 아님(220mm가 페이지 폭의 80%). 배경 아트는 832px(=623pt) 기준이라 **아트 좌표 × 1.2487 = 글자 층 CSS px**. 표지의 이름/출생정보(`COVER_NAME_TOP/META_TOP`)·쪽번호 위치(`FOOTER_NUM_TOP`)는 px로 맞춰져 있다. `--margin-*`는 물리값(본문 위·아래 28mm = 모서리 연꽃 문양을 피하는 값), 좌우는 body padding 82px.
- **페이지 번호 마커**: `PGMARK_pillars_END`, `PGMARK_sec_{i}_END` (영문+숫자만). 구버전 pdftotext가 작은 글자 사이에 공백을 끼우고 한글 ID는 못 읽어서 공백 제거 후 검색한다. 마커 색은 `rgba(255,255,255,.012)`(검출됨, 눈에 안 보임) — 글자색 `transparent`/`opacity`/6px 이하는 안 잡힌다.
- **아트를 다시 굽기**(개발 PC, Playwright·Pillow·PyMuPDF 필요): `python report_assets/art_src/build_art.py`(cover/page/opener.pdf, 해상도 1.6배·그레인 2.0·품질 82 → 페이지당 ≈260~600KB), `python report_assets/art_src/build_orn.py`(orn/*.png). 디자인은 `art_src/art.html`·`art_common.js`(별밭·액자·마법진·보케). 환경변수 `ART_DPR/ART_GRAIN/ART_Q`로 용량 조절.
- **로컬에서 서버와 같은 엔진으로 검증**: 포터블 wkhtmltopdf = GitHub `wkhtmltopdf/packaging` 릴리스 `0.12.6-1`의 `wkhtmltox-0.12.6-1.mxe-cross-win64.7z`(BCJ2라 py7zr로는 안 풀림 → 7-zip.org의 `7zr.exe`로 해제). 압축 푼 `bin`을 PATH에 넣고 `pdftotext`(Git for Windows에 있음)도 PATH에 두면 `python report_assets/art_src/make_samples.py <출력폴더> <샘플.pdf>`로 실제 파이프라인 샘플을 만든다(AI 호출 없음). 결과 PDF는 PyMuPDF로 PNG 렌더해 눈으로 확인.
- **신청 폼의 'PDF 샘플 화면'**: `make_samples.py`가 가상 인물(홍길동 1990-05-21 13:30 남)의 샘플 PDF에서 5쪽(표지·사주 원국·총론·대운·재물운)을 `webapp/assets/pdf_*_v1.jpg`로 내보낸다. PDF 디자인을 바꾸면 이 이미지도 다시 만들고 파일명 접미사(v1→v2)를 올려 캐시를 우회한다(`story.html`의 `PDF_SHOTS`).

## 신청 폼(story.html) 판타지 개편 메모 (10/13)
- 질문 흐름·검증·접수 로직은 그대로, UI만 개편: 보라 성운+금 팔레트, 회전 마법진(12지·8괘·오행 상생 오각형/상극 오각별을 SVG 4겹으로, `magicCircle()`), 파티클 캔버스(`FX`: 불씨·영혼빛·별·별똥별·터치 불꽃), 장식 대화창+명패, 주문카드형 상품(프리미엄=회전 무지갯빛 테두리), 로딩=팔자 8칸 점등, 접수 완료=낙관(接受). 웹툰 맨 아래 '이렇게 전해 드립니다'에 PDF 샘플 갤러리(좌우 스와이프·눌러서 크게 보기).
- 성능 교훈: SVG 필터가 든 레이어에 CSS `filter` 애니메이션 금지, 화면에 안 보이는 애니메이션(성운)은 정지, 화면 밖 마법진은 `.paused`. 모션 줄이기 설정 대응됨.
- 발송 시간 문구는 **'입금 확인 후 1시간 내외로 혹은 정하신 시간에 맞춰'**(사용자 지시 10/13, 예약 발송 선택지가 있으므로; story/index/classic 반영).
- **로컬 미리보기 주의**: `127.0.0.1` 테스트 서버로 접수하면 운영 서버·텔레그램으로 가지 않는다(텔레그램 토큰이 없어 알림이 건너뛰어짐). 그래서 로컬에서는 폼 상단에 빨간 '테스트 화면 · 실제 접수 안 됨' 표시가 뜬다. 알림 테스트는 운영 사이트에서 해야 한다.

## 10/13 배포 후 확인된 운영 사실 (중요 — 다음 작업 전에 읽기)
- **배포**: 10/13 커밋 `3ed8a49`(폼)·`92232ea`(PDF) 푸시 → 두 주소 모두 새 폼 반영 확인(마법진·PDF 샘플 5장·새 문구, /classic 포함). PDF의 서버 실물(pypdf 합성·글꼴)은 admin '테스트 발송'으로 사용자가 확인해야 함(미확인).
- **서비스가 둘이다**(10/13 확인: 옛 주소=optimistic-flexibility): 도메인 `금빛사주명식.store`와 `saju-report-service-production.up.railway.app`는 **별개 서비스**(갱신 시점이 달랐음) — 둘 다 이 저장소 main에서 자동 배포된다(= 푸시하면 둘 다 재배포). 변수·DB는 각자 따로.
- **접수 경로(10/13 수정)**: 예전엔 `PROD_API`가 옛 프로젝트 `optimistic-flexibility`의 `saju-report-service-production.up.railway.app`로 고정돼, 도메인에서 연 폼의 접수가 그리로 갔다(Playwright로 확인). 이제 story/index/classic의 접수·상품 API는 **항상 `https://xn--jj0bw0vf2c1zcg0du2m.store`(= pleasant-insight)**, localhost에서 열 때만 자기 자신. 도메인이 바뀌면 `PROD_API`(story/index)·`API_ROOT`(classic)도 바꿀 것.
- **Railway 변수 확인(10/13, 이름만 봄·값은 안 열음)**: pleasant-insight = 10개(ADMIN_USERNAME, ADMIN_PASSWORD, ANTHROPIC_API_KEY, GEMINI_API_KEY, RESEND_API_KEY, RESEND_FROM_EMAIL, SENDER_NAME, SENDER_PASS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID). 옛 optimistic-flexibility(`-production` 주소, Online) = 9개로 **ADMIN_PASSWORD 없음 → 그쪽 /admin은 기본 비밀번호**. 프로젝트 ID: believable-elegance=5344fdfb…, harmonious-optimism=e7d7f496…, pleasant-insight=9e279feb…, optimistic-flexibility=2d8316f0…(서비스 e139ba4b…). 옛 프로젝트는 아직 이 저장소에 연결돼 **푸시마다 같이 재배포**됨 → 중지/삭제(사용자 확인 후)를 권장. 보기 전용 브라우저 확인은 Chrome 프로필1(deviceId 99777c90…)에서 Railway가 로그인돼 있었다.
- **`GET /api/orders/{id}`**: 10/13 `verify_admin`(HTTP Basic)을 걸어 막음(예전엔 로그인 없이 주문 전체·개인정보 반환, 순차 번호 + CORS `*`). 어떤 화면도 이 API를 쓰지 않는다. 고객 정보는 조회하지 말 것(상태 코드만으로 존재 여부 확인).
- 접수 DB는 컨테이너 안 `orders.db`(경로 하드코딩, 코드상 Volume 흔적 없음) → Volume을 안 붙였다면 재배포마다 접수 기록·생성 PDF가 초기화된다. 실주문이 있는 동안에는 푸시 전에 반드시 존재 여부를 확인할 것(두 서버 `/api/orders/N`은 인증이 필요해졌으니 admin 화면으로).
- admin 비밀번호: pleasant-insight는 `ADMIN_PASSWORD` 설정됨(10/13 확인). Claude는 기본 계정으로 접속 시도 금지.
