from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from helpers.chatgpt import chat_with_gpt
from helpers.calendar import add_event_to_calendar, get_events_from_calendar
from helpers.email import create_email_draft

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて特定のオリジンに限定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 入力データモデル
class ChatRequest(BaseModel):
    message: str
    context: list

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    ChatGPTを利用してユーザーと会話し、GoogleカレンダーとGmailを操作。
    """
    try:
        # ChatGPTへのプロンプト作成
        prompt = (
            "あなたは採用面接アシスタントです。以下の文脈に基づき、"
            "適切な質問を行い、Googleカレンダーの「空き」というタイトルの日程を利用して日程調整を行ってください。"
            "Googleカレンダーにない日程を提示しないでください。"
            "行えることは一次面接の日程調整と採用活動における質問への回答のみです。"
            "一次面接以外では日程調整しないでください"
            "採用活動に対する質問以外には答えないでください\n\n"
            f"文脈: {request.context}\nユーザー: {request.message}"
        )
        chat_response = chat_with_gpt(prompt)
        response = {"reply": chat_response}

        # ChatGPTの応答に応じた処理
        if "候補日程" in chat_response:
            # カレンダーから候補日程を取得
            events = get_events_from_calendar("2024-12-25")  # 固定日付を動的に処理可能
            available_slots = events[:3]  # 最大3つの候補を取得
            response["reply"] = f"次の候補日程はいかがでしょうか？\n{available_slots}"

            # 候補日程を仮予約
            for slot in available_slots:
                add_event_to_calendar(
                    date=slot["startTime"], 
                    hours=2, 
                    title="仮予約"
                )

        elif "確定" in chat_response:
            # ユーザーが日程を確定
            selected_slot = request.message  # 確定するスロットをユーザーの入力から取得
            add_event_to_calendar(
                date=selected_slot["startTime"],
                hours=2,
                title=f"{request.context[0]['name']} - {request.context[0]['university']}"
            )

            # 確定情報をメール送信
            create_email_draft(
                recipients="example@gmail.com",
                subject="面接日程確定",
                body=f"以下の日程で確定しました: {selected_slot['startTime']}"
            )
            response["reply"] = "日程が確定しました。ありがとうございました！"

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サーバーエラー: {str(e)}")
