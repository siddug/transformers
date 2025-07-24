import re
from requests import Request
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from apps.translator import Translator
from apps.grounded_gpt import Search, Draft, Main
from main import Chain
from pydantic import BaseModel
from database import get_db, qdrant_client, task_queue
from tasks import long_running_task, process_translation_batch, process_vector_embedding

# This is a qucik api server to test the chain reaction apps
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, World!", "status": "ok"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "services": {
            "postgres": False,
            "redis": False,
            "qdrant": False
        }
    }
    
    # Check PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["postgres"] = True
    except Exception as e:
        print(f"PostgreSQL health check failed: {e}")
    
    # Check Redis
    try:
        task_queue.connection.ping()
        health_status["services"]["redis"] = True
    except Exception as e:
        print(f"Redis health check failed: {e}")
    
    # Check Qdrant
    try:
        qdrant_client.get_collections()
        health_status["services"]["qdrant"] = True
    except Exception as e:
        print(f"Qdrant health check failed: {e}")
    
    # Update overall status
    if not all(health_status["services"].values()):
        health_status["status"] = "degraded"
    
    return health_status


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
