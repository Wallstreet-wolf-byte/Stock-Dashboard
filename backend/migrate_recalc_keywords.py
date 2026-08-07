"""一次性迁移脚本：用新算法重算 news 表里所有新闻的
keywords / keywords_tagged / industries / sentiment_label / sentiment_text

用法：
    cd backend && python3 migrate_recalc_keywords.py

背景：早期 jieba TF-IDF 不带词性标注，会切出"及前""十大""高能"等碎片。
新算法用 allowPOS=名词类 + 结构化过滤 + "宁缺毋滥返回空"，需要回填到已有数据。
"""
import json
import sqlite3
import sys
from pathlib import Path

# 让脚本能直接 import backend 模块
sys.path.insert(0, str(Path(__file__).parent))

from config import DB_PATH
from nlp.stock_meta import (
    extract_smart_keywords,
    keyword_words_only,
    match_industries,
    analyze_sentiment_label,
)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. 读取所有股票（code -> name）
    stock_rows = conn.execute("SELECT code, name FROM stocks").fetchall()
    code2name = {r["code"]: r["name"] for r in stock_rows}
    print(f"[1/3] 加载 {len(code2name)} 只股票")

    # 2. 读取所有新闻
    news_rows = conn.execute(
        "SELECT id, stock_code, title, summary FROM news"
    ).fetchall()
    print(f"[2/3] 加载 {len(news_rows)} 条新闻，开始重算...")

    # 3. 逐条重算并 UPDATE
    updated = 0
    emptied = 0
    for r in news_rows:
        stock_name = code2name.get(r["stock_code"], "")
        full_text = f"{r['title'] or ''} {r['summary'] or ''}"
        keywords_tagged = extract_smart_keywords(full_text, topk=4, stock_name=stock_name)
        industries = match_industries(full_text)
        sentiment_label, sentiment_text = analyze_sentiment_label(full_text)

        if not keywords_tagged:
            emptied += 1

        conn.execute(
            """UPDATE news SET
               keywords = ?,
               keywords_tagged = ?,
               industries = ?,
               sentiment_label = ?,
               sentiment_text = ?
               WHERE id = ?""",
            (
                json.dumps(keyword_words_only(keywords_tagged), ensure_ascii=False),
                json.dumps(keywords_tagged, ensure_ascii=False),
                json.dumps(industries, ensure_ascii=False),
                sentiment_label,
                sentiment_text,
                r["id"],
            ),
        )
        updated += 1
        if updated % 50 == 0:
            conn.commit()
            print(f"    ...已处理 {updated}/{len(news_rows)}")

    conn.commit()
    conn.close()
    print(f"[3/3] 完成：重算 {updated} 条，其中 {emptied} 条因纯套话公告关键词置空")
    print("迁移完成。")


if __name__ == "__main__":
    main()
