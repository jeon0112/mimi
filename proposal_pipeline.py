"""추천 공고 → 품목 추출 → 도매가 검색 → 기술제안서 자동 생성 파이프라인"""

import os
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv
from price_agent import get_price, calculate_bid_price

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

COMPANY_INFO = """
회사명: (주)미미
대표자: (대표자명 입력)
사업자등록번호: (사업자번호 입력)
주소: (주소 입력)
연락처: (전화번호 입력)
이메일: (이메일 입력)

특이사항:
- 장애인기업 확인서 보유 (한국장애인기업종합지원센터 발급)
- 예비사회적기업 지정 (고용노동부)
- 수의계약 우선 대상 업체

취급 품목:
1. 사무소모품: A4용지, 복사용지, 토너, 잉크카트리지
2. 생활·위생용품: 화장지, 세정제, 방역소모품
3. 복지·기관납품형 물품: 생필품 세트, 판촉·행사 물품
4. 에어컨·냉난방기 세척: 병원, 학교, 공공기관 대상
5. 홍보용 인쇄물: 현수막, 브로슈어, 리플렛, 홍보물
"""


def extract_items_from_bid(bid_info: dict) -> list[dict]:
    """AI로 공고명에서 주요 품목 추출"""
    bid_name = bid_info.get("공고명", "")
    prompt = f"""다음 나라장터 공고명에서 납품해야 할 품목들을 추출하세요.

공고명: {bid_name}

JSON 배열로 반환하세요. 각 항목은 {{"품목명": "...", "검색키워드": "..."}} 형태.
검색키워드는 네이버쇼핑에서 검색하기 좋은 짧은 키워드로.
최대 5개 품목만 추출.
반드시 JSON만 반환, 설명 없이."""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # JSON 추출
    if "```" in text:
        text = text.split("```")[1].replace("json", "").strip()
    try:
        return json.loads(text)
    except Exception:
        return [{"품목명": bid_name[:20], "검색키워드": bid_name[:10]}]


def search_supply_prices(items: list[dict]) -> list[dict]:
    """품목별 도매가 검색"""
    results = []
    for item in items:
        keyword = item.get("검색키워드", item.get("품목명", ""))
        print(f"  가격 검색: {keyword}")
        price_info = get_price(keyword)
        min_price = price_info.get("min_price")
        bid_price = calculate_bid_price(min_price) if min_price else None
        results.append({
            "품목명": item.get("품목명", ""),
            "검색키워드": keyword,
            "도매참고가": min_price,
            "입찰단가": bid_price,
            "참고상품": price_info.get("title", ""),
        })
    return results


def generate_proposal_with_prices(bid_info: dict, price_data: list[dict]) -> str:
    """가격 정보를 포함한 기술제안서 생성"""
    bid_name = bid_info.get("공고명", "")
    agency = bid_info.get("발주기관", "")
    estimated_price = bid_info.get("추정가격", 0)
    contract_method = bid_info.get("계약방법", "")
    deadline = bid_info.get("입찰마감일시", "")
    eval_info = bid_info.get("평가", {})

    # 가격 정보 텍스트
    price_text = ""
    for p in price_data:
        if p["도매참고가"]:
            price_text += f"- {p['품목명']}: 도매참고가 {p['도매참고가']:,}원 → 입찰단가 {p['입찰단가']:,}원 (참고: {p['참고상품']})\n"
        else:
            price_text += f"- {p['품목명']}: 가격 별도 협의\n"

    prompt = f"""당신은 나라장터 입찰 기술제안서 작성 전문가입니다.
아래 공고 정보, 회사 정보, 도매가 조사 결과를 바탕으로 기술제안서 초안을 작성해주세요.

## 공고 정보
- 공고명: {bid_name}
- 발주기관: {agency}
- 추정가격: {estimated_price}원
- 계약방법: {contract_method}
- 입찰마감: {deadline}
- AI 적격점수: {eval_info.get('점수', 0)}점 - {eval_info.get('이유', '')}

## 회사 정보
{COMPANY_INFO}

## 도매가 조사 결과 (네이버쇼핑 기준)
{price_text if price_text else "품목 가격 별도 조사 필요"}

## 작성 지시사항
다음 구성으로 기술제안서를 작성하세요. 실제 제출 가능한 수준으로 작성해주세요.

1. **제안 개요** - 제안 목적, 우리 회사 강점
2. **회사 소개** - 장애인기업·예비사회적기업 자격 강조
3. **사업 이해 및 수행 계획** - 납품 품목, 일정, 방법
4. **가격 경쟁력** - 도매 직거래 원가 절감, 위 조사된 가격 근거로 구체적 금액 제시
5. **품질 관리 계획** - 정품 보증, A/S
6. **사회적 가치 실현** - 장애인 고용, 사회적 기업

격식체(~합니다, ~입니다)로 작성. 가격은 조사된 도매가를 근거로 구체적으로 제시하세요."""

    print(f"\n기술제안서 생성 중... ({bid_name[:30]})")
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def save_proposal(proposal_text: str, bid_info: dict, price_data: list[dict], output_dir: str) -> str:
    """제안서 저장"""
    os.makedirs(output_dir, exist_ok=True)
    bid_name = bid_info.get("공고명", "제안서")[:20]
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"제안서_{bid_name}_{date_str}.txt"
    filename = filename.replace("/", "_").replace("\\", "_").replace(":", "_")
    filepath = os.path.join(output_dir, filename)

    price_summary = "\n".join([
        f"  - {p['품목명']}: 도매 {p['도매참고가']:,}원 → 입찰 {p['입찰단가']:,}원"
        if p['도매참고가'] else f"  - {p['품목명']}: 수동 확인 필요"
        for p in price_data
    ])

    header = f"""================================================================
  기 술 제 안 서
================================================================
공고명: {bid_info.get('공고명', '')}
발주기관: {bid_info.get('발주기관', '')}
추정가격: {bid_info.get('추정가격', '')}원
계약방법: {bid_info.get('계약방법', '')}
입찰마감: {bid_info.get('입찰마감일시', '')}
AI점수: {bid_info.get('평가', {}).get('점수', 0)}점
생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}

[도매가 조사 요약]
{price_summary}
================================================================

"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header + proposal_text)

    return filepath


def run_pipeline(bid_info: dict, output_dir: str) -> str:
    """단일 공고에 대해 전체 파이프라인 실행"""
    bid_name = bid_info.get("공고명", "")
    print(f"\n{'='*55}")
    print(f"공고: {bid_name}")
    print(f"{'='*55}")

    # 1. 품목 추출
    print("1. 품목 추출 중...")
    items = extract_items_from_bid(bid_info)
    print(f"   추출된 품목: {[i['품목명'] for i in items]}")

    # 2. 도매가 검색
    print("2. 도매가 검색 중...")
    price_data = search_supply_prices(items)

    # 3. 제안서 생성
    print("3. 기술제안서 생성 중...")
    proposal_text = generate_proposal_with_prices(bid_info, price_data)

    # 4. 저장
    filepath = save_proposal(proposal_text, bid_info, price_data, output_dir)
    print(f"✅ 저장: {filepath}")

    return filepath


def run_from_json(json_file: str, output_dir: str = None) -> list[str]:
    """추천 공고 JSON에서 추천 공고만 제안서 생성"""
    if output_dir is None:
        output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "나라장터결과", "제안서")

    with open(json_file, "r", encoding="utf-8") as f:
        bids = json.load(f)

    # 추천 공고만 처리
    recommended = [b for b in bids if b.get("평가", {}).get("추천여부") == "추천"]
    print(f"총 {len(recommended)}건 추천 공고 제안서 생성 시작")

    saved = []
    for bid in recommended:
        try:
            path = run_pipeline(bid, output_dir)
            saved.append(path)
        except Exception as e:
            print(f"오류 ({bid.get('공고명', '')}): {e}")

    return saved


if __name__ == "__main__":
    import sys
    import glob

    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # 최신 JSON 파일 자동 탐색
        output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "나라장터결과")
        files = sorted(glob.glob(os.path.join(output_dir, "recommended_bids_*.json")), reverse=True)
        if not files:
            files = sorted(glob.glob("output/recommended_bids_*.json"), reverse=True)
        if not files:
            print("JSON 파일을 찾을 수 없습니다.")
            sys.exit(1)
        json_file = files[0]
        print(f"파일: {json_file}")

    run_from_json(json_file)
