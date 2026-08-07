"""东方财富个股公告 —— 股票专属数据源（必命中）"""
from crawlers.news_base import fetch_json, build_news

URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
EXTRA_HEADERS = {"Referer": "https://data.eastmoney.com/"}


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    """抓取该股票的专属公告（每条都相关，无需过滤）"""
    params = {
        "sr": -1,
        "page_size": limit,
        "page_index": 1,
        "ann_type": "A",
        "client_source": "web",
        "stock_list": stock["code"],
    }
    try:
        data = fetch_json(URL, headers=EXTRA_HEADERS, params=params)
    except Exception as e:
        print(f"[em-ann] 获取失败: {e}")
        return []
    items = []
    ann_list = data.get("data", {}).get("list", []) if isinstance(data, dict) else []
    for it in ann_list:
        title = it.get("title", "")
        if not title:
            continue
        pub = it.get("notice_date", "") or it.get("eiTime", "")
        art_code = it.get("art_code", "")
        url = (f"https://data.eastmoney.com/notices/detail/{stock['code']}/{art_code}.html"
               if art_code else "https://data.eastmoney.com/")
        # 公告摘要取 display_time + title 扩展
        summary = it.get("titleCh", "") or title
        items.append(build_news(stock, "em_ann", title, summary, url, str(pub)))
        if len(items) >= limit:
            break
    return items
