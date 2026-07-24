# 정부 부처 AI/AX 지원사업·공모 사이트 모음

전 부처의 인공지능(AI)·AX(AI 전환)·디지털 전환(DX) 관련 지원사업과 공모를 한 곳에 정리한 목록입니다.
매일 자동 크롤링되는 소스는 ✅ 표시. 나머지는 수동 확인용 링크입니다.

> 자동 수집 파이프라인: `run_gov_ai.py` (기업마당 + K-Startup) → AI 필터 → 이메일 발송
> 매일 오전 8시(KST) GitHub Actions 자동 실행

---

## 1. 통합 포털 (전 부처 한눈에)

| 사이트 | 소관 | 내용 | 자동수집 |
|--------|------|------|:---:|
| [기업마당 bizinfo](https://www.bizinfo.go.kr) | 중소벤처기업부 | **전 부처 기업지원사업 통합 검색** (AI/데이터/디지털 필터 가능) | ✅ |
| [K-Startup](https://www.k-startup.go.kr) | 창업진흥원 | 창업지원 사업공고 통합 (AI 스타트업 포함) | ✅ |
| [정부24 – 보조금24](https://www.gov.kr) | 행정안전부 | 개인·기업 대상 보조금 통합 안내 | |
| [나라장터 g2b](https://www.g2b.go.kr) | 조달청 | 공공 입찰·용역 (AI 구축·용역 공고) | |
| [e나라도움](https://www.gosims.go.kr) | 기획재정부 | 국고보조금 공모 통합 관리 | |

## 2. 과학기술·ICT (AI 핵심 부처)

| 사이트 | 소관 | 내용 |
|--------|------|------|
| [과학기술정보통신부](https://www.msit.go.kr) | 과기정통부 | AI 국가전략·공모 원부처 |
| [정보통신산업진흥원 NIPA](https://www.nipa.kr) | 과기정통부 | **AI 바우처, AI 융합, 초거대AI 활용** 지원 |
| [한국지능정보사회진흥원 NIA](https://www.nia.or.kr) | 과기정통부 | **데이터 바우처, AI 학습용 데이터, AI 허브** |
| [정보통신기획평가원 IITP](https://www.iitp.kr) | 과기정통부 | AI·ICT R&D 과제 공모 |
| [AI 허브](https://www.aihub.or.kr) | NIA | AI 학습데이터 구축·개방 사업 |
| [소프트웨어산업협회 KOSA](https://www.sw.or.kr) | 과기정통부 | SW·AI 인력양성·바우처 |

## 3. 산업·중소기업

| 사이트 | 소관 | 내용 |
|--------|------|------|
| [중소벤처기업부](https://www.mss.go.kr) | 중기부 | 스마트공장·중소기업 디지털전환 |
| [스마트제조혁신추진단](https://www.smart-factory.kr) | 중기부 | **스마트공장·AI 제조** 지원 |
| [산업통상자원부](https://www.motie.go.kr) | 산업부 | 산업 AI·디지털 전환 R&D |
| [한국산업기술기획평가원 KEIT](https://www.keit.re.kr) | 산업부 | 산업기술 R&D (AI 융합) |
| [대·중소기업·농어업협력재단](https://www.win-win.or.kr) | 중기부 | 상생형 디지털 협력 |
| [중소기업기술정보진흥원 TIPA](https://www.tipa.or.kr) | 중기부 | 중소기업 기술개발(R&D) |

## 4. 창업·투자

| 사이트 | 소관 | 내용 |
|--------|------|------|
| [창업진흥원 KISED](https://www.kised.or.kr) | 중기부 | 예비·초기 창업패키지 (AI 분야) |
| [팁스 TIPS](https://www.jointips.or.kr) | 중기부 | 민간주도 기술창업 (딥테크·AI) |
| [K-ICT 창업멘토링](https://www.ictmentor.kr) | 과기정통부 | ICT·AI 창업 멘토링 |

## 5. 데이터·디지털·지역

| 사이트 | 소관 | 내용 |
|--------|------|------|
| [공공데이터포털 data.go.kr](https://www.data.go.kr) | 행안부 | 공공데이터 활용·API |
| [디지털플랫폼정부위원회](https://www.dpg.go.kr) | 대통령 직속 | 디지털플랫폼정부 공모 |
| [한국데이터산업진흥원 K-DATA](https://www.kdata.or.kr) | 과기정통부 | **데이터바우처, 마이데이터** |
| [정보통신진흥협회 KAIT](https://www.kait.or.kr) | 과기정통부 | 디지털 인력양성 |
| 각 지역 [테크노파크 TP](https://www.technopark.kr) | 지자체 | 지역 AI·디지털 전환 지원 |

## 6. 사회적경제·장애인기업 (우대·가점 대상)

| 사이트 | 소관 | 내용 |
|--------|------|------|
| [한국사회적기업진흥원](https://www.socialenterprise.or.kr) | 고용노동부 | 사회적기업 육성·디지털화 |
| [장애인기업종합지원센터](https://www.debc.or.kr) | 중기부 | **장애인기업 전용 지원·우선구매** |
| [소상공인시장진흥공단](https://www.semas.or.kr) | 중기부 | 소상공인 디지털 전환·스마트상점 |

---

## 자동 수집 키워드

`gov_ai_collector.py`의 `AI_KEYWORDS`에서 관리:

```
인공지능, AI, AX, 인공지능전환, AI전환, AI융합, 생성형, 초거대AI, LLM,
머신러닝, 딥러닝, 데이터바우처, AI바우처, 빅데이터, 디지털전환, DX,
지능형, 스마트공장, 클라우드, SaaS, 챗봇, 음성인식, 영상인식, 로봇
```

새 소스나 키워드를 추가하려면:
- **자동 수집 소스 추가**: `gov_ai_collector.py`의 수집 함수에 파서 추가
- **키워드 조정**: `gov_ai_collector.py` `AI_KEYWORDS`
- **AI 판단 기준 변경**: `gov_ai_filter.py` `COMPANY_PROFILE`
