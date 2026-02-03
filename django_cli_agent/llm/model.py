# import requests


# class LLM:
#     def __init__(self, model_name: str = "codellama:7b"):
#         self.model_name = model_name
#         self.api_url = "http://localhost:11434/api/generate"

#     def generate(self, prompt: str) -> str:
#         payload = {
#             "model": self.model_name,
#             "prompt": prompt,
#             "stream": False
#         }

#         try:
#             response = requests.post(self.api_url, json=payload)
#             response.raise_for_status()
#             data = response.json()
#             return data.get("response", "").strip()

#         except requests.exceptions.RequestException as e:
#             return f"[ERROR] LLM request failed: {e}"

import requests


class LLM:
    def __init__(self, model_name: str = "codellama:7b"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """
        Generate LLM response
        
        Args:
            prompt: The input prompt
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
                        Lower temperature = better instruction following
        
        Returns:
            Generated text response
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 40
            }
        }

        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

        except requests.exceptions.RequestException as e:
            return f"[ERROR] LLM request failed: {e}"