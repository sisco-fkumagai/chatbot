import os
import requests

CALENDAR_API_URL = os.getenv("CALENDAR_API_URL")  # 環境変数からURLを取得

def add_event_to_calendar(date, hours, title):
    """
    Googleカレンダーにイベントを追加する。
    :param date: 開始日時 (例: "20241225T090000")
    :param hours: イベントの継続時間 (整数、時間単位)
    :param title: イベントのタイトル
    :return: APIからのレスポンス
    """
    params = {
        "Date": date,
        "Hours": hours,
        "Title": title
    }
    response = requests.post(CALENDAR_API_URL, data=params)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to add event: {response.text}")

def get_events_from_calendar(day):
    """
    特定の日付のGoogleカレンダーからイベントを取得する。
    :param day: 日付 (例: "20241225")
    :return: イベントリスト
    """
    params = {"Day": day}
    response = requests.get(CALENDAR_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch events: {response.text}")
