"""定时调度服务 —— APScheduler 每 N 分钟刷新新闻+情绪"""
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database
from services.news_service import refresh_all_news
from services.sentiment_service import analyze_all_sentiment

_scheduler: BackgroundScheduler = None
_news_job_id = "news_refresh"
_sentiment_job_id = "sentiment_refresh"
_lock = threading.Lock()


def _refresh_news_job():
    try:
        refresh_all_news()
    except Exception as e:
        print(f"[scheduler] 新闻刷新异常: {e}")


def _refresh_sentiment_job():
    try:
        analyze_all_sentiment()
    except Exception as e:
        print(f"[scheduler] 情绪刷新异常: {e}")


def start_scheduler():
    """启动定时任务"""
    global _scheduler
    with _lock:
        if _scheduler is not None:
            return
        _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        interval = int(database.get_setting("refresh_interval", "5"))
        _scheduler.add_job(
            _refresh_news_job,
            IntervalTrigger(minutes=interval),
            id=_news_job_id,
            replace_existing=True,
        )
        # 情绪分析频率低一些，默认 15 分钟
        _scheduler.add_job(
            _refresh_sentiment_job,
            IntervalTrigger(minutes=max(interval * 3, 15)),
            id=_sentiment_job_id,
            replace_existing=True,
        )
        _scheduler.start()
        print(f"[scheduler] 已启动，新闻每 {interval} 分钟刷新一次")


def update_news_interval(minutes: int):
    """动态更新新闻刷新间隔"""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.reschedule_job(
        _news_job_id, trigger=IntervalTrigger(minutes=minutes)
    )
    print(f"[scheduler] 新闻刷新间隔已更新为 {minutes} 分钟")


def trigger_refresh_now() -> dict:
    """手动触发立即刷新（在后台线程执行）"""
    def _do():
        refresh_all_news()
        analyze_all_sentiment()
    t = threading.Thread(target=_do, daemon=True)
    t.start()
    return {"status": "refreshing", "message": "已在后台开始刷新新闻与情绪数据"}
