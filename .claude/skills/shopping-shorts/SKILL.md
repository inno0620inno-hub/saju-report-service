# 쇼핑쇼츠 제작 스킬

소스 영상(제품 데모 영상)을 받아 유튜브/틱톡용 쇼핑쇼츠(9:16 세로)를 한번에 제작하는 워크플로우.

## 트리거

다음 중 하나로 실행:
- `쇼핑` 입력 (CLAUDE.md 단축 명령)
- `쇼핑쇼츠 만들어줘` + 영상 첨부
- `/shopping-shorts` + 영상 첨부

영상 없이 트리거되면 "소스 영상을 첨부해주세요. (파일을 드래그하거나 @로 경로 입력)" 안내 후 대기.

## 고정 템플릿 (절대 변경 금지)

아래 값들은 모든 영상에 동일하게 적용. 임의로 수정하지 않는다.

### 레이아웃 (1080x1920)
| 항목 | 속성 | 고정값 |
|------|------|--------|
| 제목 검은 배경 | drawbox | x=0, y=0, w=1080, h=440, color=black, t=fill |
| 제목 윗줄 | drawtext | fontsize=79, fontcolor=white, x=가운데, y=116 |
| 제목 아랫줄 (강조) | drawtext | fontsize=108, fontcolor=0xFFD700, x=가운데, y=215 |
| 자막 | drawtext | fontsize=46, fontcolor=white, x=가운데, y=(960-text_h/2) |
| 프로그레스 바 | drawbox | x=0, y=1912, h=8, color=0xFFD700@0.9, t=fill |

### 스타일
| 항목 | 고정값 |
|------|--------|
| 폰트 | 카페24단정해 (Cafe24Danjunghae-v2.0.ttf) |
| 블러 배경 | gblur sigma=25, brightness=-0.2, saturation=0.5 |
| 색보정 | contrast=1.08, saturation=1.15, brightness=0.02 |
| 제목 윗줄 그림자 | shadowcolor=black@0.9, shadowx=3, shadowy=3 |
| 제목 아랫줄 그림자 | shadowcolor=black@0.8, shadowx=3, shadowy=3 |
| 자막 그림자 | shadowcolor=black@0.9, shadowx=2, shadowy=2 |

### 오디오 믹스
| 항목 | 고정값 |
|------|--------|
| TTS 성우 | 타입캐스트 김건 |
| TTS 볼륨 | 1.0 (원본) |
| 효과음 볼륨 | 0.7 (70%) |
| 효과음 배치 | 3종을 컷 전환마다 로테이션 (0, 2, 4, 6, 8, 10, 12초...) |
| BGM 볼륨 | 0.25 (25%) |
| BGM 페이드아웃 | 끝에서 1.7초 전부터 fade out |

## 고정 에셋 경로

### 로컬 환경 (Windows CLI)
```
C:\Users\hyeji\Downloads\
├── 쇼핑쇼츠\
│   ├── Cafe24Danjunghae-v2.0.ttf (폰트)
│   ├── 효과음\
│   │   ├── _.wav
│   │   ├── ____.wav
│   │   └── ______.wav
│   └── bgm\
│       └── (BGM 파일들)
```

### BGM 선택 규칙
1. 영상 길이를 먼저 확인한다
2. 유튜브 오디오 라이브러리에서 영상 길이에 맞는 곡을 검색/다운로드한다
   - 분위기: 밝음/신남/경쾌 (쇼핑 콘텐츠에 어울리는 것)
   - 길이: 영상 길이와 비슷하거나 약간 긴 곡 (짧으면 반복, 길면 잘라서 사용)
3. 다운로드 경로: `C:\Users\hyeji\Downloads\쇼핑쇼츠\bgm\` 폴더에 저장
4. 해당 폴더에 이미 곡이 있으면 영상 길이에 가장 가까운 곡을 자동 선택
5. 볼륨 25%, 끝에서 1.7초 전부터 fade out

### 원격 환경 (웹 세션)
사용자가 영상만 첨부하면, 효과음/BGM/폰트는 업로드를 요청한다.
이미 업로드된 파일이 있으면 재사용한다.

## 영상마다 바뀌는 입력값

| 입력값 | 설명 |
|--------|------|
| 소스 영상 | 사용자가 첨부하는 제품 데모 영상 |
| 워터마크 좌표 | delogo x,y,w,h (영상마다 위치 다름) |
| 제목 텍스트 2줄 | 윗줄: 짧은 후킹, 아랫줄: 제품명 강조 |
| 자막 텍스트 N줄 | 내용 기반 한글 구어체, 2초 단위 |

## 워크플로우 순서

### 1단계: 소스 분석
```bash
ffprobe -v error -show_entries stream=width,height,duration,codec_name -show_entries format=duration -of json "$SRC"
```
- 해상도, 길이, 코덱 확인
- 워터마크/로고 위치 파악 (중국 플랫폼: 보통 상단 좌/우, 하단 좌/우)

### 2단계: 자막 스크립트 작성
- 영상 내용에 맞는 한글 구어체 자막 작성
- 영상 길이를 2초 단위로 나눠 각 구간에 1줄씩 배정
- 마지막 구간은 남은 시간 전부 할당

### 3단계: TTS 생성 (타입캐스트 김건 성우)
- **clipy MCP 사용** (로컬 환경): clipy MCP를 통해 타입캐스트 김건 성우 TTS 생성
- **원격 환경**: 사용자에게 TTS 파일 업로드 요청
- 각 자막을 별도 mp3 파일로 생성 (line1.mp3 ~ lineN.mp3)
- 각 파일을 해당 슬롯 길이(2초)에 맞게 패딩:
  ```bash
  ffmpeg -nostdin -y -i lineN.mp3 \
    -af "aresample=44100,apad=whole_dur=2.0" \
    -t 2.0 -ar 44100 -ac 1 -c:a pcm_s16le slotN.wav
  ```
- 마지막 슬롯은 남은 시간에 맞게 조정
- 전체 concat → combined.wav

### 4단계: 영상 렌더링 (ffmpeg 단일 명령)

```bash
FONT="Cafe24Danjunghae-v2.0.ttf"
# DURATION = 영상 길이(초)
# 자막 N줄, 효과음 3종, BGM 1곡

ffmpeg -nostdin -y \
  -i "$SRC" -i "$TTS_COMBINED" -i "$SFX1" -i "$SFX2" -i "$SFX3" -i "$BGM" \
  -filter_complex "
    [0:v]delogo=x=2:y=2:w=W1:h=H1,
         delogo=x=X2:y=2:w=W2:h=H2,
         delogo=x=2:y=Y3:w=W3:h=H3,
         delogo=x=X4:y=Y4:w=W4:h=H4[clean];

    [clean]split[fg][bgraw];
    [bgraw]scale=1080:1920:force_original_aspect_ratio=increase,
           crop=1080:1920,gblur=sigma=25,
           eq=brightness=-0.2:saturation=0.5[bg];
    [fg]scale=1080:-2[main];
    [bg][main]overlay=(W-w)/2:(H-h)/2[base];

    [base]eq=contrast=1.08:saturation=1.15:brightness=0.02[color];

    [color]drawbox=x=0:y=0:w=1080:h=440:color=black:t=fill[g1];
    [g1]drawtext=fontfile=${FONT}:text='윗줄제목':fontsize=79:fontcolor=white:
        x=(1080-text_w)/2:y=116:shadowcolor=black@0.9:shadowx=3:shadowy=3[t1];
    [t1]drawtext=fontfile=${FONT}:text='아랫줄강조제목':fontsize=108:fontcolor=0xFFD700:
        x=(1080-text_w)/2:y=215:shadowcolor=black@0.8:shadowx=3:shadowy=3[t2];

    [t2]drawtext=fontfile=${FONT}:text='자막1':fontsize=46:fontcolor=white:
        x=(1080-text_w)/2:y=(960-text_h/2):
        shadowcolor=black@0.9:shadowx=2:shadowy=2:
        enable='between(t,0,2)'[s1];
    ...자막 반복...

    [sN]drawbox=x=0:y=1912:w=1080*(t/DURATION):h=8:
        color=0xFFD700@0.9:t=fill[final];

    [1:a]aformat=sample_rates=44100:channel_layouts=mono[tts];
    [5:a]aformat=sample_rates=44100:channel_layouts=mono,
         volume=0.25,afade=t=out:st=(DURATION-1.7):d=1.7[bgm];

    [2:a]asplit=N1[sx1a][sx1b]...;
    [3:a]asplit=N2[sx2a][sx2b]...;
    [4:a]asplit=N3[sx3a][sx3b]...;
    [sx1a]adelay=0|0,volume=0.7[e0];
    [sx2a]adelay=2000|2000,volume=0.7[e2];
    [sx3a]adelay=4000|4000,volume=0.7[e4];
    ...로테이션 반복...
    [tts][bgm][e0][e2]...[eN]amix=inputs=COUNT:duration=first:normalize=0[audio]
  " \
  -map "[final]" -map "[audio]" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart \
  -t $DURATION "$OUT"
```

### 5단계: 출력
- 포맷: 1080x1920, H.264 CRF20, AAC 128k
- 사용자에게 SendUserFile로 전달

### 6단계: 업로드용 텍스트 자동 생성

영상 완성 후 바로 아래 3가지를 자동으로 작성하여 사용자에게 제공한다.

#### 제목
- 후킹력 있는 한 줄 (호기심/놀라움 유발)
- 이모지 1-2개 포함
- 끝에 `#꿀템 #쇼츠` 태그 포함
- 예: `무거운 가구 옮기다 허리 나갈뻔😱 이걸 진작 알았으면...#꿀템 #쇼츠`

#### 설명글
- 제품의 핵심 문제→해결 구조
- ✅ 체크마크로 주요 특징 4-5개 나열
- 마지막에 댓글 유도 문구
- 관련 해시태그 10-15개 (제품 키워드 + 일반 쇼핑 태그)

#### 고정댓글
- 실사용 후기 톤 (솔직하고 친근한 구어체)
- 구체적 사용 경험 언급 (제품 기능 자연스럽게 노출)
- ㅋㅋ, ;; 등 자연스러운 반응 포함
- 마지막에 질문/답글 유도

### 7단계: 쿠팡파트너스 딥링크 자동 생성

영상의 제품 키워드로 쿠팡파트너스 API를 호출하여 어필리에이트 딥링크를 자동 생성한다.

#### 환경변수 설정 (로컬 PC에서 1회만)
```powershell
# Windows PowerShell
[System.Environment]::SetEnvironmentVariable("COUPANG_ACCESS_KEY", "your-access-key", "User")
[System.Environment]::SetEnvironmentVariable("COUPANG_SECRET_KEY", "your-secret-key", "User")
```

#### 워크플로우
1. 제품명/키워드로 쿠팡 상품 검색 (Search API, GET)
2. 최적 상품 자동 선택 (첫 번째 결과 또는 사용자 선택)
3. 딥링크 생성 (Deeplink API, POST)
4. 6단계에서 생성한 설명글에 `🛒 구매링크: {딥링크}` 자동 삽입

#### 스크립트
```bash
python coupang_deeplink.py "제품 키워드"
```

#### API 제한
- Search API: 1시간 최대 10회 호출
- HMAC 인증 (CEA algorithm=HmacSHA256)

#### 인포크링크 자동 등록 (Playwright 브라우저 자동화)
- 인포크링크는 공개 API가 없으므로 Playwright로 브라우저 자동화
- 첫 실행 시 로그인 필요 (카카오/네이버/구글) → 이후 세션 유지
- 로그인 세션: `~/.inpock_session/state.json`

```bash
# 쿠팡 딥링크 생성 후 자동으로 인포크링크에 등록
python inpock_register.py "상품명" "https://link.coupang.com/딥링크URL"
```

워크플로우:
1. 인포크링크 접속 → 로그인 확인 (세션 있으면 자동)
2. 편집 페이지 이동
3. "블록 추가" → "링크 블록" 선택
4. URL 입력 (쿠팡 딥링크) → 제목/이미지 자동 로드
5. 제목을 "🛒 상품명"으로 커스텀
6. 저장

자동 등록 실패 시 브라우저가 열린 채로 수동 등록 안내

## 주의사항

### delogo 좌표 규칙
- x, y 최소값 2 (band width 마진 필요)
- x+w+1 <= 영상 너비, y+h+1 <= 영상 높이

### drawtext 규칙
- y좌표에 `ih` 변수 사용 불가 → 절대 픽셀값만 사용
- `text_w`, `text_h`는 사용 가능 (가운데 정렬용)

### 폰트
- 카페24단정해가 시스템에 없으면 사용자에게 업로드 요청
- 대체: Noto Sans CJK Bold (`apt install fonts-noto-cjk`)

### 원본 오디오
- 소스 영상의 오디오는 항상 제거 (-an 또는 map에서 제외)
