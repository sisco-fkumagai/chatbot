import os
import requests

CALENDAR_API_URL = os.getenv("CALENDAR_API_URL")

def add_event_to_calendar(date, hours, title):
    """
    Googleカレンダーにイベントを追加する。
    :param date: 開始日時 (例: "20250110T090000")
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

def get_events_from_calendar(start_date, end_date):
    """
    Googleカレンダーから指定期間のイベントを取得する。
    :param start_date: 開始日 (YYYY-MM-DD形式)
    :param end_date: 終了日 (YYYY-MM-DD形式)
    :return: イベントリスト
    """
    params = {"startDate": start_date, "endDate": end_date}

    try:
        response = requests.get(CALENDAR_API_URL, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API request failed: {response.text}")
    except requests.RequestException as e:
        raise Exception(f"Request error: {str(e)}")