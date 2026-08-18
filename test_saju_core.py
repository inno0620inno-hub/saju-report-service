# -*- coding: utf-8 -*-
"""
test_saju_core.py
사주 계산 엔진 회귀 테스트 스위트.

앞으로 saju_core.py를 수정할 때마다 이 파일을 실행해서
알려진 정답(검증된 외부 자료 기반)과 여전히 일치하는지 확인한다.

실행: python3 test_saju_core.py
"""

from saju_core import calculate_saju

PASS = 0
FAIL = 0

def check(label, actual, expected):
    global PASS, FAIL
    ok = (actual == expected)
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"[{status}] {label}: 실제={actual} / 기대={expected}")


def run():
    print("=" * 70)
    print("테스트 1: 간여지동 검증 (1984-11-26 23:00)")
    print("출처: 나무위키 '갑자' 문서 - 갑자년갑자월갑자일갑자시 유명 사례")
    print("=" * 70)
    r = calculate_saju(1984, 11, 26, 23, 0)
    check("연주", r["year_pillar"]["str"], "갑자")
    check("일주", r["day_pillar"]["str"], "갑자")
    check("시주", r["hour_pillar"]["str"], "갑자")

    print()
    print("=" * 70)
    print("테스트 2: 2024년 입춘(2/4) 경계 - 연주가 절기에 따라 갈리는지")
    print("출처: 이코노미스트 등 다수 언론 - 2024 갑진년은 입춘부터 시작")
    print("=" * 70)
    r2a = calculate_saju(2024, 2, 5, 10, 0)
    check("입춘 이후(2/5) 연주", r2a["year_pillar"]["str"], "갑진")
    r2b = calculate_saju(2024, 2, 3, 10, 0)
    check("입춘 이전(2/3) 연주", r2b["year_pillar"]["str"], "계묘")

    print()
    print("=" * 70)
    print("테스트 3: 서머타임 보정 (1987-07-15, 서머타임 시행기간)")
    print("출처: 척척만세력 - 1987-05-10 02:00 ~ 1987-10-11 03:00 서머타임")
    print("=" * 70)
    r3 = calculate_saju(1987, 7, 15, 14, 0, gender="M")
    check("서머타임 보정 플래그", r3["dst_corrected"], True)
    check("보정된 입력시각(14시->13시)", r3["input"]["hour"], 13)

    r3b = calculate_saju(1987, 3, 15, 14, 0, gender="M")  # 서머타임 시행 전
    check("서머타임 기간 외 보정 안 됨", r3b["dst_corrected"], False)

    print()
    print("=" * 70)
    print("테스트 4: 표준자오선 변경 보정 (1957-06-01, UTC+8:30 시기)")
    print("출처: 국가기록원 - 1954-03-21~1961-08-09 동경 127도30분 사용")
    print("=" * 70)
    r4 = calculate_saju(1957, 6, 1, 10, 0, gender="F", apply_dst=True)
    check("자오선 보정 플래그", r4["meridian_corrected"], True)
    # 1957-06-01 은 서머타임 기간(5/5~9/22)과도 겹침: -1h(서머타임) +30min(자오선) = 순변화 -30분
    check("서머타임도 동시 적용됨", r4["dst_corrected"], True)
    check("최종 보정시각(10:00 -1h +30m = 9:30)", (r4["input"]["hour"], r4["input"]["minute"]), (9, 30))

    print()
    print("=" * 70)
    print("테스트 5: 대운 순행/역행 판정")
    print("규칙: 남자+양간년=순행, 남자+음간년=역행, 여자는 반대")
    print("=" * 70)
    # 1990 = 경오년, 경(庚)은 양간 -> 남자는 순행
    r5m = calculate_saju(1990, 5, 15, 10, 30, gender="M")
    check("1990년생 남자 대운 방향", r5m["daeun"]["direction"], "순행")
    r5f = calculate_saju(1990, 5, 15, 10, 30, gender="F")
    check("1990년생 여자 대운 방향", r5f["daeun"]["direction"], "역행")

    print()
    print("=" * 70)
    print(f"결과: {PASS}개 통과 / {FAIL}개 실패 (총 {PASS+FAIL}개)")
    print("=" * 70)
    return FAIL == 0


if __name__ == "__main__":
    import sys
    success = run()
    sys.exit(0 if success else 1)
