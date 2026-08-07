"""股票元数据 —— 行业分类 + 概念标签"""

# 股票代码 → 行业 + 概念映射
STOCK_META = {
    "688048": {"name": "长光华芯", "industry": "半导体", "concepts": ["激光芯片", "光通信", "半导体"]},
    "300566": {"name": "激智科技", "industry": "光学材料", "concepts": ["光学膜", "显示材料", "新材料"]},
    "002025": {"name": "航天电器", "industry": "军工", "concepts": ["连接器", "航天", "军工"]},
    "002460": {"name": "赣锋锂业", "industry": "有色金属", "concepts": ["锂矿", "新能源", "动力电池"]},
    "300806": {"name": "斯迪克", "industry": "新材料", "concepts": ["精密膜", "电子材料", "新材料"]},
    "301015": {"name": "凯旺科技", "industry": "电子元件", "concepts": ["精密组件", "电子元件", "新能源"]},
    "688678": {"name": "福立旺", "industry": "精密零部件", "concepts": ["精密制造", "新能源", "光伏"]},
    "688638": {"name": "迅捷兴", "industry": "半导体", "concepts": ["PCB", "半导体", "电子元件"]},
    "603588": {"name": "高能环境", "industry": "环保", "concepts": ["土壤修复", "环保", "固废处理"]},
    "600703": {"name": "三安光电", "industry": "半导体", "concepts": ["LED", "化合物半导体", "光通信"]},
}

# 行业关键词映射（行业 → 相关关键词列表，要求2字以上）
INDUSTRY_KEYWORDS = {
    "半导体": ["芯片", "半导体", "晶圆", "光刻", "刻蚀", "薄膜", "沉积", "CVD", "PVD", "EDA", "IP核", "设计工具", "封测", "封装", "测试", "ASIC", "FPGA", "功率半导体", "IGBT", "MOSFET", "化合物半导体", "GaN", "SiC", "LED芯片"],
    "光学材料": ["光学膜", "背光", "显示材料", "液晶", "偏振片", "扩散膜", "增亮膜", "反射膜", "ITO", "导电膜", "柔性显示", "OLED", "LCD", "MiniLED", "MicroLED"],
    "军工": ["航天", "航空", "国防", "军工", "导弹", "卫星", "雷达", "导航", "连接器", "军用", "航空航天", "军民融合", "低空经济", "无人机"],
    "有色金属": ["锂矿", "电解铜", "黄金", "白银", "稀土", "稀有金属", "有色金属", "矿产", "采矿", "选矿", "湿法冶炼", "正极材料", "前驱体"],
    "新材料": ["新材料", "高分子", "复合材料", "纳米材料", "碳纤维", "陶瓷", "精密膜", "电子材料", "功能材料", "结构材料", "热塑性", "热固性"],
    "电子元件": ["电容", "电阻", "电感", "连接器", "继电器", "开关", "传感器", "MEMS", "晶振", "滤波", "PCB", "印制板", "FPC", "柔性板", "HDI", "IC载板"],
    "精密零部件": ["精密加工", "CNC", "数控机床", "光学零件", "机械零件", "结构件", "外壳", "中框", "精密模具", "注塑", "冲压", "阳极氧化", "电镀"],
    "环保": ["环保", "土壤修复", "固废处理", "危废", "污水处理", "废气处理", "碳排放", "碳中和", "绿色能源", "节能", "资源循环"],
    "光通信": ["光纤", "光缆", "光模块", "光通信", "5G", "基站", "数据中心", "IDC", "云计算", "算力", "AI芯片", "光收发", "DSP"],
    "新能源": ["锂电池", "动力电池", "储能", "光伏", "风电", "氢能", "新能源汽车", "充电桩", "换电", "BMS", "PCS", "逆变器", "正极", "负极", "隔膜", "电解液"],
}


def get_stock_industry(code: str) -> str:
    """获取股票所属行业"""
    meta = STOCK_META.get(code, {})
    return meta.get("industry", "")


def get_stock_concepts(code: str) -> list[str]:
    """获取股票概念标签"""
    meta = STOCK_META.get(code, {})
    return meta.get("concepts", [])


def match_industries(text: str) -> list[str]:
    """根据文本内容匹配相关行业（仅匹配2字以上关键词，避免子串误匹配）"""
    matched = set()
    text_lower = text.lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if len(kw) < 2:
                continue
            if kw.lower() in text_lower:
                matched.add(industry)
                break
    return sorted(matched)


def analyze_sentiment_label(text: str) -> tuple[str, str]:
    """分析文本情感，返回 (label, text)
    label: positive(利好) / negative(利空) / neutral(中性)
    """
    from nlp.finance_dict import POSITIVE_WORDS, NEGATIVE_WORDS

    pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)

    if pos_count > neg_count:
        return "positive", "利好"
    elif neg_count > pos_count:
        return "negative", "利空"
    else:
        return "neutral", "中性"


# 新闻关键词黑名单（宁缺毋滥）
# 这些词在公告/财报中出现频率极高但信息量≈0
KEYWORD_BLACKLIST = {
    # —— 公告模板套话 ——
    "公告", "关于", "公司", "公告书", "通知", "决议", "议案", "审议",
    "管理", "制度", "规定", "办法", "规则", "条例", "事项", "说明",
    "报告", "报告书", "摘要", "全文", "修订", "修订稿", "补充",
    # —— 公司治理套话 ——
    "董事", "监事", "高级", "人员", "股东", "大会", "会议", "资料",
    "持股", "变动", "信息", "披露", "事务", "财务", "审计", "对外",
    "投资", "募集", "专户", "注销", "督导", "保荐", "发行", "上市",
    "回购", "前十", "十大", "及前", "无限售", "限售", "条件", "股东会",
    "议事", "治理", "内控", "风险", "合规", "考核",
    "委员会", "管理层", "高管", "核心",
    # —— 股东会/董事会程序词 ——
    "临时", "召开", "第三次", "第二次", "第一次", "第四次", "第五次",
    "届次", "届", "次", "现场", "投票", "表决", "选举", "任命",
    "全资", "控股", "参股", "担保", "提供", "质押", "冻结",
    "意见书", "法律", "律师", "见证", "公证",
    "授权", "委托", "代理", "代表", "权证",
    "议案", "提案", "动议", "表决权",
    "独立", "独立董事", "专门", "战略",
    "候选人", "提名", "换届", "连任", "离任", "辞任", "罢免",
    # —— 财报模板词 ——
    "营业收入", "营业成本", "归属于", "净利润", "扣非", "每股", "净资产",
    "现金流", "资产负债", "利润表", "现金流量", "所有者权益", "合并",
    "母公司", "子公司", "分部", "抵消", "报表", "附注",
    "预增", "预减", "预亏", "预盈", "扭亏", "减亏",
    # —— 时间/数字词 ——
    "年度", "季度", "月度", "半年度", "上半年", "下半年",
    "第一季度", "第二季度", "第三季度", "第四季度",
    "一季度", "二季度", "三季度", "四季度",
    "本期", "上期", "同期", "报告期", "报告期内",
    "今年", "去年", "今日", "昨日",
    # —— 常见动词（无信息量） ——
    "进行", "完成", "实施", "开展", "推进", "落实", "执行",
    "通过", "批准", "同意", "决定", "审议通过",
    "签订", "签署", "协议", "合同",
    # —— 常见形容词/副词 ——
    "进一步", "全面", "深入", "积极", "有效", "持续", "稳步",
    # —— 其他噪音 ——
    "万元", "亿元", "元", "个", "项", "条", "次",
    "有限", "有限责任", "有限责任公司", "股份有限公司", "有限公司", "集团",
    "技术", "人员", "相关", "情况", "如下", "详见",
    "资金", "说明会", "创板", "科创板", "主板", "创业板", "北交所",
    "预告", "预增", "预减", "预亏", "预盈", "快报",
    "闲置", "补充", "流动", "流动资金", "核查", "意见",
    "管理制度", "议事规则", "换届选举", "第三届", "第十一届",
    "H股", "A股", "B股", "G股", "红筹",
    "证券", "联合证券", "华泰", "中信", "国泰君安",
    "管理人员", "股份", "董事会", "监事会", "暂时", "延期",
    "光电", "光电技术",
}


def _is_bad_kw(kw: str, stock_name: str = "") -> bool:
    """判断关键词是否应该过滤（宁缺毋滥）

    多层防御：
    1. 黑名单（公告套话、财报模板词等）
    2. 股票名本身/简称/子串（如"高能"来自"高能环境"）
    3. 结构化过滤：任意位置含连词/介词/助词字符 -> 碎片，reject
    4. 序数词碎片（"第X次""第X届"）
    """
    import re
    if not kw or len(kw) < 2:
        return True
    if kw in KEYWORD_BLACKLIST:
        return True
    # 纯数字
    if kw.isdigit():
        return True
    # 股票名本身或其子串（如"高能"来自"高能环境"，"光华"来自"长光华芯"）
    if stock_name:
        if kw == stock_name:
            return True
        if len(kw) <= 3 and kw in stock_name:
            return True
        # 股票名前2-3字简称
        if len(stock_name) >= 3 and kw == stock_name[:2]:
            return True
        if len(stock_name) >= 4 and kw == stock_name[:3]:
            return True
    # 结构化过滤：任意位置含连词/介词/助词字符 -> 碎片，reject
    # （"及前""及其""的股东""与公司"等碎片会被这里 catch）
    # 白名单豁免：含连词字符但是固定术语的词（如"碳中和"）
    _bad_chars = "及与和或同对于在的了之等"
    _structural_whitelist = {"碳中和"}
    if kw not in _structural_whitelist and any(c in _bad_chars for c in kw):
        return True
    # 含标点
    if any(c in kw for c in "，。、；：！？·…—（）()【】[]《》<>\"'"):
        return True
    # "第X次""第X届""第X期"等序数词碎片
    if re.match(r'^第[一二三四五六七八九十百千万零\d]+[次届期次会议]', kw):
        return True
    # "第X次" 单独出现
    if re.match(r'^第[一二三四五六七八九十百千万零\d]+次$', kw):
        return True
    return False


def extract_smart_keywords(text: str, topk: int = 4, stock_name: str = "") -> list[dict]:
    """智能关键词提取（宁缺毋滥版），返回带类型的关键词列表

    参数:
        text: 新闻全文（标题+摘要）
        topk: 最多返回几个关键词（默认4）
        stock_name: 股票名称，用于过滤股票名简称

    返回格式：[
        {"word": "芯片", "type": "industry"},
        {"word": "突破", "type": "positive"},
    ]

    分3个优先级提取：
    1. 行业专属关键词 (industry)  —— 信息量最高，最多2个
    2. 金融情感关键词 (positive/negative) —— 利好利空信号，最多2个
    3. jieba TF-IDF (general) —— 严格过滤后补充，宁缺毋滥
    """
    from nlp.keywords import extract_keywords
    from nlp.finance_dict import POSITIVE_WORDS, NEGATIVE_WORDS

    keywords = []
    seen = set()

    def _add(word, type_):
        if word in seen or _is_bad_kw(word, stock_name):
            return
        keywords.append({"word": word, "type": type_})
        seen.add(word)

    # 1. 行业关键词（最多2个）
    industry_added = 0
    for industry, industry_kws in INDUSTRY_KEYWORDS.items():
        if industry_added >= 2:
            break
        for kw in industry_kws:
            if len(keywords) >= topk or industry_added >= 2:
                break
            if kw in text and len(kw) >= 2:
                _add(kw, "industry")
                industry_added += 1

    # 2. 金融情感关键词（最多2个）
    sent_added = 0
    for w in POSITIVE_WORDS.keys():
        if len(keywords) >= topk or sent_added >= 2:
            break
        if w in text and len(w) >= 2:
            _add(w, "positive")
            sent_added += 1
    for w in NEGATIVE_WORDS.keys():
        if len(keywords) >= topk or sent_added >= 2:
            break
        if w in text and len(w) >= 2:
            _add(w, "negative")
            sent_added += 1

    # 3. jieba补充（宁缺毋滥：严格过滤，凑不够就少返回，不拿垃圾凑数）
    if len(keywords) < topk:
        extra = extract_keywords(text, topk=topk * 8)  # 多取候选来过滤
        for w in extra:
            if len(keywords) >= topk:
                break
            _add(w, "general")

    # 宁缺毋滥：如果一条行业/情感词都没有，说明是纯套话公告（如"前十大股东情况"），
    # 不拿 general 碎片凑数，直接返回空
    has_meaningful = any(k["type"] in ("industry", "positive", "negative") for k in keywords)
    if not has_meaningful:
        return []

    return keywords[:topk]


def keyword_words_only(tagged_keywords: list[dict]) -> list[str]:
    """从带类型的关键词中仅提取文字部分（兼容旧接口）"""
    return [k["word"] for k in tagged_keywords] if tagged_keywords else []
