import os
import requests

# 環境変数からメール送信用API URLを取得
GMAIL_API_URL = os.getenv("GAS_API_URL")

def send_email(subject, body, to="kfuka@sisco-consulting.co.jp"):
    """
    指定された宛先にメールを送信する。
    """
    data = {
        "action": "sendEmail",
        "Subject": subject,
        "Body": body,
        "To": to
    }
    response = requests.post(GMAIL_API_URL, json=data)
    if response.status_code != 200:
        raise Exception(f"メール送信失敗: {response.text}")
