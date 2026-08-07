"""股票看板平台 —— FastAPI 主应用"""
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database
from config import HOST, PORT, FRONTEND_DIR
from initial_stocks import seed_if_empty
from services import news_service, sentiment_service, quote_service, scheduler
from services.wyckoff_service import full_wyckoff_analysis
from services.trade_plan_service import generate_trade_plan, generate_all_trade_plans
from crawlers.news_base import SOURCE_LABELS


# ---------------- 股票代码自动识别 ----------------

def detect_market_secid(code: str) -> tuple[str, str]:
    """根据代码识别市场和东方财富 secid"""
    code = code.strip()
    if not re.match(r"^\d{6}$", code):
        raise ValueError("股票代码必须是6位数字")
    if code.startswith(("60", "68", "11", "13")):  # 沪市
        return "sh", f"1.{code}"
    elif code.startswith(("00", "30", "12")):  # 深市
        return "sz", f"0.{code}"
    elif code.startswith(("83", "87", "43", "88")):  # 北交所
        return "bj", f"0.{code}"
    else:
        # 默认按沪市处理
        return "sh", f"1.{code}"


# ---------------- 生命周期 ----------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    database.init_db()
    seed_if_empty()
    scheduler.start_scheduler()
    print(f"[app] 服务启动完成 → http://0.0.0.0:{PORT}")
    yield
    # 关闭
    print("[app] 服务关闭")


app = FastAPI(title="股票看板平台", lifespan=lifespan)


# ---------------- 数据模型 ----------------

class StockCreate(BaseModel):
    code: str
    name: str = ""


class SettingsUpdate(BaseModel):
    refresh_interval: int | None = None
    top_n: int | None = None


# ---------------- 股票管理 API ----------------

@app.get("/api/stocks")
def api_list_stocks():
    return {"stocks": database.list_stocks()}


@app.post("/api/stocks")
def api_add_stock(body: StockCreate):
    code = body.code.strip()
    try:
        market, secid = detect_market_secid(code)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # 若未提供名称，尝试从行情接口获取
    name = body.name.strip()
    if not name:
        stock_tmp = {"code": code, "market": market, "secid": secid}
        rt = quote_service.get_realtime(stock_tmp)
        name = rt.get("name", code)
        if not rt:
            raise HTTPException(400, f"无法验证股票代码 {code}，请确认代码正确或手动填写名称")

    stock = database.add_stock(code, name, market, secid)
    return {"status": "ok", "stock": stock}


@app.delete("/api/stocks/{code}")
def api_remove_stock(code: str):
    if not database.remove_stock(code):
        raise HTTPException(404, f"股票 {code} 不存在")
    return {"status": "ok", "message": f"已移除 {code}"}


# ---------------- 新闻 API ----------------

@app.get("/api/news/{code}")
def api_get_news(code: str, top_n: int = Query(default=None)):
    top_n = top_n or int(database.get_setting("top_n", "15"))
    items = news_service.get_stock_news(code, top_n=top_n)
    import json
    for it in items:
        it["keywords"] = json.loads(it.get("keywords") or "[]")
        it["keywords_tagged"] = json.loads(it.get("keywords_tagged") or "[]")
        it["industries"] = json.loads(it.get("industries") or "[]")
        it["source_label"] = SOURCE_LABELS.get(it["source"], it["source"])
    return {"stock_code": code, "count": len(items), "news": items}


@app.post("/api/refresh")
def api_refresh(code: str = Query(default=None)):
    """手动触发刷新。code 为空时刷新全部"""
    if code:
        stock = database.get_stock(code)
        if not stock:
            raise HTTPException(404, "股票不存在")
        from services.news_service import refresh_stock_news
        from services.sentiment_service import analyze_stock_sentiment
        n = refresh_stock_news(stock)
        analyze_stock_sentiment(stock)
        return {"status": "ok", "stock": code, "news_count": n}
    return scheduler.trigger_refresh_now()


@app.post("/api/refresh/news")
def api_refresh_news_only():
    """仅刷新新闻（后台）"""
    return scheduler.trigger_refresh_now()


# ---------------- 情绪 API ----------------

@app.get("/api/sentiment")
def api_all_sentiment():
    return {"sentiments": sentiment_service.get_all_sentiment()}


@app.get("/api/sentiment/{code}")
def api_stock_sentiment(code: str):
    item = sentiment_service.get_stock_sentiment(code)
    if not item:
        # 触发一次分析
        stock = database.get_stock(code)
        if not stock:
            raise HTTPException(404, "股票不存在")
        item = sentiment_service.analyze_stock_sentiment(stock)
        if not item:
            return {"stock_code": code, "message": "暂无足够情绪数据"}
    return item


@app.post("/api/sentiment/{code}/analyze")
def api_analyze_sentiment(code: str):
    stock = database.get_stock(code)
    if not stock:
        raise HTTPException(404, "股票不存在")
    item = sentiment_service.analyze_stock_sentiment(stock)
    if not item:
        raise HTTPException(500, "情绪数据抓取失败")
    return item


# ---------------- 行情 API ----------------

@app.get("/api/quote/realtime")
def api_all_realtime():
    return {"quotes": quote_service.get_all_realtime()}


@app.get("/api/quote/{code}")
def api_full_quote(code: str, period: str = Query(default="daily")):
    stock = database.get_stock(code)
    if not stock:
        raise HTTPException(404, "股票不存在")
    return quote_service.get_full_quote(stock)


@app.get("/api/quote/{code}/kline")
def api_kline(code: str, period: str = Query(default="daily")):
    stock = database.get_stock(code)
    if not stock:
        raise HTTPException(404, "股票不存在")
    return {"kline": quote_service.get_kline(stock, period)}


@app.get("/api/quote/{code}/moneyflow")
def api_money_flow(code: str, days: int = Query(default=30)):
    stock = database.get_stock(code)
    if not stock:
        raise HTTPException(404, "股票不存在")
    return {"money_flow": quote_service.get_money_flow(stock, days)}


@app.get("/api/quote/{code}/finance")
def api_finance(code: str):
    stock = database.get_stock(code)
    if not stock:
        raise HTTPException(404, "股票不存在")
    return quote_service.get_finance(stock)


# ---------------- 威科夫分析 API ----------------

@app.get("/api/wyckoff/all")
def api_wyckoff_all():
    """所有股票威科夫分析"""
    stocks = database.list_stocks()
    results = {}
    for stock in stocks:
        try:
            klines = quote_service.get_kline(stock, "daily")
            result = full_wyckoff_analysis(klines)
            results[stock["code"]] = {
                "stock_name": stock["name"],
                "has_data": "error" not in result,
                **result,
            }
        except Exception as e:
            results[stock["code"]] = {"stock_name": stock["name"], "error": str(e)}
    return {"stocks": results}


@app.get("/api/wyckoff/{code}")
def api_wyckoff(code: str):
    """单只股票威科夫分析"""
    stock = database.get_stock(code)
    if not stock:
        raise HTTPException(404, "股票不存在")
    klines = quote_service.get_kline(stock, "daily")
    if not klines:
        raise HTTPException(500, "无法获取K线数据")
    result = full_wyckoff_analysis(klines)
    if "error" in result:
        return {"stock_code": code, "stock_name": stock["name"], **result}
    return {"stock_code": code, "stock_name": stock["name"], **result}


# ---------------- 交易计划 API ----------------

@app.get("/api/trade-plan/all")
def api_trade_plan_all():
    """所有股票交易计划"""
    stocks = database.list_stocks()
    klines_map = {}
    for stock in stocks:
        try:
            klines_map[stock["code"]] = quote_service.get_kline(stock, "daily")
        except Exception:
            klines_map[stock["code"]] = []

    time_window = {
        "start": "2026-08-13",
        "end": "2026-08-14",
        "note": "全组合离场窗口，防范8月中下旬市场二次测试（ST）回踩风险",
    }
    plans = generate_all_trade_plans(stocks, klines_map, time_window)
    return {"plans": plans}


@app.get("/api/trade-plan/{code}")
def api_trade_plan(code: str):
    """单只股票交易计划"""
    stock = database.get_stock(code)
    if not stock:
        raise HTTPException(404, "股票不存在")
    klines = quote_service.get_kline(stock, "daily")
    if not klines:
        raise HTTPException(500, "无法获取K线数据")

    time_window = {
        "start": "2026-08-13",
        "end": "2026-08-14",
        "note": "全组合离场窗口，防范8月中下旬市场二次测试（ST）回踩风险",
    }
    plan = generate_trade_plan(stock, klines, time_window)
    return plan


# ---------------- 设置 API ----------------

@app.get("/api/settings")
def api_get_settings():
    return {
        "refresh_interval": int(database.get_setting("refresh_interval", "5")),
        "top_n": int(database.get_setting("top_n", "15")),
        "news_sources": list(SOURCE_LABELS.keys()),
        "source_labels": SOURCE_LABELS,
    }


@app.put("/api/settings")
def api_update_settings(body: SettingsUpdate):
    if body.refresh_interval is not None:
        if body.refresh_interval < 1 or body.refresh_interval > 1440:
            raise HTTPException(400, "刷新间隔需在 1-1440 分钟之间")
        database.set_setting("refresh_interval", str(body.refresh_interval))
        scheduler.update_news_interval(body.refresh_interval)
    if body.top_n is not None:
        if body.top_n not in (10, 15, 20):
            raise HTTPException(400, "Top N 仅支持 10/15/20")
        database.set_setting("top_n", str(body.top_n))
    return {
        "refresh_interval": int(database.get_setting("refresh_interval", "5")),
        "top_n": int(database.get_setting("top_n", "15")),
    }


# ---------------- 健康检查 ----------------

@app.get("/api/health")
def api_health():
    return {
        "status": "ok",
        "stocks_count": len(database.list_stocks()),
        "settings": {
            "refresh_interval": int(database.get_setting("refresh_interval", "5")),
            "top_n": int(database.get_setting("top_n", "15")),
        },
    }


# ---------------- 静态前端 ----------------

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(f"{FRONTEND_DIR}/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
