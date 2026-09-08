# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**(주)미미** 나라장터 입찰 자동화 시스템 — 매일 오전 8시(KST) GitHub Actions로 실행되어 공고 수집 → AI 필터링 → 전략 분석 → 이메일 발송까지 자동화한다.

회사 특성: 장애인기업 + 예비사회적기업 → 수의계약 우선 대상 (2천만원 이하).

## 호칭

| | |
|---|---|
| 사용자 | **시저님** (자광 전). 「시자님」이 아니다 |
| Claude Code | **안토니우스** — 이 저장소에서 설계·문서·검토를 맡는다 |
| VPS 에이전트 | **뭉클이** — Hermes 게이트웨이. VPS 에서 계속 산다. 실행을 맡는다 |

안토니우스는 세션이 끝나면 기억이 사라진다. 뭉클이는 남는다.
그래서 **남겨야 할 것은 대화가 아니라 파일에 적는다.**
`proposals/LEDGER.md` · `ROADMAP.md` · 각 지시서가 그 이유로 존재한다.

지시서에 「내가」라고 쓰지 않는다. **누가 말하는지 밝힌다** —
뭉클이 입장에서 시저님인지 안토니우스인지 구분되어야 한다.

## 실행 방법

```bash
pip install anthropic requests python-dotenv openpyxl
python run_collection.py        # 나라장터 입찰 전체 파이프라인 실행
python nara_filter.py           # 공고 수집 + AI 필터만 단독 실행
python bid_analyzer.py          # 입찰가 분석만 단독 실행 (JSON 파일 인수 가능)
python price_agent.py           # 엑셀 파일 도매가 조회만 단독 실행

python run_gov_ai.py            # 정부 AI/AX 지원사업 크롤러 전체 파이프라인 실행
python gov_ai_collector.py      # AI/AX 지원사업 수집만 단독 실행
python gov_ai_filter.py         # 수집 + AI 적격 판단만 단독 실행
```

로컬 실행 시 `.env` 파일에 환경변수 설정 필요 (아래 참고).

## 환경변수

| 변수 | 용도 | 필수 |
|------|------|------|
| `ANTHROPIC_API_KEY` | Claude AI 호출 | ✅ |
| `NARA_API_KEY` | 나라장터 OpenAPI | ✅ |
| `GMAIL_USER` | 발송 이메일 주소 | ✅ |
| `GMAIL_PASSWORD` | Gmail 앱 비밀번호 (16자리) | ✅ |
| `NOTIFY_EMAIL` | 수신 이메일 주소 | ✅ |
| `NAVER_CLIENT_ID` | 네이버 쇼핑 API (도매가 조회) | 선택 |
| `NAVER_CLIENT_SECRET` | 네이버 쇼핑 API | 선택 |
| `BIZINFO_API_KEY` | 기업마당 오픈API 인증키 (정부 AI/AX 크롤러 **주 소스**). 미설정 시 공개 데모키 | 사실상 필수 |
| `GOV_DATA_API_KEY` | 정부 AI/AX 크롤러 보조 소스(K-Startup). `NARA_API_KEY` 재사용 불가(403) | 선택 |

GitHub Secrets에 동일한 이름으로 등록 필요 (`.github/workflows/daily_collection.yml`, `.github/workflows/gov_ai_collection.yml` 참고).

## 아키텍처

### 전체 파이프라인 (`run_collection.py`)

```
collect_bids()          ← nara_collector.py  (나라장터 API, 키워드별 수집)
  → quick_filter()      ← nara_filter.py     (제외 키워드 사전 필터)
  → ai_evaluate_bids()  ← nara_filter.py     (Claude Sonnet, 20건 배치)
  → ai_detailed_check() ← nara_filter.py     (Claude Opus, 추천 공고만 세밀 점검)
  → analyze_bid()       ← bid_analyzer.py    (나라장터 낙찰 이력 → 안정형/중간형/공격형)
  → run_pipeline()      ← proposal_pipeline.py  (NAVER_CLIENT_ID 있을 때만)
  → run_winning_strategy() ← winning_strategy.py (필살기 4종)
  → send_email()                              (Gmail SMTP, 결과 + 첨부)
```

### 모듈별 역할

**`nara_filter.py`**
- `ai_evaluate_bids()`: Sonnet으로 20건 배치 처리. 추천/보류/제외 + 점수 + 한줄이유 반환.
- `ai_detailed_check()`: **추천 공고만** Opus로 개별 심층 분석. 자격요건·체크리스트·장단점·주의사항·입찰전략 반환. 결과는 `run_collection.py`에서 `detailed_checks` dict로 관리.
- `FILTER_KEYWORDS` / `COMPANY_PROFILE`: 수집 키워드 및 AI 판단 기준. 업종 추가 시 여기를 수정.

**`bid_analyzer.py`**
- 나라장터 `getSuccssfulBidListInfoThng` API로 유사 공고 낙찰 이력 조회.
- 낙찰률 통계 → 안정형(평균)/중간형/공격형(최저근처) 입찰가 3종 제시.

**`winning_strategy.py`**
- 필살기 1: 수의계약 가능 공고 우선 분류 (2천만원 이하)
- 필살기 2: `generate_contact_letter()` — Opus로 발주기관별 우선구매 요청 공문 생성
- 필살기 3: 발주기관 과거 낙찰률 패턴 분석
- 필살기 4: 마감 3일 이내 단독 입찰 기회 탐색

**`proposal_pipeline.py`** (NAVER API 필요)
- 공고명 → 품목 추출(Opus) → 네이버 쇼핑 도매가 + 상위 3개 업체 조회 → 기술제안서 생성

**`price_agent.py`**
- 네이버 쇼핑 API 래퍼. `get_price(keyword)` → `{min_price, title, suppliers[{mallName, price, title, link}]}` 반환.
- 엑셀 파일 직접 처리: `process_excel(input_file)` — 품목/규격/수량 읽어 입찰단가 자동 산출.

**`nara_collector.py`**
- `collect_bids(keywords, days)`: 키워드 목록으로 API 반복 호출, 중복 제거.
- 공고 URL 형식: `https://www.g2b.go.kr/ep/invitation/publish/bidInvitDtlPublish.do?bidno={bidNtceNo}&bidseq=00` (포트 없음)

### 출력
- GitHub Actions: `output/` 폴더 → 아티팩트로 30일 보관
- 로컬: `~/Desktop/나라장터결과/`
- 이메일: 추천/보류 목록 + 체크리스트 + 입찰가 추천 + 전략 요약, 엑셀 첨부

### 정부 AI/AX 지원사업 크롤러 (`run_gov_ai.py`)

나라장터 입찰과 **독립된 별도 파이프라인**. 전 부처의 AI/AX(AI 전환)·디지털 전환 지원사업·공모를 매일 수집해 이메일로 발송한다.

```
collect_gov_ai()      ← gov_ai_collector.py  (기업마당 + K-Startup, AI 키워드 필터)
  → quick_filter()    ← gov_ai_filter.py     (명백한 무관 공고 제거)
  → ai_evaluate()     ← gov_ai_filter.py     (Claude Sonnet, 20건 배치 → 추천/보류/제외)
  → ai_detailed_check() ← gov_ai_filter.py   (Claude Opus, 추천 공고만 심층 분석)
  → to_excel()        ← run_gov_ai.py        (엑셀 생성)
  → send_email()      ← run_gov_ai.py        (Gmail SMTP, 결과 + 엑셀 첨부)
```

**데이터 소스**
- **기업마당(bizinfo.go.kr)**: 전 부처 기업지원사업 통합. 주 소스.
  - 엔드포인트 `https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do`, 파라미터 `crtfcKey`(인증키) + `dataType=json`
  - **인증키 필요**. `BIZINFO_API_KEY` 미설정 시 공개 데모키로 동작하지만 예고 없이 막힐 수 있다.
- **K-Startup**: data.go.kr API. `GOV_DATA_API_KEY` 있을 때만 수집. 보조 소스.
  - data.go.kr 서비스키는 **신청한 서비스에만 유효**하다. `NARA_API_KEY` 재사용 시 403 — 재사용하지 않는다.
- 전체 사이트 목록: `GOV_AI_SOURCES.md` (부처별 AI/AX 지원 포털 한 곳 정리)

**신청 법인은 (주)블루바이오다** (나라장터 입찰은 (주)미미 — 두 파이프라인의 주체가 다르다)
- 소재지 `전남광주통합특별시 서구`. `gov_ai_filter.HOME_REGION` / `HOME_REGION_ALIASES`.
  공고문은 통합 이전 명칭(광주광역시/전남/호남)을 쓰는 곳이 많아 별칭을 함께 본다.
- 수집·판단 범위는 **사업자등록증 종목 안으로 한정한다.** 종목에 없는 사업은 수주할 수 없다.
  사무용품·소모품 조달, 중증장애인생산품 우선구매는 **나라장터 트랙**이지 여기가 아니다.
- 장애인기업·예비사회적기업 자격은 프로필에 넣지 않았다. 사업자등록증으로 증명되지 않고
  어느 법인의 자격인지 확인되지 않았다. 확인 전에는 채우지 않는다.

**주요 수정 포인트**
- 수집 키워드: `gov_ai_collector.py` — 종목별 6개 그룹(`KW_AI`, `KW_WELFARE_GOODS`,
  `KW_ENV`, `KW_CULTURE`, `KW_MARKET`)을 합쳐 `AI_KEYWORDS`가 된다.
- AI 판단 기준: `gov_ai_filter.py` `COMPANY_PROFILE`
- 자동 수집 소스 추가: `gov_ai_collector.py`에 `fetch_*` / `parse_*` 함수 추가 후 `collect_gov_ai()`에 연결

**마감일 처리 (중요)**
- `parse_period()` / `dday()`가 `신청기간` 문자열에서 마감일과 D-day를 뽑는다. 못 읽으면 빈 값 — 지어내지 않는다.
- 이미 마감된 공고는 제외. **마감일을 모르는 공고(`D-DAY is None`)는 남긴다** — 모르는 것은 버릴 근거가 아니다.
- 최근성 필터는 `등록일 최근 N일` **또는** `D-DAY ≤ URGENT_DAYS(7)`. 등록일만 보면
  "열흘 전에 뜬 내일 마감 공고"를 버리게 된다. 그건 절대 놓치면 안 되는 공고다.
- 결과는 D-day 오름차순 정렬, 마감일 미상은 뒤로.

**실패를 침묵시키지 않는다 (중요)**
- 수집 실패 사유는 `gov_ai_collector.LAST_ERRORS`에 남는다.
- `run_gov_ai.py`는 이를 읽어 메일 맨 위에 🚨로 표시하고 **`sys.exit(1)`로 워크플로를 빨간불로 끝낸다**.
- 이유: "0건"은 *신규 공고가 없다*와 *소스가 죽었다*를 덮는다. 실제로 2026-08~09 내내
  잘못된 엔드포인트(404)로 43회 전부 0건을 보내면서 워크플로는 success였다.

**끊긴 것과 죽은 것을 구분한다 (`request_json`)**
- 모든 외부 호출은 `request_json(url, params, label)`을 거친다. 타임아웃 `(연결 10초, 응답 30초)`.
- **재시도하는 것**: 연결 끊김·시간 초과·JSON 아님·`429/500/502/503/504`. 3회, 3초→6초 대기.
- **재시도하지 않는 것**: 그 밖의 4xx(`401/403/404` 등). 키가 틀렸거나 주소가 틀린 것은
  백 번 걸어도 답이 같고, 그동안 진짜 원인이 재시도 로그에 묻힌다. 즉시 올려보낸다.
- 재시도는 실패를 숨기지 않는다. 3회 전부 실패하면 `"3번 모두 실패 - ..."`가 사유에 남아
  오히려 *진짜 죽었다*는 더 강한 근거가 된다.
- 배경: 2026-09-06 08시 정기 실행이 기업마당 연결 타임아웃 1회로 통째로 실패했다.
  전날 낮 수동 실행은 성공했으므로 주소는 맞았다. 한 번 끊겼다고 하루치 공고를 잃지 않는다.

**실패 메시지에 인증키를 싣지 않는다 (`_mask_secrets`)**
- 예외 메시지에는 실패한 요청 URL이 통째로 들어가고, 그 쿼리에 인증키가 있다.
  이 문장은 매일 메일로 나가고 저장소가 **Public**이라 Actions 로그도 공개된다.
- `_brief()`가 `crtfcKey|serviceKey|apiKey|authKey|accessKey|api_key` 값을 `***`로 바꾼다.
- 새 소스를 추가하며 다른 이름의 키 파라미터를 쓰면 `_SECRET_RE`에 반드시 추가할 것.

**출력**: `output/gov_ai_*.json|xlsx` (GitHub) / `~/Desktop/정부지원사업결과/` (로컬)

## 사업계획서 (`proposals/`)

정부지원사업 사업계획서를 반복 가능한 공정으로 만든 체계. **작업 전 `proposals/README.md`를 먼저 읽는다.**

- `proposals/README.md` — 절대 규칙 6개와 작업 순서. 이 체계의 헌법.
- `proposals/LEDGER.md` — **근거 원장(단일 진실 원천).** 계획서의 모든 주장 문장은
  여기 한 행(`E-번호`)을 가리킨다. 가리킬 행이 없으면 그 문장은 쓰지 않고 지운다.
- `proposals/QUALITY_GATE.md` — 제출 전 13항목. 하나라도 걸리면 제출하지 않는다.
- `proposals/TEMPLATE_공고해부.md` — 새 공고가 오면 복사해서 시작.
- `proposals/<마감일>_<공고약칭>/` — 공고별 작업 폴더. 폴더명 앞의 마감일로 정렬하면 급한 순서다.

핵심 원칙은 크롤러와 같다. **없는 값은 지어내지 않는다.** 공고가 「미정」「미측정」을
허용한다고 쓴 칸은 그대로 비운다 — 빈칸은 감점이 아니지만 허위기재는 선정 취소다.

## GitHub Actions

- 스케줄: `cron: '0 23 * * *'` = 매일 KST 08:00
- **수동 실행 시 반드시 `main` 브랜치 선택** (dev 브랜치 선택 시 구버전 코드 실행됨)
- 개발 브랜치: `claude/stoic-franklin-wFzwb` → 완료 후 main에 merge

## Claude 모델 사용 기준

| 용도 | 모델 |
|------|------|
| 배치 공고 적격 판단 (20건) | `claude-sonnet-4-6` |
| 세밀 점검, 기술제안서, 공문 생성 | `claude-opus-4-8` + `thinking: {type: "adaptive"}` |
| 입찰가 분석 | 모델 없음 (통계 계산) |

## 주요 수정 포인트

- **수집 품목 추가**: `nara_collector.py` `collect_bids()` keywords 리스트
- **AI 판단 기준 변경**: `nara_filter.py` `COMPANY_PROFILE`, `FILTER_KEYWORDS`
- **수의계약 금액 기준**: `winning_strategy.py` `filter_suui_targets(max_amount=20_000_000)`
- **마진율**: `price_agent.py` `DEFAULT_MARGIN = 0.20`
