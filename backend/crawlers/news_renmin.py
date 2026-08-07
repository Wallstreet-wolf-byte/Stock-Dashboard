"""人民财讯 —— 人民网财经 RSS（通用市场快讯，全量返回）"""
import feedparser

from crawlers.news_base import build_news

URL = "http://www.people.com.cn/rss/finance.xml"


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    """抓取人民网财经RSS（市场快讯，不限个股）"""
    try:
        feed = feedparser.parse(URL)
    except Exception as e:
        print(f"[renmin] 获取失败: {e}")
        return []
    items = []
    for entry in feed.entries:
        title = entry.get("title", "")
        if not title:
            continue
        summary = entry.get("summary", "") or entry.get("description", "")
        url = entry.get("link", "")
        pub = entry.get("published", "") or entry.get("updated", "")
        items.append(build_news(stock, "renmin", title, summary, url, str(pub)))
        if len(items) >= limit:
            break
    return items
