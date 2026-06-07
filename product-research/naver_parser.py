"""네이버 쇼핑 API 파서 + FastAPI 서버 — 상품 리서치용 독립 모듈

사용법:
    # 서버 실행
    uvicorn naver_parser:app --host 0.0.0.0 --port 8000 --reload

    # CLI 직접 실행
    python naver_parser.py "A4용지"
    python naver_parser.py "토너 삼성" --display 30

환경변수:
    NAVER_CLIENT_ID      네이버 개발자센터 Client ID
    NAVER_CLIENT_SECRET  네이버 개발자센터 Client Secret
"""

import os
import re
import sys
import json
import time
import argparse
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"
NAVER_BEST100_URL = "https://search.shopping.naver.com/api/best100/main"
NAVER_REVIEW_URL = "https://search.shopping.naver.com/api/search"

HEADERS_API = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}

HEADERS_WEB = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://search.shopping.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


# ──────────────────────────────────────────────
# 1. 키워드 검색 (/search)
# ──────────────────────────────────────────────

def search(keyword: str, display: int = 20, start: int = 1, sort: str = "sim") -> dict:
    """네이버 쇼핑 검색 API 호출.

    Args:
        keyword: 검색어
        display: 결과 수 (최대 100)
        start: 시작 인덱스
        sort: sim(정확도) | date | asc | dsc

    Returns:
        {keyword, total, items: [{title, price, mall, link, product_id, image, category}]}
    """
    if not NAVER_CLIENT_ID:
        raise RuntimeError("NAVER_CLIENT_ID 환경변수가 설정되지 않았습니다.")

    params = {
        "query": keyword,
        "display": min(display, 100),
        "start": start,
        "sort": sort,
    }
    resp = requests.get(NAVER_SEARCH_URL, headers=HEADERS_API, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    items = []
    for item in data.get("items", []):
        title = re.sub(r"<[^>]+>", "", item.get("title", ""))
        items.append({
            "title": title,
            "price": int(item.get("lprice", 0)),
            "price_high": int(item.get("hprice", 0) or 0),
            "mall": item.get("mallName", ""),
            "link": item.get("link", ""),
            "product_id": item.get("productId", ""),
            "catalog_id": item.get("productId", ""),
            "image": item.get("image", ""),
            "category1": item.get("category1", ""),
            "category2": item.get("category2", ""),
            "category3": item.get("category3", ""),
            "brand": item.get("brand", ""),
            "maker": item.get("maker", ""),
            "review_count": None,  # /review 엔드포인트로 별도 조회
        })

    return {
        "keyword": keyword,
        "total": data.get("total", 0),
        "display": len(items),
        "items": items,
    }


# ──────────────────────────────────────────────
# 2. 베스트 100 (/best100)
# ──────────────────────────────────────────────

def best100(cat_id: str = "50000167", period: str = "week", limit: int = 100) -> dict:
    """네이버 쇼핑 베스트 100 내부 API 호출.

    Args:
        cat_id: 카테고리 ID (기본값 50000167 = 사무/문구)
        period: week | day
        limit: 최대 반환 수 (1~100)

    Returns:
        {cat_id, period, count, items: [{rank, title, price, mall, link, image, review_count}]}
    """
    params = {
        "catId": cat_id,
        "period": period,
        "pageSize": min(limit, 100),
        "page": 1,
    }
    resp = requests.get(
        NAVER_BEST100_URL,
        headers=HEADERS_WEB,
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    items = []
    rank = 1
    for item in data.get("productList", [])[:limit]:
        title = re.sub(r"<[^>]+>", "", item.get("productName", ""))
        items.append({
            "rank": rank,
            "title": title,
            "price": int(item.get("lowPrice", 0) or 0),
            "mall": item.get("mallName", ""),
            "link": item.get("productUrl", "") or f"https://search.shopping.naver.com/catalog/{item.get('nvMid', '')}",
            "image": item.get("imageUrl", ""),
            "product_id": item.get("nvMid", ""),
            "review_count": int(item.get("reviewCount", 0) or 0),
            "purchase_count": int(item.get("purchaseCnt", 0) or 0),
            "category": item.get("categoryName", ""),
        })
        rank += 1

    return {
        "cat_id": cat_id,
        "period": period,
        "count": len(items),
        "items": items,
    }


# ──────────────────────────────────────────────
# 3. 리뷰수 조회 (/review)
# ──────────────────────────────────────────────

def get_review_count(product_id: str) -> dict:
    """네이버 쇼핑 카탈로그 검색 내부 API로 리뷰수 조회.

    product_id는 search() 결과의 catalog_id 또는 best100()의 product_id 값.

    Returns:
        {product_id, review_count, title, price}
    """
    params = {
        "query": "",
        "cat_id": "",
        "productSet": "total",
        "nvMid": product_id,
        "pagingIndex": 1,
        "pagingSize": 1,
    }
    try:
        resp = requests.get(
            NAVER_REVIEW_URL,
            headers=HEADERS_WEB,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        products = data.get("shoppingResult", {}).get("products", [])
        if not products:
            return {"product_id": product_id, "review_count": None, "error": "상품 없음"}
        p = products[0]
        return {
            "product_id": product_id,
            "review_count": int(p.get("reviewCount", 0) or 0),
            "title": re.sub(r"<[^>]+>", "", p.get("productName", "")),
            "price": int(p.get("lowPrice", 0) or 0),
        }
    except Exception as e:
        return {"product_id": product_id, "review_count": None, "error": str(e)}


def get_review_counts_bulk(product_ids: list[str], delay: float = 0.3) -> list[dict]:
    """여러 상품의 리뷰수를 순차 조회. delay로 요청 간격 조절."""
    results = []
    for pid in product_ids:
        results.append(get_review_count(pid))
        time.sleep(delay)
    return results


# ──────────────────────────────────────────────
# FastAPI 서버
# ──────────────────────────────────────────────

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import JSONResponse

    app = FastAPI(
        title="네이버 쇼핑 리서치 API",
        description="n8n 연동용 — /search, /best100, /review",
        version="1.0.0",
    )

    @app.get("/search")
    def api_search(
        keyword: str = Query(..., description="검색어"),
        display: int = Query(20, ge=1, le=100, description="결과 수"),
        start: int = Query(1, ge=1, description="시작 인덱스"),
        sort: str = Query("sim", description="정렬: sim | date | asc | dsc"),
    ):
        """키워드로 네이버 쇼핑 검색."""
        try:
            return search(keyword, display=display, start=start, sort=sort)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except requests.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"네이버 API 오류: {e}")

    @app.get("/best100")
    def api_best100(
        cat_id: str = Query("50000167", description="카테고리 ID (기본: 사무/문구)"),
        period: str = Query("week", description="집계 기간: week | day"),
        limit: int = Query(100, ge=1, le=100, description="반환 수"),
    ):
        """네이버 쇼핑 카테고리별 베스트 100 조회."""
        try:
            return best100(cat_id=cat_id, period=period, limit=limit)
        except requests.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"네이버 내부 API 오류: {e}")

    @app.get("/review")
    def api_review(
        product_id: str = Query(..., description="네이버 상품 ID (nvMid / catalog_id)"),
    ):
        """단일 상품 리뷰수 조회."""
        return get_review_count(product_id)

    @app.post("/review/bulk")
    def api_review_bulk(product_ids: list[str], delay: float = 0.3):
        """여러 상품 리뷰수 일괄 조회 (POST body: JSON 배열)."""
        if len(product_ids) > 50:
            raise HTTPException(status_code=400, detail="한 번에 최대 50개까지 가능합니다.")
        return get_review_counts_bulk(product_ids, delay=delay)

    @app.get("/health")
    def health():
        return {"status": "ok", "naver_key_set": bool(NAVER_CLIENT_ID)}

except ImportError:
    app = None


# ──────────────────────────────────────────────
# CLI 진입점
# ──────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(description="네이버 쇼핑 리서치 CLI")
    parser.add_argument("keyword", nargs="?", help="검색어")
    parser.add_argument("--display", type=int, default=20)
    parser.add_argument("--sort", default="sim")
    parser.add_argument("--best100", metavar="CAT_ID", help="베스트100 조회 (카테고리 ID)")
    parser.add_argument("--review", metavar="PRODUCT_ID", help="리뷰수 조회")
    parser.add_argument("--period", default="week")
    args = parser.parse_args()

    if args.best100:
        result = best100(cat_id=args.best100, period=args.period)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.review:
        result = get_review_count(args.review)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.keyword:
        result = search(args.keyword, display=args.display, sort=args.sort)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
