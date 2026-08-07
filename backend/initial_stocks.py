"""初始关注的股票清单（首次启动时自动导入）"""

# 格式: (code, name, market, secid)
# market: sh=上海, sz=深圳, bj=北京
# secid:  东方财富行情接口所需 (1.=上海, 0.=深圳)
INITIAL_STOCKS = [
    ("688048", "长光华芯", "sh", "1.688048"),
    ("300566", "激智科技", "sz", "0.300566"),
    ("002025", "航天电器", "sz", "0.002025"),
    ("002460", "赣锋锂业", "sz", "0.002460"),
    ("300806", "斯迪克",   "sz", "0.300806"),
    ("301015", "凯旺科技", "sz", "0.301015"),
    ("688678", "福立旺",   "sh", "1.688678"),
    ("688638", "迅捷兴",   "sh", "1.688638"),
    ("603588", "高能环境", "sh", "1.603588"),
    ("600703", "三安光电", "sh", "1.600703"),
]


def seed_if_empty():
    """数据库为空时导入初始股票"""
    import database
    if not database.list_stocks():
        for code, name, market, secid in INITIAL_STOCKS:
            database.add_stock(code, name, market, secid)
        print(f"[init] 已导入 {len(INITIAL_STOCKS)} 只初始关注股票")
    else:
        print(f"[init] 已存在股票数据，跳过导入")
