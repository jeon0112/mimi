"""정부 부처 AI/AX 지원사업·공모 수집 모듈

전 부처의 기업지원사업을 통합 제공하는 '기업마당(bizinfo.go.kr)' 공개 API를 주 소스로,
'K-Startup(창업지원)' data.go.kr API를 보조 소스로 사용해 AI/AX 관련 공고를 모은다.

- 기업마당: 인증키 불필요 (공개 JSON 엔드포인트)
- K-Startup: data.go.kr 서비스키 필요 (GOV_DATA_API_KEY 또는 NARA_API_KEY 재사용, 선택)
"""

import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# K-Startup 등 data.go.kr 계열 보조 소스용 (선택). NARA_API_KEY와 동일 키 사용 가능.
GOV_DATA_API_KEY = os.getenv("GOV_DATA_API_KEY") or os.getenv("NARA_API_KEY")

# 기업마당 공개 지원사업 목록 (인증키 불필요)
BIZINFO_URL = "https://www.bizinfo.go.kr/uss/rss/bsnsPolicyList.do"
BIZINFO_HOST = "https://www.bizinfo.go.kr"

# K-Startup 사업공고 (data.go.kr)
KSTARTUP_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"

# AI/AX 관련 수집 키워드
AI_KEYWORDS = [
    "인공지능", "AI", "에이아이", "AX", "인공지능전환", "AI전환", "AI융합",
    "생성형", "생성형AI", "초거대", "초거대AI", "LLM", "거대언어모델",
    "머신러닝", "딥러닝", "데이터바우처", "AI바우처", "데이터", "빅데이터",
    "디지털전환", "DX", "지능형", "스마트공장", "클라우드", "SaaS",
    "디지털융합", "챗봇", "음성인식", "영상인식", "자율", "로봇",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MimiGovAICrawler/1.0)",
    "Accept": "application/json, text/plain, */*",
}


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


def _date_before(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")


def _first(item: dict, *keys, default=""):
    """여러 후보 필드명 중 값이 있는 첫 항목 반환 (API 필드명 편차 대응)"""
    for k in keys:
        v = item.get(k)
        if v not in (None, "", "null"):
            return v
    return default


def _parse_date_token(text: str) -> str:
    """문자열에서 YYYYMMDD 8자리를 추출 (등록일/신청기간 비교용)"""
    if not text:
        return ""
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


# ─────────────────────────────────────────────
# 기업마당 (전 부처 통합)
# ─────────────────────────────────────────────
def fetch_bizinfo(max_results: int = 200) -> list:
    """기업마당 지원사업 목록 조회 (공개 JSON)"""
    params = {
        "dataType": "json",
        "searchCnt": max_results,
        "rows": max_results,
    }
    try:
        resp = requests.get(BIZINFO_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  기업마당 조회 오류: {e}")
        return []

    # 응답 루트 구조 편차 대응: jsonArray / list / items
    if isinstance(data, dict):
        rows = _first(data, "jsonArray", "list", "items", "result", default=[])
    else:
        rows = data
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return []
    return rows


def parse_bizinfo_item(item: dict) -> dict:
    """기업마당 항목 파싱 → 표준 스키마"""
    url = _first(item, "pblancUrl", "rceptEngnHmpgUrl", "flpthNm")
    if url and url.startswith("/"):
        url = BIZINFO_HOST + url
    return {
        "공고ID": _first(item, "pblancId", "id"),
        "공고명": _first(item, "pblancNm", "polcyBizNm", "title"),
        "소관부처": _first(item, "jrsdInsttNm", "ministry", default="기업마당"),
        "수행기관": _first(item, "excInsttNm", "instt"),
        "지원분야": _first(item, "pldirSportRealmLclasCodeNm", "sportRealmLclasCodeNm"),
        "신청기간": _first(item, "reqstBeginEndDe", "aplyYmd", "reqstDe"),
        "등록일": _parse_date_token(_first(item, "creatPnttm", "regDt", "creatDt")),
        "해시태그": _first(item, "hashtags", "hashTag"),
        "출처": "기업마당",
        "공고URL": url or BIZINFO_HOST,
    }


# ─────────────────────────────────────────────
# K-Startup (창업진흥원, 선택)
# ─────────────────────────────────────────────
def fetch_kstartup(max_results: int = 100) -> list:
    """K-Startup 사업공고 조회 (data.go.kr 서비스키 필요)"""
    if not GOV_DATA_API_KEY:
        return []
    params = {
        "serviceKey": GOV_DATA_API_KEY,
        "numOfRows": max_results,
        "pageNo": 1,
        "returnType": "json",
    }
    try:
        resp = requests.get(KSTARTUP_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  K-Startup 조회 오류 (선택 소스, 건너뜀): {e}")
        return []

    rows = []
    if isinstance(data, dict):
        body = data.get("response", {}).get("body", data)
        rows = _first(body, "items", "item", "data", default=[])
        if isinstance(rows, dict):
            rows = _first(rows, "item", default=[rows])
    if isinstance(rows, dict):
        rows = [rows]
    return rows if isinstance(rows, list) else []


def parse_kstartup_item(item: dict) -> dict:
    """K-Startup 항목 파싱 → 표준 스키마"""
    if isinstance(item, dict) and "col" in item:  # 일부 응답은 {col:[{...}]} 형태
        pass
    pid = _first(item, "pbanc_sn", "id", "announcementId")
    url = _first(item, "detl_pg_url", "pbanc_url", "url")
    if not url and pid:
        url = f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?pbancSn={pid}"
    return {
        "공고ID": str(pid),
        "공고명": _first(item, "biz_pbanc_nm", "intg_pbanc_biz_nm", "title"),
        "소관부처": _first(item, "pbanc_ntrp_nm", "supt_biz_titl_nm", default="중소벤처기업부"),
        "수행기관": _first(item, "pbanc_ntrp_nm", "excInsttNm"),
        "지원분야": _first(item, "supt_biz_clsfc", "biz_category_cd", default="창업지원"),
        "신청기간": f"{_first(item, 'pbanc_rcpt_bgng_dt')} ~ {_first(item, 'pbanc_rcpt_end_dt')}".strip(" ~"),
        "등록일": _parse_date_token(_first(item, "creat_dt", "rgstr_dt")),
        "해시태그": _first(item, "biz_supt_bdgt_info", "supt_regin"),
        "출처": "K-Startup",
        "공고URL": url or "https://www.k-startup.go.kr",
    }


# ─────────────────────────────────────────────
# 통합 수집
# ─────────────────────────────────────────────
def _matches_ai(record: dict) -> bool:
    """공고명/지원분야/해시태그에 AI/AX 키워드가 포함되는지"""
    haystack = " ".join([
        record.get("공고명", ""),
        record.get("지원분야", ""),
        record.get("해시태그", ""),
    ]).upper()
    for kw in AI_KEYWORDS:
        k = kw.upper()
        # 'AI'는 오탐(예: MAINtenance) 방지를 위해 공백/기호 경계로 판단
        if k in ("AI", "AX", "DX", "LLM"):
            padded = f" {haystack} ".replace("(", " ").replace(")", " ").replace("/", " ").replace("-", " ")
            if f" {k} " in padded or f" {k}," in padded:
                return True
        elif k in haystack:
            return True
    return False


def collect_gov_ai(days: int = 3, include_kstartup: bool = True) -> list:
    """AI/AX 관련 정부지원사업·공모를 통합 수집

    days: 등록일 기준 최근 N일 이내 공고만 (0이면 기간 필터 없음)
    """
    records = []

    print("  [기업마당] 전 부처 지원사업 수집 중...")
    for raw in fetch_bizinfo():
        records.append(parse_bizinfo_item(raw))

    if include_kstartup:
        print("  [K-Startup] 창업지원 공고 수집 중...")
        for raw in fetch_kstartup():
            records.append(parse_kstartup_item(raw))

    # AI/AX 키워드 필터
    ai_records = [r for r in records if _matches_ai(r)]

    # 등록일 기준 최근성 필터 (등록일 파싱 실패 건은 포함)
    if days and days > 0:
        cutoff = _date_before(days)
        recent = []
        for r in ai_records:
            reg = r.get("등록일", "")
            if not reg or reg >= cutoff:
                recent.append(r)
        ai_records = recent

    # 중복 제거 (공고ID → 공고명 순)
    seen = set()
    unique = []
    for r in ai_records:
        key = r.get("공고ID") or r.get("공고명")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    print(f"\n총 {len(records)}건 수집 → AI/AX 관련 {len(unique)}건")
    return unique


def save_to_json(records: list, filename: str = None) -> str:
    if filename is None:
        filename = f"gov_ai_{_today()}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {filename}")
    return filename


if __name__ == "__main__":
    print("=== 정부 AI/AX 지원사업 수집 시작 ===\n")
    items = collect_gov_ai(days=7)
    if items:
        save_to_json(items)
        print("\n[샘플]")
        for r in items[:5]:
            print(f"- [{r['출처']}] {r['공고명']} ({r['소관부처']}) / {r['신청기간']}")
    else:
        print("수집된 공고가 없습니다.")
