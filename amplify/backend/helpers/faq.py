import json
import os
from difflib import get_close_matches
import logging

logger = logging.getLogger(__name__)

def load_faq(file_path="faq.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"FAQファイルが見つかりません: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"FAQファイルの読み込みエラー: {e}")
        return {}

def search_faq(question, faq_data, threshold=0.4):
    """
    FAQデータから質問に近い回答を検索する。
    """
    questions = [item["question"] for item in faq_data]
    matches = get_close_matches(question, questions, n=1, cutoff=threshold)

    if matches:
        matched_question = matches[0]
        for faq_item in faq_data:
            if faq_item["question"] == matched_question:
                return faq_item["answer"]
    return None
