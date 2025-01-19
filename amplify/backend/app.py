import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from helpers.chatgpt import chat_with_gpt
from helpers.calendar import get_events_from_calendar, add_event_to_calendar, delete_event_from_calendar
from helpers.gmail import send_email
from helpers.faq import load_faq, search_faq
import logging
from pytz import timezone as pytz_timezone

# 環境変数をロード
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

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# データモデル
class ChatRequest(BaseModel):
    message: str
    context: list

# JSTタイムゾーン設定
JST = pytz_timezone("Asia/Tokyo")

# 会話の状態を管理するグローバル辞書
conversation_state = {}

# FAQデータをロード
FAQ_PATH = os.path.join(os.path.dirname(__file__), "helpers", "faq.json")
faq_data = load_faq(FAQ_PATH)

def parse_period(user_message):
    today = datetime.today()
    if "来週" in user_message:
        start_date = today + timedelta(days=(7 - today.weekday()))
        end_date = start_date + timedelta(days=6)
    elif "今月" in user_message:
        start_date = today.replace(day=1)
        end_date = today.replace(day=1) + timedelta(days=30)
    elif "翌月" in user_message:
        start_date = today.replace(day=1) + timedelta(days=30)
        end_date = start_date + timedelta(days=30)
    else:
        start_date = today
        end_date = today + timedelta(days=7)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def format_date_with_weekday(start_time, end_time):
    """
    日付と時刻を指定の形式 (YYYY/M/D(WWW) h:mm-h:mm) でフォーマットする。
    :param start_time: イベント開始時刻 (ISO形式の文字列)
    :param end_time: イベント終了時刻 (ISO形式の文字列)
    :return: フォーマットされた文字列
    """
    start_dt = datetime.fromisoformat(start_time).astimezone(JST)
    end_dt = datetime.fromisoformat(end_time).astimezone(JST)

    # 曜日を日本語に変換
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_kanji = weekdays[start_dt.weekday()]

    # フォーマット済みの文字列を返す
    return f"{start_dt.strftime('%Y/%m/%d')}({weekday_kanji}) {start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"

def add_event_to_calendar_jst(start_time, duration_hours, title):
    """
    Googleカレンダーに仮予約を作成（JSTに変換して作成）。
    """
    # JSTに変換
    start_time_jst = datetime.fromisoformat(start_time).astimezone(JST).isoformat()
    end_time_jst = (datetime.fromisoformat(start_time) + timedelta(hours=duration_hours)).astimezone(JST).isoformat()

    add_event_to_calendar(start_time_jst, duration_hours, title)

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        question = request.message.strip()
        logger.debug(f"ユーザーの質問: {question}")

        # ユーザーIDを取得
        if isinstance(request.context, dict) and "user_id" in request.context:
            user_id = request.context["user_id"]
        else:
            user_id = "guest"  # デフォルト値（変更する場合は一意の識別子を適用）
        logger.debug(f"【DEBUG-1】ユーザーID: {user_id}")

        # 会話状態の初期化
        if user_id not in conversation_state:
            conversation_state[user_id] = {"step": "initial", "context": [], "name": None, "university": None, "date": None, "suggested_dates": []}
        state = conversation_state[user_id]
        logger.debug(f"【DEBUG-2】現在のステップ: {state['step']}")

        # 現在の日付を取得
        today = datetime.now().strftime("%Y-%m-%d")
        logger.debug(f"【DEBUG-3】今日の日付: {today}")

        # 初期ステップ: 名前、大学、希望日程を聞く
        if state["step"] == "initial":
            chat_prompt = (
                f"ユーザーが以下のオプションから選択しました: {request.message}\n"
                "1. 一次面接の日程調整\n"
                "2. 採用活動に関する質問\n"
                "選択に基づいて次のステップを生成してください。\n"
                "一次面接以外の日程調整はしないでください。\n"
                "日程調整を選んだ場合は、名前、大学、希望日程を聞いてください。\n"
                "希望日程は「今週」「来週」などの表現でも進めてください。\n"
                "次のステップ: 日程調整はask_details、質問はfaq_handling\n"
                "出力形式: {\"next_step\": \"次のステップ\", \"reply\": \"応答文\"}"
            )
            chat_response = chat_with_gpt(chat_prompt)
            response_data = json.loads(chat_response)

            # ステップを確実に更新
            state["step"] = response_data.get("next_step", "ask_details")
            logger.debug(f"【DEBUG-4-1】ChatGPT応答: {chat_response}")
            logger.debug(f"【DEBU-5】現在のステップ: {state['step']}")

            # 応答を返却
            return {"reply": response_data.get("reply", "選択肢を再度教えてください。")}
        
        # FAQ処理ステップ
        if state["step"] == "faq_handling":
            answer = search_faq(question, faq_data)

            if answer:
                # FAQに一致する回答が見つかった場合
                return {"reply": answer}
            else:
                # FAQに一致する回答がない場合
                chat_prompt_faq = (
                    f"以下の質問が採用活動に関連するかを判断してください:\n{question}\n"
                    "採用活動に関連する場合は以下のように応答してください:\n"
                    "『その質問についての情報は現在ありません。採用担当者にお問い合わせください。\n"
                    "連絡先: example@example.com』\n"
                    "採用活動に関連しない場合は:\n"
                    "『申し訳ありませんが、採用活動に関係のない質問にはお答えできません。』と答えてください。\n"
                    "出力形式: {\"reply\": \"応答文\"}"
                )
                chat_response = chat_with_gpt(chat_prompt_faq)
                response_data = json.loads(chat_response)

                return {"reply": response_data.get("reply", "もう一度質問を入力してください。")}
        
        # 名前、大学、希望日程を抽出するステップ
        if state["step"] == "ask_details":
            chat_prompt = (
                f"以下のユーザー入力から名前、大学、希望日程を抽出してください:\n{request.message}\n"
                "不足している情報があれば、それをユーザーに再度確認する応答文を生成してください。\n"
                "希望日程は「今週」「来週」などの表現でも次のステップに進めてください。\n"
                "次のステップはsuggest_dates\n"
                "応答は出力形式に沿ってしてください。\n"
                "出力形式: {\"next_step\": \"次のステップ\", \"reply\": \"応答文\", \"name\": \"名前\", \"university\": \"大学\", \"date\": \"希望日程\"}"
            )
            chat_response = chat_with_gpt(chat_prompt)
            logger.debug(f"【DEBUG-4-2】ChatGPT応答: {chat_response}")
            response_data = json.loads(chat_response)
            
            # 情報を更新
            state.update({
                "name": response_data.get("name", state["name"]),
                "university": response_data.get("university", state["university"]),
                "date": response_data.get("date", state["date"]),
            })

            # 希望日程が曖昧な場合でも次に進むようにする
            if state["name"] and state["university"] and state["date"]:
                state["step"] = response_data.get("next_step", "suggest_dates")
                return {"reply": f"{state['name']}さん、情報の提供ありがとうございます。承知しました。{state['date']}で進めてもよろしいでしょうか？"}
            else:
                # 情報が不足している場合は不足分を聞き返す
                state["step"] = response_data.get("next_step", "ask_details")
                return {"reply": response_data.get("reply", "もう一度教えてください。")}

        # 日程を提案するステップ
        if state["step"] == "suggest_dates":
            # 日程を計算
            start_date, end_date = parse_period(state["date"])
            events = get_events_from_calendar(start_date, end_date)
            now_utc = datetime.now(timezone.utc)
            available_events = [
                {
                    "start": datetime.fromisoformat(event["startTime"]).astimezone(JST).isoformat(),
                    "end": datetime.fromisoformat(event["endTime"]).astimezone(JST).isoformat(),
                    "id": event["id"]
                }
                for event in events
                if "空き" in event["title"] and datetime.fromisoformat(event["startTime"]).astimezone(timezone.utc) >= now_utc
            ][:3]

            if not available_events:
                return {"reply": "ご希望の日程に空きが見つかりませんでした。別の日程を教えてください。"}

            # 仮予約作成と同時に「空き」イベントを削除
            for event in available_events:
                logger.debug(f"【DEBUG-7】削除対象イベントID: {event['id']}")  # 削除対象をログに記録
                delete_event_from_calendar(event["id"])  # 同じ日程の「空き」を削除
                add_event_to_calendar(event["start"], 1.5, "仮予約")  # 仮予約を作成
                logger.debug(f"【DEBUG-8】仮予約作成: {event['start']} ~ {event['end']}")

            state["suggested_dates"] = available_events
            # 番号付きで日程を提示
            formatted_events = "\n".join([
                f"{i + 1}. {format_date_with_weekday(event['start'], event['end'])}" for i, event in enumerate(available_events)
            ])
            logger.debug(f"【DEBUG-9】提案された日程: {formatted_events}")

            # ChatGPTに応答文を生成させる
            chat_prompt_dates = (
                f"以下の日程が見つかりました:\n{formatted_events}\n"
                "ユーザーに番号で選んでもらうような応答文を生成してください。\n"
                "出力形式: {\"reply\": \"応答文\"}"
            )
            chat_response = chat_with_gpt(chat_prompt_dates)
            logger.debug(f"【DEBUG-4-2】ChatGPT応答: {chat_response}")
            response_data = json.loads(chat_response)

            state["step"] = "confirm_date"
            return {"reply": response_data.get("reply")}


        # 提案された日程から番号を選ぶステップ
        if state["step"] == "confirm_date":
            selected_index = int(request.message.strip()) - 1
            if 0 <= selected_index < len(state["suggested_dates"]):
                        
                # 提案された日程から選択された日程を取得
                selected_event = state["suggested_dates"][selected_index]
                # 日程を確定し、「仮予約」を削除して「空き」を再作成
                for i, event in enumerate(state["suggested_dates"]):
                    logger.debug(f"【DEBUG-10】選択された日程: {event}")
                    # 選択された日程は「仮予約」を削除して予約完了イベントを作成
                    delete_event_from_calendar(event["id"])
                    logger.debug(f"【DEBUG-11】削除対象イベント: {event['id']}")
                    if i == selected_index:
                        add_event_to_calendar(event["start"], 1.5, f"{state['name']} ({state['university']})")
                        logger.debug(f"【DEBUG-12】予約完了イベント作成: {event['start']} ~ {event['end']}")
                    else:
                        logger.debug(f"【DEBUG-13】非選択の日程: {event}")
                        # 他の日程は「仮予約」を削除して「空き」イベントを作成
                        add_event_to_calendar(event["start"], 1.5, "空き")
                        logger.debug(f"【DEBUG-14】仮予約削除および空き再作成: {event['start']} ~ {event['end']}")

                # メール送信
                send_email(
                    subject="面接予約完了",
                    body=f"{state['name']}（{state['university']}）様の面接予約が完了しました。\n日時: {format_date_with_weekday(selected_event['start'], selected_event['end'])}",
                    to="kfuka@sisco-consulting.co.jp"
                )

                return {"reply": f"面接予約を以下の日程で完了しました:\n{format_date_with_weekday(selected_event['start'], selected_event['end'])}"}
            else:
                return {"reply": "選択した番号が無効です。もう一度番号を入力してください。"}

        return {"reply": "処理を進めることができませんでした。再度お試しください。"}

    except Exception as e:
        logger.error(f"【ERROR】エラーが発生しました: {e}")
        return {"reply": "内部エラーが発生しました。もう一度お試しください。"}
