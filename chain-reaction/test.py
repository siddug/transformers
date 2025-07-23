from llm import Mistral
from main import Block

class Translator(Block):
    def __init__(self):
        super().__init__(name="Translator", description="Translate the text to Telugu")
        self.llm = Mistral(api_key="jCuSP6YJybcKBiI50STjl5r1Kda0Cimi")
    
    def prepare(self, context):
        return {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                    You are a translator. Translate the following text to Telugu.
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
        context["response"] = execute_response


# test code
if __name__ == "__main__":  # Fixed: __ not **
    trans = Translator()
    context = {
        "text": "Hello, how are you?"
    }
    result = trans.run(context=context)
    print(result)