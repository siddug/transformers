import re
from requests import Request
from fastapi import FastAPI
from apps.translator import Translator
from apps.grounded_gpt import Search, Draft, Main
from main import Chain
from pydantic import BaseModel

# This is a qucik api server to test the chain reaction apps
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!", "status": "ok"}


# App 1: Translator
class TranslateRequest(BaseModel):
    text: str
    languages: list[str]

@app.post("/chain/samples/translate")
def run_translate(request: TranslateRequest):
    first_language = request.languages[0] if len(request.languages) > 0 else "Telugu"
    telugu = Translator(language=first_language)
    context = {
        "text": request.text or "Hello, how are you?"
    }
    telugu.run(context=context)
    return context

# App 2: Translator Chain
@app.post("/chain/samples/translate-chain")
def run_translate_chain(request: TranslateRequest):
    languages = request.languages
    if len(languages) == 0:
        languages = ["Telugu", "Hindi", "English"]

    translators = list(map(lambda language: Translator(language=language), languages))
    for a, b in zip(translators[:-1], translators[1:]):
        a >> b
    chain = Chain(starting_block=translators[0])
    context = {
        "text": request.text or "Hello, how are you?"
    }
    chain.run(context=context)

    return context


# App 3: Grounded GPT

class GroundedGPTRequest(BaseModel):
    query: str

@app.post("/chain/samples/grounded-gpt")
def run_grounded_gpt(request: GroundedGPTRequest):
    search = Search(retries=3)
    draft = Draft(retries=3)
    main = Main()
    search >> main
    main - "draft" >> draft
    main - "search" >> search
    context = {
        "query": request.query or "What's the weather today in Singapore?"
    }
    chain = Chain(starting_block=main)
    chain.run(context=context)
    return context





