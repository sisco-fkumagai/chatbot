import json

def get_faq_response(user_message):
    try:
        with open("faq.json", "r", encoding="utf-8") as file:
            faq_data = json.load(file)
        for entry in faq_data:
            if entry["keyword"] in user_message:
                return entry["answer"]
        return "申し訳ありませんが、該当する回答が見つかりませんでした。"
    except Exception as e:
        return f"FAQデータの読み込み中にエラーが発生しました: {str(e)}"