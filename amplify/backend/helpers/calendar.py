import os
import requests
import logging

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 環境変数からAPI URLを取得
CALENDAR_API_URL = os.getenv("GAS_API_URL")

def get_events_from_calendar(start_date, end_date):
    """
    Googleカレンダーから指定期間のイベントを取得する。
    """
    params = {
        "action": "getEvents",
        "startDate": start_date,
        "endDate": end_date
    }
    response = requests.get(CALENDAR_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"カレンダー取得失敗: {response.text}")

def add_event_to_calendar(date, hours, title):
    """
    Googleカレンダーに新しいイベントを追加する。
    """
    data = {
        "action": "addEvent",
        "Date": date,
        "Hours": hours,
        "Title": title
    }
    response = requests.post(CALENDAR_API_URL, json=data)
    if response.status_code != 200:
        raise Exception(f"イベント追加失敗: {response.text}")


def delete_event_from_calendar(date, time, title):
    """
    Googleカレンダーから指定のイベントを削除する。
    :param date: 削除対象イベントの日付（例: "2025-01-30"）
    :param hours: 削除対象イベントの時間（例: "14:00"）
    :param title: 削除対象イベントのタイトル
    """
    data = {
        "action": "deleteEvent",  # GASでイベント削除処理を判定するためのアクション
        "Date": date,
        "Time": time,
        "Title": title
    }
    
    response = requests.post(CALENDAR_API_URL, json=data)
    logger.debug(f"API: {CALENDAR_API_URL}")
    if response.status_code != 200:
        raise Exception(f"削除失敗: {response.text}")
    logger.debug(f"イベント削除成功: {date} {time} {title}")