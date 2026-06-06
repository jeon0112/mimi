"""GitHub Actions / 로컬 양용 실행 스크립트"""

import os
import sys
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# 출력 폴더: GitHub Actions면 output/, 로컬이면 바탕화면\나라장터결과
IS_GITHUB = os.getenv("GITHUB_ACTIONS") == "true"

if IS_GITHUB:
    OUTPUT_DIR = "output"
else:
    OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "나라장터결과")

os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_FILE = os.path.join(OUTPUT_DIR, f"log_{datetime.now().strftime('%Y%m%d')}.txt")


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    log("=" * 50)
    log("나라장터 공고 수집 시작")
    log(f"환경: {'GitHub Actions' if IS_GITHUB else '로컬 PC'}")

    try:
        from nara_collector import collect_bids, save_to_json
        from nara_filter import quick_filter, ai_evaluate_bids
        from export_bids import json_to_excel

        # 1. 공고 수집
        log("공고 수집 중...")
        days = 1 if IS_GITHUB else 1
        bids = collect_bids(days=days)
        log(f"수집 완료: {len(bids)}건")

        if not bids:
            log("수집된 공고 없음. 종료.")
            return

        # 2. 키워드 필터
        filtered = quick_filter(bids)
        log(f"키워드 필터 후: {len(filtered)}건")

        if not filtered:
            log("필터 후 해당 공고 없음. 종료.")
            return

        # 3. AI 적격 판단
        log("AI 적격 판단 중...")
        evaluations = ai_evaluate_bids(filtered)

        # 4. 추천 분류
        recommended = []
        held = []
        for bid in filtered:
            eval_item = next(
                (e for e in evaluations if e.get("공고번호") == bid["공고번호"]), None
            )
            if eval_item:
                status = eval_item.get("추천여부", "")
                if status == "추천":
                    recommended.append({**bid, "평가": eval_item})
                elif status == "보류":
                    held.append({**bid, "평가": eval_item})

        log(f"추천: {len(recommended)}건 / 보류: {len(held)}건")

        # 5. 저장
        date_str = datetime.now().strftime("%Y%m%d")

        if recommended or held:
            all_results = recommended + held
            json_path = os.path.join(OUTPUT_DIR, f"recommended_bids_{date_str}.json")
            save_to_json(all_results, json_path)
            log(f"JSON 저장: {json_path}")

            xlsx_path = json_to_excel(json_path)
            log(f"엑셀 저장: {xlsx_path}")

            # 추천 공고 제안서 자동 생성 (네이버 API 있을 때만)
            proposal_files = []
            if recommended and os.getenv("NAVER_CLIENT_ID"):
                log("기술제안서 자동 생성 중...")
                try:
                    from proposal_pipeline import run_pipeline
                    proposal_dir = os.path.join(OUTPUT_DIR, "제안서")
                    for bid in recommended:
                        try:
                            path = run_pipeline(bid, proposal_dir)
                            proposal_files.append(path)
                            log(f"제안서 생성: {os.path.basename(path)}")
                        except Exception as e:
                            log(f"제안서 오류 ({bid.get('공고명', '')[:20]}): {e}")
                except Exception as e:
                    log(f"제안서 모듈 오류: {e}")

            # 이메일 발송
            send_email(recommended, held, xlsx_path, proposal_files)

            # 로컬에서는 자동으로 열기
            if not IS_GITHUB and sys.platform == "win32":
                os.startfile(xlsx_path)
        else:
            log("오늘 추천/보류 공고 없음")
            send_email([], [], None)

        # 6. 요약 출력
        log("\n[추천 공고 요약]")
        for bid in recommended:
            eval_info = bid.get("평가", {})
            log(f"  ✅ {bid['공고명']}")
            log(f"     {bid['발주기관']} | {bid.get('추정가격', 0)}원 | 마감: {bid.get('입찰마감일시', '')}")
            log(f"     점수: {eval_info.get('점수', 0)} | {eval_info.get('이유', '')}")
            log(f"     {bid.get('공고URL', '')}")

    except Exception as e:
        log(f"오류: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)


def send_email(recommended: list, held: list, xlsx_path: str, proposal_files: list = None) -> None:
    gmail_user = os.getenv("GMAIL_USER", "jjk0112@gmail.com")
    gmail_password = os.getenv("GMAIL_PASSWORD", "")
    to_email = os.getenv("NOTIFY_EMAIL", "jjksp112@naver.com")

    if not gmail_password:
        log("이메일 비밀번호 미설정, 발송 건너뜀")
        return

    date_str = datetime.now().strftime("%Y년 %m월 %d일")
    subject = f"[나라장터] {date_str} 추천공고 {len(recommended)}건 / 보류 {len(held)}건"

    body_lines = [
        f"안녕하세요, 오늘의 나라장터 공고 결과입니다.\n",
        f"📋 추천: {len(recommended)}건 | 보류: {len(held)}건\n",
    ]

    if recommended:
        body_lines.append("\n✅ [추천 공고]\n")
        for bid in recommended:
            eval_info = bid.get("평가", {})
            body_lines.append(f"• {bid['공고명']}")
            body_lines.append(f"  발주기관: {bid['발주기관']}")
            price = bid.get('추정가격', 0)
            try:
                price_str = f"{int(price):,}"
            except (ValueError, TypeError):
                price_str = str(price)
            body_lines.append(f"  추정가격: {price_str}원")
            body_lines.append(f"  마감: {bid.get('입찰마감일시', '')}")
            body_lines.append(f"  AI점수: {eval_info.get('점수', 0)}점 - {eval_info.get('이유', '')}")
            body_lines.append(f"  URL: {bid.get('공고URL', '')}\n")

    if held:
        body_lines.append("\n⏸ [보류 공고]\n")
        for bid in held:
            body_lines.append(f"• {bid['공고명']} ({bid['발주기관']})")

    if not recommended and not held:
        body_lines.append("\n오늘은 해당 공고가 없습니다.")

    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if xlsx_path and os.path.exists(xlsx_path):
        with open(xlsx_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(xlsx_path)}")
        msg.attach(part)

    # 제안서 파일 첨부
    for pfile in (proposal_files or []):
        if pfile and os.path.exists(pfile):
            with open(pfile, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            fname = os.path.basename(pfile)
            part.add_header("Content-Disposition", f"attachment; filename=\"{fname}\"")
            msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
        log(f"이메일 발송 완료 → {to_email}")
    except Exception as e:
        log(f"이메일 발송 실패: {e}")


if __name__ == "__main__":
    main()
