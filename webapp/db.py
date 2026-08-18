# -*- coding: utf-8 -*-
"""
db.py — 신청 내역을 저장하는 아주 가벼운 SQLite 데이터베이스.
나중에 신청량이 많아지면 PostgreSQL 등으로 옮겨도 스키마는 그대로 쓸 수 있다.
"""

import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "orders.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            birth_time TEXT,
            time_unknown INTEGER NOT NULL DEFAULT 0,
            gender TEXT NOT NULL,
            delivery_mode TEXT NOT NULL,
            scheduled_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            pdf_path TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            processed_at TEXT
        )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_order(data: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO orders
            (name, phone, email, birth_date, birth_time, time_unknown, gender,
             delivery_mode, scheduled_at, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            data["name"], data["phone"], data["email"],
            data["birth_date"], data.get("birth_time"),
            1 if data.get("time_unknown") else 0,
            data["gender"], data["delivery_mode"],
            data.get("scheduled_at"),
            datetime.utcnow().isoformat(),
        ))
        conn.commit()
        return cur.lastrowid


def get_due_orders(now_iso: str):
    """지금 처리해야 할 주문들 (즉시 발송 대기중이거나, 예약시간이 지난 것)."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM orders
            WHERE status = 'pending'
              AND (delivery_mode = 'immediate' OR scheduled_at <= ?)
        """, (now_iso,)).fetchall()
        return [dict(r) for r in rows]


def mark_processing(order_id: int):
    _update_status(order_id, "processing")


def mark_sent(order_id: int, pdf_path: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE orders SET status='sent', pdf_path=?, processed_at=?
            WHERE id=?
        """, (pdf_path, datetime.utcnow().isoformat(), order_id))
        conn.commit()


def mark_failed(order_id: int, error_message: str):
    with get_conn() as conn:
        conn.execute("""
            UPDATE orders SET status='failed', error_message=?, processed_at=?
            WHERE id=?
        """, (error_message, datetime.utcnow().isoformat(), order_id))
        conn.commit()


def _update_status(order_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        conn.commit()


def get_order(order_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None
