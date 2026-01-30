"""Daily crypto sentiment digest (V2).

This script is designed to run in GitHub Actions (scheduled) and post a daily digest to Telegram.

Requirements:
- Python 3.11+
- No third-party dependencies (stdlib only)

Env vars:
- PERPLEXITY_API_KEY (required)
- PERPLEXITY_MODEL (optional, default: sonar-pro)
- TELEGRAM_BOT_TOKEN (required)
- TELEGRAM_CHAT_ID (required)  # can be @channelusername or numeric chat id
- DIGEST_MAX_ITEMS (optional, default: 10, min 3, max 25)
- DIGEST_MIN_CONFIDENCE (optional, default: 0, min 0, max 100) - filter out items below this confidence
- DIGEST_SOURCES (optional, default: coindesk,cointelegraph) - comma-separated list

"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple


PPLX_ENDPOINT = "https://api.perplexity.ai/chat/completions"

AVAILABLE_SOURCES = {
    "coindesk": ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    "cointelegraph": ("Cointelegraph", "https://cointelegraph.com/rss"),
}


@dataclass
class Article:
    title: str
    link: str
    source: str


@dataclass
class SentimentResult:
    sentiment: str  # BULLISH | BEARISH | NEUTRAL
    confidence: int  # 0-100
    one_liner: str


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _fetch_url(url: str, timeout_sec: int = 12) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "sentiment-trading-bot-digest/2.0 (+github-actions)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return resp.read()


def _strip_html(text: str) -> str:
    # Very lightweight cleanup (RSS titles are usually clean already).
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_rss(xml_bytes: bytes, source: str, max_items: int) -> List[Article]:
    root = ET.fromstring(xml_bytes)

    # RSS 2.0 typically: rss/channel/item
    channel = root.find("channel")
    if channel is None:
        # Atom or other formats: try finding entries
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        articles: List[Article] = []
        for entry in entries[:max_items]:
            title_el = entry.find("{http://www.w3.org/2005/Atom}title")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            title = _strip_html(title_el.text if title_el is not None else "")
            link = link_el.get("href") if link_el is not None else ""
            if title and link:
                articles.append(Article(title=title, link=link, source=source))
        return articles

    items = channel.findall("item")
    articles = []
    for item in items[:max_items]:
        title_el = item.find("title")
        link_el = item.find("link")
        title = _strip_html(title_el.text if title_el is not None else "")
        link = (link_el.text or "").strip() if link_el is not None else ""
        if title and link:
            articles.append(Article(title=title, link=link, source=source))
    return articles


def _pplx_analyze_headline(api_key: str, model: str, article: Article) -> SentimentResult:
    system = (
        "You are a crypto market sentiment classifier. "
        "Return ONLY a valid JSON object with keys: sentiment, confidence, one_liner. "
        "sentiment must be one of: BULLISH, BEARISH, NEUTRAL. "
        "confidence must be an integer 0-100. "
        "one_liner must be <= 140 characters."
    )

    user = (
        "Classify the market sentiment impact of this crypto news headline.\n\n"
        f"Source: {article.source}\n"
        f"Title: {article.title}\n"
        f"Link: {article.link}\n\n"
        "Do not include markdown. Output JSON only."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }

    req = urllib.request.Request(
        PPLX_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")

    try:
        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected Perplexity response format: {e}; raw={raw[:500]}")

    content = content.strip()
    content = re.sub(r"^```(?:json)?", "", content).strip()
    content = re.sub(r"```$", "", content).strip()

    try:
        obj = json.loads(content)
    except Exception as e:
        raise RuntimeError(f"Perplexity did not return valid JSON: {e}; content={content[:500]}")

    sentiment = str(obj.get("sentiment", "NEUTRAL")).strip().upper()
    if sentiment not in {"BULLISH", "BEARISH", "NEUTRAL"}:
        sentiment = "NEUTRAL"

    try:
        confidence = int(obj.get("confidence", 50))
    except Exception:
        confidence = 50
    confidence = max(0, min(100, confidence))

    one_liner = str(obj.get("one_liner", "")).strip()
    one_liner = re.sub(r"\s+", " ", one_liner)
    if len(one_liner) > 140:
        one_liner = one_liner[:137] + "..."

    return SentimentResult(sentiment=sentiment, confidence=confidence, one_liner=one_liner)


def _sentiment_score(results: List[SentimentResult]) -> int:
    if not results:
        return 0
    bullish = sum(1 for r in results if r.sentiment == "BULLISH")
    bearish = sum(1 for r in results if r.sentiment == "BEARISH")
    score = int(round(((bullish - bearish) / len(results)) * 100))
    return max(-100, min(100, score))


def _signal_from_distribution(results: List[SentimentResult]) -> str:
    if not results:
        return "HOLD"
    bullish = sum(1 for r in results if r.sentiment == "BULLISH")
    bearish = sum(1 for r in results if r.sentiment == "BEARISH")
    total = len(results)
    if bullish / total >= 0.70:
        return "BUY"
    if bearish / total >= 0.70:
        return "SELL"
    return "HOLD"


def _escape_markdown_v1(text: str) -> str:
    """Escape special chars for Telegram MarkdownV1 (basic escaping)."""
    # MarkdownV1 special chars: _ * [ ] ( ) ~ ` > # + - = | { } . !
    # We only escape the most common ones that break links
    for char in ["_", "*", "[", "`"]:
        text = text.replace(char, f"\\{char}")
    return text


def _build_message(date_utc: datetime, articles: List[Tuple[Article, SentimentResult]]) -> str:
    grouped = {"BULLISH": [], "BEARISH": [], "NEUTRAL": []}
    for a, r in articles:
        grouped[r.sentiment].append((a, r))

    all_results = [r for _, r in articles]
    score = _sentiment_score(all_results)
    signal = _signal_from_distribution(all_results)

    def _fmt_items(items: List[Tuple[Article, SentimentResult]]) -> str:
        lines = []
        for a, r in items[:8]:
            title = a.title
            if len(title) > 70:
                title = title[:67] + "..."
            # Escape title for Markdown
            title_escaped = _escape_markdown_v1(title)
            # Create markdown link: [title](url)
            lines.append(f"- [{title_escaped}]({a.link}) ({r.confidence}%)")
        return "\n".join(lines) if lines else "- (none)"

    day = date_utc.strftime("%d %b %Y")
    header = f"📊 CRYPTO SENTIMENT - {day} (UTC)"

    msg = (
        f"{header}\n\n"
        f"🚀 BULLISH ({len(grouped['BULLISH'])})\n{_fmt_items(grouped['BULLISH'])}\n\n"
        f"📉 BEARISH ({len(grouped['BEARISH'])})\n{_fmt_items(grouped['BEARISH'])}\n\n"
        f"➡️ NEUTRAL ({len(grouped['NEUTRAL'])})\n{_fmt_items(grouped['NEUTRAL'])}\n\n"
        f"📈 Sentiment Score: {score:+d}%\n"
        f"🎯 Signal: {signal}\n"
    )

    # Telegram hard limit is 4096 chars for message text.
    if len(msg) > 3900:
        msg = msg[:3890] + "\n\n(truncated)"

    return msg


def _telegram_send_message(bot_token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": "true",  # Avoid cluttering with link previews
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        raise RuntimeError(f"Telegram HTTP error: {e.code}; body={raw[:500]}")

    # Basic sanity check
    try:
        obj = json.loads(raw)
        if not obj.get("ok"):
            raise RuntimeError(f"Telegram API error: {raw[:500]}")
    except json.JSONDecodeError:
        raise RuntimeError(f"Telegram non-JSON response: {raw[:500]}")


def main() -> int:
    api_key = _env_required("PERPLEXITY_API_KEY")
    model = os.getenv("PERPLEXITY_MODEL") or "sonar-pro"
    bot_token = _env_required("TELEGRAM_BOT_TOKEN")
    chat_id = _env_required("TELEGRAM_CHAT_ID")

    try:
        max_items = int(os.getenv("DIGEST_MAX_ITEMS") or "10")
    except Exception:
        max_items = 10
    max_items = max(3, min(25, max_items))

    try:
        min_confidence = int(os.getenv("DIGEST_MIN_CONFIDENCE") or "0")
    except Exception:
        min_confidence = 0
    min_confidence = max(0, min(100, min_confidence))

    # Parse sources (comma-separated)
    sources_str = os.getenv("DIGEST_SOURCES") or "coindesk,cointelegraph"
    source_keys = [s.strip().lower() for s in sources_str.split(",") if s.strip()]
    feeds = [(AVAILABLE_SOURCES[k][0], AVAILABLE_SOURCES[k][1]) for k in source_keys if k in AVAILABLE_SOURCES]

    if not feeds:
        print("ERROR: No valid sources configured. Check DIGEST_SOURCES env var.", file=sys.stderr)
        return 1

    print(f"Fetching from sources: {[f[0] for f in feeds]}")
    print(f"Max items: {max_items}, Min confidence: {min_confidence}%")

    articles: List[Article] = []
    for source, url in feeds:
        try:
            xml_bytes = _fetch_url(url)
            articles.extend(_parse_rss(xml_bytes, source=source, max_items=max_items))
        except Exception as e:
            print(f"WARN: failed to fetch/parse feed {source}: {e}", file=sys.stderr)

    # Dedupe by link
    seen = set()
    deduped: List[Article] = []
    for a in articles:
        if a.link in seen:
            continue
        seen.add(a.link)
        deduped.append(a)

    if not deduped:
        _telegram_send_message(
            bot_token=bot_token,
            chat_id=chat_id,
            text="📊 CRYPTO SENTIMENT - (UTC)\n\nNo articles fetched today (RSS fetch failed).",
            parse_mode="",
        )
        return 0

    # Limit total items analyzed to control API usage
    deduped = deduped[:max_items]

    analyzed: List[Tuple[Article, SentimentResult]] = []
    for idx, a in enumerate(deduped, start=1):
        try:
            r = _pplx_analyze_headline(api_key=api_key, model=model, article=a)
            # Filter by confidence
            if r.confidence >= min_confidence:
                analyzed.append((a, r))
                print(f"OK {idx}/{len(deduped)}: {r.sentiment} {r.confidence}% - {a.title}")
            else:
                print(f"SKIP {idx}/{len(deduped)}: {r.sentiment} {r.confidence}% (below threshold) - {a.title}")
        except Exception as e:
            print(f"WARN: analysis failed for {a.link}: {e}", file=sys.stderr)

        # Gentle pacing to reduce rate-limit risk
        time.sleep(1.2)

    if not analyzed:
        _telegram_send_message(
            bot_token=bot_token,
            chat_id=chat_id,
            text=f"📊 CRYPTO SENTIMENT - (UTC)\n\nNo articles met confidence threshold ({min_confidence}%).",
            parse_mode="",
        )
        return 0

    now_utc = datetime.now(timezone.utc)
    message = _build_message(date_utc=now_utc, articles=analyzed)

    _telegram_send_message(bot_token=bot_token, chat_id=chat_id, text=message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
