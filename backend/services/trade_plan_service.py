"""交易计划生成器 —— 基于威科夫分析 + 用户操盘理念

严格遵循用户指定的撤退纪律：
1. 分时盘口背离即撤（量价背离）
2. 移动止盈法（6%/10% 分档）
3. 时间窗口优先于价格（8月13-14日离场）
"""

from services.wyckoff_service import full_wyckoff_analysis


def generate_trade_plan(
    stock: dict,
    klines: list[dict],
    time_window: dict = None,
) -> dict:
    """生成单只股票的交易计划

    参数:
        stock: {"code", "name", "market", "secid"}
        klines: K线数据列表
        time_window: {"start": "2026-08-13", "end": "2026-08-14", "note": "全组合离场窗口"}

    返回: 包含精确格式化的交易计划
    """
    name = stock["name"]
    code = stock["code"]

    # 威科夫分析
    wyckoff = full_wyckoff_analysis(klines)

    if "error" in wyckoff:
        return {
            "stock_code": code,
            "stock_name": name,
            "error": wyckoff["error"],
            "message": wyckoff["message"],
        }

    current_price = wyckoff["stock"]["current_price"]
    key_levels = wyckoff["key_levels"]
    ma_data = wyckoff["ma"]
    vol_analysis = wyckoff["volume"]
    phase = wyckoff["wyckoff_phase"]
    smart_money = wyckoff["smart_money_behavior"]

    # ==================== 计算分批止盈位 ====================

    # 第一撤退点：最近1个月内的高点或高换手筹码密集区
    first_target = _find_first_target(klines, current_price, key_levels)
    # 第二撤退点：更早的高点（60日均线附近或7月初高点）
    second_target = _find_second_target(klines, current_price, key_levels, ma_data)

    # ==================== 计算止损位 ====================
    stop_loss = _find_stop_loss(klines, current_price, key_levels, ma_data)

    # ==================== 主力操盘模式识别 ====================
    mode = _identify_operation_mode(phase, vol_analysis, wyckoff["macd"], current_price, ma_data)

    # ==================== 纪律提醒 ====================
    discipline = _build_discipline(current_price, first_target, second_target, time_window)

    # ==================== 构建输出 ====================
    plan = {
        "stock_code": code,
        "stock_name": name,
        "current_price": current_price,
        "mode": mode,
        "first_target": first_target,
        "second_target": second_target,
        "stop_loss": stop_loss,
        "discipline": discipline,
        "time_window": time_window,
        "wyckoff_summary": {
            "phase": phase["phase"],
            "description": phase["description"],
            "confidence": phase["confidence"],
            "smart_money": smart_money,
        },
        "technical_summary": {
            "macd_trend": wyckoff["macd"]["trend"],
            "ma20": ma_data.get("MA20"),
            "ma60": ma_data.get("MA60"),
            "volume_trend": vol_analysis.get("volume_trend", "持平"),
            "divergence": vol_analysis.get("recent_divergence", ""),
        },
        "formatted": _format_trade_plan(
            name, code, mode, first_target, second_target, stop_loss, time_window
        ),
    }

    return plan


def _find_first_target(
    klines: list[dict],
    current_price: float,
    key_levels: dict,
) -> dict:
    """第一撤退点（获利 8%-10% 或进入阻力区）

    取最近30天内（如7月中旬）的最高价或高换手区
    """
    if len(klines) < 30:
        return {"price": round(current_price * 1.08, 2), "logic": "数据不足，默认 8% 止盈位"}

    # 最近30天（约6周）的最高价
    recent_30 = klines[-30:]
    recent_high = max(k["high"] for k in recent_30)
    high_date = ""
    for k in recent_30:
        if k["high"] == recent_high:
            high_date = k["date"]
            break

    # 如果最近阻力位更近，用它
    nearest_res = key_levels.get("nearest_resistance")
    if nearest_res and nearest_res["price"] < recent_high:
        target_price = nearest_res["price"]
        logic = f"进入{nearest_res['type']}（{target_price}元），主力易出现脉冲式洗盘，建议减仓 1/3"
    elif recent_high > current_price:
        profit_pct = round((recent_high - current_price) / current_price * 100, 1)
        logic = f"接近{high_date}形成的高点{recent_high}元（约{profit_pct}%获利空间），该区域为高换手套牢区，建议减仓 1/3"
        target_price = recent_high
    else:
        target_price = round(current_price * 1.08, 2)
        logic = f"当前价格已超过近期高点，默认 8% 止盈位（{target_price}元），建议减仓 1/3"

    return {"price": round(target_price, 2), "logic": logic}


def _find_second_target(
    klines: list[dict],
    current_price: float,
    key_levels: dict,
    ma_data: dict,
) -> dict:
    """第二撤退点（最终目标位/清仓点）

    取60日均线附近或更早高点（如7月初）
    """
    ma60 = ma_data.get("MA60")

    # 60日均线作为压制
    if ma60 and ma60 > current_price:
        profit_pct = round((ma60 - current_price) / current_price * 100, 1)
        return {
            "price": round(ma60, 2),
            "logic": f"MA60均线压制位（{ma60}元，约{profit_pct}%空间），触及此处无条件分批止盈/清仓，结合时间节点优先离场",
        }

    # 如果已站上MA60，找更早高点（60-90天前）
    if len(klines) >= 60:
        earlier_60 = klines[-90:-30] if len(klines) >= 90 else klines[-60:-30]
        if earlier_60:
            earlier_high = max(k["high"] for k in earlier_60)
            if earlier_high > current_price:
                profit_pct = round((earlier_high - current_price) / current_price * 100, 1)
                return {
                    "price": round(earlier_high, 2),
                    "logic": f"前期高点（{earlier_high}元，约{profit_pct}%空间），作为最终目标位，无条件分批锁盈/清仓",
                }

    # fallback: 15% 止盈
    target = round(current_price * 1.15, 2)
    return {
        "price": target,
        "logic": f"默认 15% 止盈位（{target}元），结合时间窗口优先执行",
    }


def _find_stop_loss(
    klines: list[dict],
    current_price: float,
    key_levels: dict,
    ma_data: dict,
) -> dict:
    """止损位计算

    优先级：放量阳线最低价 > 箱体下沿 > 20日均线
    """
    # 1. 找最近一根放量阳线的最低价
    if len(klines) >= 20:
        volumes = [k["volume"] for k in klines]
        avg_vol = sum(volumes[-20:]) / 20
        for i in range(len(klines) - 1, max(0, len(klines) - 30), -1):
            k = klines[i]
            if k["volume"] > avg_vol * 1.5 and k["close"] >= k["open"]:
                loss_pct = round((current_price - k["low"]) / current_price * 100, 1)
                return {
                    "price": round(k["low"], 2),
                    "logic": f"跌破{k['date']}放量阳线底部（{k['low']}元，-{loss_pct}%），说明主力意图失效，立即止损离场",
                }

    # 2. 最近支撑位
    nearest_sup = key_levels.get("nearest_support")
    if nearest_sup:
        loss_pct = round((current_price - nearest_sup["price"]) / current_price * 100, 1)
        return {
            "price": nearest_sup["price"],
            "logic": f"跌破{nearest_sup['type']}（{nearest_sup['price']}元，-{loss_pct}%），趋势走坏，立即止损",
        }

    # 3. 20日均线
    ma20 = ma_data.get("MA20")
    if ma20:
        loss_pct = round((current_price - ma20) / current_price * 100, 1)
        return {
            "price": round(ma20, 2),
            "logic": f"跌破20日均线（{ma20}元，-{loss_pct}%），趋势走弱，止损离场",
        }

    # fallback: -5%
    return {
        "price": round(current_price * 0.95, 2),
        "logic": "默认 5% 止损线",
    }


def _identify_operation_mode(
    phase: dict,
    vol_analysis: dict,
    macd: dict,
    current_price: float,
    ma_data: dict,
) -> str:
    """识别主力操盘模式（一句话提炼）"""
    phase_name = phase.get("phase", "")
    vol_trend = vol_analysis.get("volume_trend", "持平")
    macd_trend = macd.get("trend", "")
    divergence = vol_analysis.get("recent_divergence", "")
    ma20 = ma_data.get("MA20")
    ma60 = ma_data.get("MA60")

    if "拉升" in phase_name and "末期" not in phase_name:
        if vol_trend == "放量":
            return "主力放量拉升，量价配合良好，处于主升阶段，关注移动止盈保护利润"
        return "主力拉升中，但量能略显不足，警惕冲高回落"
    elif "派发" in phase_name:
        return "大资金高位对倒出货，放量滞涨，脉冲式拉升诱多，建议减仓避险"
    elif "下跌" in phase_name:
        return "主力已离场，下跌趋势延续，不宜抄底，等待底部放量信号"
    elif "吸筹" in phase_name:
        if "启动" in phase_name:
            return "低位放量突破，主力吸筹完成，拉升在即，关注回调加仓机会"
        return "主力在低位震荡吸筹，通过洗盘获取筹码，等待放量突破确认"
    elif "底部" in phase_name:
        return "深跌波段超跌修复，极端缩量，可能出现Spring反弹，关注反转信号"
    elif "震荡" in phase_name:
        if vol_trend == "缩量":
            return "缩量震荡蓄势，方向不明，等待放量突破确认方向"
        return "箱体震荡，板块轮动补涨特征，高抛低吸为主"
    elif divergence:
        return f"量价背离信号：{divergence}，警惕主力意图变化"
    else:
        return "主力行为不明，建议轻仓观望，等待明确信号"


def _build_discipline(
    current_price: float,
    first_target: dict,
    second_target: dict,
    time_window: dict,
) -> list[dict]:
    """构建撤退纪律列表"""
    rules = [
        {
            "rule": "分时量价背离即撤",
            "detail": "冲高过程中，若分时图股价再创新高但成交量柱明显萎缩，或出现连续百手大单向下对倒砸盘，直接手动出局",
            "trigger": "盘中实时监测",
        },
        {
            "rule": "移动止盈（6% 档）",
            "detail": f"盈利超过 6% 后，将止盈位上移至成本线+2%（约{round(current_price * 1.02, 2)}元）",
            "trigger": f"价格 > {round(current_price * 1.06, 2)}元",
        },
        {
            "rule": "移动止盈（10% 档）",
            "detail": f"盈利超过 10% 后，以当日最高点回撤 3% 作为无条件离场线",
            "trigger": f"价格 > {round(current_price * 1.10, 2)}元",
        },
        {
            "rule": "第一撤退点",
            "detail": f"目标价 {first_target['price']}元：{first_target['logic']}",
            "trigger": f"触及 {first_target['price']}元",
        },
        {
            "rule": "第二撤退点（清仓）",
            "detail": f"目标价 {second_target['price']}元：{second_target['logic']}",
            "trigger": f"触及 {second_target['price']}元",
        },
    ]

    if time_window:
        rules.append({
            "rule": "时间窗口离场（铁律）",
            "detail": f"{time_window.get('start', '')} ~ {time_window.get('end', '')} 为最终撤退窗口，届时无论价格如何，一律分批落袋。防范8月中下旬市场二次测试（ST）的回踩风险",
            "trigger": f"进入 {time_window.get('start', '')}",
        })

    return rules


def _format_trade_plan(
    name: str,
    code: str,
    mode: str,
    first_target: dict,
    second_target: dict,
    stop_loss: dict,
    time_window: dict,
) -> str:
    """按用户要求的 Markdown 格式输出交易计划"""
    lines = []
    lines.append(f"**标的名称（代码）：{name}（{code}）**")
    lines.append(f"**主力操盘模式：** {mode}")
    lines.append("")
    lines.append("**分批止盈位（卖出计划）：**")
    lines.append(f"- **第一撤退点：{first_target['price']} 元**（{first_target['logic']}）。")
    lines.append(f"- **第二撤退点（目标位）：{second_target['price']} 元附近**（{second_target['logic']}）。")
    lines.append("")
    lines.append("**风控止损位（风险底线）：**")
    lines.append(f"- **止损线：{stop_loss['price']} 元**（{stop_loss['logic']}）。")
    lines.append("")

    if time_window:
        lines.append("**备注（特殊事件）：**")
        lines.append(
            f"- {time_window.get('start', '')}下午至{time_window.get('end', '')}为最终撤退窗口，"
            f"若有冲高务必落袋。{time_window.get('note', '')}"
        )
        lines.append("")

    lines.append("---")
    return "\n".join(lines)


def generate_all_trade_plans(
    stocks: list[dict],
    klines_map: dict,
    time_window: dict = None,
) -> list[dict]:
    """为所有股票生成交易计划"""
    plans = []
    for stock in stocks:
        klines = klines_map.get(stock["code"], [])
        plan = generate_trade_plan(stock, klines, time_window)
        plans.append(plan)
    return plans