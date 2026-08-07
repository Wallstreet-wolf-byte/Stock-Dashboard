"""东方财富快讯 —— 通用市场快讯（全量返回，不过滤个股）"""
import json
import re

from crawlers.news_base import fetch_text, build_news

URL = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_ajaxResult_100_1_.html"


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    """抓取东方财富快讯（市场快讯，不限个股）"""
    try:
        text = fetch_text(URL)
    except Exception as e:
        print(f"[eastmoney] 获取失败: {e}")
        return []
    # 解析 var ajaxResult = {...} 或 [...]
    m = re.search(r"var\s+ajaxResult\s*=\s*(\{.*\}|\[.*\])\s*;?\s*$", text.strip(), re.S)
    raw = None
    if m:
        try:
            raw = json.loads(m.group(1))
        except Exception:
            raw = None
    if raw is None:
        try:
            raw = json.loads(text)
        except Exception:
            return []
    # 统一为列表：dict 取 LivesList，list 直接用
    if isinstance(raw, dict):
        data = raw.get("LivesList", []) or raw.get("data", [])
    else:
        data = raw
    items = []
    for it in data:
        title = it.get("title", "")
        digest = it.get("digest", "") or it.get("summary", "")
        if not title:
            continue
        url = it.get("url_w", "") or it.get("url", "")
        pub = it.get("showtime", "") or it.get("time", "") or it.get("digest_time", "")
        items.append(build_news(stock, "eastmoney", title, digest, url, str(pub)))
        if len(items) >= limit:
            break
    return items
