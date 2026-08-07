"""关键词提取模块 —— 基于 jieba（词性标注 + 结构化过滤）"""
import jieba
import jieba.analyse

from nlp.finance_dict import STOPWORDS

# 预加载
jieba.initialize()

# 只接受名词类词性，从根本上过滤"及前"(连词碎片)、"十大"(缩略语)、"无限"(动词)等噪音
# n:普通名词  nr:人名  ns:地名  nt:机构名  nz:其他专名  vn:名动词  eng:英文
ALLOW_POS = ("n", "nr", "ns", "nt", "nz", "vn", "eng")

# 结构化过滤：含这些字符的 token 一律 reject（连词/介词/助词碎片等）
# 注意：只含连词/介词/助词，不含方位词（前/后/上/下/中/内/外），避免误伤"前海""后端"等合法名词
_BAD_CHARS = set("及与和或同对于在的了之等")


def _is_clean_token(w: str) -> bool:
    """token 是否"干净"：不含连词/介词/助词/方位词等碎片字符"""
    if not w:
        return False
    # 含任意一个连词/介词/助词字符 -> 碎片，reject
    if any(c in _BAD_CHARS for c in w):
        return False
    # 含标点
    if any(c in w for c in "，。、；：！？·…—（）()【】[]《》<>\"'"):
        return False
    return True


def extract_keywords(text: str, topk: int = 5) -> list[str]:
    """从文本中提取关键词，返回去停用词后的列表

    采用"词性标注 + 结构化过滤"双重过滤：
    1. allowPOS 限定名词类，自动剔除"及前""十大""无限"等碎片
    2. 结构化过滤剔除含连词/介词字符的 token
    """
    if not text or len(text.strip()) < 2:
        return []
    # 使用 TF-IDF 算法 + 词性限定
    raw = jieba.analyse.extract_tags(
        text, topK=topk * 4, withWeight=False, allowPOS=ALLOW_POS
    )
    result = []
    for w in raw:
        w = w.strip()
        if not w or w in STOPWORDS or len(w) < 2:
            continue
        if w.isdigit():
            continue
        if not _is_clean_token(w):
            continue
        result.append(w)
        if len(result) >= topk:
            break
    return result


def extract_keywords_from_batch(texts: list[str], topk: int = 10) -> list[tuple]:
    """从一批文本中提取关键词（带权重），用于词云"""
    combined = " ".join(texts)
    raw = jieba.analyse.extract_tags(
        combined, topK=topk * 4, withWeight=True, allowPOS=ALLOW_POS
    )
    result = []
    for w, weight in raw:
        w = w.strip()
        if not w or w in STOPWORDS or len(w) < 2 or w.isdigit():
            continue
        if not _is_clean_token(w):
            continue
        result.append({"name": w, "value": round(weight * 100, 2)})
        if len(result) >= topk:
            break
    return result
