"""东方财富 —— 资金流向 + 财务指标"""
import json

from crawlers.news_base import fetch_json

# 资金流向（日K）
FFLOW_URL = ("http://push2.eastmoney.com/api/qt/stock/fflow/daykline/get")
FFLOW_PARAMS_BASE = {
    "lmt": 0,
    "klt": 101,   # 101=日, 102=周
    "fields1": "f1,f2,f3,f7",
    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
    "ut": "b2884a393a59ad64002292a3e90d46a5",
}

# 财务指标摘要 —— 东方财富 datacenter API
FINANCE_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def get_money_flow(stock: dict, days: int = 30) -> list[dict]:
    """获取资金流向数据"""
    secid = stock["secid"]
    params = {**FFLOW_PARAMS_BASE, "secid": secid, "lmt": days}
    try:
        data = fetch_json(FFLOW_URL, params=params)
    except Exception as e:
        print(f"[em-fflow] 获取失败: {e}")
        return []
    klines = data.get("data", {}).get("klines", []) if isinstance(data, dict) else []
    result = []
    for line in klines:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        try:
            result.append({
                "date": parts[0],
                "main_net": float(parts[1]),       # 主力净流入(元)
                "small_net": float(parts[2]),      # 小单净流入
                "medium_net": float(parts[3]),     # 中单净流入
                "large_net": float(parts[4]),      # 大单净流入
                "super_net": float(parts[5]),      # 超大单净流入
                "main_pct": float(parts[6]) if len(parts) > 6 else 0,
            })
        except (ValueError, IndexError):
            continue
    return result


def get_finance(stock: dict) -> dict:
    """获取基础财务指标（东方财富 datacenter API）"""
    em_code = f"{stock['code']}.{stock['market'].upper()}"  # 600703.SH
    params = {
        "reportName": "RPT_F10_FINANCE_MAINFINADATA",
        "columns": "ALL",
        "filter": f'(SECUCODE="{em_code}")',
        "pageNumber": 1,
        "pageSize": 1,
    }
    try:
        data = fetch_json(FINANCE_URL, params=params)
    except Exception as e:
        print(f"[em-finance] 获取失败: {e}")
        return {}
    try:
        items = data.get("result", {}).get("data", []) if isinstance(data, dict) else []
        if not items:
            return {}
        d = items[0]
        return {
            "report_date": d.get("REPORT_DATE", "") or d.get("REPORTDATE", ""),
            "eps": _f(d.get("BASIC_EPS") or d.get("EPSJB")),
            "bps": _f(d.get("BPS") or d.get("TOTAL_ASSETS_PER_SHARE")),
            "roe": _f(d.get("WEIGHTAVG_ROE") or d.get("ROEJQ")),
            "gross_margin": _f(d.get("XSMLL") or d.get("GROSS_PROFIT_RATIO")),
            "revenue": _f(d.get("TOTAL_OPERATE_INCOME") or d.get("YYZSR")),
            "revenue_yoy": _f(d.get("YSTZ") or d.get("YYZSRTBZZ")),
            "net_profit": _f(d.get("PARENT_NETPROFIT") or d.get("NETPROFIT")),
            "profit_yoy": _f(d.get("SJLTZ") or d.get("NETPROFITGROWRATE")),
        }
    except Exception:
        return {}


def _f(v):
    try:
        return float(v) if v not in (None, "") else 0
    except Exception:
        return 0
