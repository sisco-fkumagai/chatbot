import os
from dotenv import load_dotenv
import openai

# 環境変数をロード
load_dotenv(override=True)

# APIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")
print(f"Loaded API Key: {openai.api_key}")


def chat_with_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "あなたは採用管理システムのアシスタントです。応答に「ボット:」のような修飾を付けないでください。"}, {"role": "user", "content": prompt}],
        )
        return response['choices'][0]['message']['content']
    except Exception as e: 
        return f"エラーが発生しました: {str(e)}"
