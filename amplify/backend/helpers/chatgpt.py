import os
from dotenv import load_dotenv
import openai
import logging

# 環境変数をロード
load_dotenv(override=True)

openai.api_key = os.getenv("OPENAI_API_KEY")

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

        # レスポンスをデバッグログに記録
        logger.debug(f"OpenAI API Response: {response}")

        # 必要な部分を整形して返す
        reply = response["choices"][0]["message"]["content"].strip()
        return {"reply": reply, "raw_response": response}
    
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API Error: {str(e)}")
        return {"error": f"OpenAI API エラーが発生しました: {str(e)}"}
        
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        return f"エラーが発生しました: {str(e)}"
