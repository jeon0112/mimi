# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**(주)미미** 나라장터 입찰 자동화 시스템 — 매일 오전 8시(KST) GitHub Actions로 실행되어 공고 수집 → AI 필터링 → 전략 분석 → 이메일 발송까지 자동화한다.

회사 특성: 장애인기업 + 예비사회적기업 → 수의계약 우선 대상 (2천만원 이하).

## 실행 방법

```bash
pip install anthropic requests python-dotenv openpyxl
python run_collection.py        # 전체 파이프라인 실행
python nara_filter.py           # 공고 수집 + AI 필터만 단독 실행
python bid_analyzer.py          # 입찰가 분석만 단독 실행 (JSON 파일 인수 가능)
python price_agent.py           # 엑셀 파일 도매가 조회만 단독 실행
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

GitHub Secrets에 동일한 이름으로 등록 필요 (`.github/workflows/daily_collection.yml` 참고).

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
