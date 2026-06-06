"""나라장터 공고 일일 자동 수집 스케줄러"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 실행 설정
SCHEDULE_HOUR = 8       # 매일 오전 8시 실행
SCHEDULE_MINUTE = 0
COLLECT_DAYS = 1        # 최근 1일치 공고 수집 (매일 실행 시)

# 결과 저장 폴더 (바탕화면\나라장터결과)
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "나라장터결과")
os.makedirs(OUTPUT_DIR, exist_ok=True)
LOG_FILE = os.path.join(OUTPUT_DIR, "scheduler.log")


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_daily_collection() -> None:
    """공고 수집 + AI 필터링 실행"""
    log("=" * 50)
    log("나라장터 일일 공고 수집 시작")

    try:
        from nara_collector import collect_bids, save_to_json
        from nara_filter import quick_filter, ai_evaluate_bids

        # 1. 공고 수집
        log("공고 수집 중...")
        bids = collect_bids(days=COLLECT_DAYS)
        log(f"수집 완료: {len(bids)}건")

        if not bids:
            log("수집된 공고 없음. 종료.")
            return

        # 2. 필터링
        filtered = quick_filter(bids)
        log(f"키워드 필터 후: {len(filtered)}건")

        if not filtered:
            log("필터 후 해당 공고 없음. 종료.")
            return

        # 3. AI 평가
        log("AI 적격 판단 중...")
        evaluations = ai_evaluate_bids(filtered)

        # 4. 추천 공고 분류
        recommended = []
        for bid in filtered:
            eval_item = next(
                (e for e in evaluations if e.get("공고번호") == bid["공고번호"]), None
            )
            if eval_item and eval_item.get("추천여부") == "추천":
                recommended.append({**bid, "평가": eval_item})

        log(f"추천 공고: {len(recommended)}건")

        # 5. 결과 저장
        date_str = datetime.now().strftime("%Y%m%d")
        if recommended:
            json_path = os.path.join(OUTPUT_DIR, f"recommended_bids_{date_str}.json")
            filename = save_to_json(recommended, json_path)
            log(f"추천 공고 저장: {filename}")

            # 엑셀 변환
            from export_bids import json_to_excel
            xlsx_path = json_to_excel(json_path)
            log(f"엑셀 저장: {xlsx_path}")
            send_notification(recommended)
        else:
            log("오늘 추천 공고 없음")

    except Exception as e:
        log(f"오류 발생: {e}")
        import traceback
        log(traceback.format_exc())


def send_notification(recommended: list) -> None:
    """추천 공고 알림 (콘솔 출력 - 카카오톡/이메일 연동 예정)"""
    log("\n[추천 공고 알림]")
    for bid in recommended:
        eval_info = bid.get("평가", {})
        log(f"  ✅ {bid['공고명']}")
        log(f"     발주기관: {bid['발주기관']}")
        log(f"     추정가격: {bid.get('추정가격', 0)}원")
        log(f"     마감: {bid.get('입찰마감일시', '')}")
        log(f"     점수: {eval_info.get('점수', 0)}/100 - {eval_info.get('이유', '')}")
        log(f"     URL: {bid.get('공고URL', '')}")
        log("")


def setup_windows_task() -> None:
    """Windows 작업 스케줄러에 등록"""
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    task_name = "나라장터_공고수집"

    # 매일 오전 8시 실행
    cmd = [
        "schtasks", "/create", "/tn", task_name,
        "/tr", f'"{python_path}" "{script_path}" --run',
        "/sc", "daily",
        "/st", f"{SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}",
        "/f",  # 이미 있으면 덮어쓰기
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Windows 작업 스케줄러 등록 완료")
            print(f"   태스크명: {task_name}")
            print(f"   실행 시간: 매일 오전 {SCHEDULE_HOUR}시 {SCHEDULE_MINUTE}분")
            print(f"   확인: 작업 스케줄러 → {task_name}")
        else:
            print(f"❌ 등록 실패: {result.stderr}")
            print("관리자 권한으로 실행해주세요.")
    except FileNotFoundError:
        print("schtasks 명령을 찾을 수 없습니다. Windows에서 실행해주세요.")


def remove_windows_task() -> None:
    """Windows 작업 스케줄러에서 제거"""
    task_name = "나라장터_공고수집"
    cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 작업 스케줄러에서 '{task_name}' 제거 완료")
        else:
            print(f"❌ 제거 실패: {result.stderr}")
    except FileNotFoundError:
        print("Windows에서 실행해주세요.")


def run_loop() -> None:
    """백그라운드 루프 방식 실행 (스케줄러 등록 없이)"""
    print("=" * 50)
    print("  나라장터 공고 수집 스케줄러 시작")
    print(f"  매일 오전 {SCHEDULE_HOUR}:{SCHEDULE_MINUTE:02d} 실행")
    print("  종료: Ctrl+C")
    print("=" * 50)

    while True:
        now = datetime.now()
        if now.hour == SCHEDULE_HOUR and now.minute == SCHEDULE_MINUTE:
            run_daily_collection()
            time.sleep(61)  # 같은 분에 중복 실행 방지
        else:
            next_run = now.replace(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, second=0)
            if next_run < now:
                from datetime import timedelta
                next_run = next_run + timedelta(days=1)
            remaining = int((next_run - now).total_seconds() / 60)
            print(f"\r다음 실행까지 {remaining}분 남음... (현재: {now.strftime('%H:%M')})", end="", flush=True)
            time.sleep(30)


if __name__ == "__main__":
    if "--run" in sys.argv:
        # 작업 스케줄러에서 직접 호출
        run_daily_collection()
    elif "--setup" in sys.argv:
        # Windows 작업 스케줄러 등록
        setup_windows_task()
    elif "--remove" in sys.argv:
        # Windows 작업 스케줄러 제거
        remove_windows_task()
    elif "--now" in sys.argv:
        # 즉시 1회 실행 (테스트용)
        run_daily_collection()
    else:
        print("사용법:")
        print("  python scheduler.py --now        # 지금 즉시 1회 실행 (테스트)")
        print("  python scheduler.py --setup      # Windows 작업 스케줄러 등록 (매일 오전 8시)")
        print("  python scheduler.py --remove     # 작업 스케줄러 등록 해제")
        print("  python scheduler.py --run        # 작업 스케줄러에서 자동 호출용")
        print()
        print(f"  현재 설정: 매일 오전 {SCHEDULE_HOUR}:{SCHEDULE_MINUTE:02d}")
        print(f"  로그 파일: {LOG_FILE}")
