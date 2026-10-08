# PDF 삽화 풀 (금빛도사 캐릭터)
- PDF를 만들 때마다 장(章) 머리마다 **무작위로 1장씩**(한 PDF 안에서 중복 없이) 들어간다. 코드: build_report.py `_illustration_html`.
- 이미지: 1000x640 jpg(캐릭터 얼굴이 위쪽에 오도록 크롭). `pool.json`에 테마별로 파일명(확장자 없이) 나열: overview/char/time/wealth/love/health/work.
- 테마 선택 규칙: 총론·사주원국=overview, 재물·사업·이직=wealth, 애정·연인·관계·자녀=love, 건강·오행=health, 대운·세운·계절=time, 성격·십신·신살=char, 학업·직장=work. 맞는 그림이 없으면 전체 풀에서 안 쓴 것.
- 새 그림 추가: Flow 등에서 만든 캐릭터 이미지를 1000x640으로 잘라 이 폴더에 넣고 pool.json에 이름만 추가.
