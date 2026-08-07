/* ===== 股票看板平台 · 前端逻辑 · 亮色主题 ===== */

// 后端 API 地址 —— 部署时修改此处指向你的后端
const API = '/api';

let currentStock = null;
let currentPeriod = 'daily';
let klineCharts = {};
let sentimentCharts = {};
let autoRefreshTimer = null;
let stocks = [];
let newsStockFilter = 'all';

// ===== 工具函数 =====
const $ = (id) => document.getElementById(id);
const fmt = (n, d = 2) => (n === null || n === undefined || isNaN(n)) ? '--' : Number(n).toFixed(d);
const fmtVol = (v) => {
    if (!v) return '--';
    if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿';
    if (v >= 1e4) return (v / 1e4).toFixed(2) + '万';
    return String(v);
};
const fmtMoney = (v) => {
    if (!v) return '--';
    const abs = Math.abs(v);
    const sign = v < 0 ? '-' : '';
    if (abs >= 1e8) return sign + (abs / 1e8).toFixed(2) + '亿';
    if (abs >= 1e4) return sign + (abs / 1e4).toFixed(2) + '万';
    return sign + abs.toFixed(0);
};
const fmtTime = (iso) => {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        return d.toLocaleString('zh-CN', {hour12: false});
    } catch { return iso; }
};
const escapeHtml = (s) => {
    if (s === null || s === undefined) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
};

// 亮色主题ECharts公共配置
const LIGHT_THEME = {
    textColor: '#1a2233',
    axisLine: '#d0d7de',
    axisLabel: '#6b7785',
    splitLine: '#eef1f5',
    tooltipBg: 'rgba(255,255,255,0.96)',
    tooltipBorder: '#e4e8ef',
    tooltipText: '#1a2233',
};

async function api(path, options = {}) {
    const res = await fetch(API + path, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({detail: res.statusText}));
        throw new Error(err.detail || '请求失败');
    }
    return res.json();
}

// ===== 初始化 =====
async function init() {
    bindEvents();
    initSidebar();
    try {
        stocks = await loadStocks();
        await loadQuotes();
        await loadKlineGrid();
        await loadAllNews();
        await loadAllSentiment();
        loadWyckoffAll();
        loadTradePlansAll();
        setInterval(loadQuotes, 30000);
        setupAutoRefresh();
    } catch (e) {
        // 后端不可用时显示提示
        console.log('后端未连接，展示静态演示版');
        renderDemoMode();
    }
    window.addEventListener('resize', () => {
        Object.values(klineCharts).forEach(c => c && c.resize());
        Object.values(sentimentCharts).forEach(c => c && c.resize());
    });
}

function renderDemoMode() {
    const banner = document.createElement('div');
    banner.style.cssText = 'background:#fef3c7;color:#92400e;padding:12px 20px;text-align:center;font-size:14px;border-bottom:1px solid #fcd34d;';
    banner.innerHTML = '⚠️ 后端服务未连接 &mdash; 当前为静态演示版。如需完整功能，请启动后端并修改 <code>js/app.js</code> 中的 <code>API</code> 地址。';
    document.body.insertBefore(banner, document.body.firstChild);

    $('quotesGrid').innerHTML = renderDemoQuotes();
    $('newsList').innerHTML = renderDemoNews();
    $('wyckoffGrid').innerHTML = renderDemoWyckoff();
    $('tradePlanGrid').innerHTML = renderDemoTradePlans();
    $('sentimentOverview').innerHTML = renderDemoSentiment();
    $('serverInfo').textContent = '演示模式';
}

function renderDemoQuotes() {
    const demos = [
        {name:'贵州茅台',code:'600519',price:1780.50,change:15.20,change_pct:0.86,high:1795,low:1765,volume:3850000},
        {name:'宁德时代',code:'300750',price:210.30,change:-3.50,change_pct:-1.64,high:215,low:208,volume:12500000},
        {name:'比亚迪',  code:'002594',price:285.60,change:5.80,change_pct:2.07,high:288,low:278,volume:8900000},
        {name:'招商银行',code:'600036',price:38.20,change:-0.45,change_pct:-1.16,high:38.9,low:37.8,volume:52000000},
        {name:'中芯国际',code:'688981',price:52.80,change:1.20,change_pct:2.33,high:53.5,low:51.2,volume:18500000},
        {name:'中国平安',code:'601318',price:48.50,change:0.30,change_pct:0.62,high:49.0,low:47.8,volume:42000000},
    ];
    return demos.map(q => {
        const cls = q.change_pct > 0 ? 'up' : q.change_pct < 0 ? 'down' : 'flat';
        const arrow = q.change_pct > 0 ? '▲' : q.change_pct < 0 ? '▼' : '—';
        return `
            <div class="quote-card">
                <div class="quote-name">${q.name}</div>
                <div class="quote-code">${q.code}</div>
                <div class="quote-price ${cls}">${fmt(q.price)}</div>
                <div class="quote-change ${cls}">${arrow} ${fmt(Math.abs(q.change))} (${fmt(Math.abs(q.change_pct))}%)</div>
                <div class="quote-meta">
                    <span>高 ${fmt(q.high)}</span>
                    <span>低 ${fmt(q.low)}</span>
                    <span>量 ${fmtVol(q.volume)}</span>
                </div>
            </div>`;
    }).join('');
}

function renderDemoNews() {
    const demos = [
        {title:'央行宣布降准0.5个百分点，释放长期流动性',source:'央行',time:'2026-08-06 10:30',keywords:['降准','流动性','货币政策']},
        {title:'北向资金今日净流入超80亿元，连续5日净买入',source:'东方财富',time:'2026-08-06 10:15',keywords:['北向资金','净流入','外资']},
        {title:'新能源板块集体走强，光伏龙头业绩超预期',source:'证券时报',time:'2026-08-06 09:50',keywords:['新能源','光伏','业绩']},
        {title:'贵州茅台发布半年报：营收同比增长12%',source:'巨潮资讯',time:'2026-08-06 09:30',keywords:['茅台','半年报','营收']},
        {title:'AI概念股持续活跃，算力需求超预期增长',source:'财联社',time:'2026-08-06 09:00',keywords:['AI','算力','概念股']},
    ];
    return demos.map(n => {
        const kw = n.keywords.map(k => `<span class="keyword-tag kw-general">${k}</span>`).join('');
        return `
            <div class="news-item">
                <div class="news-meta">
                    <span class="news-source">${n.source}</span>
                    <span class="news-time">${n.time}</span>
                </div>
                <div class="news-title">${n.title}</div>
                <div class="news-keywords">${kw}</div>
            </div>`;
    }).join('');
}

function renderDemoWyckoff() {
    const demos = [
        {name:'贵州茅台',code:'600519',phase:'上涨拉升',price:1780.50,chg5d:0.86,macd:'多头',dif:12.35,ma20:1765,ma60:1700,vol:'温和放量',support:'1750',resist:'1820',behavior:'主力吸筹后拉升',intention:'继续持有',risk:'低'},
        {name:'宁德时代',code:'300750',phase:'二次探底',price:210.30,chg5d:-1.64,macd:'空头',dif:-2.10,ma20:215,ma60:225,vol:'缩量下跌',support:'205',resist:'220',behavior:'底部震仓洗盘',intention:'观望等待',risk:'中'},
        {name:'比亚迪',code:'002594',phase:'上涨拉升',price:285.60,chg5d:2.07,macd:'多头',dif:8.20,ma20:278,ma60:265,vol:'放量上涨',support:'278',resist:'295',behavior:'主力资金持续流入',intention:'继续持有',risk:'低'},
        {name:'招商银行',code:'600036',phase:'区间震荡',price:38.20,chg5d:-1.16,macd:'震荡',dif:0.15,ma20:38.5,ma60:39.0,vol:'缩量',support:'37.5',resist:'39.5',behavior:'机构调仓换股',intention:'轻仓观望',risk:'中'},
    ];
    return demos.map(d => `
        <div class="wyckoff-card">
            <div class="wyckoff-card-header">
                <span class="wk-name">${d.name}<span class="wk-code">${d.code}</span></span>
                <span class="wk-phase phase-markup">${d.phase}</span>
            </div>
            <div class="wk-row"><span class="wk-label">当前价</span><span class="wk-value">${fmt(d.price)}</span></div>
            <div class="wk-row"><span class="wk-label">5日涨跌</span><span class="wk-value ${d.chg5d>=0?'up':'down'}">${d.chg5d>=0?'+':''}${fmt(d.chg5d)}%</span></div>
            <div class="wk-row"><span class="wk-label">MACD趋势</span><span class="wk-value">${d.macd} | DIF: ${fmt(d.dif,4)}</span></div>
            <div class="wk-row"><span class="wk-label">MA20 / MA60</span><span class="wk-value">${fmt(d.ma20)} / ${fmt(d.ma60)}</span></div>
            <div class="wk-row"><span class="wk-label">量能趋势</span><span class="wk-value">${d.vol}</span></div>
            <div class="wk-levels">
                <div class="wk-level-item"><span class="wk-level-type">支撑</span><span class="wk-level-price support">${fmt(d.support)}</span></div>
                <div class="wk-level-item"><span class="wk-level-type">阻力</span><span class="wk-level-price resistance">${fmt(d.resist)}</span></div>
            </div>
            <div class="wk-smart-money">
                <div>${d.behavior}</div>
                <div class="wk-intention">${d.intention}<span class="wk-risk risk-low">风险${d.risk}</span></div>
            </div>
        </div>`).join('');
}

function renderDemoTradePlans() {
    const demos = [
        {name:'贵州茅台',code:'600519',mode:'机构抱团拉升',first:1820,firstLogic:'前期高点压力位',second:1900,secondLogic:'历史新高目标',stop:1720,stopLogic:'跌破60日均线止损',rules:[{rule:'分批止盈',detail:'达到第一目标位减仓50%，剩余仓位跟踪止盈'},{rule:'移动止损',detail:'股价每上涨5%，止损位上移3%'}]},
        {name:'比亚迪',code:'002594',mode:'趋势加速拉升',first:295,firstLogic:'布林带上轨压力',second:310,secondLogic:'机构目标价',stop:270,stopLogic:'跌破20日均线止损',rules:[{rule:'分批止盈',detail:'达到第一目标位减仓30%，第二目标位清仓'},{rule:'时间止损',detail:'若5个交易日内未突破当前高点，减仓50%'}]},
    ];
    return demos.map(p => `
        <div class="trade-plan-card">
            <div class="tp-header">${p.name} (${p.code})</div>
            <div class="tp-mode"><strong>主力操盘模式：</strong>${p.mode}</div>
            <div class="tp-section">
                <div class="tp-section-title">分批止盈位</div>
                <div class="tp-item target"><strong>第一撤退点：</strong><span class="tp-price">${fmt(p.first)} 元</span><span class="tp-logic">${p.firstLogic}</span></div>
                <div class="tp-item target"><strong>第二撤退点（目标位）：</strong><span class="tp-price">${fmt(p.second)} 元</span><span class="tp-logic">${p.secondLogic}</span></div>
            </div>
            <div class="tp-section">
                <div class="tp-section-title">风控止损位</div>
                <div class="tp-item stop"><strong>止损线：</strong><span class="tp-price">${fmt(p.stop)} 元</span><span class="tp-logic">${p.stopLogic}</span></div>
            </div>
            <div class="tp-discipline">
                <div class="tp-discipline-title">撤退纪律</div>
                ${p.rules.map(r => `<div class="tp-rule"><span class="tp-rule-name">${r.rule}：</span><span class="tp-rule-detail">${r.detail}</span></div>`).join('')}
            </div>
        </div>`).join('');
}

function renderDemoSentiment() {
    return `
        <div class="overview-grid">
            <div class="overview-card">
                <div class="ov-name"><span>贵州茅台</span><span class="code">600519</span></div>
                <span class="ov-level ov-level-pos">偏多</span>
                <div class="ov-score" style="color:#dc2626;">+35.2</div>
                <div class="ov-meta">
                    <span style="color:#dc2626;"><b>看多</b> 45条(65%)</span><br/>
                    <span style="color:#475569;"><b>中性</b> 15条(22%)</span><br/>
                    <span style="color:#059669;"><b>看空</b> 9条(13%)</span>
                </div>
                <div class="ov-meta" style="margin-top:4px;padding-top:4px;border-top:1px dashed #e5e7eb;"><b>建议：</b>市场情绪偏乐观，短线可持有</div>
            </div>
            <div class="overview-card">
                <div class="ov-name"><span>宁德时代</span><span class="code">300750</span></div>
                <span class="ov-level ov-level-neg">偏空</span>
                <div class="ov-score" style="color:#059669;">-28.5</div>
                <div class="ov-meta">
                    <span style="color:#dc2626;"><b>看多</b> 12条(18%)</span><br/>
                    <span style="color:#475569;"><b>中性</b> 18条(27%)</span><br/>
                    <span style="color:#059669;"><b>看空</b> 36条(55%)</span>
                </div>
                <div class="ov-meta" style="margin-top:4px;padding-top:4px;border-top:1px dashed #e5e7eb;"><b>建议：</b>短期承压，建议观望等待企稳信号</div>
            </div>
        </div>
        <div class="overview-legend">
            <b>情绪指数刻度：</b>
            <span class="legend-item"><span class="legend-dot dot-strong-up"></span>+70~+100 极度看多</span>
            <span class="legend-item"><span class="legend-dot dot-up"></span>+50~+70 强烈看多</span>
            <span class="legend-item"><span class="legend-dot dot-mild-up"></span>+20~+50 偏多</span>
            <span class="legend-item"><span class="legend-dot dot-neutral"></span>-20~+20 中性震荡</span>
            <span class="legend-item"><span class="legend-dot dot-mild-down"></span>-50~-20 偏空</span>
            <span class="legend-item"><span class="legend-dot dot-down"></span>-70~-50 强烈看空</span>
            <span class="legend-item"><span class="legend-dot dot-strong-down"></span>-100~-70 极度看空</span>
            &nbsp;|&nbsp;
            <b>计算方法：</b>
            <span>单条文本得分 = SnowNLP情感概率 × 0.4 + 金融词典归一化 × 0.6；综合分 = (样本均分 - 0.5) × 200</span>
            &nbsp;|&nbsp;
            <b>说明：</b>
            <span>当前为演示数据，连接后端后可获取真实情绪分析</span>
        </div>`;
}

function bindEvents() {
    $('refreshBtn').addEventListener('click', onRefresh);
    $('settingsBtn').addEventListener('click', openSettings);
    $('manageBtn').addEventListener('click', openManage);
    $('saveSettingsBtn').addEventListener('click', saveSettings);
    $('addStockBtn').addEventListener('click', addStock);
    $('analyzeBtn').addEventListener('click', analyzeSentiment);
    $('topNSelect').addEventListener('change', () => { loadAllNews(); });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            loadKlineGrid();
            if (currentStock) loadKlineDetail(currentStock.code, currentPeriod);
        });
    });
}

// ===== 侧边栏导航 =====
function initSidebar() {
    const navItems = document.querySelectorAll('#sidebarNav .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            const panel = item.dataset.panel;
            const panels = document.querySelectorAll('.main-content .panel[data-panel]:not(#stockDetailPanel)');

            panels.forEach(p => {
                if (p.dataset.panel === panel) {
                    p.classList.remove('hidden');
                } else {
                    p.classList.add('hidden');
                }
            });

            // 详情面板：仅在行情/K线板块显示，其余板块强制隐藏
            if (panel === 'quotes' || panel === 'kline') {
                if (currentStock) {
                    $('stockDetailPanel').style.display = 'block';
                } else {
                    $('stockDetailPanel').style.display = 'none';
                }
            } else {
                $('stockDetailPanel').style.display = 'none';
            }

            setTimeout(() => {
                Object.values(klineCharts).forEach(c => c && c.resize());
                Object.values(sentimentCharts).forEach(c => c && c.resize());
            }, 100);
        });
    });
}

// ===== 股票列表 =====
async function loadStocks() {
    try {
        const data = await api('/stocks');
        stocks = data.stocks || [];
        return stocks;
    } catch (e) {
        console.error('加载股票失败', e);
        return [];
    }
}

// ===== 实时行情卡片 =====
async function loadQuotes() {
    try {
        const data = await api('/quote/realtime');
        const grid = $('quotesGrid');
        if (!data.quotes || data.quotes.length === 0) {
            grid.innerHTML = '<div class="loading-placeholder">暂无行情数据</div>';
            return;
        }
        grid.innerHTML = data.quotes.map(q => {
            const cls = q.change_pct > 0 ? 'up' : q.change_pct < 0 ? 'down' : 'flat';
            const arrow = q.change_pct > 0 ? '▲' : q.change_pct < 0 ? '▼' : '—';
            const active = currentStock && currentStock.code === q.code ? 'active' : '';
            return `
                <div class="quote-card ${active}" onclick="selectStock('${q.code}')">
                    <div class="quote-name">${q.stock_name || q.name}</div>
                    <div class="quote-code">${q.code}</div>
                    <div class="quote-price ${cls}">${fmt(q.price)}</div>
                    <div class="quote-change ${cls}">${arrow} ${fmt(Math.abs(q.change))} (${fmt(Math.abs(q.change_pct))}%)</div>
                    <div class="quote-meta">
                        <span>高 ${fmt(q.high)}</span>
                        <span>低 ${fmt(q.low)}</span>
                        <span>量 ${fmtVol(q.volume)}</span>
                    </div>
                </div>`;
        }).join('');
        $('quoteUpdateTime').textContent = '更新于 ' + new Date().toLocaleTimeString('zh-CN', {hour12: false});
    } catch (e) {
        console.error('加载行情失败', e);
        $('quotesGrid').innerHTML = '<div class="loading-placeholder">行情加载失败</div>';
    }
}

// ===== 多股K线网格 =====
async function loadKlineGrid() {
    const grid = $('klineGrid');
    grid.innerHTML = '';
    if (stocks.length === 0) {
        grid.innerHTML = '<div class="loading-placeholder" style="grid-column:1/-1;">请先添加关注的股票</div>';
        return;
    }
    stocks.forEach(s => {
        const card = document.createElement('div');
        card.className = 'kline-card';
        card.id = `kline-card-${s.code}`;
        card.onclick = () => selectStock(s.code);
        card.innerHTML = `
            <div class="kline-card-header">
                <div>
                    <span class="kline-card-title">${s.name} <small>${s.code}</small></span>
                </div>
                <div>
                    <div class="kline-card-price" id="price-${s.code}">--</div>
                    <div class="kline-card-change" id="change-${s.code}">--</div>
                </div>
            </div>
            <div id="mini-${s.code}" class="kline-chart-mini"></div>
        `;
        grid.appendChild(card);
    });

    const promises = stocks.map(async (s) => {
        try {
            const data = await api(`/quote/${s.code}/kline?period=${currentPeriod}`);
            const klines = data.kline || [];
            const chartDom = document.getElementById(`mini-${s.code}`);
            if (!chartDom || klines.length === 0) return;

            if (klineCharts[s.code]) {
                klineCharts[s.code].dispose();
            }
            const chart = echarts.init(chartDom);
            klineCharts[s.code] = chart;

            const recent = klines.slice(-30);
            const dates = recent.map(k => k.date);
            const ohlc = recent.map(k => [k.open, k.close, k.low, k.high]);
            const volumes = recent.map(k => k.volume);
            const last = klines[klines.length - 1];
            if (last) {
                const chg = last.close - last.open;
                const chgPct = (chg / last.open) * 100;
                const cls = chg > 0 ? 'up' : chg < 0 ? 'down' : 'flat';
                const arrow = chg > 0 ? '▲' : chg < 0 ? '▼' : '—';
                const priceEl = document.getElementById(`price-${s.code}`);
                const chgEl = document.getElementById(`change-${s.code}`);
                if (priceEl) priceEl.innerHTML = `<span class="${cls}">${fmt(last.close)}</span>`;
                if (chgEl) chgEl.innerHTML = `<span class="${cls}">${arrow} ${fmt(Math.abs(chg),2)} ${fmt(Math.abs(chgPct))}%</span>`;
            }

            chart.setOption({
                backgroundColor: 'transparent',
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {type: 'cross', lineStyle: {color: '#d0d7de'}},
                    backgroundColor: LIGHT_THEME.tooltipBg,
                    borderColor: LIGHT_THEME.tooltipBorder,
                    textStyle: {color: LIGHT_THEME.tooltipText, fontSize: 11},
                    formatter: (params) => {
                        const k = params[0];
                        const v = params[1];
                        if (!k) return '';
                        return `${k.axisValue}<br/>开: ${fmt(k.data[1])} 收: ${fmt(k.data[2])}<br/>低: ${fmt(k.data[3])} 高: ${fmt(k.data[4])}<br/>量: ${fmtVol(v?.data || 0)}`;
                    }
                },
                grid: [
                    {left: '8%', right: '3%', top: '8%', height: '55%'},
                    {left: '8%', right: '3%', top: '68%', height: '22%'}
                ],
                xAxis: [
                    {type: 'category', data: dates, scale: true, boundaryGap: false,
                     axisLine: {lineStyle: {color: LIGHT_THEME.axisLine}},
                     axisLabel: {color: LIGHT_THEME.axisLabel, fontSize: 10, show: false},
                     axisTick: {show: false}},
                    {type: 'category', gridIndex: 1, data: dates, axisLabel: {show: false}, axisLine: {show: false}}
                ],
                yAxis: [
                    {scale: true, splitLine: {lineStyle: {color: LIGHT_THEME.splitLine}},
                     axisLabel: {color: LIGHT_THEME.axisLabel, fontSize: 10},
                     axisLine: {show: false}, axisTick: {show: false}},
                    {gridIndex: 1, splitNumber: 2, axisLabel: {show: false}, splitLine: {show: false}, axisLine: {show: false}}
                ],
                series: [
                    {name: 'K线', type: 'candlestick', data: ohlc,
                     itemStyle: {color: '#dc2626', color0: '#16a34a',
                                 borderColor: '#dc2626', borderColor0: '#16a34a'}},
                    {name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes,
                     itemStyle: {color: (p) => {
                         const idx = p.dataIndex;
                         const cur = recent[idx];
                         if (!cur) return '#cbd5e1';
                         return cur.close >= cur.open ? '#dc262688' : '#16a34a88';
                     }}}
                ],
                dataZoom: [{type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100}],
            });
        } catch (e) {
            console.error(`${s.name} K线加载失败`, e);
        }
    });
    await Promise.all(promises);
}

// ===== 选中股票（查看详情） =====
async function selectStock(code) {
    try {
        const stock = stocks.find(s => s.code === code);
        if (!stock) return;
        currentStock = stock;
        document.querySelectorAll('.quote-card').forEach(c => c.classList.remove('active'));
        const activeCard = document.querySelector(`.quote-card[onclick*="'${code}'"]`);
        if (activeCard) activeCard.classList.add('active');
        // 确保当前在行情面板，否则自动切过去
        const activeNav = document.querySelector('#sidebarNav .nav-item.active');
        const curPanel = activeNav ? activeNav.dataset.panel : null;
        if (curPanel !== 'quotes' && curPanel !== 'kline') {
            const quotesNav = document.querySelector('#sidebarNav .nav-item[data-panel="quotes"]');
            if (quotesNav) quotesNav.click();
        }
        // 加载详情（用内联样式，确保不会被 CSS 类覆盖）
        $('stockDetailPanel').style.display = 'block';
        $('detailStockName').textContent = `${stock.name} (${stock.code})`;
        loadKlineDetail(code, currentPeriod);
        loadMoneyFlow(code);
        loadFinance(code);
        loadSentimentDetail(code);
        $('stockDetailPanel').scrollIntoView({behavior: 'smooth', block: 'start'});
    } catch (e) {
        console.error('选择股票失败', e);
    }
}

// ===== 详情K线 =====
async function loadKlineDetail(code, period) {
    try {
        const data = await api(`/quote/${code}/kline?period=${period}`);
        const klines = data.kline || [];
        if (klines.length === 0) {
            if (klineCharts['detail']) klineCharts['detail'].setOption({title: {text: '暂无K线数据', left: 'center', top: 'center', textStyle: {color: LIGHT_THEME.axisLabel}}});
            return;
        }
        const chartDom = $('klineChart');
        if (klineCharts['detail']) klineCharts['detail'].dispose();
        const chart = echarts.init(chartDom);
        klineCharts['detail'] = chart;

        const dates = klines.map(k => k.date);
        const ohlc = klines.map(k => [k.open, k.close, k.low, k.high]);
        const volumes = klines.map(k => k.volume);

        chart.setOption({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis', axisPointer: {type: 'cross', lineStyle: {color: '#d0d7de'}},
                backgroundColor: LIGHT_THEME.tooltipBg, borderColor: LIGHT_THEME.tooltipBorder,
                textStyle: {color: LIGHT_THEME.tooltipText, fontSize: 12}
            },
            legend: {data: ['K线', '成交量'], top: 0, textStyle: {color: LIGHT_THEME.textColor}},
            grid: [
                {left: '8%', right: '5%', top: '12%', height: '58%'},
                {left: '8%', right: '5%', top: '76%', height: '16%'}
            ],
            xAxis: [
                {type: 'category', data: dates, scale: true, boundaryGap: false,
                 axisLine: {lineStyle: {color: LIGHT_THEME.axisLine}},
                 axisLabel: {color: LIGHT_THEME.axisLabel}},
                {type: 'category', gridIndex: 1, data: dates, axisLabel: {show: false}}
            ],
            yAxis: [
                {scale: true, splitLine: {lineStyle: {color: LIGHT_THEME.splitLine}},
                 axisLabel: {color: LIGHT_THEME.axisLabel}, axisLine: {show: false}},
                {gridIndex: 1, splitNumber: 2, axisLabel: {show: false}, splitLine: {show: false}, axisLine: {show: false}}
            ],
            series: [
                {name: 'K线', type: 'candlestick', data: ohlc,
                 itemStyle: {color: '#dc2626', color0: '#16a34a',
                             borderColor: '#dc2626', borderColor0: '#16a34a'}},
                {name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes,
                 itemStyle: {color: (p) => {
                     const idx = p.dataIndex;
                     const cur = klines[idx];
                     if (!cur) return '#cbd5e1';
                     return cur.close >= cur.open ? '#dc262688' : '#16a34a88';
                 }}}
            ],
            dataZoom: [
                {type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100},
                {type: 'slider', xAxisIndex: [0, 1], start: 60, end: 100, bottom: 0, height: 14,
                 borderColor: LIGHT_THEME.axisLine, fillerColor: 'rgba(43,108,176,0.15)',
                 handleStyle: {color: '#2b6cb0'},
                 textStyle: {color: LIGHT_THEME.axisLabel}}
            ],
        }, true);
    } catch (e) {
        console.error('K线加载失败', e);
    }
}

// ===== 资金流向 =====
async function loadMoneyFlow(code) {
    try {
        const data = await api(`/quote/${code}/moneyflow?days=30`);
        const flows = data.money_flow || [];
        if (flows.length === 0) {
            if (klineCharts['money']) klineCharts['money'].setOption({title: {text: '暂无资金流数据', left: 'center', top: 'center', textStyle: {color: LIGHT_THEME.axisLabel}}});
            return;
        }
        const chartDom = $('moneyFlowChart');
        if (klineCharts['money']) klineCharts['money'].dispose();
        const chart = echarts.init(chartDom);
        klineCharts['money'] = chart;

        const dates = flows.map(f => f.date);
        chart.setOption({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: LIGHT_THEME.tooltipBg, borderColor: LIGHT_THEME.tooltipBorder,
                textStyle: {color: LIGHT_THEME.tooltipText, fontSize: 12},
                formatter: (p) => {
                    let s = p[0].axisValue + '<br/>';
                    p.forEach(i => s += `${i.marker}${i.seriesName}: ${fmtMoney(i.value)}<br/>`);
                    return s;
                }
            },
            legend: {data: ['主力净流入', '超大单', '大单'], top: 0, textStyle: {color: LIGHT_THEME.textColor}},
            grid: {left: '10%', right: '5%', top: '15%', bottom: '18%'},
            xAxis: {type: 'category', data: dates,
                    axisLabel: {color: LIGHT_THEME.axisLabel, rotate: 30},
                    axisLine: {lineStyle: {color: LIGHT_THEME.axisLine}}},
            yAxis: {type: 'value',
                    axisLabel: {color: LIGHT_THEME.axisLabel, formatter: (v) => fmtMoney(v)},
                    splitLine: {lineStyle: {color: LIGHT_THEME.splitLine}}},
            series: [
                {name: '主力净流入', type: 'bar', data: flows.map(f => f.main_net),
                 itemStyle: {color: (p) => p.value >= 0 ? '#dc2626' : '#16a34a'}},
                {name: '超大单', type: 'bar', data: flows.map(f => f.super_net),
                 itemStyle: {color: '#7c3aed88'}},
                {name: '大单', type: 'bar', data: flows.map(f => f.large_net),
                 itemStyle: {color: '#2b6cb088'}},
            ],
            dataZoom: [{type: 'inside', start: 50, end: 100}],
        }, true);
    } catch (e) {
        console.error('资金流加载失败', e);
    }
}

// ===== 财务指标 =====
async function loadFinance(code) {
    try {
        const fin = await api(`/quote/${code}/finance`);
        const row = $('financeRow');
        if (!fin || Object.keys(fin).length === 0) {
            row.innerHTML = '<div class="loading-placeholder" style="grid-column:1/-1;">暂无财务数据</div>';
            return;
        }
        const items = [
            {label: '每股收益(EPS)', value: fmt(fin.eps), unit: '元'},
            {label: '每股净资产', value: fmt(fin.bps), unit: '元'},
            {label: '净资产收益率', value: fmt(fin.roe), unit: '%'},
            {label: '毛利率', value: fmt(fin.gross_margin), unit: '%'},
            {label: '营收', value: fmtMoney(fin.revenue), unit: ''},
            {label: '营收同比', value: fmt(fin.revenue_yoy), unit: '%'},
            {label: '净利润', value: fmtMoney(fin.net_profit), unit: ''},
            {label: '净利同比', value: fmt(fin.profit_yoy), unit: '%'},
        ];
        row.innerHTML = items.map(it => `
            <div class="finance-item">
                <div class="finance-label">${it.label}</div>
                <div class="finance-value">${it.value}${it.unit}</div>
            </div>`).join('') + `
            <div class="finance-item" style="grid-column:1/-1;">
                <div class="finance-label">报告期</div>
                <div class="finance-value" style="font-size:13px;">${fin.report_date || '--'}</div>
            </div>`;
    } catch (e) {
        console.error('财务加载失败', e);
    }
}

// ===== 新闻（股票池聚合）=====
async function loadAllNews() {
    const topN = $('topNSelect').value;
    renderNewsFilter();

    try {
        const allNews = [];
        const promises = stocks.map(async (s) => {
            try {
                const data = await api(`/news/${s.code}?top_n=${topN}`);
                if (data.news) {
                    data.news.forEach(n => {
                        n.stock_code = s.code;
                        n.stock_name = s.name;
                    });
                    allNews.push(...data.news);
                }
            } catch (e) { /* skip */ }
        });
        await Promise.all(promises);

        const filtered = newsStockFilter === 'all'
            ? allNews
            : allNews.filter(n => n.stock_code === newsStockFilter);

        filtered.sort((a, b) => {
            const ta = a.published_at || a.crawled_at || '';
            const tb = b.published_at || b.crawled_at || '';
            return tb.localeCompare(ta);
        });

        const list = $('newsList');
        if (filtered.length === 0) {
            list.innerHTML = '<div class="loading-placeholder">暂无相关新闻，点击"刷新"获取最新资讯</div>';
            $('newsUpdateTime').textContent = '共 0 条';
            return;
        }

        list.innerHTML = filtered.slice(0, parseInt(topN) * stocks.length).map(n => {
            let kw;
            if (n.keywords_tagged && n.keywords_tagged.length > 0) {
                kw = n.keywords_tagged.map(k => {
                    const cls = `keyword-tag kw-${k.type || 'general'}`;
                    return `<span class="${cls}">${escapeHtml(k.word)}</span>`;
                }).join('');
            } else {
                kw = (n.keywords || []).map(k => `<span class="keyword-tag kw-general">${escapeHtml(k)}</span>`).join('');
            }
            const industryTags = (n.industries || []).map(i => `<span class="industry-tag">${escapeHtml(i)}</span>`).join('');
            const sentTag = n.sentiment_label ? `<span class="sentiment-tag tag-${n.sentiment_label}">${escapeHtml(n.sentiment_text || n.sentiment_label)}</span>` : '';
            const srcClass = `src-${n.source}`;
            const stockTag = `<span class="news-stock-tag">${escapeHtml(n.stock_name || '')}</span>`;
            const link = n.url ? `<a href="${n.url}" target="_blank" rel="noopener">${escapeHtml(n.title)}</a>` : escapeHtml(n.title);
            const summary = n.summary ? `<div class="news-summary">${escapeHtml(n.summary)}</div>` : '';
            const keywordsBlock = (kw || industryTags) ? `<div class="news-keywords">${kw}${industryTags}</div>` : '';
            return `
                <div class="news-item">
                    <div class="news-meta">
                        <span class="news-source ${srcClass}">${escapeHtml(n.source_label || n.source)}</span>
                        ${stockTag}
                        ${sentTag}
                        <span class="news-time">${fmtTime(n.published_at) || fmtTime(n.crawled_at)}</span>
                    </div>
                    <div class="news-title">${link}</div>
                    ${summary}
                    ${keywordsBlock}
                </div>`;
        }).join('');
        $('newsUpdateTime').textContent = `共 ${filtered.length} 条`;
    } catch (e) {
        console.error('新闻加载失败', e);
        $('newsList').innerHTML = '<div class="loading-placeholder">新闻加载失败</div>';
    }
}

function renderNewsFilter() {
    const filter = $('newsFilter');
    if (!filter || filter.dataset.rendered === '1') return;
    filter.innerHTML = `<span class="filter-chip ${newsStockFilter === 'all' ? 'active' : ''}" data-code="all">全部</span>` +
        stocks.map(s => `<span class="filter-chip ${newsStockFilter === s.code ? 'active' : ''}" data-code="${s.code}">${s.name}</span>`).join('');
    filter.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            newsStockFilter = chip.dataset.code;
            filter.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            loadAllNews();
        });
    });
    filter.dataset.rendered = '1';
}

// ===== 情绪分析 =====
async function loadSentimentDetail(code) {
    try {
        const data = await api(`/sentiment/${code}`);
        renderSentiment(data, code);
    } catch (e) {
        console.error('情绪加载失败', e);
    }
}

function _levelClass(level) {
    if (!level) return 'ov-level-neu';
    if (level.includes('多') || level.includes('看多')) return 'ov-level-pos';
    if (level.includes('空') || level.includes('看空')) return 'ov-level-neg';
    return 'ov-level-neu';
}
function _scoreColor(score) {
    if (score === null || score === undefined || isNaN(score)) return 'var(--text-dim)';
    if (score > 0) return '#dc2626';
    if (score < 0) return '#059669';
    return '#6b7280';
}

function renderSentimentOverview(items) {
    const ov = $('sentimentOverview');
    if (!items || items.length === 0) {
        ov.innerHTML = '<div class="loading-placeholder">暂无情绪数据。请先选择一只股票，点击"立即分析"采集股吧和雪球的最新评论。<br/>📌 数据源：股吧(guba.eastmoney.com) + 雪球(xueqiu.com)</div>';
        return;
    }
    const cards = items.map(it => {
        const score = it.score || 0;
        const level = it.level || (score > 20 ? '偏多' : score < -20 ? '偏空' : '中性震荡');
        const lvClass = _levelClass(level);
        const posText = `${it.positive_texts ?? 0}条(${(it.positive*100).toFixed(0)}%)`;
        const neuText = `${it.neutral_texts ?? 0}条(${(it.neutral*100).toFixed(0)}%)`;
        const negText = `${it.negative_texts ?? 0}条(${(it.negative*100).toFixed(0)}%)`;
        return `
            <div class="overview-card">
                <div class="ov-name">
                    <span>${escapeHtml(it.stock_name || it.stock_code)}</span>
                    <span class="code">${escapeHtml(it.stock_code)}</span>
                </div>
                <span class="ov-level ${lvClass}">${escapeHtml(level)}</span>
                <div class="ov-score" style="color:${_scoreColor(score)};">${score > 0 ? '+' : ''}${fmt(score, 1)}</div>
                <div class="ov-meta">
                    <span style="color:#dc2626;"><b>看多</b> ${escapeHtml(posText)}</span><br/>
                    <span style="color:#475569;"><b>中性</b> ${escapeHtml(neuText)}</span><br/>
                    <span style="color:#059669;"><b>看空</b> ${escapeHtml(negText)}</span>
                </div>
                ${it.advice ? `<div class="ov-meta" style="margin-top:4px;padding-top:4px;border-top:1px dashed #e5e7eb;"><b>建议：</b>${escapeHtml(it.advice)}</div>` : ''}
            </div>`;
    }).join('');

    const legend = `
        <div class="overview-legend">
            <b>情绪指数刻度：</b>
            <span class="legend-item"><span class="legend-dot dot-strong-up"></span>+70~+100 极度看多</span>
            <span class="legend-item"><span class="legend-dot dot-up"></span>+50~+70 强烈看多</span>
            <span class="legend-item"><span class="legend-dot dot-mild-up"></span>+20~+50 偏多</span>
            <span class="legend-item"><span class="legend-dot dot-neutral"></span>-20~+20 中性震荡</span>
            <span class="legend-item"><span class="legend-dot dot-mild-down"></span>-50~-20 偏空</span>
            <span class="legend-item"><span class="legend-dot dot-down"></span>-70~-50 强烈看空</span>
            <span class="legend-item"><span class="legend-dot dot-strong-down"></span>-100~-70 极度看空</span>
            &nbsp;|&nbsp;
            <b>计算方法：</b>
            <span>单条文本得分 = SnowNLP情感概率 × 0.4 + 金融词典归一化 × 0.6；综合分 = (样本均分 - 0.5) × 200</span>
            <span>|</span>
            <b>样本总数：</b>
            <span>${items.reduce((s,i) => s + (i.sample_count||0), 0)} 条评论</span>
        </div>`;
    ov.innerHTML = `<div class="overview-grid">${cards}</div>${legend}`;
}

function renderSentiment(data, code) {
    if (!data || data.score === undefined || data.score === null) {
        const stockName = stocks.find(s => s.code === code)?.name || code;
        $('sentimentOverview').innerHTML = `<div class="loading-placeholder"><strong>${escapeHtml(stockName)}</strong> 暂无情绪数据。请点击"立即分析"采集股吧+雪球的最新评论。</div>`;
        ['gauge', 'pie', 'wordCloud', 'compare'].forEach(k => {
            if (sentimentCharts[k]) sentimentCharts[k].clear();
        });
        return;
    }
    const score = data.score;

    loadAllSentiment().catch(() => {});

    if (!sentimentCharts['gauge']) {
        const chartDom = $('sentimentGauge');
        sentimentCharts['gauge'] = echarts.init(chartDom);
    }
    sentimentCharts['gauge'].setOption({
        backgroundColor: 'transparent',
        series: [{
            type: 'gauge', min: -100, max: 100, splitNumber: 10,
            axisLine: {lineStyle: {width: 16, color: [
                [0.3, '#16a34a'], [0.5, '#94a3b8'], [0.7, '#d97706'], [1, '#dc2626']
            ]}},
            pointer: {width: 5, itemStyle: {color: '#1a2233'}},
            detail: {formatter: '{value}', fontSize: 28, offsetCenter: [0, '70%'], color: _scoreColor(score)},
            title: {offsetCenter: [0, '95%'], fontSize: 12, color: LIGHT_THEME.axisLabel},
            data: [{value: score, name: data.level || '情绪指数'}],
        }],
    }, true);

    const posCnt = data.positive_texts ?? Math.round((data.positive || 0) * (data.sample_count || 0));
    const neuCnt = data.neutral_texts ?? Math.round((data.neutral || 0) * (data.sample_count || 0));
    const negCnt = data.negative_texts ?? Math.round((data.negative || 0) * (data.sample_count || 0));
    if (!sentimentCharts['pie']) {
        sentimentCharts['pie'] = echarts.init($('sentimentPie'));
    }
    sentimentCharts['pie'].setOption({
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: (p) => `${p.name}: ${p.value} 条 (${p.percent}%)`
        },
        legend: {bottom: 0, textStyle: {color: LIGHT_THEME.textColor}},
        series: [{
            type: 'pie', radius: ['40%', '65%'], center: ['50%', '45%'],
            label: {color: LIGHT_THEME.textColor, formatter: '{b}\n{d}%'},
            data: [
                {value: posCnt, name: '看多', itemStyle: {color: '#dc2626'}},
                {value: neuCnt, name: '中性', itemStyle: {color: '#94a3b8'}},
                {value: negCnt, name: '看空', itemStyle: {color: '#16a34a'}},
            ],
        }],
    }, true);

    const kws = data.keywords || [];
    const kwsKey = JSON.stringify(kws);
    if (!sentimentCharts['wordCloud']) {
        sentimentCharts['wordCloud'] = echarts.init($('sentimentWordCloud'));
    }
    if (sentimentCharts['_lastWordCloudKey'] !== kwsKey) {
        sentimentCharts['_lastWordCloudKey'] = kwsKey;
        if (kws.length > 0) {
            sentimentCharts['wordCloud'].setOption({
                backgroundColor: 'transparent',
                series: [{
                    type: 'wordCloud', shape: 'circle',
                    sizeRange: [12, 48], rotationRange: [-30, 30],
                    textStyle: {color: '#2b6cb0'},
                    emphasis: {textStyle: {color: '#dc2626'}},
                    data: kws,
                }],
            }, true);
        } else {
            sentimentCharts['wordCloud'].clear();
        }
    }
}

// ===== 多股情绪对比 =====
async function loadAllSentiment() {
    try {
        const data = await api('/sentiment');
        const items = data.sentiments || [];
        const enriched = items.map(i => {
            const s = stocks.find(x => x.code === i.stock_code);
            if (s) i.stock_name = s.name;
            return i;
        });
        renderSentimentOverview(enriched);

        if (enriched.length > 0) {
            const first = enriched[0];
            renderSentiment(first, first.stock_code);
            $('sentimentUpdateTime').textContent = `当前展示: ${first.stock_name || first.stock_code} | 更新于 ${new Date().toLocaleTimeString('zh-CN', {hour12: false})}`;
        }

        if (!sentimentCharts['compare']) {
            sentimentCharts['compare'] = echarts.init($('sentimentCompare'));
        }
        if (items.length === 0) {
            sentimentCharts['compare'].setOption({title: {text: '暂无情绪数据', left: 'center', top: 'center', textStyle: {color: LIGHT_THEME.axisLabel}}});
            return;
        }
        sentimentCharts['compare'].setOption({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                formatter: (params) => {
                    const p = params[0];
                    const it = enriched[p.dataIndex] || {};
                    return `${p.name}<br/>情绪指数: <b>${p.value}</b><br/>等级: ${it.level||'-'}<br/>样本: ${it.sample_count||0}条`;
                }
            },
            grid: {left: '8%', right: '5%', top: '10%', bottom: '25%'},
            xAxis: {type: 'category', data: enriched.map(i => i.stock_name || i.stock_code),
                    axisLabel: {color: LIGHT_THEME.axisLabel, rotate: 30},
                    axisLine: {lineStyle: {color: LIGHT_THEME.axisLine}}},
            yAxis: {type: 'value', min: -100, max: 100,
                    axisLabel: {color: LIGHT_THEME.axisLabel},
                    splitLine: {lineStyle: {color: LIGHT_THEME.splitLine}},
                    name: '情绪指数 (看空-100~看多+100)', nameTextStyle: {color: LIGHT_THEME.axisLabel}},
            series: [{
                type: 'bar', data: enriched.map(i => i.score),
                itemStyle: {color: (p) => p.value >= 0 ? '#dc2626' : '#16a34a', borderRadius: [4, 4, 0, 0]},
                label: {show: true, position: 'top', color: LIGHT_THEME.textColor, fontSize: 11,
                        formatter: (p) => (p.value > 0 ? '+' : '') + p.value.toFixed(0)},
            }],
        }, true);
    } catch (e) {
        console.error('情绪对比加载失败', e);
    }
}

// ===== 立即分析情绪 =====
async function analyzeSentiment() {
    $('analyzeBtn').disabled = true;
    $('analyzeBtn').textContent = '分析中...';
    $('sentimentOverview').innerHTML = '<div class="loading-placeholder">正在采集股吧+雪球评论并分析，请耐心等待...（约需30-60秒）</div>';
    try {
        const results = [];
        for (const s of stocks) {
            try {
                const data = await api(`/sentiment/${s.code}/analyze`, {method: 'POST'});
                if (data && data.score !== undefined) {
                    data.stock_name = s.name;
                    data.stock_code = s.code;
                    results.push(data);
                }
            } catch (e) {
                console.error(`${s.name} 情绪分析失败`, e);
            }
        }
        if (results.length > 0) {
            const first = results[0];
            renderSentiment(first, first.stock_code);
            $('sentimentUpdateTime').textContent = `当前展示: ${first.stock_name || first.stock_code} | 更新于 ${new Date().toLocaleTimeString('zh-CN', {hour12: false})}`;
        }
        await loadAllSentiment();
    } catch (e) {
        console.error('分析失败', e);
        $('sentimentOverview').innerHTML = '<div class="loading-placeholder">分析失败，请重试</div>';
    } finally {
        $('analyzeBtn').disabled = false;
        $('analyzeBtn').textContent = '立即分析';
    }
}

// ===== 刷新 =====
async function onRefresh() {
    const btn = $('refreshBtn');
    btn.disabled = true;
    btn.textContent = '🔄 刷新中...';
    $('refreshStatus').textContent = '正在刷新...';
    try {
        await api('/refresh', {method: 'POST'});
        await loadQuotes();
        await loadKlineGrid();
        await loadAllNews();
        await loadAllSentiment();
        loadWyckoffAll();
        loadTradePlansAll();
        if (currentStock) {
            loadKlineDetail(currentStock.code, currentPeriod);
            loadMoneyFlow(currentStock.code);
            loadFinance(currentStock.code);
            loadSentimentDetail(currentStock.code);
        }
        $('refreshStatus').textContent = '✓ 已刷新 ' + new Date().toLocaleTimeString('zh-CN', {hour12: false});
    } catch (e) {
        $('refreshStatus').textContent = '✗ 刷新失败';
        console.error(e);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔄 刷新';
        setTimeout(() => { $('refreshStatus').textContent = ''; }, 5000);
    }
}

// ===== 自动刷新 =====
async function setupAutoRefresh() {
    try {
        const s = await api('/settings');
        const interval = s.refresh_interval || 5;
        if (autoRefreshTimer) clearInterval(autoRefreshTimer);
        autoRefreshTimer = setInterval(async () => {
            await loadQuotes();
            await loadAllNews();
            await loadAllSentiment();
            loadWyckoffAll();
            loadTradePlansAll();
            if (currentStock) {
                loadSentimentDetail(currentStock.code);
            }
        }, interval * 60 * 1000);
        $('serverInfo').textContent = `自动刷新 ${interval}分钟`;
    } catch (e) {
        console.error('设置自动刷新失败', e);
    }
}

// ===== 设置弹窗 =====
async function openSettings() {
    try {
        const s = await api('/settings');
        $('intervalInput').value = s.refresh_interval;
        $('topNInput').value = s.top_n;
        $('settingsModal').style.display = 'flex';
    } catch (e) {
        alert('加载设置失败: ' + e.message);
    }
}

async function saveSettings() {
    const interval = parseInt($('intervalInput').value);
    const topN = parseInt($('topNInput').value);
    try {
        await api('/settings', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({refresh_interval: interval, top_n: topN}),
        });
        $('topNSelect').value = topN;
        $('settingsModal').style.display = 'none';
        setupAutoRefresh();
        alert('设置已保存');
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

// ===== 股票管理 =====
async function openManage() {
    try {
        const data = await api('/stocks');
        const list = $('stockManageList');
        list.innerHTML = data.stocks.map(s => `
            <div class="stock-manage-item">
                <div class="stock-manage-info">
                    <span class="stock-manage-name">${s.name}</span>
                    <span class="stock-manage-code">${s.code} · ${s.market.toUpperCase()}</span>
                </div>
                <button class="btn-danger" onclick="removeStock('${s.code}')">移除</button>
            </div>`).join('');
        $('manageModal').style.display = 'flex';
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
}

async function addStock() {
    const code = $('newStockCode').value.trim();
    const name = $('newStockName').value.trim();
    if (!/^\d{6}$/.test(code)) {
        alert('请输入6位股票代码');
        return;
    }
    try {
        await api('/stocks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code, name}),
        });
        $('newStockCode').value = '';
        $('newStockName').value = '';
        stocks = await loadStocks();
        newsStockFilter = 'all';
        await loadQuotes();
        await loadKlineGrid();
        await loadAllNews();
        alert('添加成功，看板已更新');
    } catch (e) {
        alert('添加失败: ' + e.message);
    }
}

async function removeStock(code) {
    if (!confirm('确认移除该股票？相关新闻和情绪数据将一并清除。')) return;
    try {
        await api(`/stocks/${code}`, {method: 'DELETE'});
        stocks = await loadStocks();
        delete klineCharts[code];
        newsStockFilter = 'all';
        await loadQuotes();
        await loadKlineGrid();
        await loadAllNews();
        if (currentStock && currentStock.code === code) {
            currentStock = null;
            $('stockDetailPanel').style.display = 'none';
        }
        openManage();
    } catch (e) {
        alert('移除失败: ' + e.message);
    }
}

// ===== 威科夫分析 =====
async function loadWyckoffAll() {
    try {
        const data = await api('/wyckoff/all');
        const stocks = data.stocks || {};
        renderWyckoffGrid(stocks);
    } catch (e) {
        console.error('威科夫分析加载失败', e);
        $('wyckoffGrid').innerHTML = '<div class="loading-placeholder" style="grid-column:1/-1;">威科夫分析加载失败</div>';
    }
}

function _phaseClass(phase) {
    if (!phase) return 'phase-trading';
    if (phase.includes('拉升') || phase.includes('Markup')) return 'phase-markup';
    if (phase.includes('派发') || phase.includes('Distribution')) return 'phase-distribution';
    if (phase.includes('下跌') || phase.includes('Markdown')) return 'phase-markdown';
    if (phase.includes('吸筹') || phase.includes('Accumulation')) return 'phase-accumulation';
    if (phase.includes('底部') || phase.includes('Spring')) return 'phase-spring';
    return 'phase-trading';
}

function _riskClass(risk) {
    if (!risk) return 'risk-mid';
    if (risk === '高') return 'risk-high';
    if (risk === '低') return 'risk-low';
    return 'risk-mid';
}

function renderWyckoffGrid(stocksData) {
    const grid = $('wyckoffGrid');
    const entries = Object.entries(stocksData);

    if (entries.length === 0) {
        grid.innerHTML = '<div class="loading-placeholder" style="grid-column:1/-1;">暂无数据</div>';
        return;
    }

    grid.innerHTML = entries.map(([code, data]) => {
        if (data.error && !data.has_data) {
            return `
                <div class="wyckoff-card">
                    <div class="wyckoff-card-header">
                        <span class="wk-name">${escapeHtml(data.stock_name || code)}<span class="wk-code">${code}</span></span>
                    </div>
                    <div style="color:var(--text-dim);font-size:13px;">${escapeHtml(data.message || data.error)}</div>
                </div>`;
        }

        const phase = data.wyckoff_phase || {};
        const smart = data.smart_money_behavior || {};
        const keyLevels = data.key_levels || {};
        const macd = data.macd || {};
        const ma = data.ma || {};
        const vol = data.volume || {};
        const stock = data.stock || {};

        const support = keyLevels.nearest_support;
        const resistance = keyLevels.nearest_resistance;

        return `
        <div class="wyckoff-card">
            <div class="wyckoff-card-header">
                <span class="wk-name">${escapeHtml(data.stock_name || '')}<span class="wk-code">${code}</span></span>
                <span class="wk-phase ${_phaseClass(phase.phase)}">${escapeHtml(phase.phase || '--')}</span>
            </div>

            <div class="wk-row">
                <span class="wk-label">当前价</span>
                <span class="wk-value">${fmt(stock.current_price)}</span>
            </div>
            <div class="wk-row">
                <span class="wk-label">5日涨跌</span>
                <span class="wk-value ${(stock.chg_5d||0) >= 0 ? 'up' : 'down'}">${(stock.chg_5d||0) >= 0 ? '+' : ''}${fmt(stock.chg_5d)}%</span>
            </div>
            <div class="wk-row">
                <span class="wk-label">MACD趋势</span>
                <span class="wk-value">${escapeHtml(macd.trend || '--')} | DIF: ${fmt(macd.dif, 4)}</span>
            </div>
            <div class="wk-row">
                <span class="wk-label">MA20 / MA60</span>
                <span class="wk-value">${fmt(ma.MA20)} / ${fmt(ma.MA60)}</span>
            </div>
            <div class="wk-row">
                <span class="wk-label">量能趋势</span>
                <span class="wk-value">${escapeHtml(vol.volume_trend || '--')}</span>
            </div>

            ${support || resistance ? `
            <div class="wk-levels">
                ${support ? `<div class="wk-level-item"><span class="wk-level-type">${escapeHtml(support.type)}</span><span class="wk-level-price support">${fmt(support.price)}</span></div>` : ''}
                ${resistance ? `<div class="wk-level-item"><span class="wk-level-type">${escapeHtml(resistance.type)}</span><span class="wk-level-price resistance">${fmt(resistance.price)}</span></div>` : ''}
            </div>` : ''}

            <div class="wk-smart-money">
                <div>${escapeHtml(smart.behavior || '')}</div>
                <div class="wk-intention">${escapeHtml(smart.intention || '')}<span class="wk-risk ${_riskClass(smart.risk_level)}">风险${escapeHtml(smart.risk_level || '中')}</span></div>
            </div>
        </div>`;
    }).join('');

    $('wyckoffUpdateTime').textContent = '更新于 ' + new Date().toLocaleTimeString('zh-CN', {hour12: false});
}

// ===== 交易计划 =====
async function loadTradePlansAll() {
    try {
        const data = await api('/trade-plan/all');
        const plans = data.plans || [];
        renderTradePlanGrid(plans);
    } catch (e) {
        console.error('交易计划加载失败', e);
        $('tradePlanGrid').innerHTML = '<div class="loading-placeholder" style="grid-column:1/-1;">交易计划加载失败</div>';
    }
}

function renderTradePlanGrid(plans) {
    const grid = $('tradePlanGrid');

    if (plans.length === 0) {
        grid.innerHTML = '<div class="loading-placeholder" style="grid-column:1/-1;">暂无交易计划</div>';
        return;
    }

    grid.innerHTML = plans.map(p => {
        if (p.error) {
            return `
                <div class="trade-plan-card">
                    <div class="tp-header">${escapeHtml(p.stock_name || '')} (${p.stock_code})</div>
                    <div style="color:var(--text-dim);font-size:13px;">${escapeHtml(p.message || p.error)}</div>
                </div>`;
        }

        const first = p.first_target || {};
        const second = p.second_target || {};
        const stop = p.stop_loss || {};
        const discipline = p.discipline || [];
        const tw = p.time_window;

        return `
        <div class="trade-plan-card">
            <div class="tp-header">${escapeHtml(p.stock_name)} (${p.stock_code})</div>

            <div class="tp-mode">
                <strong>主力操盘模式：</strong>${escapeHtml(p.mode || '')}
            </div>

            <div class="tp-section">
                <div class="tp-section-title">分批止盈位</div>
                <div class="tp-item target">
                    <strong>第一撤退点：</strong><span class="tp-price">${fmt(first.price)} 元</span>
                    <span class="tp-logic">${escapeHtml(first.logic || '')}</span>
                </div>
                <div class="tp-item target">
                    <strong>第二撤退点（目标位）：</strong><span class="tp-price">${fmt(second.price)} 元</span>
                    <span class="tp-logic">${escapeHtml(second.logic || '')}</span>
                </div>
            </div>

            <div class="tp-section">
                <div class="tp-section-title">风控止损位</div>
                <div class="tp-item stop">
                    <strong>止损线：</strong><span class="tp-price">${fmt(stop.price)} 元</span>
                    <span class="tp-logic">${escapeHtml(stop.logic || '')}</span>
                </div>
            </div>

            ${tw ? `
            <div class="tp-section">
                <div class="tp-section-title">特殊事件</div>
                <div class="tp-item time">
                    <strong>${tw.start} 下午 ~ ${tw.end}</strong> 为最终撤退窗口
                    <span class="tp-logic">${escapeHtml(tw.note || '')}</span>
                </div>
            </div>` : ''}

            <div class="tp-discipline">
                <div class="tp-discipline-title">撤退纪律</div>
                ${discipline.map(d => `
                    <div class="tp-rule">
                        <span class="tp-rule-name">${escapeHtml(d.rule)}：</span>
                        <span class="tp-rule-detail">${escapeHtml(d.detail)}</span>
                    </div>
                `).join('')}
            </div>
        </div>`;
    }).join('');

    $('tradePlanUpdateTime').textContent = '更新于 ' + new Date().toLocaleTimeString('zh-CN', {hour12: false});
}

// 启动
window.addEventListener('DOMContentLoaded', init);