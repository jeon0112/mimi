# n8n 멀티에이전트 오케스트레이터

`multi_agent_orchestrator.json` — 라우터 1 + 전문 에이전트 2 + 폴백 구조.

## 구조

```
웹훅(POST /orchestrate)
  → 라우터 에이전트 (claude-sonnet-4-6 + 구조화 출력파서: {route, task, reason})
  → Switch (route 값으로 분기)
       ├ agent1 → AI 에이전트1 (claude-opus-4-8) ┐
       ├ agent2 → AI 에이전트2 (claude-opus-4-8) ┼→ 웹훅에 응답하기
       └ 폴백   → 폴백 응답(Set)                  ┘
```

배타적 분기이므로 **Merge 노드 없이** 세 출력을 Respond에 직결한다(실행된 한쪽만 응답 발사).

## Import 후 반드시 손볼 곳

1. **자격증명**: 세 개의 Anthropic Chat Model 노드에서 `Anthropic account` 자격증명 재선택
   (JSON의 `REPLACE_WITH_CREDENTIAL_ID`는 import 시 빈 값 → 직접 골라야 ⚠️ 사라짐).
2. **라우터 시스템 프롬프트**: `라우터 에이전트` 노드의 `agent1 / agent2` 담당 영역 설명 작성.
3. **전문 에이전트 프롬프트**: `AI 에이전트1 / 2`의 시스템 메시지에 담당 영역·출력 형식 정의.
4. **확장**: 전문 에이전트를 늘리려면 출력파서 enum에 값 추가 → Switch 규칙 추가 →
   해당 에이전트 + 모델 노드 추가 후 Respond에 연결.

## 모델 기준 (mimi 프로젝트와 일치)

| 역할 | 모델 |
|------|------|
| 라우팅 판단 | `claude-sonnet-4-6` |
| 전문 분석 | `claude-opus-4-8` |
