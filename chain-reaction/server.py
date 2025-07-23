from requests import Request
from fastapi import FastAPI
from test import Translator
from pydantic import BaseModel


# This is a qucik api server to test the chain reaction apps
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


class TranslateRequest(BaseModel):
    text: str
    language: str | None = None

@app.post("/chain/samples/translate")
def run_easy_chain(request: TranslateRequest):
    telugu = Translator(language=request.language or "Telugu")
    context = {
        "text": request.text or "Hello, how are you?"
    }
    telugu.run(context=context)
    return context






