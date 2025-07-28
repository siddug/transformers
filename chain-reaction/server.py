import re
from requests import Request
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from apps.translator import Translator
from apps.grounded_gpt import Search, Draft, Main
from main import Chain
from pydantic import BaseModel
from database import get_db, qdrant_client, task_queue, create_tables, create_qdrant_chunks_collection, github_queue, rag_queue
from tasks import long_running_task, process_translation_batch, process_vector_embedding, generate_file_jobs_for_repo, generate_rag_response
from s3_utils import upload_file, download_file, delete_file, list_files, get_file_info
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from apps.github_rag import ingest_repo, get_repo_files, get_file_details, create_rag_request, get_rag_request_status

# This is a qucik api server to test the chain reaction apps
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://nextjs:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    try:
        create_tables()
        print("Database tables initialized successfully")
        create_qdrant_chunks_collection()
        print("Qdrant chunks collection created successfully")
    except Exception as e:
        print(f"Error initializing database tables: {e}")
        # You might want to exit or handle this differently in production
        raise

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


# S3 File Operations Endpoints

@app.post("/files/upload")
async def upload_file_endpoint(file: UploadFile = File(...), bucket: str = "chain-reaction"):
    """Upload a file to MinIO S3"""
    try:
        contents = await file.read()
        result = upload_file(
            file_data=contents,
            file_name=file.filename,
            bucket_name=bucket,
            content_type=file.content_type or "application/octet-stream"
        )
        return {
            "message": "File uploaded successfully",
            "file_info": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_name}")
async def download_file_endpoint(file_name: str, bucket: str = "chain-reaction"):
    """Download a file from MinIO S3"""
    try:
        file_data = download_file(file_name, bucket)
        return StreamingResponse(
            BytesIO(file_data),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/files/{file_name}")
async def delete_file_endpoint(file_name: str, bucket: str = "chain-reaction"):
    """Delete a file from MinIO S3"""
    try:
        result = delete_file(file_name, bucket)
        return {"message": "File deleted successfully", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files")
async def list_files_endpoint(bucket: str = "chain-reaction", prefix: str = ""):
    """List files in MinIO S3 bucket"""
    try:
        files = list_files(bucket, prefix)
        return {"files": files, "count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_name}/info")
async def get_file_info_endpoint(file_name: str, bucket: str = "chain-reaction"):
    """Get information about a specific file"""
    try:
        info = get_file_info(file_name, bucket)
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# App 4: Github RAG
class GithubRAGRequest(BaseModel):
    repo_url: str

@app.post("/chain/samples/github-rag")
def run_github_rag(request: GithubRAGRequest):
    repo_id, job_creation_info = ingest_repo(request.repo_url)
    if job_creation_info:
        github_queue.enqueue(generate_file_jobs_for_repo, repo_id, job_id=job_creation_info["job_id"])
    return {"message": "Repo ingested successfully", "repo_id": repo_id, "job_creation_info": job_creation_info, "success": "ok"}

class GithubRAGFilesRequest(BaseModel):
    repo_id: str
    page: int
    page_size: int

# paginated fetch of repo files
@app.post("/chain/samples/github-rag/files")
def run_github_rag_files(request: GithubRAGFilesRequest):
    print(f"Running github rag files for repo {request.repo_id} with page {request.page} and page size {request.page_size}")
    files, total_num_files, page, page_size = get_repo_files(request.repo_id, request.page, request.page_size)
    return {"files": files, "total_num_files": total_num_files, "page": page, "page_size": page_size, "success": "ok"}

# get file details
@app.get("/chain/samples/github-rag/files/{file_id}")
def run_github_rag_file_details(file_id: str):
    file = get_file_details(file_id)
    return {"file": file, "success": "ok"}

class GithubRAGRequest(BaseModel):
    repo_id: str
    messages: list[dict]

@app.post("/chain/samples/github-rag/request/create")
def run_github_rag_request(request: GithubRAGRequest):
    request_id, job_creation_info = create_rag_request(request.repo_id, request.messages)
    if job_creation_info:
        rag_queue.enqueue(generate_rag_response, request_id, job_id=job_creation_info["job_id"])
    return {"request_id": request_id, "job_creation_info": job_creation_info, "success": "ok"}

class GithubRAGRequestStatusRequest(BaseModel):
    request_id: str

@app.post("/chain/samples/github-rag/request/status")
def run_github_rag_request_status(request: GithubRAGRequestStatusRequest):
    status = get_rag_request_status(request.request_id)
    return {"status": status, "success": "ok"}


