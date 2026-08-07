"""情绪分析模块 —— SnowNLP + 金融词典融合"""
from snownlp import SnowNLP

from nlp.finance_dict import lexicon_score


# 情绪等级对照表：分数 -> 等级标签、专业解释、颜色
SENTIMENT_LEVELS = [
    # (分数下限, 等级标签, 专业解读, 操作建议)
    (70,  "极度看多", "市场情绪高度一致看多，追涨意愿强烈", "注意过热风险，警惕回调"),
    (50,  "强烈看多", "多头情绪占优，资金积极介入", "顺势持有，但不宜追高"),
    (20,  "偏多",      "看多情绪略占优势，分歧较小", "可逐步建仓，分批布局"),
    (-20, "中性震荡",  "多空力量均衡，缺乏明确方向", "观望为主，等待信号明朗"),
    (-50, "偏空",      "看空情绪略占上风，抛压显现", "谨慎为主，控制仓位"),
    (-70, "强烈看空",  "空头情绪占优，资金出逃明显", "减仓避险，勿盲目抄底"),
    (-101,"极度看空",  "恐慌情绪蔓延，踩踏风险极高", "果断离场，等待情绪修复"),
]


def sentiment_level(score: float) -> dict:
    """根据情绪分返回等级信息

    score: -100 ~ 100
    """
    for (threshold, level, interp, advice) in SENTIMENT_LEVELS:
        if score > threshold:
            return {
                "level": level,
                "interpretation": interp,
                "advice": advice,
                "threshold": threshold,
            }
    # 兜底
    return {
        "level": SENTIMENT_LEVELS[-1][1],
        "interpretation": SENTIMENT_LEVELS[-1][2],
        "advice": SENTIMENT_LEVELS[-1][3],
        "threshold": SENTIMENT_LEVELS[-1][0],
    }


def analyze_text(text: str) -> float:
    """对单条文本进行情绪打分，返回 0~1 (0=极空, 0.5=中性, 1=极多)

    融合策略: SnowNLP 基础分 * 0.5 + 金融词典修正 * 0.5
    """
    if not text or len(text.strip()) < 2:
        return 0.5
    try:
        s = SnowNLP(text)
        snow_score = s.sentiments  # 0~1
    except Exception:
        snow_score = 0.5

    lex = lexicon_score(text)  # -1~1
    lex_normalized = (lex + 1) / 2  # 转为 0~1

    # 金融词典命中时给予更高权重
    if abs(lex) > 0.01:
        final = snow_score * 0.4 + lex_normalized * 0.6
    else:
        final = snow_score
    return max(0.0, min(1.0, final))


def analyze_batch(texts: list[str]) -> dict:
    """对一批文本进行情绪聚合分析

    返回:
        {
            "positive": float,   # 看多比例 0~1
            "neutral": float,    # 中性比例 0~1
            "negative": float,   # 看空比例 0~1
            "score": float,      # 综合情绪分 -100~100
            "sample_count": int, # 样本数
            "level": str,        # 情绪等级（极度看多/强烈看多/偏多/中性震荡/偏空/强烈看空/极度看空）
            "interpretation": str, # 专业解读
            "advice": str,       # 操作建议
            "positive_texts": int, # 看多样本数
            "neutral_texts": int,  # 中性样本数
            "negative_texts": int, # 看空样本数
            "formula": str,      # 计算方法说明
        }
    """
    if not texts:
        return {
            "positive": 0.33, "neutral": 0.34, "negative": 0.33,
            "score": 0.0, "sample_count": 0,
            "level": "数据不足",
            "interpretation": "暂无足够评论样本进行情绪分析",
            "advice": "请等待样本积累，或手动刷新重新采集",
            "positive_texts": 0, "neutral_texts": 0, "negative_texts": 0,
            "formula": "SnowNLP情感概率 × 0.4 + 金融词典打分(归一化) × 0.6；综合分=(均分-0.5)×200",
        }
    scores = [analyze_text(t) for t in texts if t and len(t.strip()) > 1]
    if not scores:
        return {
            "positive": 0.33, "neutral": 0.34, "negative": 0.33,
            "score": 0.0, "sample_count": 0,
            "level": "数据不足",
            "interpretation": "暂无有效文本样本",
            "advice": "请等待样本积累，或手动刷新重新采集",
            "positive_texts": 0, "neutral_texts": 0, "negative_texts": 0,
            "formula": "SnowNLP情感概率 × 0.4 + 金融词典打分(归一化) × 0.6；综合分=(均分-0.5)×200",
        }
    pos_count = sum(1 for s in scores if s > 0.6)
    neg_count = sum(1 for s in scores if s < 0.4)
    neu_count = len(scores) - pos_count - neg_count
    total = len(scores)
    avg = sum(scores) / total
    # 综合分 -100 ~ 100
    composite = (avg - 0.5) * 200
    lv = sentiment_level(composite)
    return {
        "positive": round(pos_count / total, 4),
        "neutral": round(neu_count / total, 4),
        "negative": round(neg_count / total, 4),
        "score": round(composite, 2),
        "sample_count": total,
        "level": lv["level"],
        "interpretation": lv["interpretation"],
        "advice": lv["advice"],
        "positive_texts": pos_count,
        "neutral_texts": neu_count,
        "negative_texts": neg_count,
        "formula": "单条得分 = SnowNLP情感概率×0.4 + 金融词典归一化×0.6；综合分 = (样本均分 - 0.5) × 200，区间[-100, 100]",
    }
