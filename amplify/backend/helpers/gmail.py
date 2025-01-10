import requests

GMAIL_API_URL = "https://script.google.com/macros/s/AKfycbzsGxR9v1nYA2GwjEK49vy1Fw06_h6lxxtRRO6mDDHRbzyPhI5rXfL7nKcYgp8OMXIs/exec"

def create_email_draft(recipients, subject, body, cc=None):
    """
    Gmailの下書きを作成する。
    :param recipients: 受信者のメールアドレス (例: "example@gmail.com")
    :param subject: メールの件名
    :param body: メール本文
    :param cc: CC先のメールアドレス（オプション）
    :return: 下書き作成の結果
    """
    payload = {
        "action": "createDraft",
        "recipients": recipients,
        "subject": subject,
        "body": body
    }
    if cc:
        payload["cc"] = cc

    response = requests.post(GMAIL_API_URL, json=payload)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to create email draft: {response.text}")

def send_email_draft(draft_id):
    """
    Gmailの下書きを送信する。
    :param draft_id: 下書きのID
    :return: 送信結果
    """
    payload = {
        "action": "sendDraft",
        "draftId": draft_id
    }

    response = requests.post(GMAIL_API_URL, json=payload)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to send email draft: {response.text}")