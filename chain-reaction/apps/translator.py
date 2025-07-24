from dotenv import load_dotenv
import os

from utils.llm import Mistral
from utils.llm import Gemini
from main import Block


class Translator(Block):
    def __init__(self, language: str = "Telugu"):
        load_dotenv()  # take environment variables from .env.
        super().__init__(name=f"Translator to {language}", description=f"Translate the text to {language}", retries=3)

        # LLM setup
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        self.mistral_api_key = mistral_api_key
        self.mistral_llm = Mistral(api_key=mistral_api_key)
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.gemini_llm = Gemini(api_key=self.gemini_api_key)

        # Block specific setup
        self.language = language
    
    def prepare(self, context):
        return {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                    You are a translator. Translate the following text to {self.language}.
                    {context["text"]}
                    Return only the translated text. Do not include any other text.
                    """,
                    "type": "text"
                },
            ]
        }
    
    def execute(self, context, prepare_response):
        self.rotate_llm_token = 0
        self.rotate_llm_token = (self.rotate_llm_token + 1) % 2
        if self.rotate_llm_token == 0:
            return self.mistral_llm.generate_text(model="mistral-large-latest", messages=prepare_response["messages"])
        else:
            return self.gemini_llm.generate_text(model="gemini-2.0-flash", messages=prepare_response["messages"])

    def post_process(self, context, prepare_response, execute_response):
        context["text"] = execute_response
        context["results"] = context["results"] if "results" in context else {}
        context["results"][self.language] = context["text"]
        return "default" # same as not returning any action

    def execute_fallback(self, context, prepare_response, error):
        return "Error: " + str(error)