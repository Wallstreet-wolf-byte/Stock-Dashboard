"""财联社电报"""
from datetime import datetime

from crawlers.news_base import fetch_json, strip_html, stock_match, build_news

URL = "https://www.cls.cn/nodeapi/updateTelegraphList"
PARAMS = {
    "app": "CailianpressWeb",
    "category": "",
    "os": "web",
    "rn": 80,
    "last_time": "",
    "sv": "7.7.5",
}


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    try:
        data = fetch_json(URL, params=PARAMS)
    except Exception as e:
        print(f"[cls] 获取失败: {e}")
        return []
    items = []
    roll = data.get("data", {}).get("roll_data", []) if isinstance(data, dict) else []
    for it in roll:
        title = it.get("title", "") or it.get("brief", "")
        content = strip_html(it.get("content", "")) or it.get("brief", "")
        combined = f"{title} {content}"
        if not stock_match(combined, stock):
            continue
        pub_ts = it.get("ctime", "")
        if isinstance(pub_ts, (int, float)):
            pub = datetime.fromtimestamp(pub_ts).isoformat()
        else:
            pub = str(pub_ts)
        url = f"https://www.cls.cn/detail/{it.get('id', '')}"
        title = title or content[:60]
        items.append(build_news(stock, "cls", title, content, url, pub))
        if len(items) >= limit:
            break
    return items
