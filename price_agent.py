"""네이버 쇼핑 API를 활용한 품목 단가 자동 조회 에이전트"""

import os
import json
import time
import requests
import openpyxl
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"

# 마진율 기본값
DEFAULT_MARGIN = 0.20  # 20%
DELIVERY_COST = 3000   # 배송비


def search_price(keyword: str, display: int = 5) -> list:
    """네이버 쇼핑에서 키워드로 최저가 검색"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("오류: NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다.")
        return []

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": keyword,
        "display": display,
        "sort": "asc",  # 가격 오름차순
    }

    try:
        response = requests.get(NAVER_SEARCH_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("items", [])
        return items
    except Exception as e:
        print(f"  검색 오류 ({keyword}): {e}")
        return []


def get_min_price(keyword: str) -> dict:
    """최저가 및 평균가 반환"""
    items = search_price(keyword)
    if not items:
        return {"keyword": keyword, "min_price": None, "avg_price": None, "title": ""}

    prices = []
    for item in items:
        try:
            price = int(item.get("lprice", 0))
            if price > 0:
                prices.append(price)
        except Exception:
            continue

    if not prices:
        return {"keyword": keyword, "min_price": None, "avg_price": None, "title": ""}

    return {
        "keyword": keyword,
        "min_price": min(prices),
        "avg_price": int(sum(prices) / len(prices)),
        "title": items[0].get("title", "").replace("<b>", "").replace("</b>", ""),
    }


def calculate_bid_price(cost_price: int, margin: float = DEFAULT_MARGIN) -> int:
    """매입가 → 입찰 단가 계산"""
    return int((cost_price + DELIVERY_COST) * (1 + margin))


def process_excel(input_file: str, output_file: str = None, margin: float = DEFAULT_MARGIN) -> str:
    """엑셀 품목 리스트에서 단가 자동 조회 후 결과 저장"""
    if output_file is None:
        output_file = input_file.replace(".xlsx", "_단가조회결과.xlsx")

    wb = openpyxl.load_workbook(input_file)
    ws = wb.active

    # 헤더 찾기 (순번, 품목, 규격, 단위, 예정수량, 단가, 금액)
    header_row = None
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), 1):
        if row and "품목" in str(row):
            header_row = i
            break

    if not header_row:
        print("헤더를 찾을 수 없습니다.")
        return ""

    # 컬럼 위치 파악
    headers = [cell.value for cell in ws[header_row]]
    품목_col = headers.index("품목") + 1 if "품목" in headers else 2
    규격_col = headers.index("규격") + 1 if "규격" in headers else 3
    수량_col = headers.index("예정수량") + 1 if "예정수량" in headers else 5
    단가_col = headers.index("단가") + 1 if "단가" in headers else 6
    금액_col = headers.index("금액") + 1 if "금액" in headers else 7

    # 매입가/입찰단가 컬럼 추가
    ws.cell(row=header_row, column=단가_col).value = "단가(입찰)"
    ws.cell(row=header_row, column=금액_col).value = "금액(입찰)"
    매입가_col = ws.max_column + 1
    ws.cell(row=header_row, column=매입가_col).value = "네이버최저가"
    ws.cell(row=header_row, column=매입가_col + 1).value = "검색상품명"

    total_rows = ws.max_row - header_row
    print(f"\n총 {total_rows}개 품목 단가 조회 시작...\n")

    for row_idx in range(header_row + 1, ws.max_row + 1):
        품목 = ws.cell(row=row_idx, column=품목_col).value
        규격 = ws.cell(row=row_idx, column=규격_col).value
        수량 = ws.cell(row=row_idx, column=수량_col).value

        if not 품목:
            continue

        # 검색 키워드 조합
        keyword = f"{품목} {규격}" if 규격 else str(품목)
        keyword = keyword.strip()

        print(f"  [{row_idx - header_row}/{total_rows}] {keyword} 검색 중...")

        result = get_min_price(keyword)
        min_price = result["min_price"]

        if min_price:
            bid_price = calculate_bid_price(min_price, margin)
            amount = bid_price * int(수량) if 수량 else 0

            ws.cell(row=row_idx, column=단가_col).value = bid_price
            ws.cell(row=row_idx, column=금액_col).value = amount
            ws.cell(row=row_idx, column=매입가_col).value = min_price
            ws.cell(row=row_idx, column=매입가_col + 1).value = result["title"][:30]

            print(f"    최저가: {min_price:,}원 → 입찰단가: {bid_price:,}원 (수량: {수량})")
        else:
            ws.cell(row=row_idx, column=단가_col).value = "수동입력필요"
            print(f"    검색결과 없음 → 수동 입력 필요")

        time.sleep(0.1)  # API 호출 간격

    # 총액 합계
    total_amount = sum(
        ws.cell(row=r, column=금액_col).value or 0
        for r in range(header_row + 1, ws.max_row + 1)
        if isinstance(ws.cell(row=r, column=금액_col).value, (int, float))
    )

    wb.save(output_file)
    print(f"\n✅ 완료! 저장: {output_file}")
    print(f"   총 입찰 예상금액: {total_amount:,}원")
    return output_file


if __name__ == "__main__":
    import sys

    print("=" * 55)
    print("  품목 단가 자동 조회 에이전트 (네이버 쇼핑)")
    print("=" * 55)

    # 엑셀 파일 경로
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        excel_file = input("\n엑셀 파일 경로를 입력하세요: ").strip().strip('"')

    if not os.path.exists(excel_file):
        print(f"파일을 찾을 수 없습니다: {excel_file}")
        sys.exit(1)

    margin_input = input("마진율 입력 (기본 20%, 엔터 입력 시 기본값): ").strip()
    margin = float(margin_input) / 100 if margin_input else DEFAULT_MARGIN

    process_excel(excel_file, margin=margin)
