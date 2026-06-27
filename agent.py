#!/usr/bin/env python3
"""한국 주식 투자 분석 에이전트 (KRX)
GLM-5.2 (의도 파악) + Claude Opus (데이터 수집 & 심층 분석) 듀얼 모델
"""

import json
import os
import sys
from dotenv import load_dotenv
import anthropic
from zhipuai import ZhipuAI

from tools import (
    fetch_stock_info,
    fetch_price_history,
    fetch_financial_metrics,
    fetch_market_cap_ranking,
    search_ticker_by_name,
    fetch_sector_performance,
)

load_dotenv()

TOOL_DEFINITIONS = [
    {
        "name": "fetch_stock_info",
        "description": "주식 종목의 현재가, 시가, 고가, 저가, 거래량 등 기본 정보를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드 (예: 005930 삼성전자)"}
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "fetch_price_history",
        "description": "주가 히스토리와 기술적 지표(RSI, MACD, 이동평균)를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드"},
                "days": {"type": "integer", "description": "조회 기간 (일), 기본값 120", "default": 120},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "fetch_financial_metrics",
        "description": "PER, PBR, EPS, 배당수익률 등 재무 지표를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "종목 코드"}
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "fetch_market_cap_ranking",
        "description": "KOSPI 또는 KOSDAQ 시가총액 상위 종목을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "market": {"type": "string", "enum": ["KOSPI", "KOSDAQ"], "description": "시장 구분", "default": "KOSPI"},
                "top_n": {"type": "integer", "description": "상위 N개 종목", "default": 20},
            },
        },
    },
    {
        "name": "search_ticker_by_name",
        "description": "종목명으로 티커(종목 코드)를 검색합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "검색할 종목명 (부분 일치)"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "fetch_sector_performance",
        "description": "KOSPI 또는 KOSDAQ 지수의 현재 수준과 최근 수익률을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "market": {"type": "string", "enum": ["KOSPI", "KOSDAQ"], "description": "시장 구분", "default": "KOSPI"}
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "fetch_stock_info": fetch_stock_info,
    "fetch_price_history": fetch_price_history,
    "fetch_financial_metrics": fetch_financial_metrics,
    "fetch_market_cap_ranking": fetch_market_cap_ranking,
    "search_ticker_by_name": search_ticker_by_name,
    "fetch_sector_performance": fetch_sector_performance,
}

GLM_SYSTEM_PROMPT = """당신은 사용자의 한국 주식 투자 관련 질문을 분석하는 전처리 에이전트입니다.

사용자 질문을 읽고 다음을 JSON으로 반환하세요:
{
  "intent": "종목분석|시장현황|종목검색|포트폴리오|기타",
  "tickers": ["종목코드 또는 종목명 리스트, 없으면 빈 배열"],
  "analysis_types": ["technical|fundamental|market|ranking 중 필요한 것들"],
  "market": "KOSPI|KOSDAQ|전체|null",
  "summary": "질문 핵심을 한 문장으로 요약",
  "refined_query": "분석 에이전트에게 전달할 명확하고 구체적인 질문"
}

JSON만 반환하고 다른 텍스트는 포함하지 마세요."""

CLAUDE_SYSTEM_PROMPT = """당신은 한국 주식 시장(KRX) 전문 투자 분석 에이전트입니다.

pykrx를 통해 실시간 KRX 데이터를 조회하고, 다음을 수행합니다:
1. **기술적 분석**: RSI, MACD, 이동평균선을 활용한 매매 신호 분석
2. **기본적 분석**: PER, PBR, EPS, 배당수익률 등 밸류에이션 분석
3. **시장 분석**: 시가총액 순위, 지수 동향 파악
4. **종합 투자 의견**: 매수/중립/매도 의견과 근거 제시

분석 시 다음 기준을 참고하세요:
- RSI 30 이하: 과매도 구간 (매수 고려)
- RSI 70 이상: 과매수 구간 (매도 고려)
- MACD > 시그널: 상승 모멘텀
- PER이 업종 평균보다 낮으면 저평가 가능성

항상 한국어로 응답하고, 구체적인 수치와 근거를 바탕으로 분석하세요.
투자는 최종적으로 투자자 본인의 판단과 책임임을 안내하세요."""


def parse_intent(glm_client: ZhipuAI, user_input: str) -> dict:
    """GLM-5.2로 사용자 질문 의도 파악"""
    response = glm_client.chat.completions.create(
        model="glm-5.2",
        messages=[
            {"role": "system", "content": GLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    # 마크다운 코드블록 제거
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"refined_query": user_input, "summary": user_input}


def run_tool(name: str, inputs: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if not fn:
        return json.dumps({"error": f"알 수 없는 도구: {name}"}, ensure_ascii=False)
    result = fn(**inputs)
    return json.dumps(result, ensure_ascii=False, default=str)


def analyze(claude_client: anthropic.Anthropic, messages: list, query: str) -> str:
    """Claude Opus로 tool use 기반 심층 분석"""
    messages.append({"role": "user", "content": query})

    while True:
        response = claude_client.messages.create(
            model="claude-opus-4-8",
            max_tokens=8096,
            thinking={"type": "adaptive"},
            system=CLAUDE_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [도구 실행] {block.name}({block.input})")
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return ""


def chat(glm_client: ZhipuAI, claude_client: anthropic.Anthropic, messages: list, user_input: str) -> str:
    print("  [GLM-5.2] 질문 분석 중...")
    intent = parse_intent(glm_client, user_input)

    summary = intent.get("summary", "")
    refined_query = intent.get("refined_query", user_input)
    analysis_types = intent.get("analysis_types", [])

    if summary:
        print(f"  [GLM-5.2] 파악: {summary}")
    if analysis_types:
        print(f"  [GLM-5.2] 필요 분석: {', '.join(analysis_types)}")

    print("  [Claude Opus] 데이터 수집 및 분석 시작...")
    return analyze(claude_client, messages, refined_query)


def main():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    glm_key = os.getenv("GLM_API_KEY")

    if not anthropic_key:
        print("오류: ANTHROPIC_API_KEY 환경 변수를 설정하세요.")
        sys.exit(1)
    if not glm_key:
        print("오류: GLM_API_KEY 환경 변수를 설정하세요.")
        sys.exit(1)

    claude_client = anthropic.Anthropic(api_key=anthropic_key)
    glm_client = ZhipuAI(api_key=glm_key)
    messages = []

    print("=" * 60)
    print("  한국 주식 투자 분석 에이전트 (KRX)")
    print("  GLM-5.2 + Claude Opus 듀얼 모델")
    print("=" * 60)
    print("종목 분석, 추천, 시장 현황 등을 물어보세요.")
    print("종료하려면 'quit' 또는 'exit'을 입력하세요.\n")

    while True:
        try:
            user_input = input("질문: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "종료"):
            print("종료합니다.")
            break

        print()
        try:
            response = chat(glm_client, claude_client, messages, user_input)
            print(f"에이전트:\n{response}\n")
        except Exception as e:
            print(f"오류 발생: {e}\n")


if __name__ == "__main__":
    main()
