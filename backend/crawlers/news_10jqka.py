"""同花顺财经 —— 财经推送 API（通用市场快讯，全量返回）"""
from crawlers.news_base import fetch_json, build_news

URL = "https://news.10jqka.com.cn/tapp/news/push/stock/"
PARAMS = {"page": 1, "tag": "", "track": "web", "pagesize": 80}


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    """抓取同花顺财经推送（市场快讯，不限个股）"""
    try:
        data = fetch_json(URL, params=PARAMS)
    except Exception as e:
        print(f"[10jqka] 获取失败: {e}")
        return []
    items = []
    news_list = data.get("data", {}).get("list", []) if isinstance(data, dict) else []
    for it in news_list:
        title = it.get("title", "") or it.get("digest", "")
        if not title:
            continue
        summary = it.get("digest", "") or it.get("content", "")
        url = it.get("url", "") or it.get("link", "")
        pub = it.get("ctime", "") or it.get("time", "") or it.get("display_time", "")
        items.append(build_news(stock, "10jqka", title, summary, url, str(pub)))
        if len(items) >= limit:
            break
    return items
