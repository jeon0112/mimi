"""나라장터 입찰 기술제안서 자동 초안 생성 에이전트 (Claude Opus)"""

import os
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv

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


def generate_proposal(bid_info: dict) -> str:
    """공고 정보를 받아 기술제안서 초안 생성"""

    bid_name = bid_info.get("공고명", "")
    agency = bid_info.get("발주기관", "")
    estimated_price = bid_info.get("추정가격", 0)
    contract_method = bid_info.get("계약방법", "")
    deadline = bid_info.get("입찰마감일시", "")
    items = bid_info.get("품목리스트", "")
    bid_no = bid_info.get("공고번호", "")

    prompt = f"""당신은 나라장터 입찰 기술제안서 작성 전문가입니다.
아래 공고 정보와 회사 정보를 바탕으로 기술제안서 초안을 작성해주세요.

## 공고 정보
- 공고번호: {bid_no}
- 공고명: {bid_name}
- 발주기관: {agency}
- 추정가격: {estimated_price}원
- 계약방법: {contract_method}
- 입찰마감: {deadline}
- 주요 품목: {items if items else '공고명 기반으로 추정'}

## 회사 정보
{COMPANY_INFO}

## 작성 지시사항
다음 구성으로 기술제안서 초안을 작성하세요. 실제 제출 가능한 수준으로 구체적이고 전문적으로 작성해주세요.

1. **제안 개요**
   - 제안 목적 및 배경
   - 우리 회사의 강점 (장애인기업/사회적기업 우선공급 자격 강조)

2. **회사 소개**
   - 업체 개요 및 주요 실적
   - 장애인기업·예비사회적기업 자격 설명 (사회적 가치 실현)

3. **사업 이해 및 수행 계획**
   - 발주기관의 요구사항 이해
   - 납품 품목 상세 및 품질 기준
   - 납품 일정 및 방법

4. **품질 관리 계획**
   - 정품 보증 방안
   - 불량·하자 처리 절차
   - 납품 후 A/S 방안

5. **가격 경쟁력**
   - 합리적 가격 산정 근거
   - 도매 직거래로 인한 원가 절감

6. **사회적 가치 실현**
   - 장애인 고용 현황
   - 사회적 기업으로서의 역할

각 항목은 실제 제안서에 바로 사용할 수 있도록 완성된 문장으로 작성해주세요.
공문서 형식에 맞게 격식체(~합니다, ~입니다)를 사용해주세요.
"""

    print(f"\n기술제안서 생성 중... ({bid_name})")
    print("(Claude Opus 처리 중, 잠시 기다려주세요...)\n")

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    proposal_text = ""
    for block in response.content:
        if block.type == "text":
            proposal_text = block.text
            break

    return proposal_text


def save_proposal(proposal_text: str, bid_info: dict) -> str:
    """기술제안서를 텍스트 파일로 저장"""
    output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "나라장터결과")
    os.makedirs(output_dir, exist_ok=True)

    bid_name = bid_info.get("공고명", "제안서")[:20]
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"제안서_{bid_name}_{date_str}.txt"
    filename = filename.replace("/", "_").replace("\\", "_").replace(":", "_")
    filename = os.path.join(output_dir, filename)

    header = f"""================================================================
  기 술 제 안 서
================================================================
공고명: {bid_info.get('공고명', '')}
발주기관: {bid_info.get('발주기관', '')}
추정가격: {bid_info.get('추정가격', '')}원
계약방법: {bid_info.get('계약방법', '')}
입찰마감: {bid_info.get('입찰마감일시', '')}
생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}
================================================================

"""
    full_text = header + proposal_text

    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_text)

    return filename


def run_from_json(json_file: str) -> None:
    """추천 공고 JSON 파일에서 제안서 일괄 생성"""
    with open(json_file, "r", encoding="utf-8") as f:
        bids = json.load(f)

    print(f"총 {len(bids)}건 제안서 생성 시작\n")

    for i, bid in enumerate(bids, 1):
        print(f"[{i}/{len(bids)}] {bid.get('공고명', '')}")
        try:
            proposal = generate_proposal(bid)
            filename = save_proposal(proposal, bid)
            print(f"  ✅ 저장: {filename}\n")
        except Exception as e:
            print(f"  ❌ 오류: {e}\n")


def run_interactive() -> None:
    """대화형으로 공고 정보 입력 후 제안서 생성"""
    print("=" * 55)
    print("  기술제안서 자동 초안 생성 에이전트")
    print("=" * 55)
    print("\n공고 정보를 입력하세요 (빈값은 엔터):\n")

    bid_info = {
        "공고번호": input("공고번호: ").strip(),
        "공고명": input("공고명: ").strip(),
        "발주기관": input("발주기관: ").strip(),
        "추정가격": input("추정가격 (숫자만): ").strip(),
        "계약방법": input("계약방법 (수의계약/일반경쟁 등): ").strip(),
        "입찰마감일시": input("입찰마감일시: ").strip(),
        "품목리스트": input("주요 품목 (간략히): ").strip(),
    }

    proposal = generate_proposal(bid_info)
    filename = save_proposal(proposal, bid_info)

    print("\n" + "=" * 55)
    print(proposal[:500] + "\n...(이하 생략)...")
    print("=" * 55)
    print(f"\n✅ 저장 완료: {filename}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        run_from_json(sys.argv[1])
    else:
        run_interactive()
