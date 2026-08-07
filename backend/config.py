"""全局配置"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Render 部署时使用 /tmp 存放数据
if os.environ.get("RENDER"):
    DATA_DIR = "/tmp/data"
    FRONTEND_DIR = BASE_DIR  # 前端文件在项目根目录

DB_PATH = os.path.join(DATA_DIR, "stocks.db")

# 服务配置
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8000))

# 新闻刷新配置（分钟）
DEFAULT_REFRESH_INTERVAL = 5
DEFAULT_TOP_N = 15  # 默认每只股票展示的资讯条数，可选 10/15/20

# 爬虫配置
CRAWL_TIMEOUT = 15  # 单个数据源请求超时秒数
CRAWL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 情绪分析每只股票抓取的评论条数
SENTIMENT_SAMPLE_SIZE = 80

# 新闻数据源（启用项）
# em_ann/cninfo: 个股专属公告源（必命中）
# sina/eastmoney/10jqka/renmin: 通用市场快讯（全量返回）
ENABLED_NEWS_SOURCES = [
    "em_ann", "cninfo", "sina", "eastmoney", "10jqka", "renmin"
]

# 情绪数据源
ENABLED_SENTIMENT_SOURCES = ["guba", "xueqiu"]

os.makedirs(DATA_DIR, exist_ok=True)
