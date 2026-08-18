# -*- coding: utf-8 -*-
"""
server.py — 사주 리포트 서비스의 메인 서버.

역할:
1. 랜딩페이지(landing.html)의 신청폼 제출을 받는다 (POST /api/submit)
2. 즉시 발송 신청이면 바로 처리, 예약 발송이면 DB에 저장해두고 대기
3. 백그라운드 스케줄러가 1분마다 "지금 처리해야 할 주문"을 확인해서
   사주 계산 -> AI 해석 -> PDF 생성 -> 카톡/이메일 발송까지 자동 처리

실행 방법:
  pip install -r requirements.txt
  uvicorn server:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()  # .env 파일이 있으면 환경변수로 불러온다

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator
from apscheduler.schedulers.background import BackgroundScheduler

import db
from notify import send_email_with_pdf, send_kakao_alimtalk

# saju_core.py, generate_report.py 등이 있는 상위 폴더를 import 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from generate_report import generate_full_report, call_ai_for_section  # noqa: E402

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "generated_reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="사주 명식 리포트 서비스")

# 랜딩페이지에서 fetch()로 호출할 수 있도록 CORS 허용
# (실제 배포시엔 allow_origins를 실제 랜딩페이지 도메인으로 제한할 것)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 생성된 PDF를 다운로드 링크로 제공 (카카오 알림톡용)
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")


# ---------------------------------------------------------------------------
# 요청 데이터 검증
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(r"^01[0-9]-?\d{3,4}-?\d{4}$")

class SubmitRequest(BaseModel):
    name: str
    phone: str
    email: EmailStr
    birth_date: str          # "YYYY-MM-DD"
    birth_time: str | None = None   # "HH:MM"
    time_unknown: bool = False
    gender: str               # "M" or "F"
    delivery_mode: str        # "immediate" or "scheduled"
    schedule_date: str | None = None
    schedule_time: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("올바른 휴대폰 번호 형식이 아닙니다.")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v not in ("M", "F"):
            raise ValueError("성별은 M 또는 F여야 합니다.")
        return v

    @field_validator("delivery_mode")
    @classmethod
    def validate_delivery(cls, v):
        if v not in ("immediate", "scheduled"):
            raise ValueError("delivery_mode는 immediate 또는 scheduled여야 합니다.")
        return v


# ---------------------------------------------------------------------------
# API 엔드포인트
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    db.init_db()
    scheduler.start()


@app.post("/api/submit")
def submit_order(req: SubmitRequest):
    if not req.time_unknown and not req.birth_time:
        raise HTTPException(400, "태어난 시간을 입력하거나 '모름'을 체크해주세요.")

    scheduled_at = None
    if req.delivery_mode == "scheduled":
        if not (req.schedule_date and req.schedule_time):
            raise HTTPException(400, "예약 발송 시간을 입력해주세요.")
        try:
            scheduled_dt = datetime.fromisoformat(f"{req.schedule_date}T{req.schedule_time}")
        except ValueError:
            raise HTTPException(400, "예약 날짜/시간 형식이 올바르지 않습니다.")
        if scheduled_dt < datetime.now():
            raise HTTPException(400, "예약 시간은 현재보다 미래여야 합니다.")
        scheduled_at = scheduled_dt.isoformat()

    order_id = db.create_order({
        "name": req.name, "phone": req.phone, "email": req.email,
        "birth_date": req.birth_date, "birth_time": req.birth_time,
        "time_unknown": req.time_unknown, "gender": req.gender,
        "delivery_mode": req.delivery_mode, "scheduled_at": scheduled_at,
    })

    # 즉시 발송이면 바로 처리 시도 (실패해도 스케줄러가 재시도하도록 pending 유지 가능)
    if req.delivery_mode == "immediate":
        process_order(order_id)

    return {"order_id": order_id, "status": "accepted"}


@app.get("/api/orders/{order_id}")
def get_order_status(order_id: int):
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(404, "주문을 찾을 수 없습니다.")
    return order


# ---------------------------------------------------------------------------
# 실제 처리 로직: 계산 -> AI 해석 -> PDF -> 발송
# ---------------------------------------------------------------------------

def process_order(order_id: int):
    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        return

    db.mark_processing(order_id)
    try:
        y, m, d = order["birth_date"].split("-")
        if order["time_unknown"]:
            hour, minute = 12, 0  # 시간 모름 -> 시주 제외하고 정오로 계산 (리포트에 안내 문구 필요)
        else:
            hour, minute = order["birth_time"].split(":")

        customer = {
            "name": order["name"], "phone": order["phone"], "email": order["email"],
            "birth_year": int(y), "birth_month": int(m), "birth_day": int(d),
            "birth_hour": int(hour), "birth_minute": int(minute),
            "gender": order["gender"],
        }

        pdf_path = generate_full_report(customer, output_dir=OUTPUT_DIR)

        # 카카오 알림톡 발송 (실패해도 이메일은 계속 시도)
        kakao_error = None
        try:
            send_kakao_alimtalk(order["phone"], order["name"], os.path.basename(pdf_path))
        except Exception as e:
            kakao_error = str(e)

        email_error = None
        try:
            send_email_with_pdf(order["email"], order["name"], pdf_path)
        except Exception as e:
            email_error = str(e)

        if kakao_error and email_error:
            db.mark_failed(order_id, f"카톡: {kakao_error} / 이메일: {email_error}")
        else:
            db.mark_sent(order_id, pdf_path)

    except Exception as e:
        db.mark_failed(order_id, str(e))


# ---------------------------------------------------------------------------
# 백그라운드 스케줄러: 1분마다 처리해야 할 주문 확인
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()

@scheduler.scheduled_job("interval", minutes=1)
def check_due_orders():
    due = db.get_due_orders(datetime.now().isoformat())
    for order in due:
        process_order(order["id"])
