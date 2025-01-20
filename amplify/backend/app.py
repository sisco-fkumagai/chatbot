import os
import json
import re
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
import uuid

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
    user_id: str = None

# JSTタイムゾーン設定
JST = pytz_timezone("Asia/Tokyo")

# 会話の状態を管理するグローバル辞書
conversation_state = {}

# FAQデータをロード
FAQ_PATH = os.path.join(os.path.dirname(__file__), "helpers", "faq.json")
faq_data = load_faq(FAQ_PATH)


def insert_line_breaks(text):
    """
    テキストに改行を適切に挿入する。
    - 句点ごとに改行を挿入。
    - 番号付きリスト（1. や 2. など）の前後に改行を追加。
    """
    if not isinstance(text, str):
        return text

    # 初期テキストをログに記録
    print(f"【DEBUG】改行挿入前: {text}")

    # 句点（。）ごとに改行を追加。ただし、リスト番号は除外
    text = re.sub(r'(?<!\d)\。', '。\n', text)

    # 番号付きリスト（1. や 2. など）の後ろに改行を追加
    text = re.sub(r'(\d+\.\s)', r'\n\1', text)

    # 最終テキストをログに記録
    print(f"【DEBUG】改行挿入後: {text}")

    return text.strip()



def parse_period(user_message):
    """
    ユーザー入力の期間表現を具体的な日付範囲に変換する。
    """
    today = datetime.today()
    weekdays = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}

    if "来週" in user_message:
        start_date = today + timedelta(days=(7 - today.weekday()))
        end_date = start_date + timedelta(days=6)
    elif "今週" in user_message:
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif "から" in user_message and "まで" in user_message:
        # 例: "今週の木曜から金曜"
        parts = user_message.split("から")
        start_day = parts[0][-2:]
        end_day = parts[1][:2]

        if start_day in weekdays and end_day in weekdays:
            start_date = today - timedelta(days=today.weekday()) + timedelta(days=weekdays[start_day])
            end_date = today - timedelta(days=today.weekday()) + timedelta(days=weekdays[end_day])
        else:
            raise ValueError("日付範囲の解析に失敗しました")
    else:
        # デフォルトは1週間
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

def clean_response(response):
    """
    ChatGPTの応答をクリーンアップして、不正な制御文字やフォーマットの問題を解消する。
    """
    if isinstance(response, dict):
        return {k: clean_response(v) for k, v in response.items()}
    elif isinstance(response, str):
        response = re.sub(r'[\x00-\x1F\x7F]', '', response)
        response = response.strip()
        return response
    return response


@app.post("/chat")
async def chat(request: ChatRequest):
    debug_log = []  # デバッグ情報を収集するリスト

    try:
        # ユーザーIDを取得
        user_id = request.user_id or str(uuid.uuid4())
        debug_log.append(f"【DEBUG-1】ユーザーID: {user_id}")

        # 会話状態の初期化
        if user_id not in conversation_state:
            conversation_state[user_id] = {
                "step": "initial",
                "context": [],
                "name": None,
                "university": None,
                "date": None,
                "suggested_dates": [],
            }
        state = conversation_state[user_id]
        #debug_log.append(f"【DEBUG-3】現在のステップ: {state['step']}")

        question = request.message.strip()
        debug_log.append(f"【DEBUG-2】ユーザーの応答: {question}")

        # 現在の日付を取得
        today = datetime.now().strftime("%Y-%m-%d")
        debug_log.append(f"【DEBUG-3】今日の日付: {today}")

        # 初期ステップ: 名前、大学、希望日程を聞く
        if state["step"] == "initial":
            chat_prompt = (
                f"ユーザーが以下のオプションから選択しました: {request.message}\n"
                "1. 一次面接の日程調整\n"
                "2. 採用活動に関する質問\n"
                "選択に基づいて次のステップを生成してください。\n"
                "一次面接の日程調整と採用活動に関する質問への回答以外は行わないでください。\n"
                "一次面接以外の日程調整はしないでください。\n"
                "日程調整を選んだ場合は、名前、大学、希望日程を聞いてください。\n"
                "希望日程は「今週」「来週」などの表現でも進めてください。\n"
                "次のステップ: 日程調整はask_details、質問はfaq_handling\n"
                "出力形式: {\"next_step\": \"次のステップ\", \"reply\": \"応答文\"}"
            )
            chat_response = chat_with_gpt(chat_prompt)
            debug_log.append(f"【DEBUG-4-1】ChatGPT応答: {chat_response}")
            
            # 応答が辞書の場合はそのまま利用
            if isinstance(chat_response, dict):
                response_data = chat_response
            elif isinstance(chat_response, str):
                # 応答が文字列の場合はパースを試みる
                try:
                    response_data = json.loads(chat_response)
                except json.JSONDecodeError as e:
                    debug_log.append(f"【ERROR】JSON解析失敗: {str(e)}")
                    return {
                        "reply": "サーバー内部エラーが発生しました。応答を解析できませんでした。",
                        "debug_log": debug_log,
                    }
            else:
                debug_log.append("【ERROR】ChatGPT応答が不明な形式です。")
                return {
                    "reply": "サーバー内部エラーが発生しました。不明な応答形式です。",
                    "debug_log": debug_log,
                }
            
            # 応答の生成箇所で改行を挿入
            if "reply" in response_data:
                response_data["reply"] = insert_line_breaks(response_data["reply"])

            # ステップ更新と応答送信
            state["step"] = response_data.get("next_step", "ask_details")
            debug_log.append(f"【DEBUG-4-2】次のステップ: {state['step']}")
            return {
                "reply": response_data.get("reply", "選択肢を再度教えてください。"),
                "debug_log": debug_log
            }
        
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

                # ChatGPTの応答をパース
                if isinstance(chat_response, str):
                    try:
                        response_data = json.loads(chat_response)
                    except json.JSONDecodeError as e:
                        debug_log.append(f"【ERROR】FAQ JSON解析失敗: {str(e)}")
                        return {
                            "reply": "サーバー内部エラーが発生しました。",
                            "debug_log": debug_log,
                        }
                elif isinstance(chat_response, dict):
                    response_data = chat_response
                else:
                    debug_log.append("【ERROR】FAQ応答形式が不明です。")
                    return {"reply": "不明なエラーが発生しました。", "debug_log": debug_log}

                return {"reply": response_data.get("reply", "もう一度質問を入力してください。"), "debug_log": debug_log}
        
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
            debug_log.append(f"【DEBUG-5】ChatGPT応答: {chat_response}")
            
            try:
                # ChatGPT応答のクリーンアップ
                cleaned_response = clean_response(chat_response)
                debug_log.append(f"【DEBUG-5-1】クリーンアップ後の応答: {cleaned_response}")

                # クリーンアップ後のJSONをパース
                response_data = json.loads(cleaned_response) if isinstance(cleaned_response, str) else cleaned_response
                debug_log.append(f"【DEBUG-5-2】JSONパース後のデータ: {response_data}")
                         
                # `reply`フィールドが再度JSON形式の場合の処理
                if isinstance(response_data.get("reply"), str) and "{" in response_data["reply"]:
                    try:
                        nested_data_start = response_data["reply"].find("{")
                        nested_data = json.loads(response_data["reply"][nested_data_start:])
                        response_data.update(nested_data)
                        debug_log.append(f"【DEBUG-5-3】埋め込まれたJSONを統合: {response_data}")
                    except json.JSONDecodeError as e:
                        debug_log.append(f"【WARNING】埋め込まれたJSONの解析に失敗: {str(e)}")

                # 必要な情報を抽出
                name = response_data.get("name")
                university = response_data.get("university")
                date = response_data.get("date")
                next_step = response_data.get("next_step", "suggest_dates")

                # 情報が不足しているかチェック
                if not all([name, university, date]):
                    debug_log.append(f"【WARNING】情報が不足しています: 名前={name}, 大学={university}, 希望日程={date}")
                    return {
                        "reply": response_data.get("reply", "情報が不足しています。もう一度教えてください。"),
                        "debug_log": debug_log,
                    }
                
                # 日程解析（期間表現を具体的な日付範囲に変換）
                try:
                    start_date, end_date = parse_period(date)
                    state["date"] = f"{start_date} ~ {end_date}"  # 具体的な日付範囲を記録
                    debug_log.append(f"【DEBUG-7】解析された日程範囲: {state['date']}")
                except Exception as e:
                    debug_log.append(f"【ERROR】日程解析失敗: {str(e)}")
                    return {
                        "reply": "希望日程の解析に失敗しました。具体的な日程を教えてください。",
                        "debug_log": debug_log,
                    }

                # `state` の更新
                state.update({
                    "name": name,
                    "university": university,
                    "date": state["date"],  # 解析された日程範囲を保持
                    "step": next_step,  # 必ず次のステップを'suggest_dates'に設定
                })

                # デバッグログに更新内容を記録
                debug_log.append(f"【DEBUG-5-2】抽出された名前: {state['name']}")
                debug_log.append(f"【DEBUG-5-3】抽出された大学: {state['university']}")
                debug_log.append(f"【DEBUG-5-4】抽出された希望日程: {state['date']}")
                debug_log.append(f"【DEBUG-6】state更新後: {state}")

                # 応答の生成箇所で改行を挿入
                if "reply" in response_data:
                    response_data["reply"] = insert_line_breaks(response_data["reply"])

                # 次のステップへ進む応答を返す
                state["step"] = response_data.get("next_step", "suggest_dates")
                return {
                    "reply": f"{state['name']}さん、情報の提供ありがとうございます。「{state['date']}」で進めてもよろしいでしょうか？",
                    "debug_log": debug_log,
                }

            except json.JSONDecodeError as e:
                debug_log.append(f"【ERROR】JSON解析失敗: {str(e)}")
                return {
                    "reply": "内部エラーが発生しました。応答の解析に失敗しました。",
                    "debug_log": debug_log,
                }
            except Exception as e:
                debug_log.append(f"【ERROR】予期せぬエラー: {str(e)}")
                return {
                    "reply": "予期せぬエラーが発生しました。再度お試しください。",
                    "debug_log": debug_log,
                }


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
                debug_log.append(f"【DEBUG-6】削除対象イベントID: {event['id']}")  # 削除対象をログに記録
                delete_event_from_calendar(event["id"])  # 同じ日程の「空き」を削除
                add_event_to_calendar(event["start"], 1.5, "仮予約")  # 仮予約を作成
                debug_log.append(f"【DEBUG-7】仮予約作成: {event['start']} ~ {event['end']}")

            state["suggested_dates"] = available_events
            # 番号付きで日程を提示
            formatted_events = "\n".join([
                f"{i + 1}. {format_date_with_weekday(event['start'], event['end'])}" for i, event in enumerate(available_events)
            ])
            debug_log.append(f"【DEBUG-8】提案された日程: {formatted_events}")

            # ChatGPTに応答文を生成させる
            chat_prompt_dates = (
                f"以下の日程が見つかりました:\n{formatted_events}\n"
                "ユーザーに番号で選んでもらうような応答文を生成してください。\n"
                "出力形式: {\"reply\": \"応答文\"}"
            )
            chat_response = clean_response(chat_with_gpt(chat_prompt_dates))
            debug_log.append(f"【DEBUG-9】ChatGPT応答: {chat_response}")
            if isinstance(chat_response, str):
                try:
                    response_data = json.loads(chat_response)
                except json.JSONDecodeError as e:
                    debug_log.append(f"【ERROR】日程提案 JSON解析失敗: {str(e)}")
                    return {
                        "reply": "サーバー内部エラーが発生しました。",
                        "debug_log": debug_log,
                    }
            elif isinstance(chat_response, dict):
                response_data = chat_response
            else:
                debug_log.append("【ERROR】日程提案応答形式が不明です。")
                return {"reply": "不明なエラーが発生しました。", "debug_log": debug_log}
            
            if "reply" in response_data:
                response_data["reply"] = insert_line_breaks(response_data["reply"])

            state["step"] = "confirm_date"
            return {"reply": response_data.get("reply"),"debug_log": debug_log,}


        # 提案された日程から番号を選ぶステップ
        if state["step"] == "confirm_date":
            # ユーザーが選択した番号を取得
            selected_index = int(request.message.strip()) - 1
            if 0 <= selected_index < len(state["suggested_dates"]):
                        
                # 提案された日程から選択された日程を取得
                selected_event = state["suggested_dates"][selected_index]
                # 日程を確定し、「仮予約」を削除して「空き」を再作成
                for i, event in enumerate(state["suggested_dates"]):
                    debug_log.append(f"【DEBUG-10】選択された日程: {event}")
                    # 選択された日程は「仮予約」を削除して予約完了イベントを作成
                    delete_event_from_calendar(event["id"])
                    debug_log.append(f"【DEBUG-11】削除対象イベント: {event['id']}")
                    if i == selected_index:
                        add_event_to_calendar(event["start"], 1.5, f"{state['name']} ({state['university']})")
                        debug_log.append(f"【DEBUG-12】予約完了イベント作成: {event['start']} ~ {event['end']}")
                    else:
                        debug_log.append(f"【DEBUG-13】非選択の日程: {event}")
                        # 他の日程は「仮予約」を削除して「空き」イベントを作成
                        add_event_to_calendar(event["start"], 1.5, "空き")
                        debug_log.append(f"【DEBUG-14】仮予約削除および空き再作成: {event['start']} ~ {event['end']}")

                # メール送信
                send_email(
                    subject="面接予約完了",
                    body=f"{state['name']}（{state['university']}）様の面接予約が完了しました。\n日時: {format_date_with_weekday(selected_event['start'], selected_event['end'])}",
                    to="kfuka@sisco-consulting.co.jp"
                )

                # 応答の生成箇所で改行を挿入
                if "reply" in response_data:
                    response_data["reply"] = insert_line_breaks(response_data["reply"])

                # 予約完了のメッセージをユーザーに返す
                debug_log.append(f"【DEBUG-15】メール送信完了: {state['name']}（{state['university']}）様の予約が確定しました。")
                return {
                    "reply": f"面接予約を以下の日程で完了しました:\n{format_date_with_weekday(selected_event['start'], selected_event['end'])}",
                    "debug_log": debug_log  # デバッグ情報を含めて返す
                }
            else:
                return {
                    "reply": "選択した番号が無効です。もう一度番号を入力してください。",
                    "debug_log": debug_log
                }

    except Exception as e:
        debug_log.append(f"エラー: {str(e)}")
        return {
            "reply": "内部エラーが発生しました。もう一度お試しください。",
            "debug_log": debug_log  # エラー時のデバッグ情報を含める
        }
