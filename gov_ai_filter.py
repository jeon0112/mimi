"""정부 AI/AX 지원사업 적격 판단 모듈 (Claude Sonnet 배치 + Opus 심층)"""

import os
import json
import anthropic
from dotenv import load_dotenv
from gov_ai_collector import collect_gov_ai, save_to_json

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 회사 정보 (적격 판단 기준)
# ─────────────────────────────────────────────
# 신청 법인 (사업자등록증 2026-09-01 발급본 기준)
# ─────────────────────────────────────────────
# 소재지. 지역제한 공고를 걸러내는 데 쓴다. 비우면 지역 판단을 하지 않는다.
HOME_REGION = "전남광주통합특별시 서구"

# 공고문은 통합 이전 명칭을 그대로 쓰는 경우가 많다. 같은 곳으로 봐야 하는 표기들.
HOME_REGION_ALIASES = ["전남광주통합특별시", "광주광역시", "광주", "전라남도", "전남", "호남"]

COMPANY_PROFILE = """
- 법인명: (주)블루바이오 / 대표자: 노종희
- 설립: 2022-01-11 (업력 4년, 창업 7년 이내 요건 충족)
- 규모: 중소기업

- 등록 종목 (사업자등록증 기준 - 이 범위 안의 사업만 수행 가능)
  [정보통신업]
  · 패키지 및 응용 소프트웨어 개발 및 공급업
  · 컴퓨터 시스템 통합 자문 및 구축 서비스업
  · 데이터 수집·가공 및 데이터베이스 구축업
  · 데이터베이스 및 온라인 정보제공업
  · 문화예술콘텐츠개발
  [도소매업]
  · 노인복지용구, 장애인보장구
  · 문화예술콘텐츠(미술품, 공예품, 굿즈)
  [서비스업]
  · 에어컨청소, 새집증후군제거
  · 행사대행, 전시, 문화공연, 컨벤션 및 축제 기획업

- 주력 방향: AI 도입 및 AX(AI 전환)·디지털 전환(DX)
  · AI 바우처 / 데이터 바우처 등 도입 지원
  · 생성형 AI·챗봇·업무 자동화 도입, AI 기반 콘텐츠 제작
  · 클라우드·SaaS 전환, 데이터 구축·가공
  · AI 인력양성·컨설팅·실증(PoC)

- 목표: 위 종목 범위 안에서 정부 부처·지자체의 지원사업·공모에 참여해
        지원금·바우처·컨설팅·판로를 확보한다.
"""

def _profile() -> str:
    """소재지가 설정돼 있으면 프로필에 덧붙인다."""
    if not HOME_REGION:
        return COMPANY_PROFILE
    return COMPANY_PROFILE + f"- 소재지: {HOME_REGION}\n"


def _region_rule() -> str:
    """소재지를 모르면 지역 규칙을 아예 넣지 않는다."""
    if not HOME_REGION:
        return ""
    alias = ", ".join(HOME_REGION_ALIASES)
    return (
        f'- 지역제한: 공고가 특정 지역 기업만 대상으로 하는데 그 지역이 "{HOME_REGION}"이 '
        f'아니면 내용이 아무리 맞아도 "제외". 공고명 앞의 [부산]·[충북] 같은 표기, '
        f'해시태그의 지역명, 수행기관의 지역 테크노파크·진흥원 이름이 단서다.\n'
        f'  다음 표기는 모두 우리 지역으로 본다: {alias}\n'
        f'  전국 대상이거나 지역 언급이 없으면 지역 때문에 감점하지 말 것.\n'
    )


# 사전 제외 키워드 (명백히 무관한 공고)
EXCLUDE_KEYWORDS = ["채용공고", "입찰공고", "낙찰", "수의계약 체결", "결과발표", "선정결과", "종료"]


def quick_filter(records: list) -> list:
    """1차 사전 필터 (명백한 무관 공고 제거)"""
    filtered = []
    for r in records:
        name = r.get("공고명", "")
        if any(kw in name for kw in EXCLUDE_KEYWORDS):
            continue
        filtered.append(r)
    return filtered


def ai_evaluate(records: list) -> list:
    """Claude Sonnet으로 지원사업 적격 판단 (20건씩 배치 처리)"""
    if not records:
        return []

    all_results = []
    batch_size = 20

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        print(f"  배치 {i//batch_size + 1}/{(len(records)-1)//batch_size + 1} 판단 중... ({len(batch)}건)")

        text = "\n".join([
            f"{j+1}. [{r.get('공고ID','')}] {r['공고명']} | 소관: {r.get('소관부처','')} | "
            f"수행: {r.get('수행기관','')} | 분야: {r.get('지원분야','')} | "
            f"신청기간: {r.get('신청기간','')} | 대상: {r.get('대상','')} | "
            f"태그: {r.get('해시태그','')[:120]}"
            for j, r in enumerate(batch)
        ])

        prompt = f"""당신은 정부 지원사업 컨설턴트입니다. 아래 회사 프로필을 보고 각 공고가
이 회사가 참여할 만한 'AI/AX(인공지능 전환) 관련 정부 지원사업/공모'인지 판단하세요.

## 회사 프로필
{_profile()}

## 평가할 공고 목록
{text}

## 지시사항
각 공고에 대해 다음 형식의 JSON 배열만 응답하세요 (다른 텍스트 없이):
[
  {{
    "공고ID": "...",
    "추천여부": "추천" 또는 "보류" 또는 "제외",
    "점수": 0~100,
    "지역제한": "전국" 또는 해당 지역명(예: "부산광역시"),
    "이유": "한 줄 이유"
  }}
]

판단 기준:
- "추천": 위 등록 종목 중 하나로 수행 가능한 지원사업. 구체적으로는
  · AI/AX/DX: 인공지능·생성형·데이터·디지털전환·AI바우처·데이터바우처·클라우드·SaaS
    도입/실증(PoC)/컨설팅/인력양성/솔루션 개발
  · 데이터: 데이터 수집·가공·구축·개방, 데이터베이스·온라인 정보제공
  · 문화예술·콘텐츠: 콘텐츠 개발, 미술품·공예품·굿즈 유통
  · 행사: 행사대행·전시·컨벤션·축제·문화공연 기획 용역 및 관련 지원사업
  · 복지용구: 노인복지용구·장애인보장구·고령친화·보조공학기기 유통, 우선구매·판로지원
  · 환경/공기질: 실내공기질 개선, 새집증후군, 환경 서비스 관련 지원
  · 자격 기반: 장애인기업·사회적기업·예비사회적기업·사회적경제 대상 지원사업
- "보류": 종목과 부분적으로 닿거나 대상·조건이 애매하지만 가능성 있는 공고
- "제외": 등록 종목 어느 것으로도 수행할 수 없는 공고(건설·공사·제조설비·농수산 생산 등),
  이미 마감·종료된 공고
- 장애인기업·사회적기업 우대·가점이 명시된 공고는 가점 부여
- 종목에 없는 사업이라도 "장애인기업 대상"처럼 자격만으로 신청 가능한 공고는 "보류" 이상
{_region_rule()}- "지역제한" 필드는 소재지 설정과 무관하게 항상 채운다. 지역 언급이 없으면 "전국".
- 확실하지 않으면 "보류" (제외보다 보류 우선)
"""
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            body = response.content[0].text
            start = body.find("[")
            end = body.rfind("]") + 1
            all_results.extend(json.loads(body[start:end]))
        except Exception as e:
            print(f"  배치 파싱 오류: {e}")
            continue

    return all_results


DETAIL_PROMPT = """당신은 정부 지원사업 전문 컨설턴트입니다.
아래 AI/AX 지원사업 공고를 분석하여 (주)미미가 신청 전 확인할 사항을 정리해 주세요.

## 회사 프로필
{company_profile}

## 분석할 공고
- 공고명: {name}
- 소관부처: {ministry}
- 수행기관: {instt}
- 지원분야: {field}
- 신청기간: {period}
- 출처: {source}
- AI 1차 점수: {score}점 / 이유: {reason}

## 지시사항
다음 JSON 형식으로만 분석하세요 (다른 텍스트 없이):
{{
  "공고ID": "...",
  "핵심요약": "이 사업이 무엇을 지원하는지 2문장",
  "지원내용": ["예상되는 지원금/바우처/컨설팅 등"],
  "신청자격": ["대상 요건 추정"],
  "적합성": "높음" 또는 "보통" 또는 "낮음",
  "체크리스트": [
    {{"항목": "...", "상태": "✅ 확인" 또는 "⚠️ 확인필요", "설명": "..."}}
  ],
  "준비서류": ["예상 제출서류"],
  "주의사항": ["마감·자격 등 놓치면 안 되는 사항"],
  "신청전략": "이 공고에 대한 신청 전략 2-3문장"
}}

체크리스트는 4~6개. 실제로 중요한 것만. 공고 원문 확인이 필요한 부분은 '확인필요'로 표시."""


def ai_detailed_check(recommended: list) -> dict:
    """추천 공고에 대한 심층 분석 (Claude Opus 사용)"""
    if not recommended:
        return {}

    results = {}
    for r in recommended:
        rid = r.get("공고ID", "") or r.get("공고명", "")
        eval_info = r.get("평가", {})
        print(f"\n  심층 분석: {r.get('공고명', '')[:40]}")

        prompt = DETAIL_PROMPT.format(
            company_profile=COMPANY_PROFILE,
            name=r.get("공고명", ""),
            ministry=r.get("소관부처", ""),
            instt=r.get("수행기관", ""),
            field=r.get("지원분야", ""),
            period=r.get("신청기간", ""),
            source=r.get("출처", ""),
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
            body = ""
            for block in response.content:
                if block.type == "text":
                    body = block.text
                    break
            start = body.find("{")
            end = body.rfind("}") + 1
            data = json.loads(body[start:end])
            results[rid] = data
            print(f"    적합성: {data.get('적합성', '?')} | 체크: {len(data.get('체크리스트', []))}건")
        except Exception as e:
            print(f"    심층 분석 오류: {e}")

    return results


def run_filter_pipeline(days: int = 7) -> None:
    """단독 실행용 파이프라인"""
    print("=" * 50)
    print("  정부 AI/AX 지원사업 수집 및 적격 판단")
    print("=" * 50)

    records = collect_gov_ai(days=days)
    if not records:
        print("수집된 공고가 없습니다.")
        return

    filtered = quick_filter(records)
    print(f"\n사전 필터 후: {len(filtered)}건")

    evaluations = ai_evaluate(filtered)

    recommended = []
    for r in filtered:
        e = next((x for x in evaluations if x.get("공고ID") == r.get("공고ID")), None)
        if e:
            status = e.get("추천여부", "")
            icon = "✅" if status == "추천" else ("⚠️" if status == "보류" else "❌")
            print(f"\n{icon} [{status}] {r['공고명']}")
            print(f"   소관: {r.get('소관부처','')} | 점수: {e.get('점수',0)} | {e.get('이유','')}")
            print(f"   URL: {r['공고URL']}")
            if status == "추천":
                recommended.append({**r, "평가": e})

    if recommended:
        save_to_json(recommended, f"gov_ai_recommended_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.json")
        print(f"\n✅ 추천 {len(recommended)}건 저장 완료")
    else:
        print("\n추천 공고가 없습니다.")


if __name__ == "__main__":
    run_filter_pipeline(days=7)
