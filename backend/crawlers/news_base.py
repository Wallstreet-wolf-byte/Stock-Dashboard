"""新闻爬虫公共工具"""
import json
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from config import CRAWL_HEADERS, CRAWL_TIMEOUT
from nlp.keywords import extract_keywords
from nlp.stock_meta import (extract_smart_keywords, keyword_words_only,
                             match_industries, analyze_sentiment_label)


def fetch_text(url: str, headers: Optional[dict] = None,
               params: Optional[dict] = None, timeout: int = CRAWL_TIMEOUT,
               encoding: Optional[str] = None) -> str:
    """同步获取网页/接口文本

    encoding: 强制指定编码（如 'gbk' 用于新浪行情）
    """
    hdr = {**CRAWL_HEADERS, **(headers or {})}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=hdr) as c:
        r = c.get(url, params=params)
        if encoding:
            r.encoding = encoding
        elif r.encoding is None:
            r.encoding = "utf-8"
        return r.text


def fetch_json(url: str, headers: Optional[dict] = None,
               params: Optional[dict] = None, timeout: int = CRAWL_TIMEOUT):
    """同步获取 JSON"""
    hdr = {**CRAWL_HEADERS, **(headers or {})}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=hdr) as c:
        r = c.get(url, params=params)
        return r.json()


def strip_html(html: str) -> str:
    """去除 HTML 标签"""
    if not html:
        return ""
    # 若不含 HTML 标签，直接返回清理后的文本
    if "<" not in html or ">" not in html:
        return re.sub(r"\s+", " ", html).strip()
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)


def stock_match(text: str, stock: dict) -> bool:
    """判断文本是否与某只股票相关"""
    if not text:
        return False
    name = stock["name"]
    code = stock["code"]
    # 全名匹配
    if name in text:
        return True
    # 代码匹配（带前后边界，避免部分匹配）
    if code in text:
        return True
    # 简称匹配（取名字前2-3字，对3字以上名称）
    if len(name) >= 3:
        short = name[:2]
        # 避免误匹配，仅当简称独立出现时算命中
        if re.search(rf"(?<![\u4e00-\u9fa5]){re.escape(short)}", text):
            return True
    return False


def build_news(stock: dict, source: str, title: str, summary: str,
               url: str, published_at: str) -> dict:
    """构造新闻条目：智能关键词(带type) + 行业标签 + 情感标签"""
    full_text = f"{title} {summary}"
    keywords_tagged = extract_smart_keywords(full_text, topk=4, stock_name=stock.get("name", ""))
    industries = match_industries(full_text)
    sentiment_label, sentiment_text = analyze_sentiment_label(full_text)
    return {
        "stock_code": stock["code"],
        "source": source,
        "title": title.strip()[:200],
        "summary": (summary or "").strip()[:500],
        "url": url,
        "keywords": json.dumps(keyword_words_only(keywords_tagged), ensure_ascii=False),
        "keywords_tagged": json.dumps(keywords_tagged, ensure_ascii=False),
        "industries": json.dumps(industries, ensure_ascii=False),
        "sentiment_label": sentiment_label,
        "sentiment_text": sentiment_text,
        "published_at": published_at,
        "crawled_at": datetime.now().isoformat(),
    }


SOURCE_LABELS = {
    "em_ann": "个股公告",
    "cninfo": "巨潮资讯",
    "sina": "新浪财经",
    "eastmoney": "东方财富",
    "10jqka": "同花顺",
    "renmin": "人民财讯",
}
