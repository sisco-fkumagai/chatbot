import os
import json

# faq.json の絶対パスを取得
faq_path = os.path.join(os.path.dirname(__file__), "faq.json")

# ファイルの存在を確認してデバッグ出力
if not os.path.exists(faq_path):
    raise FileNotFoundError(f"FAQファイルが見つかりません: {faq_path}")
else:
    print(f"FAQファイルのパス: {faq_path}")

with open(faq_path, "r", encoding="utf-8") as file:
    FAQ_DATA = json.load(file)

def get_faq_response(message):
    """
    FAQデータに基づいて適切な応答を返す。
    """
    for faq in FAQ_DATA["faqs"]:
        if faq["question"] in message:
            return faq["answer"]
    return "その質問についての情報はありません。採用担当者へお問い合わせください。"
