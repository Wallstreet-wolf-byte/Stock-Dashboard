"""威科夫操盘分析服务 —— 主力资金行为 + 技术指标 + 量价关系

基于威科夫理论（Wyckoff Method）的核心思想：
1. 市场由主力资金（Smart Money）驱动，散户跟随
2. 量价关系（Volume-Price Relationship）是判断主力意图的关键
3. 四个阶段：吸筹(Accumulation) → 拉升(Markup) → 派发(Distribution) → 下跌(Markdown)

本模块实现：
- MACD 穿0轴检测（动能衰竭信号）
- 均线系统（MA20/MA60 支撑/压制）
- 成交量分析（放量阳线/阴线、量价背离）
- 关键价格位（支撑/阻力/筹码密集区）
- 威科夫阶段判定
"""

import math
from typing import Optional


def ema(data: list[float], period: int) -> list[float]:
    """计算指数移动平均"""
    if len(data) < period:
        return [0.0] * len(data)
    result = [0.0] * len(data)
    k = 2.0 / (period + 1)
    # 第一个 EMA 值用 SMA
    result[period - 1] = sum(data[:period]) / period
    for i in range(period, len(data)):
        result[i] = result[i - 1] + k * (data[i] - result[i - 1])
    return result


def sma(data: list[float], period: int) -> list[float]:
    """简单移动平均"""
    result = [0.0] * len(data)
    for i in range(len(data)):
        if i < period - 1:
            result[i] = 0.0
        else:
            result[i] = sum(data[i - period + 1:i + 1]) / period
    return result


def calc_macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """计算 MACD

    返回: (DIF, DEA, MACD柱) 三个等长列表
    """
    if len(closes) < slow:
        return [0] * len(closes), [0] * len(closes), [0] * len(closes)

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    dif = [0.0] * len(closes)
    for i in range(len(closes)):
        dif[i] = ema_fast[i] - ema_slow[i]

    dea = ema(dif, signal)
    macd_bar = [0.0] * len(closes)
    for i in range(len(closes)):
        macd_bar[i] = 2.0 * (dif[i] - dea[i])

    return dif, dea, macd_bar


def detect_macd_zero_cross(dif: list[float], dea: list[float]) -> dict:
    """检测 MACD 穿0轴（动能衰竭信号）

    返回: {
        "dif_crossed_up": bool,   # DIF从下方上穿0轴
        "dea_crossed_up": bool,   # DEA从下方上穿0轴
        "days_since_cross": int,  # 最近一次上穿距今几天
        "signal": str,            # 信号描述
        "warning": str,           # 警告
    }
    """
    result = {
        "dif_crossed_up": False,
        "dea_crossed_up": False,
        "days_since_cross": 0,
        "signal": "未触发",
        "warning": "",
    }

    if len(dif) < 3:
        return result

    # 从后往前找最近一次上穿0轴
    for i in range(len(dif) - 2, 0, -1):
        if dif[i] <= 0 and dif[i + 1] > 0:
            result["dif_crossed_up"] = True
            result["days_since_cross"] = len(dif) - 1 - (i + 1)
            break

    for i in range(len(dea) - 2, 0, -1):
        if dea[i] <= 0 and dea[i + 1] > 0:
            result["dea_crossed_up"] = True
            break

    if result["dif_crossed_up"] and result["days_since_cross"] <= 5:
        result["signal"] = "DIF 近日上穿0轴"
        result["warning"] = "短期修复动能可能衰竭，注意回调风险"
    elif result["dea_crossed_up"]:
        result["signal"] = "DEA 上穿0轴"
        result["warning"] = "动能衰竭信号，关注量能是否配合"

    return result


def calc_ma(closes: list[float], periods: list[int] = None) -> dict:
    """计算多条均线"""
    if periods is None:
        periods = [20, 60]
    result = {}
    for p in periods:
        vals = sma(closes, p)
        result[f"MA{p}"] = vals[-1] if vals[-1] > 0 else None
        result[f"MA{p}_full"] = vals
    return result


def analyze_volume(volumes: list[float], opens: list[float], closes: list[float]) -> dict:
    """成交量分析 —— 识别放量K线、量价关系

    返回: {
        "avg_volume_20": float,
        "avg_volume_60": float,
        "high_volume_days": [{"index": int, "date": str, "volume": float, "type": "bullish/bearish"}],
        "volume_trend": "放量/缩量/持平",
        "recent_divergence": str,  # 近期量价背离描述
    }
    """
    n = len(volumes)
    if n < 20:
        return {"error": "数据不足"}

    avg_20 = sum(volumes[-20:]) / 20
    avg_60 = sum(volumes[-60:]) / min(60, n) if n >= 60 else avg_20

    # 放量日（成交量 > 1.5倍 20日均量）
    high_volume_days = []
    for i in range(max(0, n - 30), n):
        if volumes[i] > avg_20 * 1.5:
            bar_type = "bullish" if closes[i] >= opens[i] else "bearish"
            high_volume_days.append({
                "index": i,
                "volume": volumes[i],
                "vol_ratio": round(volumes[i] / avg_20, 2),
                "type": bar_type,
            })

    # 量能趋势：最近5天 vs 前20天
    recent_5 = sum(volumes[-5:]) / 5
    previous_20 = sum(volumes[-25:-5]) / 20 if n >= 25 else avg_20
    if recent_5 > previous_20 * 1.3:
        volume_trend = "放量"
    elif recent_5 < previous_20 * 0.7:
        volume_trend = "缩量"
    else:
        volume_trend = "持平"

    # 量价背离检测（最近5天）
    divergence = ""
    if n >= 5:
        price_up = closes[-1] > closes[-5]
        vol_down = recent_5 < previous_20 * 0.8
        if price_up and vol_down:
            divergence = "量价背离：股价上行但量能萎缩，上攻动力不足"
        elif not price_up and not vol_down and recent_5 > previous_20 * 1.3:
            divergence = "放量滞涨：量能放大但股价未涨，主力可能在派发"

    return {
        "avg_volume_20": round(avg_20, 0),
        "avg_volume_60": round(avg_60, 0),
        "high_volume_days": high_volume_days,
        "volume_trend": volume_trend,
        "recent_divergence": divergence,
    }


def find_key_levels(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    opens: list[float],
    ma_data: dict,
) -> dict:
    """寻找关键价格位 —— 支撑/阻力/筹码密集区

    返回:
    - support_levels: 近期支撑位列表
    - resistance_levels: 近期阻力位列表
    - nearest_support: 最近支撑位
    - nearest_resistance: 最近阻力位
    - high_vol_support: 放量阳线支撑
    - box_range: 箱体震荡区间
    """
    n = len(closes)
    current_price = closes[-1] if n > 0 else 0

    # 支撑位来源
    supports = []
    # 1. 放量阳线最低价（最近60天）
    if n >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        for i in range(max(0, n - 60), n):
            if volumes[i] > avg_vol * 1.5 and closes[i] >= opens[i]:
                supports.append({
                    "price": lows[i],
                    "type": "放量阳线支撑",
                    "index": i,
                    "strength": "强" if volumes[i] > avg_vol * 2 else "中",
                })

    # 2. 20日均线
    ma20 = ma_data.get("MA20")
    if ma20 and ma20 < current_price:
        supports.append({"price": round(ma20, 2), "type": "MA20均线支撑", "index": -1, "strength": "中"})

    # 3. 近期低点（最近30天）
    if n >= 30:
        recent_lows = lows[-30:]
        min_idx = recent_lows.index(min(recent_lows))
        supports.append({
            "price": min(recent_lows),
            "type": "近期低点支撑",
            "index": n - 30 + min_idx,
            "strength": "强",
        })

    # 阻力位来源
    resistances = []
    # 1. MA60
    ma60 = ma_data.get("MA60")
    if ma60 and ma60 > current_price:
        resistances.append({"price": round(ma60, 2), "type": "MA60均线压制", "index": -1, "strength": "强"})

    # 2. 近期高点（最近60天）
    if n >= 30:
        recent_highs = highs[-60:] if n >= 60 else highs[-30:]
        max_h = max(recent_highs)
        resistances.append({
            "price": max_h,
            "type": "近期高点阻力",
            "index": n - len(recent_highs) + recent_highs.index(max_h),
            "strength": "强",
        })

    # 3. 放量阴线高点（套牢盘）
    if n >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        for i in range(max(0, n - 60), n):
            if volumes[i] > avg_vol * 1.5 and closes[i] < opens[i]:
                resistances.append({
                    "price": highs[i],
                    "type": "放量阴线套牢区",
                    "index": i,
                    "strength": "强" if volumes[i] > avg_vol * 2 else "中",
                })

    # 最近支撑/阻力
    supports.sort(key=lambda x: x["price"], reverse=True)
    resistances.sort(key=lambda x: x["price"])

    nearest_support = None
    for s in supports:
        if s["price"] < current_price:
            nearest_support = s
            break

    nearest_resistance = None
    for r in resistances:
        if r["price"] > current_price:
            nearest_resistance = r
            break

    # 箱体区间
    box_high = max(s["price"] for s in supports) if supports else current_price * 1.05
    box_low = min(r["price"] for r in resistances) if resistances else current_price * 0.95

    return {
        "support_levels": supports[:5],
        "resistance_levels": resistances[:5],
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "box_range": {
            "high": round(box_high, 2),
            "low": round(box_low, 2),
        },
        "current_price": round(current_price, 2),
    }


def assess_wyckoff_phase(
    closes: list[float],
    volumes: list[float],
    dif: list[float],
    ma_data: dict,
) -> dict:
    """评估威科夫阶段

    基于价格行为、成交量变化、MACD 位置综合判断：
    - Accumulation（吸筹）：低位震荡+缩量+MACD底背离
    - Markup（拉升）：突破阻力+放量+MACD在0轴上方
    - Distribution（派发）：高位震荡+放量滞涨+MACD顶背离
    - Markdown（下跌）：破位+放量+MACD在0轴下方
    """
    n = len(closes)
    if n < 60:
        return {"phase": "数据不足", "description": "需要至少60个交易日数据"}

    current_price = closes[-1]
    ma20 = ma_data.get("MA20")
    ma60 = ma_data.get("MA60")

    # 价格位置判断
    recent_high = max(closes[-60:])
    recent_low = min(closes[-60:])
    price_range = recent_high - recent_low
    if price_range == 0:
        return {"phase": "无法判断", "description": "价格波动为0"}

    price_position = (current_price - recent_low) / price_range  # 0~1

    # 成交量判断
    if n >= 20:
        avg_vol_20 = sum(volumes[-20:]) / 20
        avg_vol_60 = sum(volumes[-60:]) / 60 if n >= 60 else avg_vol_20
        vol_ratio = avg_vol_20 / avg_vol_60 if avg_vol_60 > 0 else 1.0
    else:
        vol_ratio = 1.0

    # MACD 位置
    dif_now = dif[-1] if dif else 0
    dif_prev_5 = dif[-6] if len(dif) >= 6 else 0

    # 趋势判断
    if n >= 20:
        ma20_trend = closes[-1] > closes[-20] if n >= 20 else False
    else:
        ma20_trend = False

    # 综合判断
    phase = ""
    description = ""
    confidence = ""

    if price_position < 0.3 and dif_now < 0 and dif_now > dif_prev_5:
        # 低位 + MACD在0轴下方但开始回升
        phase = "潜吸筹 (Preliminary Support)"
        description = "股价处于60日低位区间，MACD在0轴下方拐头，成交量萎缩，可能进入吸筹阶段"
        confidence = "低"
    elif price_position < 0.5 and dif_now > 0 and dif_now > dif_prev_5 and vol_ratio > 1.2:
        # 中低位 + MACD在0轴上方向上 + 放量
        phase = "吸筹确认 → 拉升启动 (Accumulation→Markup)"
        description = "放量突破低位，MACD上穿0轴，量价配合良好，主力吸筹完成，拉升在即"
        confidence = "中"
    elif ma20 and ma60 and closes[-1] > ma20 and closes[-1] > ma60 and dif_now > 0 and vol_ratio > 1.0:
        # 均线多头 + MACD在0轴上方
        phase = "拉升中 (Markup)"
        description = "均线多头排列，MACD在0轴上方运行，量能配合，处于主升阶段"
        confidence = "高"
    elif price_position > 0.7 and dif_now > 0 and dif_now < dif_prev_5 and vol_ratio < 0.8:
        # 高位 + MACD走平或回落 + 缩量
        phase = "拉升末期 → 潜派发 (Late Markup → Preliminary Distribution)"
        description = "股价处于高位，MACD动能衰减，成交量萎缩，警惕主力派发"
        confidence = "中"
    elif price_position > 0.7 and dif_now < 0 and vol_ratio > 1.2:
        # 高位 + MACD在0轴下方 + 放量
        phase = "派发确认 (Distribution)"
        description = "高位放量，MACD在0轴下方，主力出货迹象明显，减仓观望"
        confidence = "高"
    elif dif_now < 0 and dif_now < dif_prev_5 and vol_ratio > 1.0:
        # MACD在0轴下方加速下行
        phase = "下跌中 (Markdown)"
        description = "MACD在0轴下方加速下行，量能放大，下跌趋势延续，不宜抄底"
        confidence = "高"
    elif price_position < 0.3 and dif_now < 0 and vol_ratio < 0.7:
        # 低位缩量
        phase = "潜在底部 (Potential Spring)"
        description = "极端缩量下跌至低位，可能出现Spring（弹簧效应），关注反转信号"
        confidence = "低"
    else:
        phase = "震荡蓄势 (Trading Range)"
        description = "股价在箱体内震荡，方向不明，等待放量突破确认方向"
        confidence = "低"

    return {
        "phase": phase,
        "description": description,
        "confidence": confidence,
        "price_position": round(price_position * 100, 1),
        "vol_ratio": round(vol_ratio, 2),
        "dif_value": round(dif_now, 4),
    }


def full_wyckoff_analysis(klines: list[dict]) -> dict:
    """完整的威科夫分析

    输入: klines 列表，每项包含 {"date", "open", "close", "high", "low", "volume"}

    返回: 完整的分析结果字典
    """
    if not klines or len(klines) < 60:
        return {
            "error": "数据不足",
            "message": f"需要至少60个交易日K线数据，当前仅{len(klines) if klines else 0}条",
            "available": len(klines) if klines else 0,
        }

    dates = [k["date"] for k in klines]
    opens = [k["open"] for k in klines]
    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    volumes = [k["volume"] for k in klines]

    n = len(closes)
    current_price = closes[-1]

    # 1. MACD
    dif, dea, macd_bar = calc_macd(closes)
    macd_signal = detect_macd_zero_cross(dif, dea)

    # 2. 均线
    ma_data = calc_ma(closes)

    # 3. 成交量分析
    vol_analysis = analyze_volume(volumes, opens, closes)

    # 4. 关键价格位
    key_levels = find_key_levels(highs, lows, closes, volumes, opens, ma_data)

    # 5. 威科夫阶段
    wyckoff_phase = assess_wyckoff_phase(closes, volumes, dif, ma_data)

    # 6. 近期涨跌幅
    if n >= 5:
        chg_5d = round((closes[-1] - closes[-5]) / closes[-5] * 100, 2)
    else:
        chg_5d = 0
    if n >= 20:
        chg_20d = round((closes[-1] - closes[-20]) / closes[-20] * 100, 2)
    else:
        chg_20d = 0

    # 7. 量价关系综合评估
    volume_price_signals = []
    if vol_analysis.get("recent_divergence"):
        volume_price_signals.append(vol_analysis["recent_divergence"])
    if macd_signal.get("warning"):
        volume_price_signals.append(macd_signal["warning"])

    # 8. 主力行为推断
    smart_money_behavior = _infer_smart_money(
        wyckoff_phase["phase"],
        vol_analysis,
        macd_signal,
        key_levels,
        closes,
        volumes,
    )

    return {
        "stock": {
            "current_price": round(current_price, 2),
            "chg_5d": chg_5d,
            "chg_20d": chg_20d,
            "data_points": n,
            "date_range": f"{dates[0]} ~ {dates[-1]}",
        },
        "macd": {
            "dif": round(dif[-1], 4),
            "dea": round(dea[-1], 4),
            "macd_bar": round(macd_bar[-1], 4),
            "zero_cross": macd_signal,
            "trend": "多头" if dif[-1] > dea[-1] else "空头",
        },
        "ma": {
            "MA20": round(ma_data["MA20"], 2) if ma_data["MA20"] else None,
            "MA60": round(ma_data["MA60"], 2) if ma_data["MA60"] else None,
            "MA20_position": "上方" if ma_data["MA20"] and current_price > ma_data["MA20"] else "下方",
            "MA60_position": "上方" if ma_data["MA60"] and current_price > ma_data["MA60"] else "下方",
        },
        "volume": vol_analysis,
        "key_levels": key_levels,
        "wyckoff_phase": wyckoff_phase,
        "volume_price_signals": volume_price_signals,
        "smart_money_behavior": smart_money_behavior,
        "analysis_time": _now(),
    }


def _infer_smart_money(
    phase: str,
    vol_analysis: dict,
    macd_signal: dict,
    key_levels: dict,
    closes: list[float],
    volumes: list[float],
) -> dict:
    """推断主力资金行为

    基于威科夫理论，结合量价关系推断主力当前意图
    """
    behavior = ""
    intention = ""
    risk_level = ""

    if "吸筹" in phase:
        behavior = "主力在低位偷偷吸筹，通过震荡洗盘获取廉价筹码"
        intention = "吸筹完成后将启动拉升，等待放量突破信号确认"
        risk_level = "低"
    elif "拉升" in phase or "Markup" in phase:
        if "末期" in phase:
            behavior = "主力在高位边拉边出，通过脉冲式拉升诱多"
            intention = "逐步减仓落袋，不追高"
            risk_level = "高"
        else:
            behavior = "主力积极做多，量价配合良好，趋势延续"
            intention = "持仓为主，移动止盈保护利润"
            risk_level = "中"
    elif "派发" in phase:
        behavior = "主力高位出货，通过大单对倒制造活跃假象"
        intention = "坚决减仓，不参与高位博弈"
        risk_level = "高"
    elif "下跌" in phase:
        behavior = "主力已离场或正在砸盘，散户恐慌抛售"
        intention = "空仓观望，等待底部放量信号"
        risk_level = "高"
    elif "底部" in phase:
        behavior = "极端缩量下跌，主力可能在测试底部支撑（Spring）"
        intention = "关注反转信号，不急于抄底"
        risk_level = "高"
    else:
        behavior = "主力方向不明，处于震荡蓄势阶段"
        intention = "轻仓观望，等待方向选择"
        risk_level = "中"

    return {
        "behavior": behavior,
        "intention": intention,
        "risk_level": risk_level,
    }


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()