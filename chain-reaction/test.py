from llm import Mistral
from main import Block, Chain

class Translator(Block):
    def __init__(self, language: str = "Telugu"):
        import os
        super().__init__(name=f"Translator to {language}", description=f"Translate the text to {language}")
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        self.llm = Mistral(api_key=mistral_api_key)
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
        return self.llm.generate_text(model="mistral-large-latest", messages=prepare_response["messages"])

    def post_process(self, context, prepare_response, execute_response):
        context["text"] = execute_response


# test code
if __name__ == "__main__":  # Fixed: __ not **

    # Simple block
    telugu = Translator(language="Telugu")
    context = {
        "text": "Hello, how are you?"
    }
    telugu.run(context=context)
    print(context)

    # Simple chain telugu -> hindi
    hindi = Translator(language="Hindi")
    telugu >> "default" >> hindi
    context = {
        "text": "I like music"
    }
    chain = Chain(starting_block=telugu)
    chain.run(context=context)
    print(context)