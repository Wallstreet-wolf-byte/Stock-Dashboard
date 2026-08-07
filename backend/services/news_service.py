"""新闻聚合服务 —— 调度 6 个数据源并行抓取"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import database
from config import ENABLED_NEWS_SOURCES
from crawlers import (news_sina, news_eastmoney, news_10jqka,
                      news_renmin, news_stock_em, news_cninfo)

SOURCE_MODULES = {
    "em_ann": news_stock_em,
    "cninfo": news_cninfo,
    "sina": news_sina,
    "eastmoney": news_eastmoney,
    "10jqka": news_10jqka,
    "renmin": news_renmin,
}


def refresh_stock_news(stock: dict, top_n: int = 15) -> int:
    """刷新单只股票的新闻，返回新增条数"""
    per_source = max(20, top_n)  # 每个源抓取上限
    all_items = []

    def _run(src_name):
        mod = SOURCE_MODULES[src_name]
        try:
            return mod.fetch(stock, limit=per_source)
        except Exception as e:
            print(f"[news] {src_name} 抓取 {stock['name']} 失败: {e}")
            return []

    with ThreadPoolExecutor(max_workers=len(ENABLED_NEWS_SOURCES)) as pool:
        futures = {pool.submit(_run, s): s for s in ENABLED_NEWS_SOURCES}
        for fut in as_completed(futures):
            all_items.extend(fut.result())

    # 去重（按标题）
    seen = set()
    deduped = []
    for it in all_items:
        key = it["title"]
        if key and key not in seen:
            seen.add(key)
            deduped.append(it)

    # 按时间倒序（有时间的在前）
    deduped.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    # 限制总数：每只股票最多保留 top_n * 5 条（5个源各贡献top_n条）
    deduped = deduped[: top_n * 5]

    # 清理旧缓存再写入新数据
    database.clear_news(stock["code"])
    database.save_news(deduped)
    print(f"[news] {stock['name']}({stock['code']}) 抓取 {len(deduped)} 条")
    return len(deduped)


def refresh_all_news(top_n: int = None) -> dict:
    """刷新所有关注股票的新闻"""
    if top_n is None:
        top_n = int(database.get_setting("top_n", "15"))
    stocks = database.list_stocks()
    result = {"total": 0, "stocks": {}}
    for stock in stocks:
        count = refresh_stock_news(stock, top_n=top_n)
        result["stocks"][stock["code"]] = count
        result["total"] += count
    result["refreshed_at"] = datetime.now().isoformat()
    return result


def get_stock_news(stock_code: str, top_n: int = None) -> list[dict]:
    """读取已缓存的新闻"""
    if top_n is None:
        top_n = int(database.get_setting("top_n", "15"))
    return database.get_news(stock_code, limit=top_n)
