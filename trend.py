"""
trend.py — 트렌드 수집 + 주제 선정
API 키가 없으면 데모 모드로 동작한다.
"""

import os
import json
import logging
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return None

load_dotenv()
logger = logging.getLogger(__name__)


def fetch_google_trends():
    """Google Trends 실시간 급상승 키워드를 가져온다."""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="ko", tz=540)
        trending = pytrends.trending_searches(pn="south_korea")
        keywords = trending[0].tolist()[:10]
        return [{"source": "google", "keyword": kw, "score": 100 - i * 10}
                for i, kw in enumerate(keywords)]
    except Exception as e:
        logger.warning(f"Google Trends 사용 불가: {e}")
        return []


def fetch_naver_trends():
    """네이버 DataLab 검색어 트렌드를 가져온다."""
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.info("네이버 API 키 없음 → 스킵")
        return []

    try:
        import httpx
        from datetime import timedelta
        today = datetime.now()
        start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        body = {
            "startDate": start, "endDate": end, "timeUnit": "date",
            "keywordGroups": [
                {"groupName": "건강", "keywords": ["홈트", "다이어트", "루틴"]},
                {"groupName": "재테크", "keywords": ["주식", "부동산", "투자"]},
                {"groupName": "IT", "keywords": ["AI", "챗GPT", "코딩"]},
            ],
        }
        resp = httpx.post(
            "https://openapi.naver.com/v1/datalab/search",
            headers={"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret,
                     "Content-Type": "application/json"},
            json=body, timeout=10,
        )
        resp.raise_for_status()
        results = []
        for group in resp.json().get("results", []):
            avg = sum(d["ratio"] for d in group["data"]) / len(group["data"])
            results.append({"source": "naver", "keyword": group["title"], "score": round(avg, 2)})
        return sorted(results, key=lambda x: x["score"], reverse=True)
    except Exception as e:
        logger.warning(f"네이버 API 오류: {e}")
        return []


def fetch_rss_news():
    """RSS 뉴스피드에서 최신 키워드를 추출한다."""
    try:
        import feedparser
        feed = feedparser.parse("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko")
        return [{"source": "rss", "keyword": entry.title, "score": 50}
                for entry in feed.entries[:5]]
    except Exception as e:
        logger.warning(f"RSS 사용 불가: {e}")
        return []


def select_topic_with_claude(trends: list) -> dict:
    """Claude Haiku로 주제를 선정한다. API 없으면 데모."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY 없음 → 데모 주제 반환")
        return _demo_topic()

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        trend_text = "\n".join(f"- [{t['source']}] {t['keyword']} (점수: {t['score']})" for t in trends[:20])

        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=500,
            messages=[{"role": "user", "content": f"""트렌드 키워드:\n{trend_text}\n
인스타그램 카드뉴스 주제 Top 3를 JSON으로 반환하라.
[{{"topic": "...", "urgency": "high/medium/low", "reason": "..."}}]"""}],
        )
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        topics = json.loads(text)
        high = [t for t in topics if t.get("urgency") == "high"]
        return high[0] if high else topics[0]
    except Exception as e:
        logger.error(f"Claude 주제 선정 오류: {e}")
        return _demo_topic()


def _demo_topic():
    """데모 주제"""
    return {
        "topic": "2026 직장인 아침 루틴 5가지",
        "urgency": "high",
        "reason": "데모 모드 - 자기계발 + 건강 조합으로 높은 관심도",
    }


def analyze_trends() -> dict:
    """트렌드를 수집하고 최적 주제를 반환한다."""
    logger.info("트렌드 수집 시작...")
    all_trends = []
    all_trends.extend(fetch_naver_trends())
    all_trends.extend(fetch_google_trends())
    all_trends.extend(fetch_rss_news())

    if not all_trends:
        logger.warning("트렌드 수집 결과 없음 → 데모 주제 사용")
        return _demo_topic()

    logger.info(f"수집된 트렌드: {len(all_trends)}개")
    return select_topic_with_claude(all_trends)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(analyze_trends(), ensure_ascii=False, indent=2))
