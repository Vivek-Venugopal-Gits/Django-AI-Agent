import requests


class LLM:
    def __init__(self, model_name: str = "codellama:7b"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

        except requests.exceptions.RequestException as e:
            return f"[ERROR] LLM request failed: {e}"
