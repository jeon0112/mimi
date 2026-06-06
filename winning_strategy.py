"""낙찰 필살기 4종 세트"""

import os
import json
import requests
import anthropic
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
API_KEY = os.getenv("NARA_API_KEY")
BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

COMPANY_INFO = """
회사명: (주)미미
자격: 장애인기업 확인서 보유, 예비사회적기업 지정
우선구매 근거: 중소기업제품 구매촉진 및 판로지원법, 장애인기업활동촉진법
"""


# ─────────────────────────────────────────────
# 필살기 1: 수의계약 우선 타겟 (2천만원 이하)
# ─────────────────────────────────────────────
def filter_suui_targets(bids: list, max_amount: int = 20_000_000) -> list:
    """수의계약 가능 공고 우선 분류"""
    suui = []
    competition = []

    for bid in bids:
        try:
            price = float(str(bid.get("추정가격", 0)).replace(",", "") or 0)
        except Exception:
            price = 0

        contract = bid.get("계약방법", "")
        is_suui = price <= max_amount or "수의" in contract

        if is_suui:
            bid["수의계약여부"] = True
            bid["전략등급"] = "S"  # 최우선
            suui.append(bid)
        else:
            bid["수의계약여부"] = False
            bid["전략등급"] = "A"
            competition.append(bid)

    print(f"  수의계약 대상: {len(suui)}건 (2천만원 이하)")
    print(f"  일반경쟁 대상: {len(competition)}건")
    return suui + competition  # 수의계약 먼저


# ─────────────────────────────────────────────
# 필살기 2: 발주기관 사전 접촉 공문 자동 생성
# ─────────────────────────────────────────────
def generate_contact_letter(agency: str, bid_info: dict = None) -> str:
    """발주기관 우선구매 요청 공문 생성"""
    bid_context = ""
    if bid_info:
        bid_context = f"""
현재 귀 기관에서 진행 중인 공고:
- 공고명: {bid_info.get('공고명', '')}
- 추정가격: {bid_info.get('추정가격', '')}원
- 마감: {bid_info.get('입찰마감일시', '')}
"""

    prompt = f"""다음 발주기관에 보낼 장애인기업 우선구매 요청 공문을 작성해주세요.

발주기관: {agency}
{bid_context}

회사 정보:
{COMPANY_INFO}

공문 요구사항:
1. 공문 형식 (수신, 참조, 제목, 내용, 붙임)
2. 장애인기업활동촉진법 제9조 우선구매 조항 인용
3. 예비사회적기업으로서 사회적 가치 실현 강조
4. 구체적인 납품 가능 품목 제시
5. 담당자 연락 요청으로 마무리

격식체(~합니다)로 작성. A4 1장 분량."""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def generate_contact_letters(recommended: list, output_dir: str) -> list:
    """추천 공고 발주기관에 공문 일괄 생성"""
    os.makedirs(output_dir, exist_ok=True)
    saved = []
    seen_agencies = set()

    for bid in recommended:
        agency = bid.get("발주기관", "")
        if not agency or agency in seen_agencies:
            continue
        seen_agencies.add(agency)

        print(f"  공문 생성: {agency}")
        try:
            letter = generate_contact_letter(agency, bid)
        except Exception as e:
            print(f"  공문 생성 오류 ({agency}): {e}")
            import traceback
            traceback.print_exc()
            continue

        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"공문_{agency}_{date_str}.txt".replace("/", "_")
        filepath = os.path.join(output_dir, filename)

        header = f"""================================================================
  우선구매 요청 공문
================================================================
수신: {agency}
생성일: {datetime.now().strftime('%Y년 %m월 %d일')}
================================================================

"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + letter)

        saved.append(filepath)
        print(f"  ✅ 저장: {os.path.basename(filepath)}")

    return saved


# ─────────────────────────────────────────────
# 필살기 3: 발주기관별 낙찰 패턴 학습
# ─────────────────────────────────────────────
def fetch_agency_bid_history(agency: str, max_results: int = 50) -> list:
    """특정 발주기관의 과거 낙찰 이력 조회"""
    if not API_KEY:
        return []

    params = {
        "serviceKey": API_KEY,
        "numOfRows": max_results,
        "pageNo": 1,
        "ntceInsttNm": agency,
        "type": "json",
    }

    try:
        url = f"{BASE_URL}/getSuccssfulBidListInfoThng"
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", [])
        if isinstance(items, dict):
            items = [items]
        return items or []
    except Exception as e:
        print(f"  기관 이력 조회 오류: {e}")
        return []


def analyze_agency_pattern(agency: str) -> dict:
    """발주기관 낙찰 패턴 분석"""
    items = fetch_agency_bid_history(agency)
    if not items:
        return {"기관": agency, "샘플수": 0, "추천낙찰률": 94.0, "근거": "데이터 없음"}

    rates = []
    for item in items:
        try:
            pred = float(item.get("presmptPrce", 0) or 0)
            win = float(item.get("sucsfbidAmt", 0) or 0)
            if pred > 0 and win > 0:
                rate = (win / pred) * 100
                if 50 <= rate <= 105:
                    rates.append(rate)
        except Exception:
            continue

    if not rates:
        return {"기관": agency, "샘플수": 0, "추천낙찰률": 94.0, "근거": "데이터 없음"}

    import statistics
    avg = statistics.mean(rates)
    # 이 기관에서 낙찰 잘 되는 구간: 평균 기준 ±1%
    recommended_rate = round(avg - 1, 1)

    return {
        "기관": agency,
        "샘플수": len(rates),
        "평균낙찰률": round(avg, 2),
        "최저낙찰률": round(min(rates), 2),
        "최고낙찰률": round(max(rates), 2),
        "추천낙찰률": recommended_rate,
        "근거": f"과거 {len(rates)}건 분석",
    }


# ─────────────────────────────────────────────
# 필살기 4: 마감 임박 + 경쟁자 적은 공고
# ─────────────────────────────────────────────
def fetch_deadline_soon_bids(days_left: int = 3) -> list:
    """마감 임박 공고 조회 (경쟁자가 놓친 공고)"""
    if not API_KEY:
        return []

    now = datetime.now()
    start = now.strftime("%Y%m%d") + "0000"
    end = (now + timedelta(days=days_left)).strftime("%Y%m%d") + "2359"

    params = {
        "serviceKey": API_KEY,
        "numOfRows": 100,
        "pageNo": 1,
        "inqryDiv": 1,
        "inqryBgnDt": start,
        "inqryEndDt": end,
        "type": "json",
    }

    try:
        url = f"{BASE_URL}/getBidPblancListInfoThng"
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", [])
        if isinstance(items, dict):
            items = [items]
        return items or []
    except Exception as e:
        print(f"  마감 임박 공고 조회 오류: {e}")
        return []


def find_low_competition_bids(keywords: list) -> list:
    """경쟁자가 적을 것 같은 마감 임박 공고 탐색"""
    print("  마감 3일 이내 공고 탐색 중...")
    items = fetch_deadline_soon_bids(days_left=3)

    results = []
    for item in items:
        name = item.get("bidNtceNm", "")
        if any(kw in name for kw in keywords):
            deadline = item.get("bidClseDt", "")
            try:
                dl = datetime.strptime(deadline[:8], "%Y%m%d")
                days_remaining = (dl - datetime.now()).days + 1
            except Exception:
                days_remaining = 99

            results.append({
                "공고명": name,
                "발주기관": item.get("ntceInsttNm", ""),
                "추정가격": item.get("asignBdgtAmt", 0),
                "마감일": deadline,
                "남은일수": days_remaining,
                "공고번호": item.get("bidNtceNo", ""),
                "전략": "마감임박_단독입찰기회",
            })

    # 마감 임박 순 정렬
    results.sort(key=lambda x: x.get("남은일수", 99))
    print(f"  마감 임박 관련 공고: {len(results)}건")
    return results


# ─────────────────────────────────────────────
# 전체 전략 통합 실행
# ─────────────────────────────────────────────
def run_winning_strategy(recommended: list, held: list, output_dir: str) -> dict:
    """4가지 필살기 통합 실행"""
    print("\n" + "="*55)
    print("  낙찰 필살기 4종 세트 실행")
    print("="*55)

    results = {}

    # 필살기 1: 수의계약 우선 분류
    print("\n[필살기 1] 수의계약 우선 타겟 분류")
    all_bids = recommended + held
    prioritized = filter_suui_targets(all_bids)
    suui_bids = [b for b in prioritized if b.get("수의계약여부")]
    results["수의계약대상"] = suui_bids

    # 필살기 2: 발주기관 공문 생성
    print("\n[필살기 2] 발주기관 사전 접촉 공문 생성")
    letter_dir = os.path.join(output_dir, "공문")
    letter_files = generate_contact_letters(recommended, letter_dir)
    results["공문파일"] = letter_files

    # 필살기 3: 발주기관별 낙찰 패턴
    print("\n[필살기 3] 발주기관 낙찰 패턴 분석")
    agency_patterns = {}
    for bid in recommended:
        agency = bid.get("발주기관", "")
        if agency and agency not in agency_patterns:
            pattern = analyze_agency_pattern(agency)
            agency_patterns[agency] = pattern
            print(f"  {agency}: 추천 낙찰률 {pattern['추천낙찰률']}% ({pattern['근거']})")
    results["기관별패턴"] = agency_patterns

    # 필살기 4: 마감 임박 공고
    print("\n[필살기 4] 마감 임박 단독 입찰 기회 탐색")
    from nara_filter import FILTER_KEYWORDS
    urgent = find_low_competition_bids(FILTER_KEYWORDS)
    results["마감임박공고"] = urgent[:5]  # 상위 5건

    return results


def format_strategy_email(results: dict) -> str:
    """이메일용 전략 요약 텍스트 생성"""
    lines = ["\n" + "="*50, "🏆 낙찰 필살기 전략 보고", "="*50]

    # 수의계약 대상
    suui = results.get("수의계약대상", [])
    if suui:
        lines.append(f"\n🎯 [필살기1] 수의계약 우선 대상 ({len(suui)}건)")
        for b in suui[:3]:
            price = b.get("추정가격", 0)
            try:
                price_str = f"{int(float(str(price).replace(',',''))):,}"
            except Exception:
                price_str = str(price)
            lines.append(f"  • {b['공고명'][:30]} ({price_str}원)")

    # 기관별 패턴
    patterns = results.get("기관별패턴", {})
    if patterns:
        lines.append(f"\n📊 [필살기3] 발주기관별 최적 낙찰률")
        for agency, p in patterns.items():
            lines.append(f"  • {agency}: {p['추천낙찰률']}% 추천 ({p['근거']})")

    # 마감 임박
    urgent = results.get("마감임박공고", [])
    if urgent:
        lines.append(f"\n⚡ [필살기4] 마감 임박 단독 기회 ({len(urgent)}건)")
        for b in urgent[:3]:
            lines.append(f"  • {b['공고명'][:30]} (D-{b['남은일수']})")

    # 공문
    letters = results.get("공문파일", [])
    if letters:
        lines.append(f"\n📄 [필살기2] 발주기관 접촉 공문 {len(letters)}건 생성 완료 (첨부)")

    return "\n".join(lines)
