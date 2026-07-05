"""매일 아침 읽을거리 큐레이션: 4대 신문 오피니언 칼럼 + 구글 핫 뉴스 → 이메일 발송"""

import os
import re
import sys
import html
import smtplib
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from datetime import datetime

import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 신문사별 오피니언/사설·칼럼 RSS. 다른 신문으로 바꾸려면 이 dict만 수정하면 됨.
NEWSPAPER_FEEDS = {
    "조선일보": "http://www.chosun.com/site/data/rss/editorials.xml",
    "중앙일보": "http://rss.joinsmsn.com/sonagi/joins_sonagi_opinion_list.xml",
    "동아일보": "http://rss.donga.com/editorials.xml",
    "경향신문": "http://www.khan.co.kr/rss/rssdata/opinion.xml",
}

GOOGLE_NEWS_RSS = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

ITEMS_PER_FEED = 5


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw or "")
    return html.unescape(text).strip()


def fetch_feed(name: str, url: str, limit: int = ITEMS_PER_FEED) -> list:
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        root = ET.fromstring(res.content)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = _clean_text(item.findtext("title", ""))
            link = _clean_text(item.findtext("link", ""))
            summary = _clean_text(item.findtext("description", ""))[:120]
            if title and link:
                items.append({"title": title, "link": link, "summary": summary, "source": name})
        log(f"{name}: {len(items)}건 수집")
        return items
    except Exception as e:
        log(f"{name} 수집 실패: {e}")
        return []


def fetch_opinion_columns() -> dict:
    return {name: fetch_feed(name, url) for name, url in NEWSPAPER_FEEDS.items()}


def fetch_hot_news(limit: int = 10) -> list:
    return fetch_feed("구글 핫 뉴스", GOOGLE_NEWS_RSS, limit=limit)


def build_email_body(opinion_by_source: dict, hot_news: list) -> str:
    date_str = datetime.now().strftime("%Y년 %m월 %d일")
    lines = [f"안녕하세요, {date_str} 아침 읽을거리입니다.\n"]

    lines.append("📰 [오늘의 오피니언 칼럼]")
    for source, items in opinion_by_source.items():
        if not items:
            continue
        lines.append(f"\n■ {source}")
        for item in items:
            lines.append(f"• {item['title']}")
            if item["summary"]:
                lines.append(f"  {item['summary']}")
            lines.append(f"  {item['link']}")

    if hot_news:
        lines.append("\n\n🔥 [구글 핫 뉴스]")
        for item in hot_news:
            lines.append(f"• {item['title']}")
            lines.append(f"  {item['link']}")

    if not any(opinion_by_source.values()) and not hot_news:
        lines.append("\n오늘은 가져올 기사가 없습니다.")

    return "\n".join(lines)


def send_email(body: str) -> None:
    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_password = os.getenv("GMAIL_PASSWORD", "")
    to_email = os.getenv("NOTIFY_EMAIL", "")

    if not gmail_password:
        log("이메일 비밀번호 미설정, 발송 건너뜀")
        return

    date_str = datetime.now().strftime("%Y년 %m월 %d일")
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = f"[아침 읽을거리] {date_str}"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
        log(f"이메일 발송 완료 → {to_email}")
    except Exception as e:
        log(f"이메일 발송 실패: {e}")


def main():
    log("아침 읽을거리 수집 시작")
    opinion_by_source = fetch_opinion_columns()
    hot_news = fetch_hot_news()
    body = build_email_body(opinion_by_source, hot_news)
    send_email(body)
    log("완료")


if __name__ == "__main__":
    main()
