"""나라장터 낙찰 데이터 분석 → 최적 입찰가 추천"""

import os
import requests
import statistics
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NARA_API_KEY")
BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"


def fetch_bid_results(keyword: str, max_results: int = 100) -> list:
    """나라장터 낙찰 결과 조회"""
    if not API_KEY:
        print("오류: NARA_API_KEY가 설정되지 않았습니다.")
        return []

    params = {
        "serviceKey": API_KEY,
        "numOfRows": max_results,
        "pageNo": 1,
        "inqryDiv": 1,
        "bidNtceNm": keyword,
        "type": "json",
    }

    try:
        url = f"{BASE_URL}/getSuccssfulBidListInfoThng"
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", [])
        )
        if isinstance(items, dict):
            items = [items]
        return items or []
    except Exception as e:
        print(f"  낙찰 데이터 조회 오류: {e}")
        return []


def analyze_winning_rates(items: list) -> dict:
    """낙찰 데이터에서 낙찰률 분석"""
    rates = []
    samples = []

    for item in items:
        try:
            # 예정가격 (발주기관 내부 기준가)
            pred_price = float(item.get("presmptPrce", 0) or 0)
            # 낙찰금액
            win_price = float(item.get("sucsfbidAmt", 0) or 0)
            # 추정가격
            est_price = float(item.get("asignBdgtAmt", 0) or 0)

            if pred_price > 0 and win_price > 0:
                rate = (win_price / pred_price) * 100
                if 50 <= rate <= 105:  # 비정상 데이터 제외
                    rates.append(rate)
                    samples.append({
                        "공고명": item.get("bidNtceNm", "")[:30],
                        "발주기관": item.get("ntceInsttNm", ""),
                        "추정가격": est_price,
                        "예정가격": pred_price,
                        "낙찰금액": win_price,
                        "낙찰률": round(rate, 2),
                    })
        except Exception:
            continue

    if not rates:
        return {"샘플수": 0, "rates": [], "samples": []}

    return {
        "샘플수": len(rates),
        "평균낙찰률": round(statistics.mean(rates), 2),
        "중앙값낙찰률": round(statistics.median(rates), 2),
        "최저낙찰률": round(min(rates), 2),
        "최고낙찰률": round(max(rates), 2),
        "표준편차": round(statistics.stdev(rates), 2) if len(rates) > 1 else 0,
        "rates": rates,
        "samples": samples[:5],  # 상위 5개 샘플
    }


def recommend_bid_price(estimated_price, analysis: dict, strategy: str = "중간") -> dict:
    """분석 결과를 바탕으로 입찰가 추천"""
    if not estimated_price:
        return {}

    try:
        est = float(str(estimated_price).replace(",", ""))
    except Exception:
        return {}

    if analysis.get("샘플수", 0) < 3:
        # 데이터 부족 시 기본값 사용
        rates = {"안정": 0.98, "중간": 0.94, "공격": 0.90}
        note = "데이터 부족 - 일반 기준 적용"
    else:
        avg = analysis["평균낙찰률"] / 100
        med = analysis["중앙값낙찰률"] / 100
        low = analysis["최저낙찰률"] / 100

        rates = {
            "안정": avg,                          # 평균낙찰률 (당선 가능성 높음)
            "중간": (avg + med) / 2,              # 평균과 중앙값 사이
            "공격": max(low * 1.02, 0.875),       # 최저낙찰률 근처 (낙찰하한율 이상)
        }
        note = f"과거 {analysis['샘플수']}건 낙찰 데이터 기반"

    chosen_rate = rates.get(strategy, rates["중간"])
    bid_price = int(est * chosen_rate)

    return {
        "추정가격": int(est),
        "전략": strategy,
        "적용낙찰률": f"{chosen_rate*100:.1f}%",
        "추천입찰가": bid_price,
        "예상마진": int(est - bid_price),
        "안정형입찰가": int(est * rates["안정"]),
        "중간형입찰가": int(est * rates["중간"]),
        "공격형입찰가": int(est * rates["공격"]),
        "근거": note,
    }


def analyze_bid(bid_info: dict) -> dict:
    """공고 하나에 대한 전체 입찰가 분석"""
    bid_name = bid_info.get("공고명", "")
    estimated_price = bid_info.get("추정가격", 0)

    # 키워드 추출 (공고명 앞 2단어)
    words = bid_name.split()
    keyword = " ".join(words[:2]) if len(words) >= 2 else bid_name[:10]

    print(f"\n[입찰가 분석] {bid_name[:40]}")
    print(f"  추정가격: {int(float(str(estimated_price).replace(',','') or 0)):,}원")
    print(f"  유사 낙찰 데이터 검색 중: '{keyword}'")

    items = fetch_bid_results(keyword)
    analysis = analyze_winning_rates(items)

    print(f"  유사 낙찰 데이터: {analysis.get('샘플수', 0)}건")
    if analysis.get("샘플수", 0) >= 3:
        print(f"  평균 낙찰률: {analysis['평균낙찰률']}% | 범위: {analysis['최저낙찰률']}~{analysis['최고낙찰률']}%")

    recommendation = recommend_bid_price(estimated_price, analysis)

    return {
        "공고명": bid_name,
        "추정가격": estimated_price,
        "낙찰분석": analysis,
        "입찰가추천": recommendation,
    }


def print_report(result: dict) -> None:
    """분석 결과 출력"""
    rec = result.get("입찰가추천", {})
    analysis = result.get("낙찰분석", {})

    print(f"\n{'='*55}")
    print(f"공고: {result['공고명'][:45]}")
    print(f"{'='*55}")
    print(f"추정가격:    {int(float(str(result['추정가격']).replace(',','') or 0)):>15,}원")
    print(f"{'─'*55}")

    if rec:
        print(f"[입찰가 추천]")
        print(f"  안정형:  {rec.get('안정형입찰가', 0):>15,}원  (낙찰 가능성 높음)")
        print(f"  중간형:  {rec.get('중간형입찰가', 0):>15,}원  (균형)")
        print(f"  공격형:  {rec.get('공격형입찰가', 0):>15,}원  (마진 최대화)")
        print(f"{'─'*55}")
        print(f"  근거: {rec.get('근거', '')}")

    if analysis.get("샘플수", 0) > 0:
        print(f"\n[유사 낙찰 사례 {analysis['샘플수']}건]")
        for s in analysis.get("samples", []):
            print(f"  • {s['공고명']} ({s['발주기관']})")
            print(f"    낙찰가: {int(s['낙찰금액']):,}원 / 낙찰률: {s['낙찰률']}%")
    print(f"{'='*55}")


def analyze_recommended_bids(json_file: str) -> list:
    """추천 공고 JSON에서 추천 공고 전체 입찰가 분석"""
    import json

    with open(json_file, "r", encoding="utf-8") as f:
        bids = json.load(f)

    recommended = [b for b in bids if b.get("평가", {}).get("추천여부") == "추천"]
    print(f"추천 공고 {len(recommended)}건 입찰가 분석 시작\n")

    results = []
    for bid in recommended:
        result = analyze_bid(bid)
        print_report(result)
        results.append(result)

    return results


if __name__ == "__main__":
    import sys
    import glob

    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        dirs = [
            os.path.join(os.path.expanduser("~"), "Desktop", "나라장터결과"),
            "output",
            ".",
        ]
        json_file = None
        for d in dirs:
            files = sorted(glob.glob(os.path.join(d, "recommended_bids_*.json")), reverse=True)
            if files:
                json_file = files[0]
                break

    if not json_file:
        print("JSON 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"파일: {json_file}")
    analyze_recommended_bids(json_file)
