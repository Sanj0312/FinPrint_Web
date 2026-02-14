import os

import requests


class BlackboardService:
    DEFAULT_BASE_URL = "https://app.backboard.io/api"

    def __init__(self):
        self.api_key = os.getenv("BLACKBOARD_API_KEY") or os.getenv("BACKBOARD_API_KEY")
        if not self.api_key:
            raise ValueError("BLACKBOARD_API_KEY or BACKBOARD_API_KEY is not set.")
        self.base_url = (
            os.getenv("BACKBOARD_API_BASE_URL")
            or os.getenv("BLACKBOARD_API_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")

    def get_user_profile(self) -> dict:
        endpoint = f"{self.base_url}/models"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        response = requests.get(endpoint, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        models = data.get("models", []) if isinstance(data, dict) else []
        providers = sorted({m.get("provider") for m in models if isinstance(m, dict) and m.get("provider")})
        return {
            "name": "Backboard API Key",
            "email": "Not provided by API key endpoint",
            "profile_info": {
                "api_base_url": self.base_url,
                "models_count": len(models),
                "providers": providers,
            },
        }
