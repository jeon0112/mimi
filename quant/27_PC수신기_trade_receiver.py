#!/usr/bin/env python3
"""PC 안토니우스 — 신호 메일 수신·검증·실행 (뭉클이 블록 #43 응답 기반)

2026-09-25 안토니우스. 뭉클이의 trade_signal.py(/opt/data/sentinel/)가 보내는
이메일을 읽어 검증하고, 검증을 전부 통과한 것만 실행한다.

★★★★★ 오늘은 "실행" 자리를 비워 둔다 — DRY_RUN 이 기본값이다.
실제 증권사·거래소 API 연결은 시저님이 API 키를 넣고 DRY_RUN=False 로
바꾸기 전까지 아무 주문도 나가지 않는다. (quant/23 의 ①②③ 순서 그대로.)

이 파일은 뭉클이의 sentinel.py 를 흉내 내지 않는다 — 역할이 다르다.
뭉클이 = 판단(신호를 만든다). 이 스크립트 = 실행(신호를 받아서만 한다).
"""

import imaplib
import email
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# 설정 — 전부 환경변수에서 읽는다. 값은 여기 하드코딩하지 않는다.
# (게이트 3번 규칙: 키 값을 출력하지 않는다 · .env 에서만 읽는다)
# ============================================================

IMAP_HOST = "imap.gmail.com"
GMAIL_USER = os.environ.get("PC_ANTONIUS_GMAIL_USER")      # 신호를 받는 함
GMAIL_APP_PASSWORD = os.environ.get("PC_ANTONIUS_GMAIL_APP_PASSWORD")

# ★★★★★ 기본값은 항상 실행하지 않는 쪽이다 (fail-closed)
DRY_RUN = os.environ.get("PC_TRADE_DRY_RUN", "true").lower() != "false"

# 뭉클이와 별개로 PC 쪽에서 다시 한 번 자체 검사한다 — E-1030 그대로.
# 뭉클이 쪽 한도가 뚫려도(버그·공격) PC 쪽이 독립적으로 다시 막는다.
# "구조가 막는다"를 한쪽에만 걸지 않는다 — 이중화가 오늘 원칙의 실물이다.
TOTAL_CAPITAL = 5_000_000
LIMIT_TOTAL = 1_000_000       # 전체 20%
LIMIT_PER_TRADE = 250_000     # 1회 5%
LIMIT_DAILY = 500_000         # 하루 10%

LEDGER_PATH = Path(__file__).parent / "pc_trade_ledger.json"


# ============================================================
# ① 메일 읽기 — 읽기 전용. E-945 의 원칙(readonly=True) 그대로.
# ============================================================

def fetch_signal_emails() -> list[dict]:
    """읽지 않은 신호 메일을 읽기 전용으로 가져온다. 지우거나 옮기지 않는다."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise SystemExit(
            "PC_ANTONIUS_GMAIL_USER / PC_ANTONIUS_GMAIL_APP_PASSWORD 가 "
            ".env 에 없다. 시저님이 넣어야 하는 자리 — 지어내지 않는다."
        )

    imap = imaplib.IMAP4_SSL(IMAP_HOST)
    imap.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    # ★★★ readonly=True — 뭉클이가 오늘 IMAP 에 쓴 구조 방어와 같다(E-945).
    imap.select("INBOX", readonly=True)

    status, data = imap.search(None, '(UNSEEN SUBJECT "매매신호")')
    signals = []
    if status == "OK":
        for num in data[0].split():
            _, msg_data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            body = _extract_body(msg)
            parsed = _parse_signal(body)
            if parsed:
                signals.append(parsed)
    imap.logout()
    return signals


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="replace")
        return ""
    return msg.get_payload(decode=True).decode("utf-8", errors="replace")


# ============================================================
# ② 파싱 — 뭉클이가 고정한 정형 형식만 받는다. 자유 텍스트는 버린다.
#    (이게 곧 E-942 의 원칙: 값을 본다, 설명을 믿지 않는다)
# ============================================================

SIGNAL_PATTERN = re.compile(
    r"종목:\s*(?P<ticker>\S+)\s*\n"
    r"매수/매도:\s*(?P<side>buy|sell)\s*\n"
    r"수량:\s*(?P<qty>[\d.]+)\s*\n"
    r"단가:\s*(?P<price>[\d,]+)"
    r"(?:\s*\(금액\s*(?P<amount>[\d,]+)원?\))?"
    r"\s*\n"
    r"사유:\s*(?P<reason>.+)",
    re.MULTILINE,
)


def _parse_signal(body: str) -> dict | None:
    """정형 형식과 안 맞으면 None — 지어내서 채우지 않는다."""
    m = SIGNAL_PATTERN.search(body)
    if not m:
        return None
    g = m.groupdict()
    try:
        qty = float(g["qty"])
        price = float(g["price"].replace(",", ""))
        amount = (
            float(g["amount"].replace(",", ""))
            if g["amount"]
            else qty * price
        )
    except ValueError:
        return None

    return {
        "ticker": g["ticker"],
        "side": g["side"],
        "qty": qty,
        "price": price,
        "amount": amount,
        "reason": g["reason"].strip(),
        # ★★★★★ confirm_send 는 메일 본문이 아니라 메일 헤더의 별도 필드로
        # 받는다(뭉클이의 X-Confirm-Send 헤더 제안 — 블록 #44 에서 확정).
        # 그때까지는 무조건 False 로 취급한다 — 없으면 막는다.
        "confirm_send": False,
    }


# ============================================================
# ③ 검사 — 뭉클이 쪽과 별개로 PC 쪽이 다시 잰다 (이중 구조 방어)
# ============================================================

def _today_spent() -> float:
    if not LEDGER_PATH.exists():
        return 0.0
    rows = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    today = datetime.now(timezone.utc).date().isoformat()
    return sum(r["amount"] for r in rows if r["date"] == today and r["executed"])


def _total_loss() -> float:
    """실제 손익 계산은 체결가 대조가 필요하다 — 오늘은 지출 누계로 대신한다.
    ★ 이건 손실이 아니라 지출이다. 진짜 손실 한도로 쓰려면 체결 후 평가손익을
    반영해야 한다 — 미구현. 뭉클이에게 물을 것으로 남긴다."""
    if not LEDGER_PATH.exists():
        return 0.0
    rows = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return sum(r["amount"] for r in rows if r["executed"])


def check_limits(signal: dict) -> tuple[bool, str]:
    if signal["amount"] > LIMIT_PER_TRADE:
        return False, f"1회 한도 초과: {signal['amount']:,.0f} > {LIMIT_PER_TRADE:,}"

    if _today_spent() + signal["amount"] > LIMIT_DAILY:
        return False, f"하루 한도 초과: {_today_spent():,.0f}+{signal['amount']:,.0f} > {LIMIT_DAILY:,}"

    if _total_loss() + signal["amount"] > LIMIT_TOTAL:
        return False, (
            f"전체 한도 초과 — 자동 중단 상태. "
            f"해제하려면 {LEDGER_PATH} 를 직접 고쳐야 한다(구조가 막는다, E-1018)"
        )

    if not signal["confirm_send"]:
        return False, "confirm_send 없음 — 신호가 아니라 초안으로 취급한다"

    return True, "통과"


# ============================================================
# ④ 실행 — ★★★★★ 오늘은 여기가 비어 있다. DRY_RUN 이 기본이다.
# ============================================================

def execute(signal: dict) -> dict:
    """실제 증권사·거래소 주문은 여기 들어간다. 오늘은 안 넣는다.

    다음에 채울 것 (시저님이 API 키를 넣은 뒤, 별도 지시서로):
      - 한국투자증권 KIS Developers REST API (quant/23 §1 참고)
      - 코인 거래소 Open API (개인 명의, quant/23 §4 참고)
      - 둘 다 모의투자 환경에서 먼저 검증한 뒤에 실전 전환
    """
    if DRY_RUN:
        return {
            "executed": False,
            "note": "DRY_RUN=true — 실제 주문 없음. 기록만 남긴다.",
        }
    # TODO(다음 지시서): 실제 API 호출
    raise NotImplementedError(
        "DRY_RUN=false 인데 실제 실행 코드가 아직 없다. "
        "지어내서 채우지 않는다 — 여기서 멈춘다."
    )


def log_result(signal: dict, result: dict) -> None:
    rows = json.loads(LEDGER_PATH.read_text(encoding="utf-8")) if LEDGER_PATH.exists() else []
    rows.append({
        "date": datetime.now(timezone.utc).date().isoformat(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "ticker": signal["ticker"],
        "side": signal["side"],
        "qty": signal["qty"],
        "amount": signal["amount"],
        "reason": signal["reason"],
        "executed": result["executed"],
        "note": result["note"],
    })
    LEDGER_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


# ============================================================
def main():
    signals = fetch_signal_emails()
    if not signals:
        print("새 신호 없음.")
        return

    for sig in signals:
        ok, reason = check_limits(sig)
        if not ok:
            print(f"🚨 차단: {sig['ticker']} {sig['side']} {sig['amount']:,.0f}원 — {reason}")
            log_result(sig, {"executed": False, "note": f"BLOCKED: {reason}"})
            continue

        result = execute(sig)
        print(f"{'✅ 실행' if result['executed'] else '📝 기록만'}: "
              f"{sig['ticker']} {sig['side']} {sig['amount']:,.0f}원 — {result['note']}")
        log_result(sig, result)


if __name__ == "__main__":
    main()
