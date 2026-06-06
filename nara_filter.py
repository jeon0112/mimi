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
- 업종:
  1. 사무소모품 (A4용지, 복사용지, 토너)
  2. 생활·위생용품 (화장지, 세정제, 방역소모품)
  3. 복지·기관납품형 물품 (생필품 세트, 판촉·행사 물품)
  4. 에어컨·냉난방기 세척 (병원, 학교, 공공기관 대상)
  5. 홍보용 인쇄물 (현수막, 브로슈어, 리플렛, 홍보물, 홍보용품)
- 자격: 장애인기업, 예비사회적기업 (수의계약 우선 대상)
- 금액 기준:
  - 수의계약: 1억원 이하 우선 고려
  - 일반/제한경쟁 입찰: 금액 제한 없이 참여 가능
- 입찰 방식: 수의계약, 일반경쟁, 제한경쟁 모두 참여 가능
"""

FILTER_KEYWORDS = ["A4", "복사용지", "토너", "화장지", "세정제", "방역", "소모품", "생필품", "판촉", "행사용품", "위생", "사무용품"]
EXCLUDE_KEYWORDS = ["공사", "건설", "설계", "제조", "설치공사", "시공"]


DETAILED_CHECK_PROMPT = """당신은 나라장터 입찰 전문가입니다.
아래 공고를 꼼꼼히 분석하여 입찰 참여 전 반드시 확인해야 할 사항을 체크해 주세요.

## 회사 프로필
{company_profile}

## 분석할 공고
- 공고명: {bid_name}
- 발주기관: {agency}
- 추정가격: {price}원
- 계약방법: {contract_method}
- 입찰방식: {bid_method}
- 입찰마감: {deadline}
- AI 1차 점수: {score}점 / 이유: {reason}

## 지시사항
다음 항목을 JSON 형식으로 분석하세요 (다른 텍스트 없이):

{{
  "공고번호": "...",
  "자격요건": {{
    "장애인기업우선구매": true/false,
    "지역제한": "없음" 또는 "지역명",
    "자격증필요": "없음" 또는 "필요 자격증명",
    "기업규모제한": "없음" 또는 "중소기업" 등
  }},
  "계약조건": {{
    "수의계약가능": true/false,
    "낙찰방식": "최저가" 또는 "제안서" 또는 "협상",
    "납품기한": "...일" 또는 "정보없음",
    "선금": "있음" 또는 "없음" 또는 "정보없음"
  }},
  "체크리스트": [
    {{"항목": "...", "상태": "✅ 충족" 또는 "⚠️ 확인필요" 또는 "❌ 미충족", "설명": "..."}}
  ],
  "장점": ["...", "..."],
  "단점": ["...", "..."],
  "주의사항": ["절대 놓치면 안 되는 중요 사항들"],
  "입찰전략": "이 공고에 대한 최적 입찰 전략 2-3문장",
  "최종권고": "강력추천" 또는 "추천" 또는 "신중검토"
}}

체크리스트는 6~8개 항목으로 구성. 실제로 중요한 것만."""


def ai_detailed_check(recommended_bids: list) -> dict:
    """추천 공고에 대한 세밀한 점검 (Claude Opus 사용)"""
    if not recommended_bids:
        return {}

    results = {}
    for bid in recommended_bids:
        bid_no = bid.get("공고번호", "")
        eval_info = bid.get("평가", {})
        print(f"\n  세밀 점검: {bid.get('공고명', '')[:40]}")

        prompt = DETAILED_CHECK_PROMPT.format(
            company_profile=COMPANY_PROFILE,
            bid_name=bid.get("공고명", ""),
            agency=bid.get("발주기관", ""),
            price=bid.get("추정가격", 0),
            contract_method=bid.get("계약방법", "정보없음"),
            bid_method=bid.get("입찰방식", "정보없음"),
            deadline=bid.get("입찰마감일시", "정보없음"),
            score=eval_info.get("점수", 0),
            reason=eval_info.get("이유", ""),
        )

        try:
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=2000,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": prompt}],
            )
            text = ""
            for block in response.content:
                if block.type == "text":
                    text = block.text
                    break
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])
            results[bid_no] = data

            # 콘솔 요약 출력
            checklist = data.get("체크리스트", [])
            issues = [c for c in checklist if "⚠️" in c.get("상태", "") or "❌" in c.get("상태", "")]
            print(f"    최종권고: {data.get('최종권고', '?')} | 주의항목: {len(issues)}건")
            for issue in issues:
                print(f"    {issue['상태']} {issue['항목']}: {issue['설명']}")
        except Exception as e:
            print(f"    세밀 점검 오류: {e}")
            import traceback
            traceback.print_exc()

    return results


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
    """Claude Sonnet으로 공고 적격 판단 (20건씩 배치 처리)"""
    if not bids:
        return []

    all_results = []
    batch_size = 20

    for i in range(0, len(bids), batch_size):
        batch = bids[i:i + batch_size]
        print(f"  배치 {i//batch_size + 1}/{(len(bids)-1)//batch_size + 1} 판단 중... ({len(batch)}건)")

        bid_text = "\n".join([
            f"{j+1}. [{bid['공고번호']}] {bid['공고명']} | {bid['발주기관']} | "
            f"추정가: {bid.get('추정가격', 0)}원 | 계약방법: {bid.get('계약방법', '')}"
            for j, bid in enumerate(batch)
        ])

        prompt = f"""당신은 나라장터 입찰 전문가입니다. 아래 회사 프로필을 보고 각 공고의 입찰 적격 여부를 판단하세요.

## 회사 프로필
{COMPANY_PROFILE}

## 평가할 공고 목록
{bid_text}

## 지시사항
각 공고에 대해 다음 형식으로 JSON 배열만 응답하세요 (다른 텍스트 없이):
[
  {{
    "공고번호": "...",
    "추천여부": "추천" 또는 "보류" 또는 "제외",
    "점수": 0~100,
    "이유": "한 줄 이유"
  }}
]

판단 기준 (관대하게 적용):
- "추천": 업종(사무소모품/위생용품/생필품/판촉/에어컨세척)과 직접 관련된 공고
- "보류": 업종과 부분적으로 관련되거나 가능성 있는 공고
- "제외": 공사, 건설, 완전히 다른 업종(중장비, 의료기기, IT개발 등)만 제외
- 수의계약은 1억 이하 우대, 일반입찰은 금액 무관하게 추천 가능
- 에어컨/냉난방기/공조기 세척 관련은 적극 추천
- 확실하지 않으면 "보류"로 판정 (제외보다 보류 우선)
"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            start = text.find("[")
            end = text.rfind("]") + 1
            results = json.loads(text[start:end])
            all_results.extend(results)
        except Exception as e:
            print(f"  배치 파싱 오류: {e}")
            continue

    return all_results


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
            print(f"   추정가격: {bid.get('추정가격', 0)}원")
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
