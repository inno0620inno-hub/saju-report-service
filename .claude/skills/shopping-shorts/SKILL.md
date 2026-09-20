# 쇼핑쇼츠 제작 스킬

소스 영상(제품 데모 영상)을 받아 유튜브/틱톡용 쇼핑쇼츠(9:16 세로)를 한번에 제작하는 워크플로우.

## 트리거

사용자가 영상 파일을 첨부하고 "쇼핑쇼츠 만들어줘" 또는 `/shopping-shorts`라고 입력하면 실행.

## 워크플로우

### 1단계: 소스 분석
```bash
ffprobe -v error -show_entries stream=width,height,duration,codec_name -show_entries format=duration -of json "$SRC"
```
- 해상도, 길이, 코덱 확인
- 워터마크/로고 위치 파악 (중국 플랫폼 영상은 보통 상단 좌/우, 하단 좌/우)

### 2단계: 자막 스크립트 작성
- 영상 내용에 맞는 한글 구어체 자막 작성
- 영상 길이를 2초 단위로 나눠 각 구간에 1줄씩 배정
- 예시 (14초 영상 → 7줄):
  ```
  0-2s:   이거 진짜 꿀템 자석 이동 바퀴야
  2-4s:   뒤에 테이프 붙이기만 하면 끝
  4-6s:   자석이라 철제에도 바로 착!
  6-8s:   볼베어링이라 움직임이 부드러워
  8-10s:  무거운 정수기도 한 손으로 슥~
  10-12s: 밑에 숨은 먼지 이제 싹 청소
  12-14s: 가구 이동이 이렇게 쉬울 줄이야
  ```

### 3단계: TTS 생성 (타입캐스트 김건 성우)
- **clipy MCP 사용** (로컬 환경): clipy MCP를 통해 타입캐스트 김건 성우 TTS 생성
- 각 자막을 별도 mp3 파일로 생성 (line1.mp3 ~ lineN.mp3)
- 각 파일을 해당 슬롯 길이(2초)에 맞게 패딩:
  ```bash
  ffmpeg -nostdin -y -i lineN.mp3 \
    -af "aresample=44100,apad=whole_dur=2.0" \
    -t 2.0 -ar 44100 -ac 1 -c:a pcm_s16le slotN.wav
  ```
- 마지막 슬롯은 남은 시간에 맞게 조정
- 전체 concat:
  ```bash
  ffmpeg -nostdin -y -i slot1.wav ... -i slotN.wav \
    -filter_complex "[0][1]...[N-1]concat=n=N:v=0:a=1[out]" \
    -map "[out]" -ar 44100 -ac 1 -c:a pcm_s16le combined.wav
  ```

### 4단계: 영상 렌더링 (ffmpeg)

#### 필수 에셋
- **폰트**: 카페24단정해 (`Cafe24Danjunghae-v2.0.ttf`)
- **효과음**: 3종 (컷 전환 시 로테이션)
- **배경음악**: 유튜브 무료음원 (볼륨 20-25%)

#### ffmpeg 파이프라인
```bash
FONT="Cafe24Danjunghae-v2.0.ttf"

ffmpeg -nostdin -y -i "$SRC" -i "$TTS_COMBINED" -i "$SFX1" -i "$SFX2" -i "$SFX3" -i "$BGM" \
  -filter_complex "
    # 워터마크 제거 (delogo - 좌표는 영상마다 조정)
    [0:v]delogo=x=2:y=2:w=W:h=H,
         delogo=x=X:y=2:w=W:h=H,
         delogo=x=2:y=Y:w=W:h=H,
         delogo=x=X:y=Y:w=W:h=H[clean];

    # 9:16 세로 포맷 (블러 배경)
    [clean]split[fg][bgraw];
    [bgraw]scale=1080:1920:force_original_aspect_ratio=increase,
           crop=1080:1920,gblur=sigma=25,
           eq=brightness=-0.2:saturation=0.5[bg];
    [fg]scale=1080:-2[main];
    [bg][main]overlay=(W-w)/2:(H-h)/2[base];

    # 색보정
    [base]eq=contrast=1.08:saturation=1.15:brightness=0.02[color];

    # 제목 (검은 배경 + 2줄)
    [color]drawbox=x=0:y=0:w=1080:h=440:color=black:t=fill[g1];
    [g1]drawtext=fontfile=${FONT}:text='윗줄 제목':fontsize=79:fontcolor=white:
        x=(1080-text_w)/2:y=116:shadowcolor=black@0.9:shadowx=3:shadowy=3[t1];
    [t1]drawtext=fontfile=${FONT}:text='아랫줄 강조 제목':fontsize=108:fontcolor=0xFFD700:
        x=(1080-text_w)/2:y=215:shadowcolor=black@0.8:shadowx=3:shadowy=3[t2];

    # 자막 (화면 정중앙, 2초 간격 enable)
    [t2]drawtext=fontfile=${FONT}:text='자막1':fontsize=46:fontcolor=white:
        x=(1080-text_w)/2:y=(960-text_h/2):shadowcolor=black@0.9:shadowx=2:shadowy=2:
        enable='between(t,0,2)'[s1];
    # ... 반복 ...

    # 프로그레스 바 (하단 골드색)
    [sN]drawbox=x=0:y=1912:w=1080*(t/DURATION):h=8:color=0xFFD700@0.9:t=fill[final];

    # 오디오: TTS + BGM(25%) + 효과음(70%) 로테이션
    [1:a]aformat=sample_rates=44100:channel_layouts=mono[tts];
    [5:a]aformat=sample_rates=44100:channel_layouts=mono,volume=0.25,
         afade=t=out:st=END-1.7:d=1.7[bgm];
    [2:a]asplit=N[sx1a][sx1b]...;
    [3:a]asplit=N[sx2a][sx2b]...;
    [4:a]asplit=N[sx3a][sx3b]...;
    # adelay로 각 컷 타이밍에 배치, volume=0.7
    [tts][bgm][e0][e2]...[eN]amix=inputs=COUNT:duration=first:normalize=0[audio]
  " -map "[final]" -map "[audio]" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -movflags +faststart \
    -t DURATION "$OUT"
```

### 5단계: 출력
- 파일명: `shopping_shorts_final.mp4`
- 포맷: 1080x1920, H.264, AAC 128k
- 사용자에게 SendUserFile로 전달

## 주의사항

### delogo 좌표 규칙
- x, y 최소값 2 (band width 마진 필요)
- x+w+1 <= 영상 너비, y+h+1 <= 영상 높이

### drawtext 규칙
- y좌표에 `ih` 변수 사용 불가 → 절대 픽셀값 사용
- `text_w`, `text_h`는 사용 가능 (가운데 정렬용)

### 폰트
- 카페24단정해가 없으면 사용자에게 업로드 요청
- 대체: Noto Sans CJK Bold (`apt install fonts-noto-cjk`)

### 색상 팔레트
- 제목 윗줄: white
- 제목 아랫줄 (강조): 0xFFD700 (골드)
- 자막: white + 검은 그림자
- 프로그레스 바: 0xFFD700@0.9
- 제목 배경: 불투명 black
