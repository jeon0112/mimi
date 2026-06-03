import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    USE_YFINANCE = True
except ImportError:
    USE_YFINANCE = False


KRX_TICKERS = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "LG에너지솔루션": "373220",
    "삼성바이오로직스": "207940",
    "현대차": "005380",
    "기아": "000270",
    "POSCO홀딩스": "005490",
    "셀트리온": "068270",
    "KB금융": "105560",
    "신한지주": "055550",
    "카카오": "035720",
    "NAVER": "035420",
    "LG화학": "051910",
    "삼성SDI": "006400",
    "현대모비스": "012330",
}


def _to_yf_ticker(ticker: str) -> str:
    return f"{ticker}.KS"


def fetch_stock_info(ticker: str) -> dict:
    """종목 기본 정보 조회"""
    if not USE_YFINANCE:
        return {"error": "yfinance가 설치되지 않았습니다. pip install yfinance 실행하세요."}
    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        info = t.info
        hist = t.history(period="5d")
        if hist.empty:
            return {"error": f"종목 {ticker} 데이터를 찾을 수 없습니다."}

        latest = hist.iloc[-1]
        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName", ticker),
            "current_price": round(float(latest["Close"]), 0),
            "open": round(float(latest["Open"]), 0),
            "high": round(float(latest["High"]), 0),
            "low": round(float(latest["Low"]), 0),
            "volume": int(latest["Volume"]),
            "market_cap": info.get("marketCap"),
            "date": hist.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_price_history(ticker: str, days: int = 120) -> dict:
    """주가 히스토리 조회 및 기술적 지표 계산"""
    if not USE_YFINANCE:
        return {"error": "yfinance가 설치되지 않았습니다."}
    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        hist = t.history(period=f"{days + 60}d")

        if hist.empty or len(hist) < 20:
            return {"error": "데이터가 부족합니다."}

        close = hist["Close"]

        # 이동평균
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        # RSI (14일)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()

        hist = hist.tail(days)
        close = close.tail(days)

        recent_prices = [
            {"date": idx.strftime("%Y-%m-%d"), "close": round(float(val), 0),
             "volume": int(hist.loc[idx, "Volume"])}
            for idx, val in close.items()
        ]

        return {
            "ticker": ticker,
            "period_days": days,
            "price_change_1m": round((close.iloc[-1] / close.iloc[-21] - 1) * 100, 2) if len(close) >= 21 else None,
            "price_change_3m": round((close.iloc[-1] / close.iloc[-63] - 1) * 100, 2) if len(close) >= 63 else None,
            "ma5": round(float(ma5.iloc[-1]), 0),
            "ma20": round(float(ma20.iloc[-1]), 0),
            "ma60": round(float(ma60.iloc[-1]), 0) if not np.isnan(ma60.iloc[-1]) else None,
            "rsi_14": round(float(rsi.iloc[-1]), 2),
            "macd": round(float(macd.iloc[-1]), 2),
            "macd_signal": round(float(signal.iloc[-1]), 2),
            "macd_histogram": round(float(macd.iloc[-1] - signal.iloc[-1]), 2),
            "52w_high": round(float(close.max()), 0),
            "52w_low": round(float(close.min()), 0),
            "recent_prices": recent_prices[-10:],
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_financial_metrics(ticker: str) -> dict:
    """재무 지표 조회 (PER, PBR 등)"""
    if not USE_YFINANCE:
        return {"error": "yfinance가 설치되지 않았습니다."}
    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        info = t.info
        return {
            "ticker": ticker,
            "per": info.get("trailingPE"),
            "forward_per": info.get("forwardPE"),
            "pbr": info.get("priceToBook"),
            "eps": info.get("trailingEps"),
            "roe": info.get("returnOnEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "dividend_yield": info.get("dividendYield"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_market_cap_ranking(market: str = "KOSPI", top_n: int = 20) -> dict:
    """시가총액 상위 종목 조회 (주요 종목 기준)"""
    tickers = list(KRX_TICKERS.items())[:top_n]
    results = []
    for name, ticker in tickers:
        info = fetch_stock_info(ticker)
        if "error" not in info:
            results.append({
                "ticker": ticker,
                "name": name,
                "current_price": info.get("current_price"),
                "market_cap": info.get("market_cap"),
                "volume": info.get("volume"),
            })
    return {"market": market, "stocks": results}


def search_ticker_by_name(name: str) -> dict:
    """종목명으로 티커 검색"""
    results = []
    for stock_name, ticker in KRX_TICKERS.items():
        if name in stock_name:
            results.append({"ticker": ticker, "name": stock_name, "market": "KOSPI"})
    if not results:
        return {"query": name, "results": [], "note": "내장 DB에 없는 종목입니다. 직접 종목코드를 입력하세요."}
    return {"query": name, "results": results}


def fetch_sector_performance(market: str = "KOSPI") -> dict:
    """지수 현황 조회"""
    if not USE_YFINANCE:
        return {"error": "yfinance가 설치되지 않았습니다."}
    try:
        index_ticker = "^KS11" if market == "KOSPI" else "^KQ11"
        t = yf.Ticker(index_ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            return {"error": "지수 데이터를 찾을 수 없습니다."}
        close = hist["Close"]
        return {
            "market": market,
            "index_current": round(float(close.iloc[-1]), 2),
            "change_1m": round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2),
            "date": hist.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception as e:
        return {"error": str(e)}
