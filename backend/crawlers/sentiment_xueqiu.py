"""雪球讨论 —— 投资者情绪数据"""
from crawlers.news_base import fetch_json, strip_html

URL = "https://xueqiu.com/query/v1/symbol/search/status"
EXTRA_HEADERS = {
    "Referer": "https://xueqiu.com/",
    "Origin": "https://xueqiu.com",
}


def _xq_symbol(stock: dict) -> str:
    return f"{stock['market'].upper()}{stock['code']}"


def fetch(stock: dict, limit: int = 80) -> list[str]:
    """抓取雪球个股讨论文本，返回文本列表用于情绪分析"""
    symbol = _xq_symbol(stock)
    texts = []
    params = {
        "count": limit,
        "comment": 0,
        "hl": 0,
        "source": "all",
        "sort": "time",
        "page": 1,
        "symbol": symbol,
    }
    try:
        data = fetch_json(URL, headers=EXTRA_HEADERS, params=params)
    except Exception as e:
        print(f"[xueqiu-sentiment] 获取失败: {e}")
        return []
    posts = data.get("list", []) if isinstance(data, dict) else []
    for it in posts:
        parts = []
        if it.get("title"):
            parts.append(it["title"])
        if it.get("description"):
            parts.append(strip_html(it["description"]))
        if it.get("text"):
            parts.append(strip_html(it["text"]))
        text = " ".join(parts).strip()
        if text and len(text) > 2:
            texts.append(text)
        if len(texts) >= limit:
            break
    return texts
