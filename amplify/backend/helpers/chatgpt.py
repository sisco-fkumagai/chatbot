import os
from dotenv import load_dotenv
import openai

# 環境変数をロード
load_dotenv(override=True)

openai.api_key = os.getenv("OPENAI_API_KEY")

def chat_with_gpt(prompt, system_message=None):
    """
    ChatGPTとのやり取りを管理します。
    :param prompt: ユーザーの入力内容や具体的な指示が含まれるプロンプト
    :param system_message: チャットの全体的な文脈や役割を定義するシステムメッセージ
    :return: ChatGPTの応答
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
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"
