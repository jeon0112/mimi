import pandas as pd
import numpy as np
from pykrx import stock
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


def get_today():
    return datetime.now().strftime("%Y%m%d")


def get_date_before(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")


def fetch_stock_info(ticker: str) -> dict:
    """종목 기본 정보 조회"""
    try:
        today = get_today()
        name = stock.get_market_ticker_name(ticker)

        df = stock.get_market_ohlcv_by_date(get_date_before(5), today, ticker)
        if df.empty:
            return {"error": f"종목 {ticker} 데이터를 찾을 수 없습니다."}

        latest = df.iloc[-1]
        return {
            "ticker": ticker,
            "name": name,
            "current_price": int(latest["종가"]),
            "open": int(latest["시가"]),
            "high": int(latest["고가"]),
            "low": int(latest["저가"]),
            "volume": int(latest["거래량"]),
            "date": df.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_price_history(ticker: str, days: int = 120) -> dict:
    """주가 히스토리 조회 및 기술적 지표 계산"""
    try:
        end = get_today()
        start = get_date_before(days + 60)

        df = stock.get_market_ohlcv_by_date(start, end, ticker)
        if df.empty or len(df) < 20:
            return {"error": "데이터가 부족합니다."}

        close = df["종가"]

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

        df = df.tail(days)
        close = close.tail(days)

        recent_prices = [
            {"date": idx.strftime("%Y-%m-%d"), "close": int(val), "volume": int(df.loc[idx, "거래량"])}
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
            "52w_high": int(close.max()),
            "52w_low": int(close.min()),
            "recent_prices": recent_prices[-10:],
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_financial_metrics(ticker: str) -> dict:
    """재무 지표 조회 (PER, PBR, ROE 등)"""
    try:
        today = get_today()
        start = get_date_before(30)

        df = stock.get_market_fundamental_by_date(start, today, ticker)
        if df.empty:
            return {"error": "재무 데이터를 찾을 수 없습니다."}

        latest = df.iloc[-1]
        return {
            "ticker": ticker,
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "per": round(float(latest.get("PER", 0)), 2),
            "pbr": round(float(latest.get("PBR", 0)), 2),
            "eps": round(float(latest.get("EPS", 0)), 0),
            "bps": round(float(latest.get("BPS", 0)), 0),
            "div_yield": round(float(latest.get("DIV", 0)), 2),
            "dps": round(float(latest.get("DPS", 0)), 0),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_market_cap_ranking(market: str = "KOSPI", top_n: int = 20) -> dict:
    """시가총액 상위 종목 조회"""
    try:
        today = get_today()
        df = stock.get_market_cap_by_ticker(today, market=market)
        if df.empty:
            yesterday = get_date_before(1)
            df = stock.get_market_cap_by_ticker(yesterday, market=market)

        df = df.sort_values("시가총액", ascending=False).head(top_n)

        result = []
        for ticker, row in df.iterrows():
            name = stock.get_market_ticker_name(ticker)
            result.append({
                "ticker": ticker,
                "name": name,
                "market_cap": int(row["시가총액"]),
                "current_price": int(row["종가"]),
                "volume": int(row["거래량"]),
            })

        return {"market": market, "top_n": top_n, "stocks": result}
    except Exception as e:
        return {"error": str(e)}


def search_ticker_by_name(name: str) -> dict:
    """종목명으로 티커 검색"""
    try:
        kospi = stock.get_market_ticker_list(market="KOSPI")
        kosdaq = stock.get_market_ticker_list(market="KOSDAQ")
        all_tickers = kospi + kosdaq

        results = []
        for ticker in all_tickers:
            ticker_name = stock.get_market_ticker_name(ticker)
            if name in ticker_name:
                market = "KOSPI" if ticker in kospi else "KOSDAQ"
                results.append({"ticker": ticker, "name": ticker_name, "market": market})
                if len(results) >= 10:
                    break

        return {"query": name, "results": results}
    except Exception as e:
        return {"error": str(e)}


def fetch_sector_performance(market: str = "KOSPI") -> dict:
    """업종별 수익률 조회"""
    try:
        today = get_today()
        start = get_date_before(30)

        df = stock.get_index_ohlcv_by_date(start, today, "1001" if market == "KOSPI" else "2001")
        if df.empty:
            return {"error": "지수 데이터를 찾을 수 없습니다."}

        close = df["종가"]
        return {
            "market": market,
            "index_current": round(float(close.iloc[-1]), 2),
            "change_1m": round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2),
            "date": df.index[-1].strftime("%Y-%m-%d"),
        }
    except Exception as e:
        return {"error": str(e)}
