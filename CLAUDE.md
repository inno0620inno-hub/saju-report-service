# 금빛사주명식 (사주 PDF 리포트 서비스)
- 웹(claude.ai/code)에서도 이어서 작업하기 위한 저장소. 운영 절차·함정은 `.claude/skills/geumbit-service-ops/SKILL.md`를 **먼저 읽는다**(Railway 운영 프로젝트 구분, Gemini 키, 샘플 발송, PDF 디자인 규칙).
- 푸시하면 Railway(optimistic-flexibility 프로젝트)가 자동 배포한다. 비밀 값(GEMINI_API_KEY 등)은 Railway 환경변수에만 둔다(저장소에 넣지 않는다).
- 사주 유입 쇼츠 워크플로우는 `.claude/skills/saju-shorts/`. 응답은 한국어, 쉽고 짧게.
- 사주 유입 쇼츠 제작 워크플로우와 이미지는 `claude-backup` 저장소의 `.claude/skills/saju-shorts/`(기준본)에 있다. 이 저장소에는 서비스 운영 스킬만 둔다.
