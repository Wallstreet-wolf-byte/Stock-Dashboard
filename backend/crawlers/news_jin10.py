"""金十数据快讯"""
from datetime import datetime

from crawlers.news_base import fetch_json, strip_html, stock_match, build_news

URL = "https://flash-api.jin10.com/get_flash_list"
PARAMS = {"max_time": "", "channel": "-8200", "t": ""}


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    try:
        data = fetch_json(URL, params=PARAMS)
    except Exception as e:
        print(f"[jin10] 获取失败: {e}")
        return []
    items = []
    if not isinstance(data, list):
        return []
    for it in data:
        title = it.get("title", "")
        content = strip_html(it.get("content", ""))
        combined = f"{title} {content}"
        if not stock_match(combined, stock):
            continue
        pub_ts = it.get("time", "")
        if isinstance(pub_ts, (int, float)):
            pub = datetime.fromtimestamp(pub_ts).isoformat()
        else:
            pub = str(pub_ts)
        url = f"https://www.jin10.com/flash/{it.get('id', '')}"
        title = title or content[:60]
        items.append(build_news(stock, "jin10", title, content, url, pub))
        if len(items) >= limit:
            break
    return items
