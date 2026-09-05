"""정부 부처 AI/AX 지원사업·공모 수집 모듈

전 부처의 기업지원사업을 통합 제공하는 '기업마당(bizinfo.go.kr)' API를 주 소스로,
'K-Startup(창업지원)' data.go.kr API를 보조 소스로 사용해 AI/AX 관련 공고를 모은다.

- 기업마당: 인증키 필요 (BIZINFO_API_KEY). bizinfo.go.kr 오픈API 신청으로 발급.
            미설정 시 공개 데모키로 동작하지만 한도·중단 위험이 있으므로 정식 키 권장.
- K-Startup: data.go.kr 서비스키 필요 (GOV_DATA_API_KEY). 나라장터 키는 서비스별로
             권한이 달라 재사용 불가(403). 미설정 시 이 소스는 건너뛴다.

수집 실패는 삼키지 않는다. 실패 사유는 LAST_ERRORS 에 남고, 호출자가 이를 근거로
"신규 공고가 없다"와 "소스가 죽었다"를 구분해야 한다.
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# K-Startup 등 data.go.kr 계열 보조 소스용 (선택).
# 주의: data.go.kr 서비스키는 신청한 서비스에만 유효하다. NARA_API_KEY(나라장터)를
# 재사용하면 403이 돌아온다 - 재사용하지 않는다.
GOV_DATA_API_KEY = os.getenv("GOV_DATA_API_KEY")

# 기업마당 지원사업 목록 API (인증키 필요)
BIZINFO_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
BIZINFO_HOST = "https://www.bizinfo.go.kr"

# 공개 데모키. 우리 키가 아니므로 예고 없이 막힐 수 있다. 정식 키 발급 전 임시 다리.
BIZINFO_DEMO_KEY = "QP6yn2"
BIZINFO_API_KEY = os.getenv("BIZINFO_API_KEY") or BIZINFO_DEMO_KEY

# 마감 임박 기준(일). 이 안에 드는 공고는 등록일이 오래됐어도 절대 버리지 않는다.
URGENT_DAYS = 7

# 수집 중 발생한 실패 사유. collect_gov_ai() 시작 시 비워지고, 호출자가 읽는다.
LAST_ERRORS = []

# K-Startup 사업공고 (data.go.kr)
KSTARTUP_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"

# ─────────────────────────────────────────────
# 수집 키워드 — (주)블루바이오 사업자등록증 종목 기준
# 여기서 걸리지 않으면 AI 판단 단계로 넘어가지도 못한다. 넓게 잡고 뒤에서 거른다.
# ─────────────────────────────────────────────

# 정보통신업 — 소프트웨어·시스템통합·데이터
KW_AI = [
    "인공지능", "AI", "에이아이", "AX", "인공지능전환", "AI전환", "AI융합",
    "생성형", "생성형AI", "초거대", "초거대AI", "LLM", "거대언어모델",
    "머신러닝", "딥러닝", "데이터바우처", "AI바우처", "데이터", "빅데이터",
    "디지털전환", "DX", "지능형", "스마트공장", "클라우드", "SaaS",
    "디지털융합", "챗봇", "음성인식", "영상인식", "자율", "로봇",
    "소프트웨어", "시스템통합", "정보화", "플랫폼", "디지털",
]

# 도소매업 — 노인복지용구, 장애인보장구 (등록 종목)
# 자격 기반 키워드(장애인기업·장애인고용·중증장애인생산품 등)는 넣지 않는다.
# 그쪽은 사무용품 우선구매에 가깝고, 나라장터 물품입찰 트랙에서 다룬다.
KW_WELFARE_GOODS = [
    "노인복지용구", "장애인보장구", "복지용구", "고령친화", "보조공학",
]

# 서비스업 — 에어컨청소, 새집증후군제거 (등록 종목)
KW_ENV = [
    "실내공기질", "공기질", "새집증후군", "실내환경",
]

# 서비스업 — 행사대행·전시·문화공연·컨벤션·축제 기획업 (등록 종목)
# 정보통신업 — 문화예술콘텐츠개발 / 도소매업 — 미술품·공예품·굿즈
KW_CULTURE = [
    "행사대행", "행사기획", "축제", "컨벤션", "전시", "문화공연",
    "문화예술", "콘텐츠", "공예", "굿즈", "지역축제",
]

# 판로 — 위 종목의 매출로 이어지는 지원
KW_MARKET = ["판로", "판로개척"]

AI_KEYWORDS = KW_AI + KW_WELFARE_GOODS + KW_ENV + KW_CULTURE + KW_MARKET

# 짧아서 오탐이 나는 약어 — 단어 경계로만 인정한다
SHORT_KEYWORDS = {"AI", "AX", "DX", "LLM"}

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


# 신청기간 문자열에서 날짜를 뽑는다.
# "2026-09-03 ~ 2026-09-17", "2026.09.03~2026.09.17 16:00", "20260811 ~ 20260831" 모두 대응.
_DATE_RE = re.compile(r"(20\d{2})[.\-/]?(\d{2})[.\-/]?(\d{2})")


def parse_period(text: str):
    """신청기간 문자열 → (시작일, 마감일). YYYY-MM-DD. 못 읽으면 ("", "").

    날짜가 하나뿐이면 마감일로 본다 (마감을 놓치는 쪽보다 안전하다).
    '상시', '예산 소진시까지' 처럼 날짜가 없으면 빈 값을 남긴다 - 지어내지 않는다.
    """
    if not text:
        return "", ""
    found = []
    for y, m, d in _DATE_RE.findall(str(text)):
        if not (1 <= int(m) <= 12 and 1 <= int(d) <= 31):
            continue
        found.append(f"{y}-{m}-{d}")
    if not found:
        return "", ""
    if len(found) == 1:
        return "", found[0]
    return found[0], found[-1]


def dday(deadline: str):
    """마감일(YYYY-MM-DD) → 남은 일수. 오늘 마감이면 0, 어제 마감이면 -1.

    마감일을 모르면 None. None 은 '여유 있음'이 아니라 '모름'이다.
    """
    if not deadline:
        return None
    try:
        end = datetime.strptime(deadline, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (end - datetime.now().date()).days


# ─────────────────────────────────────────────
# 기업마당 (전 부처 통합)
# ─────────────────────────────────────────────
def fetch_bizinfo(max_results: int = 200) -> list:
    """기업마당 지원사업 목록 조회 (인증키 필요)

    실패하면 빈 리스트를 돌려주되, 사유를 LAST_ERRORS 에 남긴다.
    "오늘 공고가 없다"와 "소스가 죽었다"는 다른 상태다 - 섞이면 안 된다.
    """
    if BIZINFO_API_KEY == BIZINFO_DEMO_KEY:
        print("  [경고] 기업마당 공개 데모키로 동작 중입니다. "
              "BIZINFO_API_KEY 를 발급받아 설정하세요.")
    params = {
        "crtfcKey": BIZINFO_API_KEY,
        "dataType": "json",
        "searchCnt": max_results,
    }
    try:
        resp = requests.get(BIZINFO_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        msg = f"기업마당(주 소스) 조회 실패: {e}"
        print(f"  {msg}")
        LAST_ERRORS.append(msg)
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
    period = _first(item, "reqstBeginEndDe", "aplyYmd", "reqstDe")
    _, deadline = parse_period(period)
    return {
        "공고ID": _first(item, "pblancId", "id"),
        "공고명": _first(item, "pblancNm", "polcyBizNm", "title"),
        "소관부처": _first(item, "jrsdInsttNm", "ministry", default="기업마당"),
        "수행기관": _first(item, "excInsttNm", "instt"),
        "지원분야": _first(item, "pldirSportRealmLclasCodeNm", "sportRealmLclasCodeNm"),
        "신청기간": period,
        "마감일": deadline,
        "D-DAY": dday(deadline),
        "등록일": _parse_date_token(_first(item, "creatPnttm", "regDt", "creatDt")),
        "해시태그": _first(item, "hashtags", "hashTag"),
        "대상": _first(item, "trgetNm", "trgetNmDetail"),
        "출처": "기업마당",
        "공고URL": url or BIZINFO_HOST,
    }


# ─────────────────────────────────────────────
# K-Startup (창업진흥원, 선택)
# ─────────────────────────────────────────────
def fetch_kstartup(max_results: int = 100) -> list:
    """K-Startup 사업공고 조회 (data.go.kr 서비스키 필요)"""
    if not GOV_DATA_API_KEY:
        print("  [K-Startup] GOV_DATA_API_KEY 미설정 - 보조 소스 건너뜀")
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
        msg = f"K-Startup(보조 소스) 조회 실패: {e}"
        print(f"  {msg}")
        LAST_ERRORS.append(msg)
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
    period = f"{_first(item, 'pbanc_rcpt_bgng_dt')} ~ {_first(item, 'pbanc_rcpt_end_dt')}".strip(" ~")
    _, deadline = parse_period(period)
    return {
        "공고ID": str(pid),
        "공고명": _first(item, "biz_pbanc_nm", "intg_pbanc_biz_nm", "title"),
        "소관부처": _first(item, "pbanc_ntrp_nm", "supt_biz_titl_nm", default="중소벤처기업부"),
        "수행기관": _first(item, "pbanc_ntrp_nm", "excInsttNm"),
        "지원분야": _first(item, "supt_biz_clsfc", "biz_category_cd", default="창업지원"),
        "신청기간": period,
        "마감일": deadline,
        "D-DAY": dday(deadline),
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
        if k in SHORT_KEYWORDS:
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
    LAST_ERRORS.clear()
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

    # 이미 마감된 공고는 버린다. 마감일을 모르는 건(None) 남긴다 - 모르는 것은 버릴 근거가 없다.
    before_closed = len(ai_records)
    ai_records = [r for r in ai_records if r.get("D-DAY") is None or r["D-DAY"] >= 0]
    closed = before_closed - len(ai_records)

    # 최근성 필터.
    # 등록일만 보면 "열흘 전에 뜬 내일 마감 공고"를 버린다 - 사활이 걸린 파이프라인에서
    # 그건 정확히 놓치면 안 되는 공고다. 그래서 '최근 등록' 또는 '마감 임박' 중 하나면 남긴다.
    if days and days > 0:
        cutoff = _date_before(days)
        kept = []
        for r in ai_records:
            reg = r.get("등록일", "")
            is_new = (not reg) or reg >= cutoff
            d = r.get("D-DAY")
            is_urgent = d is not None and d <= URGENT_DAYS
            if is_new or is_urgent:
                r["신규"] = bool(is_new)
                kept.append(r)
        ai_records = kept

    # 중복 제거 (공고ID → 공고명 순)
    seen = set()
    unique = []
    for r in ai_records:
        key = r.get("공고ID") or r.get("공고명")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    # 마감이 급한 순. 마감일을 모르는 건 뒤로.
    unique.sort(key=lambda r: (r.get("D-DAY") is None, r.get("D-DAY") or 0))

    print(f"\n총 {len(records)}건 수집 → AI/AX 관련 {len(unique)}건"
          f" (마감 경과 {closed}건 제외)")
    urgent = [r for r in unique if r.get("D-DAY") is not None and r["D-DAY"] <= URGENT_DAYS]
    if urgent:
        print(f"  ⚠ 마감 임박(D-{URGENT_DAYS} 이내) {len(urgent)}건")
    if LAST_ERRORS:
        print("  ※ 수집 실패한 소스가 있습니다:")
        for m in LAST_ERRORS:
            print(f"    - {m}")
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
