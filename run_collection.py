"""GitHub Actions / 로컬 양용 실행 스크립트"""

import os
import sys
import json
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

            # 로컬에서는 자동으로 열기
            if not IS_GITHUB and sys.platform == "win32":
                os.startfile(xlsx_path)
        else:
            log("오늘 추천/보류 공고 없음")

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


if __name__ == "__main__":
    main()
