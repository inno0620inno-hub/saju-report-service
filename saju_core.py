# -*- coding: utf-8 -*-
"""
saju_core.py
사주팔자(四柱八字) 계산 엔진

핵심 설계 원칙:
- 절기(24절기)는 '달력의 근사 날짜'가 아니라 태양의 황경(ecliptic longitude)을
  실제로 계산해서 구한다. (Jean Meeus, "Astronomical Algorithms" 저(低)정밀도 알고리즘,
  오차 약 0.01도 = 정밀도 충분)
- 일주(日柱)는 1984-11-26 이 '갑자일'이라는 것으로 알려진 기준일(간여지동:
  갑자년 갑자월 갑자일 갑자시가 겹친 유명한 날)로 60갑자 순환을 보정(calibrate)한다.
- 연주(年柱) 경계는 '입춘(立春)', 월주(月柱) 경계는 '각 절기(節氣, 12개의 홀수 번째 절기)'
  기준으로 한다 (양력 1/1이나 음력 1/1이 아님 — 명리학 관행).
- 시주(時柱)는 23:00을 하루의 시작(자시)으로 본다 (야자시/조자시 세부 논쟁은 이 버전에서 단순화).
"""

import math
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 0. 한국 서머타임(일광절약시간제) 보정 테이블
#    이 기간에 "시계상"으로 기록된 출생시각은 실제 태양시보다 1시간 빠르므로,
#    사주 계산 전에 1시간을 빼서 보정해야 한다.
#    출처: 사주 전문 만세력 사이트(척척만세력)의 서머타임 시행기간 정리
# ---------------------------------------------------------------------------

KOREA_DST_PERIODS = [
    (datetime(1948, 6, 1, 0, 0), datetime(1948, 9, 13, 0, 0)),
    (datetime(1949, 4, 3, 0, 0), datetime(1949, 9, 11, 0, 0)),
    (datetime(1950, 4, 1, 0, 0), datetime(1950, 9, 10, 0, 0)),
    (datetime(1951, 5, 6, 0, 0), datetime(1951, 9, 9, 0, 0)),
    (datetime(1955, 5, 5, 0, 0), datetime(1955, 9, 9, 0, 0)),
    (datetime(1956, 5, 20, 0, 0), datetime(1956, 9, 30, 0, 0)),
    (datetime(1957, 5, 5, 0, 0), datetime(1957, 9, 22, 0, 0)),
    (datetime(1958, 5, 4, 0, 0), datetime(1958, 9, 21, 0, 0)),
    (datetime(1959, 5, 3, 0, 0), datetime(1959, 9, 20, 0, 0)),
    (datetime(1960, 5, 1, 0, 0), datetime(1960, 9, 18, 0, 0)),
    (datetime(1987, 5, 10, 2, 0), datetime(1987, 10, 11, 3, 0)),
    (datetime(1988, 5, 8, 2, 0), datetime(1988, 10, 9, 3, 0)),
]

def apply_dst_correction(dt):
    """
    출생 datetime이 한국 서머타임 시행기간에 속하면 1시간을 빼서 보정한 datetime을 반환.
    """
    for start, end in KOREA_DST_PERIODS:
        if start <= dt < end:
            return dt - timedelta(hours=1), True
    return dt, False

# ---------------------------------------------------------------------------
# 0-1. 1954~1961년 한국 표준시 자오선 변경(동경 127도30분, UTC+8:30) 보정
#      이 기간엔 지금(UTC+9:00)보다 시계가 30분 느렸으므로, 오늘날 기준으로
#      환산하려면 기록된 시계 시각에 30분을 더해야 한다.
#      출처: 국가기록원, 위키백과 '한국 표준시' 문서
# ---------------------------------------------------------------------------

MERIDIAN_SHIFT_START = datetime(1954, 3, 21, 0, 30)
MERIDIAN_SHIFT_END = datetime(1961, 8, 10, 0, 0)

def apply_meridian_correction(dt):
    """1954-03-21 00:30 ~ 1961-08-10 00:00 사이면 30분을 더해 오늘날 UTC+9 기준으로 환산."""
    if MERIDIAN_SHIFT_START <= dt < MERIDIAN_SHIFT_END:
        return dt + timedelta(minutes=30), True
    return dt, False

# ---------------------------------------------------------------------------
# 1. 기본 상수: 천간(天干) / 지지(地支) / 오행 / 60갑자
# ---------------------------------------------------------------------------

CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
CHEONGAN_HANJA = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
CHEONGAN_OHENG = ["목", "목", "화", "화", "토", "토", "금", "금", "수", "수"]
CHEONGAN_UMYANG = ["양", "음", "양", "음", "양", "음", "양", "음", "양", "음"]

JIJI = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
JIJI_HANJA = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
JIJI_OHENG = ["수", "토", "목", "목", "토", "화", "화", "토", "금", "금", "토", "수"]
JIJI_DONGMUL = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]

def ganzhi_index_to_str(idx, hanja=False):
    """0~59 인덱스를 '갑자' 같은 간지 문자열로 변환"""
    idx = idx % 60
    g = idx % 10
    j = idx % 12
    if hanja:
        return CHEONGAN_HANJA[g] + JIJI_HANJA[j]
    return CHEONGAN[g] + JIJI[j]

def ganzhi_detail(idx):
    idx = idx % 60
    g = idx % 10
    j = idx % 12
    return {
        "index": idx,
        "gan": CHEONGAN[g],
        "gan_hanja": CHEONGAN_HANJA[g],
        "ji": JIJI[j],
        "ji_hanja": JIJI_HANJA[j],
        "gan_oheng": CHEONGAN_OHENG[g],
        "ji_oheng": JIJI_OHENG[j],
        "umyang": CHEONGAN_UMYANG[g],
        "str": CHEONGAN[g] + JIJI[j],
        "hanja": CHEONGAN_HANJA[g] + JIJI_HANJA[j],
        "dongmul": JIJI_DONGMUL[j],
    }

# ---------------------------------------------------------------------------
# 2. 율리우스적일(Julian Day Number) 계산
# ---------------------------------------------------------------------------

def to_julian_day(year, month, day, hour=12, minute=0, second=0):
    """그레고리력 -> 율리우스적일(JD). hour 등은 UT 기준 소수일로 반영."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
    day_fraction = (hour + minute / 60 + second / 3600) / 24
    return jd + day_fraction

def julian_day_to_jdn_int(jd):
    """일주(day pillar) 계산용: 정오(12시) 기준 정수 JDN."""
    return math.floor(jd + 0.5)

# ---------------------------------------------------------------------------
# 3. 태양 황경(黃經) 계산 - Meeus 저정밀도 알고리즘
#    (오차 약 0.01도, 절기 계산에 충분한 정밀도)
# ---------------------------------------------------------------------------

def solar_longitude(jd):
    """주어진 율리우스적일(jd, UT 기준)에서 태양의 겉보기 황경(도, 0~360)을 계산."""
    T = (jd - 2451545.0) / 36525.0  # J2000.0 기준 율리우스 세기

    # 태양의 평균 황경
    L0 = 280.46646 + T * (36000.76983 + T * 0.0003032)
    L0 = L0 % 360

    # 태양의 평균 근점이각(mean anomaly)
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    M_rad = math.radians(M % 360)

    # 이심률
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)

    # 중심차(equation of center)
    C = ((1.914602 - T * (0.004817 + 0.000014 * T)) * math.sin(M_rad)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
         + 0.000289 * math.sin(3 * M_rad))

    true_long = L0 + C  # 진황경(true longitude)

    # 겉보기 황경(apparent longitude) - 章動/광행차 보정(근사)
    omega = 125.04 - 1934.136 * T
    apparent_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    return apparent_long % 360

def find_solar_term_jd(target_longitude, approx_jd, search_days=20):
    """
    target_longitude(태양 황경, 도)에 도달하는 정확한 JD를 이분탐색으로 찾는다.
    approx_jd 근처(+-search_days) 에서 탐색.
    """
    def diff(jd):
        lon = solar_longitude(jd)
        d = (lon - target_longitude + 540) % 360 - 180  # -180~180 로 정규화
        return d

    lo = approx_jd - search_days
    hi = approx_jd + search_days

    # 부호가 바뀌는 구간을 촘촘히 스캔해서 찾은 뒤 이분탐색
    steps = 400
    step_size = (hi - lo) / steps
    prev_jd = lo
    prev_d = diff(prev_jd)
    bracket = None
    for i in range(1, steps + 1):
        cur_jd = lo + i * step_size
        cur_d = diff(cur_jd)
        if prev_d == 0:
            bracket = (prev_jd, prev_jd)
            break
        if (prev_d < 0 and cur_d > 0) or (prev_d > 0 and cur_d < 0):
            bracket = (prev_jd, cur_jd)
            break
        prev_jd, prev_d = cur_jd, cur_d

    if bracket is None:
        raise ValueError(f"절기 탐색 실패 (target={target_longitude}, approx_jd={approx_jd})")

    a, b = bracket
    for _ in range(60):
        mid = (a + b) / 2
        d = diff(mid)
        if abs(d) < 1e-7:
            return mid
        da = diff(a)
        if (da < 0) == (d < 0):
            a = mid
        else:
            b = mid
    return (a + b) / 2

# 24절기: (이름, 태양황경)  -- 0도=춘분 기준
SOLAR_TERMS = [
    ("소한", 285), ("대한", 300), ("입춘", 315), ("우수", 330),
    ("경칩", 345), ("춘분", 0), ("청명", 15), ("곡우", 30),
    ("입하", 45), ("소만", 60), ("망종", 75), ("하지", 90),
    ("소서", 105), ("대서", 120), ("입추", 135), ("처서", 150),
    ("백로", 165), ("추분", 180), ("한로", 195), ("상강", 210),
    ("입동", 225), ("소설", 240), ("대설", 255), ("동지", 270),
]

# 월주(月柱) 경계로 쓰이는 12절기(節氣) - "절입"이라 부르는, 홀수번째(음력 월의 시작) 절기만.
# 인월(1월)=입춘, 묘월(2월)=경칩, 진월(3월)=청명, 사월(4월)=입하, 오월(5월)=망종, 미월(6월)=소서,
# 신월(7월)=입추, 유월(8월)=백로, 술월(9월)=한로, 해월(10월)=입동, 자월(11월)=대설, 축월(12월)=소한
MONTH_BOUNDARY_TERMS = [
    ("입춘", 315, 2),  # (이름, 황경, 지지 인덱스: 인=2)
    ("경칩", 345, 3),
    ("청명", 15, 4),
    ("입하", 45, 5),
    ("망종", 75, 6),
    ("소서", 105, 7),
    ("입추", 135, 8),
    ("백로", 165, 9),
    ("한로", 195, 10),
    ("입동", 225, 11),
    ("대설", 255, 0),  # 자
    ("소한", 285, 1),  # 축
]

def get_solar_terms_for_year_range(year):
    """해당 연도 근처(전년 12월 ~ 익년 1월 포함)의 절기 JD 목록을 계산."""
    results = []
    for y in [year - 1, year, year + 1]:
        for name, lon in SOLAR_TERMS:
            # 대략적인 날짜 추정(그레고리력 기준 절기는 매년 거의 비슷한 날짜)
            approx_month_day = {
                "소한": (1, 6), "대한": (1, 20), "입춘": (2, 4), "우수": (2, 19),
                "경칩": (3, 6), "춘분": (3, 21), "청명": (4, 5), "곡우": (4, 20),
                "입하": (5, 6), "소만": (5, 21), "망종": (6, 6), "하지": (6, 21),
                "소서": (7, 7), "대서": (7, 23), "입추": (8, 8), "처서": (8, 23),
                "백로": (9, 8), "추분": (9, 23), "한로": (10, 8), "상강": (10, 23),
                "입동": (11, 7), "소설": (11, 22), "대설": (12, 7), "동지": (12, 22),
            }[name]
            approx_jd = to_julian_day(y, approx_month_day[0], approx_month_day[1], 12)
            exact_jd = find_solar_term_jd(lon, approx_jd, search_days=10)
            results.append((name, lon, exact_jd, y))
    results.sort(key=lambda x: x[2])
    return results

# ---------------------------------------------------------------------------
# 4. 연주(年柱) / 월주(月柱) / 일주(日柱) / 시주(時柱) 계산
# ---------------------------------------------------------------------------

# 캘리브레이션 기준: "1984-11-26 23시~01시가 갑자년갑자월갑자일갑자시"라는 유명한 간여지동 기록에서,
# 23:00 경계 규칙(하루가 23시에 바뀜)을 적용하면 이 갑자일은 '1984-11-27의 정규(00:00~22:59) 일주'와
# 같은 간지다. 즉 1984-11-27 낮 시간대의 일주가 갑자(인덱스 0).
_CALIB_YEAR, _CALIB_MONTH, _CALIB_DAY = 1984, 11, 27
_CALIB_JDN = julian_day_to_jdn_int(to_julian_day(_CALIB_YEAR, _CALIB_MONTH, _CALIB_DAY, 12))
_CALIB_GANZHI_INDEX = 0  # 갑자

def day_pillar(year, month, day, hour, minute=0):
    """
    일주 계산. 전통 명리학에서 하루는 23:00(자시 시작)에 바뀐다고 보므로,
    23:00~23:59 에 태어난 경우 다음날의 일주를 사용한다.
    """
    dt = datetime(year, month, day, hour, minute)
    if hour == 23:
        dt = dt + timedelta(days=1)
    jdn = julian_day_to_jdn_int(to_julian_day(dt.year, dt.month, dt.day, 12))
    idx = (jdn - _CALIB_JDN + _CALIB_GANZHI_INDEX) % 60
    return ganzhi_detail(idx), dt  # dt: 일주 계산에 사용된(보정된) 날짜


def year_pillar(year, month, day, hour, minute=0):
    """
    연주 계산. 입춘을 연도의 경계로 삼는다.
    """
    terms = get_solar_terms_for_year_range(year)
    ipchun_list = [(name, jd, y) for (name, lon, jd, y) in terms if name == "입춘"]
    ipchun_list.sort(key=lambda x: x[1])

    birth_jd = to_julian_day(year, month, day, hour, minute)

    # 생일이 속한 절기년(입춘~다음 입춘 전)의 '연 갑자'를 구한다.
    # 갑자년 기준점: 1984년은 갑자년 (index 0)
    effective_year = year
    # 그 해 입춘을 찾는다
    this_year_ipchun = next(jd for (name, jd, y) in ipchun_list if y == year)
    if birth_jd < this_year_ipchun:
        effective_year = year - 1  # 아직 입춘 전이면 전년도 간지 사용

    idx = (effective_year - 1984) % 60
    detail = ganzhi_detail(idx)
    return detail, effective_year


def month_pillar(year, month, day, hour, minute, year_gan_index):
    """
    월주 계산. 12절기(절입) 경계로 월지를 정하고,
    연간(年干)에 따라 월간의 시작 천간을 정하는 '오호둔(五虎遁)' 규칙을 적용.

    오호둔: 연간이
      갑/기 -> 인월(1월) 천간은 병(丙)
      을/경 -> 무(戊)
      병/신 -> 경(庚)
      정/임 -> 임(壬)
      무/계 -> 갑(甲)
    이후 매월 천간은 순서대로 1씩 증가.
    """
    birth_jd = to_julian_day(year, month, day, hour, minute)
    terms = get_solar_terms_for_year_range(year)

    # MONTH_BOUNDARY_TERMS 이름에 해당하는 절기들만 추려서 시간순 정렬
    boundary_names = {name for (name, lon, jiji_idx) in MONTH_BOUNDARY_TERMS}
    name_to_jiji = {name: jiji_idx for (name, lon, jiji_idx) in MONTH_BOUNDARY_TERMS}
    boundaries = [(name, jd) for (name, lon, jd, y) in terms if name in boundary_names]
    boundaries.sort(key=lambda x: x[1])

    # 생일보다 작거나 같은 마지막 절입을 찾는다
    current = None
    for name, jd in boundaries:
        if jd <= birth_jd:
            current = (name, jd)
        else:
            break
    if current is None:
        # 이례적으로 못 찾으면 리스트의 첫 항목 이전 -> 가장 마지막(이전 해) 절기 사용
        current = boundaries[0]

    month_ji_idx = name_to_jiji[current[0]]

    # 오호둔: 인월(월지=2)의 천간을 연간에 따라 결정
    # 연간 index: 0=갑 1=을 2=병 3=정 4=무 5=기 6=경 7=신 8=임 9=계
    ohodun_start = {
        0: 2, 5: 2,   # 갑/기 -> 병(2)
        1: 4, 6: 4,   # 을/경 -> 무(4)
        2: 6, 7: 6,   # 병/신 -> 경(6)
        3: 8, 8: 8,   # 정/임 -> 임(8)
        4: 0, 9: 0,   # 무/계 -> 갑(0)
    }
    inwol_gan = ohodun_start[year_gan_index % 10]

    # 인월(지지idx=2)로부터 몇 칸 떨어져 있는지 계산 (지지 순환: 인=2 부터 시작해서 다음이 묘=3 ...)
    offset = (month_ji_idx - 2) % 12
    month_gan_idx = (inwol_gan + offset) % 10

    idx = None
    # 월주 60갑자 인덱스 = 천간idx, 지지idx 조합으로 역산 (10과 12의 최소공배수 60 범위에서 탐색)
    for i in range(60):
        if i % 10 == month_gan_idx and i % 12 == month_ji_idx:
            idx = i
            break

    return ganzhi_detail(idx), current[0]


def hour_pillar(day_gan_index, hour, minute=0):
    """
    시주 계산. 오서둔(五鼠遁) 규칙: 일간에 따라 자시(23~01)의 천간이 결정됨.
      갑/기일 -> 자시 갑(甲)
      을/경일 -> 자시 병(丙)
      병/신일 -> 자시 무(戊)
      정/임일 -> 자시 경(庚)
      무/계일 -> 자시 임(壬)
    이후 매 시진(2시간)마다 천간 1씩 증가.
    시지는 23:00~00:59=자, 01:00~02:59=축, ... 2시간 단위로 순환.
    """
    oseodun_start = {
        0: 0, 5: 0,   # 갑/기 -> 갑(0)
        1: 2, 6: 2,   # 을/경 -> 병(2)
        2: 4, 7: 4,   # 병/신 -> 무(4)
        3: 6, 8: 6,   # 정/임 -> 경(6)
        4: 8, 9: 8,   # 무/계 -> 임(8)
    }
    jasi_gan = oseodun_start[day_gan_index % 10]

    # 시지 인덱스 계산: 23:00~00:59 -> 자(0), 01:00~02:59 -> 축(1), ...
    h = hour % 24
    if h == 23:
        hour_ji_idx = 0
    else:
        hour_ji_idx = ((h + 1) // 2) % 12

    hour_gan_idx = (jasi_gan + hour_ji_idx) % 10

    idx = None
    for i in range(60):
        if i % 10 == hour_gan_idx and i % 12 == hour_ji_idx:
            idx = i
            break
    return ganzhi_detail(idx)


# ---------------------------------------------------------------------------
# 5-1. 대운(大運) 계산 - 10년 주기로 바뀌는 운의 흐름
# ---------------------------------------------------------------------------

YANG_GAN_INDICES = {0, 2, 4, 6, 8}  # 갑,병,무,경,임

def calculate_daeun(year, month, day, hour, minute, gender, year_gan_index, month_pillar_index):
    """
    대운 계산.
    gender: 'M'(남) 또는 'F'(여)

    순행/역행 규칙:
      남자 + 양간년(갑병무경임) -> 순행 / 남자 + 음간년(을정기신계) -> 역행
      여자 + 양간년 -> 역행 / 여자 + 음간년 -> 순행

    대운수(첫 대운이 시작하는 나이):
      순행이면 생일~다음 절입(절기)까지의 일수, 역행이면 이전 절입~생일까지의 일수를 3으로 나눈 값
      (전통 규칙: 3일 = 1년, 나머지는 반올림)
    """
    is_yang_year = (year_gan_index % 10) in YANG_GAN_INDICES
    male = (gender == "M")
    forward = (male and is_yang_year) or (not male and not is_yang_year)

    birth_jd = to_julian_day(year, month, day, hour, minute)
    terms = get_solar_terms_for_year_range(year)
    boundary_names = {name for (name, lon, jiji_idx) in MONTH_BOUNDARY_TERMS}
    boundaries = [(name, jd) for (name, lon, jd, y) in terms if name in boundary_names]
    boundaries.sort(key=lambda x: x[1])

    if forward:
        # 생일 이후의 가장 가까운 절입을 찾는다
        next_term_jd = next(jd for (name, jd) in boundaries if jd > birth_jd)
        days_diff = next_term_jd - birth_jd
    else:
        # 생일 이전의 가장 가까운 절입을 찾는다
        prev_term_jd = max(jd for (name, jd) in boundaries if jd <= birth_jd)
        days_diff = birth_jd - prev_term_jd

    daeun_start_age = round(days_diff / 3)
    if daeun_start_age < 1:
        daeun_start_age = 1

    # 대운 각 단계의 간지 = 월주에서 순행/역행으로 이동
    steps = []
    idx = month_pillar_index
    for i in range(9):  # 대운 9단계 (약 90세까지)
        if i > 0:
            idx = (idx + 1) % 60 if forward else (idx - 1) % 60
        age_start = daeun_start_age + i * 10
        detail = ganzhi_detail(idx)
        steps.append({
            "age_start": age_start,
            "age_end": age_start + 9,
            "ganzhi": detail["str"],
            "detail": detail,
        })

    return {
        "direction": "순행" if forward else "역행",
        "daeun_start_age": daeun_start_age,
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# 5-3. 십신(十神) 계산 — 일간(본인)을 기준으로 다른 천간들이 어떤 관계인지
#      (비견/겁재/식신/상관/편재/정재/편관/정관/편인/정인)
# ---------------------------------------------------------------------------

_OHENG_ORDER = ["목", "화", "토", "금", "수"]

def _generates(elem):
    """elem이 상생(相生)으로 낳아주는 다음 오행 (목생화, 화생토, 토생금, 금생수, 수생목)"""
    i = _OHENG_ORDER.index(elem)
    return _OHENG_ORDER[(i + 1) % 5]

def _overcomes(elem):
    """elem이 상극(相剋)으로 극하는 오행 (목극토, 화극금, 토극수, 금극목, 수극화)"""
    i = _OHENG_ORDER.index(elem)
    return _OHENG_ORDER[(i + 2) % 5]

def sipsin_between(day_gan_index, other_gan_index):
    """일간(day_gan_index) 기준으로 other_gan_index 천간의 십신을 반환."""
    day_elem = CHEONGAN_OHENG[day_gan_index % 10]
    day_yy = CHEONGAN_UMYANG[day_gan_index % 10]
    other_elem = CHEONGAN_OHENG[other_gan_index % 10]
    other_yy = CHEONGAN_UMYANG[other_gan_index % 10]
    same_yy = (day_yy == other_yy)

    if other_elem == day_elem:
        return "비견" if same_yy else "겁재"
    elif _generates(day_elem) == other_elem:
        return "식신" if same_yy else "상관"
    elif _overcomes(day_elem) == other_elem:
        return "편재" if same_yy else "정재"
    elif _overcomes(other_elem) == day_elem:
        return "편관" if same_yy else "정관"
    elif _generates(other_elem) == day_elem:
        return "편인" if same_yy else "정인"
    return None  # 이론상 도달 불가

SIPSIN_MEANING = {
    "비견": "자기 자신과 같은 힘 - 독립심, 자존심, 동료·경쟁자",
    "겁재": "자신과 비슷하나 다른 결의 힘 - 추진력, 손재 위험, 형제·동업자",
    "식신": "내가 낳는 부드러운 힘 - 표현력, 여유, 의식주 복",
    "상관": "내가 낳는 날카로운 힘 - 재능, 비판력, 규범을 벗어나려는 기질",
    "편재": "내가 다스리는 유동적인 재물 - 활동을 통한 재물, 사업 수완",
    "정재": "내가 다스리는 안정적인 재물 - 착실한 축적, 배우자운(남성 기준)",
    "편관": "나를 억누르는 강한 힘 - 추진력, 위기 대응력, 스트레스",
    "정관": "나를 다스리는 질서 - 책임감, 명예, 조직 적응력",
    "편인": "나를 낳아주는 특이한 힘 - 직관, 종교·철학적 관심, 변칙적 학습",
    "정인": "나를 낳아주는 순정한 힘 - 학문, 보호받는 기운, 어머니운",
}

def calculate_sipsin(data):
    """계산된 사주 데이터(연/월/일/시주)를 받아 연간·월간·시간의 십신을 반환."""
    day_gan_idx = data["day_pillar"]["index"] % 10
    result = {}
    for key, label in [("year_pillar", "년간"), ("month_pillar", "월간"), ("hour_pillar", "시간")]:
        other_idx = data[key]["index"] % 10
        sipsin = sipsin_between(day_gan_idx, other_idx)
        result[key] = {"label": label, "sipsin": sipsin, "meaning": SIPSIN_MEANING.get(sipsin, "")}
    return result


# ---------------------------------------------------------------------------
# 5-1-2. 천을귀인(天乙貴人) 계산 — 신살(神殺) 중 가장 널리 쓰이는 길신(吉神).
#      일간을 기준으로 정해진 두 지지가 사주 안에 있는지 확인하는, 고정된
#      공식이라 AI가 아니라 코드로 정확하게 계산한다.
# ---------------------------------------------------------------------------

# 일간별 천을귀인 지지 (전통 명리학 표준 공식)
CHEON_EUL_GWIIN_TABLE = {
    "갑": ["축", "미"], "무": ["축", "미"], "경": ["축", "미"],
    "을": ["자", "신"], "기": ["자", "신"],
    "병": ["해", "유"], "정": ["해", "유"],
    "임": ["묘", "사"], "계": ["묘", "사"],
    "신": ["인", "오"],
}

def calculate_cheoneulgwiin(data):
    """일간 기준 천을귀인에 해당하는 지지가 연/월/일/시지 중에 있는지 확인."""
    day_gan = data["day_pillar"]["gan"]
    target_jiji = CHEON_EUL_GWIIN_TABLE.get(day_gan, [])
    found = []
    for key, label in [("year_pillar", "년지"), ("month_pillar", "월지"),
                        ("day_pillar", "일지"), ("hour_pillar", "시지")]:
        ji = data[key]["ji"]
        if ji in target_jiji:
            found.append({"pillar": label, "jiji": ji})
    return {"target_jiji": target_jiji, "found": found, "has_gwiin": len(found) > 0}


# ---------------------------------------------------------------------------
# 5-2. 특정 시점(오늘, 올해 등)의 세운(歲運)/월운(月運) 계산
#      - 개인 생년월일과 무관하게, "지금 이 시점"의 연간지/월간지를 구한다.
#      - 신년운세, 월간운세 같은 상품에 사용.
# ---------------------------------------------------------------------------

def calculate_period_pillars(year=None, month=None, day=None):
    """
    특정 날짜(기본값: 오늘)의 세운(연간지)과 월운(월간지)을 계산해 반환.
    시(時)는 의미가 없으므로 정오(12:00) 기준으로 계산한다.
    """
    if year is None:
        today = datetime.now()
        year, month, day = today.year, today.month, today.day

    y_detail, effective_year = year_pillar(year, month, day, 12, 0)
    m_detail, term_name = month_pillar(year, month, day, 12, 0, y_detail["index"] % 10)

    return {
        "year": year, "month": month, "day": day,
        "se_un": y_detail,       # 세운(歲運) - 올해의 간지
        "wol_un": m_detail,      # 월운(月運) - 이번 달의 간지
        "effective_year": effective_year,
    }


def calculate_year_all_months(year):
    """해당 연도 1~12월 전체의 월운(月運)을 리스트로 반환 (각 달 15일 기준으로 계산)."""
    return [calculate_period_pillars(year, m, 15) for m in range(1, 13)]


def calculate_saju(year, month, day, hour, minute=0, gender=None, apply_dst=True):
    """
    생년월일시(양력, 한국시간 기준)를 입력받아 사주팔자 4주 + 대운을 계산해 반환.
    gender: 'M' 또는 'F' (대운 순행/역행 판단에 필요, 없으면 대운은 생략)
    apply_dst: True면 한국 서머타임 시행기간 자동 보정
    """
    dst_applied = False
    meridian_applied = False
    if apply_dst:
        dt0 = datetime(year, month, day, hour, minute)
        dt1, dst_applied = apply_dst_correction(dt0)
        dt2, meridian_applied = apply_meridian_correction(dt1)
        if dst_applied or meridian_applied:
            year, month, day, hour, minute = (dt2.year, dt2.month, dt2.day, dt2.hour, dt2.minute)

    y_detail, effective_year = year_pillar(year, month, day, hour, minute)
    m_detail, term_name = month_pillar(year, month, day, hour, minute, y_detail["index"] % 10)
    d_detail, adjusted_dt = day_pillar(year, month, day, hour, minute)
    h_detail = hour_pillar(d_detail["index"] % 10, hour, minute)

    # 오행 분포 집계 (8글자 기준: 천간4 + 지지4)
    oheng_count = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    for d in [y_detail, m_detail, d_detail, h_detail]:
        oheng_count[d["gan_oheng"]] += 1
        oheng_count[d["ji_oheng"]] += 1

    result = {
        "input": {"year": year, "month": month, "day": day, "hour": hour, "minute": minute},
        "dst_corrected": dst_applied,
        "meridian_corrected": meridian_applied,
        "year_pillar": y_detail,
        "month_pillar": m_detail,
        "day_pillar": d_detail,
        "hour_pillar": h_detail,
        "effective_year_for_ganzhi": effective_year,
        "month_boundary_term": term_name,
        "oheng_distribution": oheng_count,
        "day_master": d_detail["gan"],  # 일간(日干) = 본인을 상징하는 핵심 글자
        "summary_string": f"{y_detail['str']}년 {m_detail['str']}월 {d_detail['str']}일 {h_detail['str']}시",
    }
    result["sipsin"] = calculate_sipsin(result)
    result["cheoneulgwiin"] = calculate_cheoneulgwiin(result)

    if gender in ("M", "F"):
        result["daeun"] = calculate_daeun(
            year, month, day, hour, minute, gender,
            y_detail["index"] % 10, m_detail["index"]
        )

    return result


if __name__ == "__main__":
    # 간단 테스트
    result = calculate_saju(1990, 5, 15, 10, 30)
    for k, v in result.items():
        print(k, ":", v)
