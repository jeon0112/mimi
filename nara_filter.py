"""나라장터 공고 필터링 및 적격 판단 모듈 (Claude Sonnet 사용)"""

import os
import json
import anthropic
from dotenv import load_dotenv
from nara_collector import collect_bids, save_to_json

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 회사 정보 (적격 판단 기준)
COMPANY_PROFILE = """
- 업종: 사무소모품(A4용지, 복사용지, 토너), 생활·위생용품(화장지, 세정제, 방역소모품), 복지·기관납품형 물품(생필품 세트, 판촉·행사 물품)
- 자격: 장애인기업, 예비사회적기업 (수의계약 우선 대상)
- 선호 금액: 100만원 ~ 5,000만원
- 선호 계약방법: 수의계약, 일반경쟁, 제한경쟁
"""

FILTER_KEYWORDS = ["A4", "복사용지", "토너", "화장지", "세정제", "방역", "소모품", "생필품", "판촉", "행사용품", "위생", "사무용품"]
EXCLUDE_KEYWORDS = ["공사", "건설", "설계", "용역", "SW", "소프트웨어", "IT", "시스템", "개발"]


def quick_filter(bids: list) -> list:
    """1차 키워드 필터링 (빠른 사전 필터)"""
    # 수집 키워드로 이미 필터됐으므로 제외 키워드만 적용
    filtered = []
    for bid in bids:
        name = bid.get("공고명", "")
        if any(kw in name for kw in EXCLUDE_KEYWORDS):
            continue
        filtered.append(bid)
    return filtered


def ai_evaluate_bids(bids: list) -> list:
    """Claude Sonnet으로 공고 적격 판단"""
    if not bids:
        return []

    bid_text = "\n".join([
        f"{i+1}. [{bid['공고번호']}] {bid['공고명']} | {bid['발주기관']} | "
        f"추정가: {bid.get('추정가격', 0)}원 | 계약방법: {bid.get('계약방법', '')}"
        for i, bid in enumerate(bids)
    ])

    prompt = f"""당신은 나라장터 입찰 전문가입니다. 아래 회사 프로필을 보고 각 공고의 입찰 적격 여부를 판단하세요.

## 회사 프로필
{COMPANY_PROFILE}

## 평가할 공고 목록
{bid_text}

## 지시사항
각 공고에 대해 다음 형식으로 JSON 배열로 응답하세요:
[
  {{
    "번호": 1,
    "공고번호": "...",
    "추천여부": "추천" 또는 "보류" 또는 "제외",
    "점수": 0~100,
    "이유": "한 줄 이유"
  }},
  ...
]

추천 기준:
- 업종 일치 여부
- 금액 적정성 (100만~5000만원 선호)
- 장애인기업/사회적기업 우대 가능성
- 수의계약 해당 여부 (2000만원 이하)
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    try:
        start = text.find("[")
        end = text.rfind("]") + 1
        results = json.loads(text[start:end])
        return results
    except Exception:
        print("AI 응답 파싱 오류")
        return []


def run_filter_pipeline(days: int = 3) -> None:
    """전체 필터링 파이프라인 실행"""
    print("=" * 50)
    print("  나라장터 입찰공고 수집 및 적격 판단")
    print("=" * 50)

    # 1단계: 공고 수집
    print("\n[1단계] 공고 수집 중...")
    bids = collect_bids(days=days)

    if not bids:
        print("수집된 공고가 없습니다.")
        return

    # 2단계: 키워드 필터링
    print(f"\n[2단계] 키워드 필터링 중... ({len(bids)}건 → ", end="")
    filtered = quick_filter(bids)
    print(f"{len(filtered)}건)")

    if not filtered:
        print("필터링 후 해당 공고가 없습니다.")
        return

    # 3단계: AI 적격 판단
    print(f"\n[3단계] AI 적격 판단 중... (Claude Sonnet)")
    evaluations = ai_evaluate_bids(filtered)

    # 결과 출력
    print("\n" + "=" * 50)
    print("  [분석 결과]")
    print("=" * 50)

    recommended = []
    for bid in filtered:
        eval_item = next(
            (e for e in evaluations if e.get("공고번호") == bid["공고번호"]), None
        )
        if eval_item:
            status = eval_item.get("추천여부", "")
            score = eval_item.get("점수", 0)
            reason = eval_item.get("이유", "")
            icon = "✅" if status == "추천" else ("⚠️" if status == "보류" else "❌")
            print(f"\n{icon} [{status}] {bid['공고명']}")
            print(f"   발주기관: {bid['발주기관']}")
            print(f"   추정가격: {bid.get('추정가격', 0):,}원")
            print(f"   점수: {score}/100 | {reason}")
            print(f"   URL: {bid['공고URL']}")

            if status == "추천":
                recommended.append({**bid, "평가": eval_item})

    # 결과 저장
    if recommended:
        save_to_json(recommended, f"recommended_bids_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.json")
        print(f"\n✅ 추천 공고 {len(recommended)}건 저장 완료")
    else:
        print("\n추천 공고가 없습니다.")


if __name__ == "__main__":
    run_filter_pipeline(days=3)
