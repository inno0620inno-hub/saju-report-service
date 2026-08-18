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

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, field_validator
from apscheduler.schedulers.background import BackgroundScheduler
import secrets

import db
from notify import send_email_with_pdf, send_kakao_alimtalk

# saju_core.py, generate_report.py 등이 있는 상위 폴더를 import 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from generate_report import generate_full_report, call_ai_for_section  # noqa: E402
from report_prompts import PRODUCTS, PRODUCTS_BY_ID  # noqa: E402

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
# 관리자 인증 (아이디/비밀번호는 환경변수로 설정)
# ---------------------------------------------------------------------------

security = HTTPBasic()
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401, detail="인증 실패",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
    product_id: str = "full"  # report_prompts.PRODUCTS 중 하나
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

    @field_validator("product_id")
    @classmethod
    def validate_product(cls, v):
        if v not in PRODUCTS_BY_ID:
            raise ValueError(f"알 수 없는 상품입니다: {v}")
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

@app.get("/api/products")
def get_products():
    """랜딩페이지가 상품 목록/가격을 항상 최신으로 가져갈 수 있도록 제공."""
    return PRODUCTS

@app.on_event("startup")
def on_startup():
    db.init_db()
    scheduler.start()


@app.post("/api/submit")
def submit_order(req: SubmitRequest, background_tasks: BackgroundTasks):
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
        "product_id": req.product_id, "price": PRODUCTS_BY_ID[req.product_id]["price"],
        "delivery_mode": req.delivery_mode, "scheduled_at": scheduled_at,
    })

    # 이제 신청만으로는 처리를 시작하지 않는다. 관리자가 입금을 확인하고
    # /admin 페이지에서 '입금확인' 버튼을 눌러야 그때부터 처리가 시작된다.

    return {"order_id": order_id, "status": "awaiting_payment"}


@app.get("/api/orders/{order_id}")
def get_order_status(order_id: int):
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(404, "주문을 찾을 수 없습니다.")
    return order


# ---------------------------------------------------------------------------
# 관리자 페이지 — 입금대기 목록 확인 + '입금확인' 버튼
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
def admin_page(username: str = Depends(verify_admin)):
    orders = db.get_awaiting_payment_orders()

    rows_html = ""
    if not orders:
        rows_html = "<tr><td colspan='7' style='text-align:center; padding:24px; color:#888;'>입금 대기 중인 주문이 없습니다.</td></tr>"
    for o in orders:
        product = PRODUCTS_BY_ID.get(o["product_id"], {})
        rows_html += f"""
        <tr>
          <td>{o['id']}</td>
          <td>{o['name']}</td>
          <td>{o['phone']}</td>
          <td>{product.get('name', o['product_id'])}</td>
          <td>{o['price']:,}원</td>
          <td>{o['created_at'][:16].replace('T',' ')}</td>
          <td>
            <form method="post" action="/admin/confirm/{o['id']}" onsubmit="return confirm('입금을 확인하셨습니까? {o['name']}님 / {o['price']:,}원');">
              <button type="submit" style="background:#B8923F; color:#16140F; border:none; padding:8px 14px; border-radius:4px; font-weight:700; cursor:pointer;">입금확인</button>
            </form>
          </td>
        </tr>"""

    return f"""
    <html><head><meta charset="utf-8"><title>입금 확인 관리자 페이지</title>
    <style>
      body {{ font-family: -apple-system, sans-serif; background:#16140F; color:#F3EDE0; padding:30px; }}
      h1 {{ color:#D4AF5A; }}
      table {{ width:100%; border-collapse: collapse; margin-top:20px; }}
      th, td {{ padding:10px 12px; border-bottom:1px solid #333; text-align:left; font-size:14px; }}
      th {{ color:#D4AF5A; }}
    </style>
    </head><body>
      <h1>입금 확인 대기 목록</h1>
      <p style="color:#999;">은행 앱에서 입금자명·금액을 직접 확인하신 후, 일치하는 주문의 '입금확인' 버튼을 눌러주세요.
      버튼을 누르면 시스템은 별도 검증 없이 바로 리포트 생성·발송을 시작합니다.</p>
      <table>
        <tr><th>ID</th><th>이름</th><th>연락처</th><th>상품</th><th>금액</th><th>신청시각</th><th>액션</th></tr>
        {rows_html}
      </table>
    </body></html>
    """


@app.post("/admin/confirm/{order_id}")
def admin_confirm_payment(order_id: int, background_tasks: BackgroundTasks,
                           username: str = Depends(verify_admin)):
    order = db.get_order(order_id)
    if not order or order["status"] != "awaiting_payment":
        raise HTTPException(404, "입금 대기 중인 주문이 아닙니다.")

    db.confirm_payment(order_id)

    # 즉시발송 주문이면 바로 처리 시작. 예약발송 주문은 스케줄러가 예약시각에 처리.
    if order["delivery_mode"] == "immediate":
        background_tasks.add_task(process_order, order_id)

    return HTMLResponse('<script>alert("입금확인 처리되었습니다."); window.location.href="/admin";</script>')


# ---------------------------------------------------------------------------
# 실제 처리 로직: 계산 -> AI 해석 -> PDF -> 발송
# ---------------------------------------------------------------------------

def process_order(order_id: int):
    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        return

    print(f"[주문 {order_id}] 처리 시작: {order['name']}")
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

        print(f"[주문 {order_id}] 사주 계산 + AI 해석문 생성 시작 (1~2분 소요)...")
        pdf_path = generate_full_report(customer, product_id=order["product_id"], output_dir=OUTPUT_DIR)
        print(f"[주문 {order_id}] PDF 생성 완료: {pdf_path}")

        # 카카오 알림톡 발송 (실패해도 이메일은 계속 시도)
        kakao_error = None
        try:
            send_kakao_alimtalk(order["phone"], order["name"], os.path.basename(pdf_path))
            print(f"[주문 {order_id}] 카카오 알림톡 발송 완료")
        except Exception as e:
            kakao_error = str(e)
            print(f"[주문 {order_id}] 카카오 알림톡 발송 실패: {kakao_error}")

        email_error = None
        try:
            send_email_with_pdf(order["email"], order["name"], pdf_path)
            print(f"[주문 {order_id}] 이메일 발송 완료")
        except Exception as e:
            email_error = str(e)
            print(f"[주문 {order_id}] 이메일 발송 실패: {email_error}")

        if kakao_error and email_error:
            db.mark_failed(order_id, f"카톡: {kakao_error} / 이메일: {email_error}")
            print(f"[주문 {order_id}] 최종 실패 (카톡/이메일 둘 다 실패)")
        else:
            db.mark_sent(order_id, pdf_path)
            print(f"[주문 {order_id}] 최종 완료")

    except Exception as e:
        db.mark_failed(order_id, str(e))
        print(f"[주문 {order_id}] 처리 중 오류로 실패: {e}")


# ---------------------------------------------------------------------------
# 백그라운드 스케줄러: 1분마다 처리해야 할 주문 확인
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()

@scheduler.scheduled_job("interval", minutes=1)
def check_due_orders():
    due = db.get_due_orders(datetime.now().isoformat())
    for order in due:
        process_order(order["id"])
