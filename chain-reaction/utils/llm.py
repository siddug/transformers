# Simple wrappers around llms. 
# TODO: (SG) Add tensorzero here once we dockerize the whole thing

import requests
import json

class LLM:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_text(self, messages: list[dict]):
        pass

    def parse_response(self, response: str):
        # trim the response, then ```json <content> ``` of the form should be parsed and only JSON.parse(content) should be returned
        response = response.strip()
        if response.startswith("```json") and response.endswith("```"):
            response = response[7:-3]
        try:
            return json.loads(response)
        except Exception as e:
            raise Exception(f"Error parsing response: {str(e)} \n\n Response: {response}")

class Mistral(LLM):
    models = {
        "mistral-large-latest": {
            "supportsImages": True,
        }
    }

    model = "mistral-large-latest"

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key)
        if model is not None and model in self.models:
            self.model = model

    def format_messages(self, messages: list[dict]):
        # each message is of the form role, content and type. content = {"type": "image_url", "dataUrl": "url"} for images. type = image_url and text other wise
        formatted_messages = []
        for message in messages:
            if message["type"] == "image_url" and self.models[self.model]["supportsImages"]:
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

    def generate_text(self, messages: list[dict], model: str = None, max_tokens: int = 1000):
        if model is not None and model in self.models:
            self.model = model

        if self.model not in self.models:
            raise Exception(f"Model {self.model} not supported")

        formatted_messages = self.format_messages(messages)

        print("CHECKING MODEL", self.model)

        body = {
            "model": self.model,
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
    

    
class Gemini(LLM):

    models = {
        "gemini-2.0-flash": {
            "supportsImages": True,
        }
    }

    model = "gemini-2.0-flash"

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key)
        if model is not None and model in self.models:
            self.model = model

    def format_messages(self, messages: list[dict]):
        # each message is of the form role, content and type. content = {"type": "image_url", "dataUrl": "url", "mime": "image/png"} for images. type = image_url and text other wise
        formatted_messages = []
        for message in messages:
            # strip away system messsages if any
            if message["role"] == "system":
                continue
            if message["type"] == "image_url" and self.models[self.model]["supportsImages"]:
                formatted_messages.append({
                    "role": "user" if message["role"] == "user" else "model",
                    "parts": [
                        {
                            "inlineData": {
                                "data": message["content"]["dataUrl"].split(",")[1],
                                "mime_type": message["content"]["mime"]
                            }
                        }
                    ]
                })
            else:
                formatted_messages.append({
                    "role": "user" if message["role"] == "user" else "model",
                    "parts": [
                        {
                            "text": message["content"]
                        }
                    ]
                })

        return formatted_messages

    def generate_text(self, messages: list[dict], model: str = None, max_tokens: int = 1000):
        if model is not None and model in self.models:
            self.model = model

        if self.model not in self.models:
            raise Exception(f"Model {self.model} not supported")

        formatted_messages = self.format_messages(messages)

        system_messages = [msg for msg in formatted_messages if msg["role"] == "system"]
        system_message = system_messages[0]["content"][0]["text"] if len(system_messages) > 0 and "content" in system_messages[0] and system_messages[0]["type"] == "text" else ""

        body = {
            "contents": formatted_messages,
            "generationConfig": {
                "temperature": 1.0,
                "topP": 0.8,
                "topK": 10,
                "maxOutputTokens": max_tokens
            },
            "systemInstruction": {
                "parts": [
                    {
                        "text": system_message
                    }
                ]
            }
        }

        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/" + self.model + ":generateContent?key=" + self.api_key,
            json=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
        )

        if response.status_code != 200:
            raise Exception(f"Failed to generate text: {response.status_code} {response.text}")
        
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    