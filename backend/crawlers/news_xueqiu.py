"""雪球 —— 个股动态（股票专属数据源）"""
from crawlers.news_base import fetch_json, stock_match, build_news

URL = "https://xueqiu.com/query/v1/symbol/search/status"
EXTRA_HEADERS = {
    "Referer": "https://xueqiu.com/",
    "Origin": "https://xueqiu.com",
}


def _xq_symbol(stock: dict) -> str:
    """转换为雪球代码格式 SH600703 / SZ000001"""
    market = stock["market"].upper()
    return f"{market}{stock['code']}"


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    symbol = _xq_symbol(stock)
    params = {
        "count": limit * 2,
        "comment": 0,
        "hl": 0,
        "source": "user",
        "sort": "time",
        "page": 1,
        "symbol": symbol,
    }
    try:
        data = fetch_json(URL, headers=EXTRA_HEADERS, params=params)
    except Exception as e:
        print(f"[xueqiu] 获取失败: {e}")
        return []
    items = []
    posts = data.get("list", []) if isinstance(data, dict) else []
    for it in posts:
        title = it.get("title") or it.get("description", "")[:60]
        summary = it.get("description", "") or it.get("text", "")
        if not title:
            continue
        url = f"https://xueqiu.com{it.get('target', '')}"
        pub = it.get("created_at", "")
        if isinstance(pub, (int, float)):
            from datetime import datetime
            pub = datetime.fromtimestamp(pub / 1000).isoformat()
        items.append(build_news(stock, "xueqiu", title, summary, url, str(pub)))
        if len(items) >= limit:
            break
    return items
