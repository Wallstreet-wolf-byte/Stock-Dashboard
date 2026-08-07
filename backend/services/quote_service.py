"""行情数据服务 —— 实时价/K线/资金流/财务"""
from concurrent.futures import ThreadPoolExecutor, as_completed

from crawlers import quote_sina, quote_eastmoney


def get_realtime(stock: dict) -> dict:
    return quote_sina.get_realtime(stock)


def get_kline(stock: dict, period: str = "daily") -> list[dict]:
    """获取K线
    period: daily/weekly/monthly/60min/30min/15min/5min
    """
    scale_map = {
        "daily": 240, "weekly": 1680, "monthly": 7200,
        "60min": 60, "30min": 30, "15min": 15, "5min": 5,
    }
    scale = scale_map.get(period, 240)
    datalen = 180 if period == "daily" else 120
    return quote_sina.get_kline(stock, scale=scale, datalen=datalen)


def get_money_flow(stock: dict, days: int = 30) -> list[dict]:
    return quote_eastmoney.get_money_flow(stock, days=days)


def get_finance(stock: dict) -> dict:
    return quote_eastmoney.get_finance(stock)


def get_full_quote(stock: dict) -> dict:
    """一次性获取全部行情数据（实时+K线+资金流+财务）"""
    result = {"stock": stock}

    def _rt():
        return ("realtime", get_realtime(stock))

    def _kl():
        return ("kline", get_kline(stock, "daily"))

    def _mf():
        return ("money_flow", get_money_flow(stock, 30))

    def _fin():
        return ("finance", get_finance(stock))

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(f) for f in (_rt, _kl, _mf, _fin)]
        for fut in as_completed(futures):
            key, val = fut.result()
            result[key] = val
    return result


def get_all_realtime() -> list[dict]:
    """获取所有关注股票的实时行情"""
    import database
    stocks = database.list_stocks()
    result = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(get_realtime, s): s for s in stocks}
        for fut in as_completed(futures):
            stock = futures[fut]
            try:
                rt = fut.result()
                if rt:
                    rt["code"] = stock["code"]
                    rt["stock_name"] = stock["name"]
                    result.append(rt)
            except Exception as e:
                print(f"[quote] {stock['name']} 获取失败: {e}")
    return result
