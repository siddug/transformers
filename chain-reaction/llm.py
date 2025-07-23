# Simple wrappers around llms. 
# TODO: (SG) Add tensorzero here once we dockerize the whole thing

import requests

class LLM:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_text(self, messages: list[dict]):
        pass

class Mistral(LLM):

    models = {
        "mistral-large-latest": {
            "supportsImages": True,
        }
    }

    def __init__(self, api_key: str):
        super().__init__(api_key)

    def format_messages(self, model, messages: list[dict]):
        # each message is of the form role, content and type. content = {"type": "image_url", "dataUrl": "url"} for images. type = image_url and text other wise
        formatted_messages = []
        for message in messages:
            if message["type"] == "image_url" and self.models[model]["supportsImages"]:
                formatted_messages.append({
                    "role": message["role"],
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": message["content"]["dataUrl"]
                        }
                    ]
                })
            else:
                formatted_messages.append({
                    "role": message["role"],
                    "content": [
                        {
                            "type": "text",
                            "text": message["content"]
                        }
                    ]
                })

        return formatted_messages

    def generate_text(self, model, messages: list[dict], max_tokens: int = 1000):

        if model not in self.models:
            raise Exception(f"Model {model} not supported")

        formatted_messages = self.format_messages(model, messages)

        body = {
            "model": model,
            "messages": formatted_messages,
            "stream": False,
            "max_tokens": max_tokens
        }

        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            json=body)
        
        if response.status_code != 200:
            raise Exception(f"Failed to generate text: {response.status_code} {response.text}")
        
        return response.json()["choices"][0]["message"]["content"]
    