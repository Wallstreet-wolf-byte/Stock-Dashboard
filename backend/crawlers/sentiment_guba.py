"""东方财富股吧 —— 投资者情绪数据"""
import re

from crawlers.news_base import fetch_text

URL = "https://guba.eastmoney.com/list,{code}_{page}.html"
EXTRA_HEADERS = {"Referer": "https://guba.eastmoney.com/"}


def fetch(stock: dict, limit: int = 80) -> list[str]:
    """抓取股吧帖子标题，返回文本列表用于情绪分析"""
    texts = []
    code = stock["code"]
    # 帖子链接正则：/news,{code},{id}.html 后跟标题文本
    title_pattern = re.compile(
        rf'<a[^>]*href="(/news,{re.escape(code)},[^"]+)"[^>]*>([^<]{{4,}})</a>'
    )
    # 抓前2页
    for page in range(1, 3):
        try:
            html = fetch_text(URL.format(code=code, page=page),
                              headers=EXTRA_HEADERS)
        except Exception as e:
            print(f"[guba] 第{page}页获取失败: {e}")
            continue
        for match in title_pattern.finditer(html):
            title = match.group(2).strip()
            # 过滤广告和无关内容
            if title and len(title) > 3 and title not in texts:
                # 排除明显的导航/广告文字
                if not any(skip in title for skip in ["点击查看", "下载APP", "举报"]):
                    texts.append(title)
            if len(texts) >= limit:
                return texts
    return texts
