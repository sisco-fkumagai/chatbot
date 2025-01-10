import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from helpers.chatgpt import chat_with_gpt
from helpers.calendar import add_event_to_calendar, get_events_from_calendar
from helpers.gmail import create_email_draft
from helpers.faq import get_faq_response  # FAQ回答取得用の新規モジュール
import logging
import re

# .envファイルを読み込み
load_dotenv()

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ログレベルをDEBUGに設定
logging.basicConfig(
    level=logging.DEBUG,  # DEBUGレベルのログを出力
    format="%(asctime)s [%(levelname)s] %(message)s",  # ログフォーマット
    handlers=[
        logging.StreamHandler()  # 標準出力にログを出力
    ]
)
logger = logging.getLogger(__name__)

# 入力データモデル
class ChatRequest(BaseModel):
    message: str
    context: list


def parse_period(user_message):
    """
    ユーザーの自然言語での期間指定を解析し、開始日と終了日を返す。
    """
    today = datetime.today()
    logger.debug(f"【DEBUG】today: {today.isoformat()}")  # ログに出力

    if "来週" in user_message:
        start_date = today + timedelta(days=(7 - today.weekday()))  # 来週月曜日
        end_date = start_date + timedelta(days=6)  # 来週日曜日
    elif "今月" in user_message:
        start_date = today.replace(day=1)  # 今月の1日
        end_date = today.replace(day=1) + relativedelta(months=1, days=-1)  # 今月末
    elif "翌月" in user_message:
        start_date = today.replace(day=1) + relativedelta(months=1)  # 翌月1日
        end_date = start_date + relativedelta(months=1, days=-1)  # 翌月末
    else:
        # デフォルトは今週
        start_date = today
        end_date = today + timedelta(days=7)

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


# ユーザー入力から情報を抽出
def extract_user_info(message):
    name = None
    university = None
    date = None

    if "," in message:
        parts = [part.strip() for part in message.split(",")]
        if len(parts) >= 1:
            name = parts[0]
        if len(parts) >= 2:
            university = parts[1]
        if len(parts) >= 3:
            date = parts[2]

    return name, university, date


def format_response_with_newlines(response):
    """
    ChatGPTの応答を一文ごとに改行を追加して整形する。
    """
    return re.sub(r'(?<=[。！？])', '\n', response)


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    ChatGPTを利用してユーザーと会話し、日程調整や質問回答を行う。
    ユーザーのリクエストに応じた分岐処理。
    """

    # 現在の日付を取得
    today = datetime.now().strftime("%Y-%m-%d")
    logger.debug(f"【DEBUG】Today's date: {today}")
    
    # ChatGPTへのプロンプト作成
    prompt = (
        f"今日の日付は {today} です。"
        "あなたは採用面接アシスタントです。以下の制約を守り、適切な質問を行い、日程調整や採用活動に対する質問への回答を行ってください。"
        "1. このチャットボットが行えることは「一次面接の日程調整」と「採用活動における質問への回答」のみです。\n"
        "2. 一次面接の日程調整では他の面接日程調整は行わないでください。\n"
        "3. 採用活動に関する質問（FAQ）では他の質問には回答しないでください。\n"
        "4. 初期メッセージに対して面接の日程調整が選択された場合、初めに「名前、大学、希望日程」を聞いてください。\n"
        "4. 日程調整のための情報を求めるときにユーザーからの返答のフォーマットは 名前、大学、希望日程 になるように聞いてください。例: 田中太郎、AB大学、来週\n"
        "5. ユーザーに提示する日程は時間まで含めて、日付はYYYY-MM-DDの形で今日の日付から日程を近いものから最大3つ提示してください。"
        "   面接は日基本的に対面となる。"
        "6. 日程調整ではGoogleカレンダー上の「空き」イベントのみを考慮してください。"
        "7. 必要な情報が不足している場合は、具体的に何を入力すべきか指示してください。\n"
        "8. Googleカレンダーを使用しているなど内部処理に関わることはユーザーに伝えないでください\n\n"
        #"提示する日程はユーザーが希望した日程のうちGoogleカレンダーで取得した日程と一致する日程を近いものから最大3つ提示してください。"
        f"文脈: {request.context}\nユーザー: {request.message}"
    )

    try:
        # ChatGPTに応答を依頼
        chat_response = chat_with_gpt(prompt)
        logger.debug(f"【DEBUG】ChatGPT応答: {chat_response}")

        # ChatGPTの応答を整形して返す
        formatted_response = format_response_with_newlines(chat_response)

        # 日程調整処理
        if "1" in request.message or any(keyword in request.message for keyword in ["日程", "面接", "調整"]):
            # 文脈に必要な情報が含まれているか確認
            name, university, date = extract_user_info(request.message)

            if not name or not university or not date:
                # 必要な情報が不足している場合、詳細をユーザーに尋ねる
                if not name and not university and not date:
                    return {"reply": formatted_response }

                missing_info = []
                if not name:
                    missing_info.append("名前")
                if not university:
                    missing_info.append("大学名")
                if not date:
                    missing_info.append("希望日程")
                
                return {
                    "reply": f"以下の情報が不足しています: {', '.join(missing_info)}\n"
                            "以下の形式で入力してください:\n"
                            "名前, 大学名, 希望日程\n例: 田中太郎, AB大学, 来週"
                }

            # 情報が揃っている場合、日程調整を行う
            start_date, end_date = parse_period(request.message)
            events = get_events_from_calendar(start_date, end_date)
            logger.debug(f"【DEBUG】取得したイベント: {events}")

            now = datetime.now(timezone.utc)  # タイムゾーン情報付きの現在時刻を取得
            filtered_events = [
                f"{datetime.fromisoformat(event['startTime']).strftime('%Y-%m-%d %H:%M')} ~ "
                f"{datetime.fromisoformat(event['endTime']).strftime('%H:%M')}"
                for event in events
                if "空き" in event["title"] and datetime.fromisoformat(event["startTime"]) >= now
            ][:3]
            
            if filtered_events:
                custom_response = (
                    f"{name}さん（{university}）のご希望に基づき、以下の日程が見つかりました:\n\n" +
                    "\n".join(filtered_events)
                )
                return {"reply": custom_response}
            else:
                return {
                    "reply": (
                        "申し訳ありませんが、"
                        f"{name}さん（{university}）のご希望の期間内に利用可能な日程が見つかりませんでした。"
                    )
                }

        # FAQ処理
        if "2" in request.message or any(keyword in request.message for keyword in ["準備", "服装", "質問"]):
            faq_response = get_faq_response(request.message)
            return {"reply": faq_response}

        # 制約外の質問への対応
        return {"reply": formatted_response }

    except Exception as e:
        logger.error(f"【ERROR】{str(e)}")
        return {"reply": f"エラーが発生しました: {str(e)}"}