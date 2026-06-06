"""나라장터 입찰공고 수집 모듈"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NARA_API_KEY")
BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"


def get_today():
    return datetime.now().strftime("%Y%m%d")


def get_date_before(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")


def fetch_bid_list(keyword: str = "", days: int = 3, max_results: int = 100) -> list:
    """나라장터 입찰공고 목록 조회"""
    if not API_KEY:
        print("오류: NARA_API_KEY가 설정되지 않았습니다.")
        return []

    start_date = get_date_before(days)
    end_date = get_today()

    params = {
        "serviceKey": API_KEY,
        "numOfRows": max_results,
        "pageNo": 1,
        "inqryDiv": 1,
        "inqryBgnDt": start_date + "0000",
        "inqryEndDt": end_date + "2359",
        "type": "json",
    }

    if keyword:
        params["bidNtceNm"] = keyword

    try:
        url = f"{BASE_URL}/getBidPblancListInfoThng"
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

    except requests.exceptions.HTTPError as e:
        print(f"API 오류 ({e.response.status_code}): {e.response.text[:300]}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"네트워크 오류: {e}")
        return []
    except Exception as e:
        print(f"오류: {e}")
        return []


def parse_bid_item(item: dict) -> dict:
    """공고 항목 파싱"""
    return {
        "공고번호": item.get("bidNtceNo", ""),
        "공고명": item.get("bidNtceNm", ""),
        "발주기관": item.get("ntceInsttNm", ""),
        "공고일시": item.get("bidNtceDt", ""),
        "입찰마감일시": item.get("bidClseDt", ""),
        "추정가격": item.get("asignBdgtAmt", 0),
        "계약방법": item.get("cntrctMthd", ""),
        "입찰방식": item.get("bidMthdNm", ""),
        "공고URL": f"https://www.g2b.go.kr/ep/invitation/publish/bidInvitDtlPublish.do?bidno={item.get('bidNtceNo', '')}&bidseq=00",
    }


def collect_bids(keywords: list = None, days: int = 3) -> list:
    """키워드 목록으로 공고 수집"""
    if keywords is None:
        keywords = ["A4용지", "복사용지", "토너", "화장지", "세정제", "방역", "생필품", "판촉",
                    "에어컨세척", "에어컨 세척", "냉방기세척", "공조기세척", "냉난방기세척",
                    "홍보물", "인쇄물", "현수막", "브로슈어", "리플렛", "홍보용품"]

    all_bids = []
    seen = set()

    for keyword in keywords:
        print(f"  '{keyword}' 공고 수집 중...")
        items = fetch_bid_list(keyword=keyword, days=days)
        for item in items:
            parsed = parse_bid_item(item)
            bid_no = parsed["공고번호"]
            if bid_no and bid_no not in seen:
                seen.add(bid_no)
                all_bids.append(parsed)

    print(f"\n총 {len(all_bids)}건 수집 완료")
    return all_bids


def save_to_json(bids: list, filename: str = None) -> str:
    """수집된 공고를 JSON 파일로 저장"""
    if filename is None:
        filename = f"bids_{get_today()}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(bids, f, ensure_ascii=False, indent=2)

    print(f"저장 완료: {filename}")
    return filename


if __name__ == "__main__":
    print("=== 나라장터 공고 수집 시작 ===\n")
    bids = collect_bids(days=3)

    if bids:
        save_to_json(bids)
        print("\n[샘플 공고]")
        for bid in bids[:3]:
            print(f"- {bid['공고명']} ({bid['발주기관']}) / 추정가: {bid['추정가격']:,}원")
    else:
        print("수집된 공고가 없습니다.")
