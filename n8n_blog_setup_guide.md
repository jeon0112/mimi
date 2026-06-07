# n8n 블로그 AI 편집국 시스템 - 설치 가이드

## 워크플로우 개요

```
수요수집 → 점수계산(100점) → 65점이상 통과 → 리서치 → 아웃라인
→ [사람 승인 1] → 초안 작성 → 4중 QA → 수정 → 발행패키지
→ [사람 승인 2] → Google Docs 저장 → 로그 기록 → 완료 알림
```

전체 노드: 41개 | Claude API 호출: 5회 | 사람 승인: 2회

---

## Step 1: n8n에 임포트

1. n8n 열기 → 상단 메뉴 → **Import from file**
2. `n8n_blog_workflow.json` 선택
3. 워크플로우 열리면 저장

---

## Step 2: Credentials 설정 (5개)

### 1. Anthropic API (Claude)
- n8n → Settings → Credentials → New
- Type: **HTTP Header Auth**
- Name: `anthropicApiKey`
- Header Name: `x-api-key`
- Header Value: `sk-ant-api03-...` (Anthropic API 키)

### 2. Google Sheets
- Type: **Google Sheets OAuth2**
- Name: `Google Sheets 계정`
- Google Cloud Console에서 OAuth2 설정 필요

### 3. Gmail
- Type: **Gmail OAuth2**
- Name: `Gmail 계정`

### 4. Google Docs
- Type: **Google Docs OAuth2**
- Name: `Google Docs 계정`

### 5. 네이버 API (데이터랩)
- 네이버 개발자 센터에서 앱 생성
- 검색어 트렌드 API 권한 신청
- HTTP Request 노드에서 직접 헤더에 입력

---

## Step 3: Set Init Config 노드 수정

워크플로우 시작 후 **Set Init Config** 노드를 열고 아래 값 수정:

| 필드 | 입력값 |
|------|--------|
| `approver_email` | 승인받을 이메일 주소 |
| `sheets_id` | Google Sheets 스프레드시트 ID |
| `target_audience` | 타겟 독자 (예: "1인사업자/소상공인") |
| `blog_channel` | 발행 채널 (예: "네이버블로그") |
| `claude_model` | `claude-sonnet-4-6` (기본값) |

**Google Sheets ID 찾는 법:**
URL에서 `https://docs.google.com/spreadsheets/d/[여기가_ID]/edit`

---

## Step 4: Google Search Console 설정

**HTTP Request - Google Search Console** 노드에서:
- URL의 `여기에_사이트URL_입력` 부분을 실제 사이트 URL로 변경
- 예: `https://searchconsole.googleapis.com/webmasters/v3/sites/https%3A%2F%2Fyourblog.com/searchAnalytics/query`
- URL 인코딩 필요 (`:` → `%3A`, `/` → `%2F`)

---

## Step 5: Google Sheets 구조 설정

스프레드시트에 아래 3개 시트(탭) 생성:

### 시트 1: `주제큐`
| topic_id | keyword | angle | intent | audience | status | memo | priority | created_at |
|----------|---------|-------|--------|----------|--------|------|----------|------------|
| (자동생성) | n8n 블로그 자동화 | 실무형 가이드 | how-to | 1인사업자 | pending | | | 2026-06-07 |

**status 값:** `pending` → `published` / `outline_rejected` / `final_rejected`

### 시트 2: `발행로그`
| topic_id | keyword | title | meta_title | demand_score | quality_score | docs_url | tags | status | published_at | run_id | performance_check_date |
|----------|---------|-------|-----------|--------------|---------------|----------|------|--------|--------------|--------|----------------------|

### 시트 3: `저점수로그`
| topic_id | keyword | demand_score | action | score_detail | logged_at |

---

## Step 6: 점수 기준 이해

### 수요 점수 100점 기준 (보고서 반영)

| 항목 | 만점 | 계산 방법 |
|------|------|----------|
| 네이버 검색 추이 상승도 | 25점 | 최근 4주 vs 이전 4주 비율 |
| Search Console 노출량 | 20점 | 총 impressions 기준 |
| CTR 개선 가능성 | 15점 | 낮은 CTR + 1페이지 = 기회 |
| 질문형 쿼리 여부 | 15점 | 어떻게/방법/추천 등 포함 |
| 전환 가능성 | 15점 | 구매/상담 의도 키워드 |
| 기존 글 부족도 | 10점 | 중복 없으면 자동 만점 |

**판정:**
- 80점 이상 → 바로 작성
- 65~79점 → 아웃라인 후보
- 50~64점 → 보류 (저점수 로그 저장)
- 49점 이하 → 폐기

---

## Step 7: 실행 방법

1. 주제큐 시트에 키워드 입력 (status: pending)
2. n8n에서 워크플로우 열기
3. **Manual Trigger** 클릭 → **Test workflow**
4. 이메일로 아웃라인 승인 요청 수신
5. 이메일 내 [승인] 버튼 클릭
6. 초안 자동 작성 + QA 실행
7. 이메일로 최종 승인 요청 수신
8. [승인 & 발행] 클릭 → Google Docs에 저장

---

## Claude API 호출 구조 (5회)

| 단계 | 역할 | 모델 | max_tokens |
|------|------|------|------------|
| Claude 리서치 | 자료조사, 고충분석 | claude-sonnet-4-6 | 2,000 |
| Claude 아웃라인 | answer-first 목차 | claude-sonnet-4-6 | 2,000 |
| Claude 초안 작성 | 본문 1,500자 | claude-sonnet-4-6 | 4,000 |
| Claude 4중 QA | 사실/SEO/전환/중복 | claude-sonnet-4-6 | 2,000 |
| Claude 수정 (조건부) | QA 이슈 반영 재작성 | claude-sonnet-4-6 | 4,000 |
| Claude 발행 패키지 | 메타/SNS/태그 생성 | claude-sonnet-4-6 | 1,500 |

**1회 실행 예상 비용:** 약 $0.05~0.15 (Sonnet 기준)

---

## 4중 QA 기준

| 검수 | 확인 항목 |
|------|---------|
| 사실 검수 | 근거 없는 단정, 허위 수치, 과장 표현 |
| SEO 검수 | 키워드 밀도, FAQ 존재, 소제목 구조 |
| 전환 검수 | CTA 존재 여부, 다음 행동 명확성 |
| 중복 검수 | 반복 문장, 동일 표현 과다 사용 |

**건강/법률/금융 관련 글 → 자동 발행 차단, 수동 검토 큐 이동**

---

## 2단계 확장 (안정화 후 추가)

- [ ] Schedule Trigger로 자동 실행 (매일 오전 9시)
- [ ] WordPress/티스토리 API 발행 노드 추가
- [ ] 14일 후 Search Console 성과 자동 재측정
- [ ] Naver DataLab 수요 상승 키워드 자동 발굴 서브워크플로우
- [ ] SNS 멀티채널 발행 (인스타, 카카오채널)

---

## 주의사항

1. **n8n Cloud 사용 시**: Execute Command 노드 없음 - 이 워크플로우는 모두 HTTP Request로 Claude API 직접 호출 (Cloud 호환)
2. **Wait 노드**: 실행 중 워크플로우가 승인 대기 상태로 멈춤. n8n Cloud는 execution 유지 비용 발생 가능
3. **네이버 데이터랩**: 하루 1,000회 호출 한도. 키워드 그룹은 1회 요청에 최대 5개
4. **Google OAuth**: 주기적으로 토큰 갱신 필요
