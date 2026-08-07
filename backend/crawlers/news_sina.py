"""新浪财经 7x24 快讯 —— 通用市场快讯（全量返回，不过滤个股）"""
import json
from datetime import datetime

from crawlers.news_base import fetch_json, strip_html, build_news

URL = "https://zhibo.sina.com.cn/api/zhibo/feed"
PARAMS = {"page": 1, "page_size": 100, "zhibo_id": 152, "tag_id": 0, "type": 0}


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    """抓取新浪 7x24 全部快讯（市场快讯，不限个股）"""
    try:
        data = fetch_json(URL, params=PARAMS)
    except Exception as e:
        print(f"[sina] 获取失败: {e}")
        return []
    items = []
    try:
        feed = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
    except Exception:
        feed = []
    for it in feed:
        rich = it.get("rich_text") or it.get("text", "")
        text = strip_html(rich)
        if not text:
            continue
        title = text[:60].replace("\n", " ")
        pub = it.get("create_time") or it.get("ctime", "")
        url = it.get("url", f"https://finance.sina.com.cn/7x24/")
        items.append(build_news(stock, "sina", title, text, url, str(pub)))
        if len(items) >= limit:
            break
    return items
