"""行情数据 —— 腾讯实时报价 + 新浪K线"""
import json
import re

from crawlers.news_base import fetch_text

# 腾讯实时行情
TENCENT_URL = "https://qt.gtimg.cn/q={symbol}"
# 新浪K线
KLINE_URL = ("https://money.finance.sina.com.cn/quotes_service/api/"
             "json_v2.php/CN_MarketData.getKLineData")


def _tencent_symbol(stock: dict) -> str:
    """腾讯代码格式: sh600703 / sz000001"""
    return f"{stock['market']}{stock['code']}"


def get_realtime(stock: dict) -> dict:
    """获取实时行情（腾讯数据源，稳定可靠）"""
    symbol = _tencent_symbol(stock)
    try:
        text = fetch_text(TENCENT_URL.format(symbol=symbol), encoding="gbk")
    except Exception as e:
        print(f"[tencent-quote] 获取失败: {e}")
        return {}
    m = re.search(r'"([^"]+)"', text)
    if not m:
        return {}
    fields = m.group(1).split("~")
    if len(fields) < 35:
        return {}
    try:
        name = fields[1]
        price = float(fields[3]) if fields[3] else 0
        pre_close = float(fields[4]) if fields[4] else 0
        open_p = float(fields[5]) if fields[5] else 0
        volume = int(float(fields[6])) if fields[6] else 0  # 手
        change = float(fields[31]) if fields[31] else 0
        change_pct = float(fields[32]) if fields[32] else 0
        high = float(fields[33]) if fields[33] else 0
        low = float(fields[34]) if fields[34] else 0
        # 成交额从 fields[35] 提取 (price/volume/amount)
        amount = 0
        if "/" in fields[35]:
            parts = fields[35].split("/")
            if len(parts) >= 3:
                amount = float(parts[2]) if parts[2] else 0
        return {
            "name": name,
            "price": round(price, 3),
            "open": open_p,
            "pre_close": pre_close,
            "high": high,
            "low": low,
            "volume": volume * 100,  # 转为股
            "amount": amount,
            "change": round(change, 3),
            "change_pct": round(change_pct, 2),
        }
    except (ValueError, IndexError) as e:
        print(f"[tencent-quote] 解析失败: {e}")
        return {}


def get_kline(stock: dict, scale: int = 240, datalen: int = 180) -> list[dict]:
    """获取K线数据（新浪数据源）
    scale: 5/15/30/60分钟, 240=日线, 1680=周线, 7200=月线
    """
    symbol = _tencent_symbol(stock)
    params = {"symbol": symbol, "scale": scale, "datalen": datalen}
    try:
        text = fetch_text(KLINE_URL, params=params)
        data = json.loads(text)
    except Exception as e:
        print(f"[sina-kline] 获取失败: {e}")
        return []
    result = []
    for it in data:
        result.append({
            "date": it.get("day", ""),
            "open": float(it.get("open", 0)),
            "close": float(it.get("close", 0)),
            "high": float(it.get("high", 0)),
            "low": float(it.get("low", 0)),
            "volume": int(float(it.get("volume", 0))),
        })
    return result
