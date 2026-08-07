"""情绪分析服务 —— 股吧+雪球 文本聚合 + NLP 分析"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import database
from config import ENABLED_SENTIMENT_SOURCES, SENTIMENT_SAMPLE_SIZE
from crawlers import sentiment_guba, sentiment_xueqiu
from nlp.sentiment import analyze_batch
from nlp.keywords import extract_keywords_from_batch

SOURCE_MODULES = {
    "guba": sentiment_guba,
    "xueqiu": sentiment_xueqiu,
}


def analyze_stock_sentiment(stock: dict) -> dict:
    """分析单只股票的投资情绪"""
    texts = []

    def _run(src_name):
        mod = SOURCE_MODULES[src_name]
        try:
            return mod.fetch(stock, limit=SENTIMENT_SAMPLE_SIZE)
        except Exception as e:
            print(f"[sentiment] {src_name} 抓取 {stock['name']} 失败: {e}")
            return []

    with ThreadPoolExecutor(max_workers=len(ENABLED_SENTIMENT_SOURCES)) as pool:
        futures = {pool.submit(_run, s): s for s in ENABLED_SENTIMENT_SOURCES}
        for fut in as_completed(futures):
            texts.extend(fut.result())

    if not texts:
        print(f"[sentiment] {stock['name']} 无可用文本")
        return {}

    result = analyze_batch(texts)
    # 情绪关键词词云
    kw = extract_keywords_from_batch(texts, topk=15)
    item = {
        "stock_code": stock["code"],
        "source": "guba+xueqiu",
        "positive": result["positive"],
        "neutral": result["neutral"],
        "negative": result["negative"],
        "score": result["score"],
        "sample_count": result["sample_count"],
        "positive_texts": result.get("positive_texts", 0),
        "neutral_texts": result.get("neutral_texts", 0),
        "negative_texts": result.get("negative_texts", 0),
        "level": result.get("level", "中性震荡"),
        "interpretation": result.get("interpretation", ""),
        "advice": result.get("advice", ""),
        "formula": result.get("formula", ""),
        "keywords": json.dumps(kw, ensure_ascii=False),
        "created_at": datetime.now().isoformat(),
    }
    database.save_sentiment(item)
    print(f"[sentiment] {stock['name']} 情绪分={result['score']:.1f} "
          f"等级={result.get('level','')} 样本={result['sample_count']}")
    return item


def analyze_all_sentiment() -> dict:
    """分析所有关注股票的情绪"""
    stocks = database.list_stocks()
    result = {"stocks": {}}
    for stock in stocks:
        item = analyze_stock_sentiment(stock)
        result["stocks"][stock["code"]] = item
    result["analyzed_at"] = datetime.now().isoformat()
    return result


def get_stock_sentiment(stock_code: str) -> dict:
    """读取最新情绪快照"""
    latest = database.get_latest_sentiment(stock_code)
    if not latest:
        return {}
    latest["keywords"] = json.loads(latest.get("keywords") or "[]")
    return latest


def get_all_sentiment() -> list[dict]:
    """获取所有股票最新情绪"""
    stocks = database.list_stocks()
    result = []
    for stock in stocks:
        item = get_stock_sentiment(stock["code"])
        if item:
            item["stock_name"] = stock["name"]
            result.append(item)
    return result
