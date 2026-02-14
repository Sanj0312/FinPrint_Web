import json
import os

import google.generativeai as genai


_ALLOWED_CATEGORIES = {"Food", "Travel", "Shopping", "Subscription", "Utilities", "Other"}


class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def categorize_expense(self, expense_name: str) -> str:
        prompt = (
            "Categorize this expense into one category: "
            "Food, Travel, Shopping, Subscription, Utilities, Other. "
            f"Expense: {expense_name}. "
            "Return only the category name."
        )

        try:
            response = self.model.generate_content(prompt)
            raw_category = (response.text or "").strip()
            normalized = raw_category.split("\n")[0].strip().replace(".", "")
            if normalized in _ALLOWED_CATEGORIES:
                return normalized
            for category in _ALLOWED_CATEGORIES:
                if category.lower() in normalized.lower():
                    return category
            return "Other"
        except Exception:
            return "Other"

    def generate_insights(self, expenses: list[dict]) -> str:
        serialized = json.dumps(expenses, ensure_ascii=True)
        prompt = (
            "Analyze these expenses and generate financial insights: "
            f"{serialized}"
        )

        try:
            response = self.model.generate_content(prompt)
            return (response.text or "No insights available.").strip()
        except Exception:
            return "Unable to generate AI insights at the moment."
