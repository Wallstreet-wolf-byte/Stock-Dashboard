"""巨潮资讯 —— 上市公司公告（cninfo.com.cn 全站搜索 API）"""
import re
from datetime import datetime, timedelta

import httpx

from crawlers.news_base import build_news
from config import CRAWL_HEADERS, CRAWL_TIMEOUT

SEARCH_URL = "http://www.cninfo.com.cn/new/fulltextSearch/full"
DETAIL_URL = "http://www.cninfo.com.cn/new/disclosure/detail"


def fetch(stock: dict, limit: int = 20) -> list[dict]:
    """抓取巨潮资讯的个股公告（全站搜索 API）"""
    code = stock["code"]
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    headers = {
        **CRAWL_HEADERS,
        "Referer": "http://www.cninfo.com.cn/new/fulltextSearch",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "http://www.cninfo.com.cn",
    }
    form_data = {
        "pageNum": 1,
        "pageSize": min(limit, 30),
        "searchkey": code,
        "sdate": start_date,
        "edate": end_date,
        "isfulltext": "false",
        "sortName": "pubdate",
        "sortType": "desc",
    }

    try:
        with httpx.Client(timeout=max(CRAWL_TIMEOUT, 20), follow_redirects=True, headers=headers) as c:
            r = c.post(SEARCH_URL, data=form_data)
            data = r.json()
    except Exception as e:
        print(f"[cninfo] 获取失败: {e}")
        return []

    items = []
    announcements = data.get("announcements", []) if isinstance(data, dict) else []

    for it in announcements:
        title = it.get("announcementTitle", "")
        if not title:
            continue

        # 去除 HTML 高亮标签
        title = re.sub(r"<[^>]+>", "", title).strip()

        # 公告时间（毫秒时间戳）
        pub_ts = it.get("announcementTime", 0)
        if isinstance(pub_ts, (int, float)) and pub_ts > 1e10:
            pub = datetime.fromtimestamp(pub_ts / 1000).isoformat()
        elif isinstance(pub_ts, str):
            pub = pub_ts
        else:
            pub = ""

        # 构造公告详情链接
        ann_id = it.get("announcementId", "")
        sec_code = it.get("secCode", code)
        org_id = it.get("orgId", "")
        url = f"{DETAIL_URL}?stockCode={sec_code}&announcementId={ann_id}&orgId={org_id}&announcementTime={pub_ts}"

        # 摘要取标题
        summary = title

        items.append(build_news(stock, "cninfo", title, summary, url, str(pub)))
        if len(items) >= limit:
            break

    return items