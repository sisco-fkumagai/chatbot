import os
from dotenv import load_dotenv
import openai
import logging
import json

# 環境変数をロード
load_dotenv(override=True)

openai.api_key = os.getenv("OPENAI_API_KEY")

logging.debug(f"API: {openai.api_key}")

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def chat_with_gpt(prompt, system_message=None):
    """
    ChatGPTとのやり取りを管理します。
    :param prompt: ユーザーの入力内容や具体的な指示が含まれるプロンプト
    :param system_message: チャットの全体的な文脈や役割を定義するシステムメッセージ
    :return: JSON形式のChatGPT応答
    """
    try:
        # デフォルトのシステムメッセージ（役割の説明）
        default_system_message = (
            "あなたは採用活動を支援するAIアシスタントです。\n"
            "ユーザーとの自然な会話を維持しながら、要求を正確に理解し、応答してください。\n"
            "必要に応じてステップや処理の流れを提案してください。"
        )

        # システムメッセージが指定されていない場合はデフォルトを使用
        system_content = system_message if system_message else default_system_message

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
        )

        # 応答を辞書形式にパース
        content = response['choices'][0]['message']['content']
        try:
            parsed_response = json.loads(content)
            return parsed_response  # 辞書を返す
        except json.JSONDecodeError:
            # 応答が JSON 形式でない場合はそのまま返す
            return {"reply": content, "next_step": None}

    except Exception as e:
        return {"reply": f"エラーが発生しました: {str(e)}", "next_step": None}
