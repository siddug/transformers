"""
The idea - Given a github repo, give an interface for the user to ask questions about the codebase.

Implementation:
1. Ingestion API - 
    - Given a github repo, get the files and folder structure of the codebase
    - Ignore all the files that are not relevant to the codebase (like .git, .env, etc.)
    - For each file, 
        - Summarize the file
        - Schedule a RQ job to convert the file into chunks, 
        - Convert the chunks into vector embeddings
        - Store the summary, chunks, file path and Github repo url and vector embeddings in the database
    - Expose this as an API
        - In the API, we should see total number of files, how many of them are being processed, how many are processed, how many are failed (per file)
2. Repo API - 
    - List files and folders in the repo
    - Get relevant chunks of the repo for a given text with metadata
    - Get a particular file from the repo
2. RAG API - 
    - Using chain-reaction framework, create a RAG agent that takes in User's query
    - Blocks: 
        - Embedding gen block - takes in a text and generates an embedding
        - Vector search block - takes in a embedding and searches the vector database for relevant chunks
        - LLM block - takes in user's query + chunks context and generates a response
        - Links:
            - Embedding gen block >> Vector search block
            - Vector search block >> LLM block
            - LLM block >> END
    - Expose the flow as an API
    - Since this might take time, make blocks and flow's async
    - Each flow run - maintain it as a job in the database with status updates (current block, status, etc.)
    - Expose the job status as an API
3. UI - 
    - NextJS app that accepts a github repo url
    - Take user to Github repo page
    - User can see the files and folders in the repo with status of the files (processing, processed, failed)
    - User can ask questions about the codebase
    - For each question, create a flow run and show the status of the flow run

Next steps:
1. How do we eval this? (Checkout NDCG and Relevancy + Synthetic Q&A generation)
    - What's NDCG?
    - In the retreival step, how do we calculate Contextual Relevancy/ Recall/ Precision?
    - In the generation step, how do we calculate Answer Relevancy/ Faithfulness?
    - How do we generate synthetic Q&A so that we can evaluate the system?
2. What are the generic metrics that we can use to evaluate the system? So I can benchmark RAG against agents?
    - G-eval on the system (custom criteria + eval steps + threshold and using llms to score); Tonality, Safety, Coherence, Answer correctness
    - DAG on the system (graph based evaluation of the system)
3. How do we make the UI interaction better? Instead of polling system? - WebSockets is a good option?
4. Instead of making it a fixed RAG, can we make it an agent with more tools?


PG DB schema:
- Repo
    - id (auto gen uuid)
    - owner
    - name
    - branch
    - added_at
- File
    - id (auto gen uuid)
    - repo_id (foreign key to Repo.id)
    - path
    - raw_content
    - summary
    - summary_status (processing, processed, failed)
    - chunks_status (processing, processed, failed)
    - added_at

Qdrant DB schema:
- Chunk
    - id (auto gen uuid)
    - repo_id 
    - file_id
    - file_path
    - raw_chunk_text
    - vector_embeddings
    - added_at
"""

import uuid
from database import repo_table, file_table, engine, github_queue, rag_requests_table, rag_queue
from sqlalchemy.orm import Session
from sqlalchemy import select, func, insert
from main import Block, Chain
from utils.llm import Mistral, Gemini
import os
from dotenv import load_dotenv
import time
from qdrant_client import QdrantClient

load_dotenv()


# Ingestion and Repo API fn's that will be used by server.py

"""
1. Ingest a repo
Take repo url as input -> break down into owner, name, branch with defaults if not provided. Then check if there's an existing repo in the db. If not, create a new repo.
Start a new job to convert the repo into chunks if the repo is not already in the db. 
Return the repo id.

2. Given a repo id, return paginated list of files and folders in the repo.
Return the list of files and folders. Totals + Page.

3. Given a file id, return the file details.
Return the file details.
"""

def ingest_repo(repo_url: str):
    if "github.com" not in repo_url:
        # check if there's a / in the middle of the url
        if "/" in repo_url:
            # split the url into owner, name, branch
            owner, name = repo_url.split("/")
            branch = "main"
        else:
            raise ValueError("Invalid repo url")
    else:
        repo_url = repo_url.split("github.com/")[-1]
        owner, name = repo_url.split("/")
        branch = "main"

    # remove any trailing or starting slashes from the owner and name
    owner = owner.strip("/")
    name = name.strip("/")

    job_creation_info = None

    # check if there's an existing repo in the db
    with Session(engine) as session:
        stmt = select(repo_table.c.id).where(repo_table.c.owner == owner, repo_table.c.name == name, repo_table.c.branch == branch)
        repo_id = session.execute(stmt).scalar_one_or_none()
        if repo_id:
            # check how many files are in the repo. If it's 0, then let's schedule a new job to generate the files
            stmt = select(func.count(file_table.c.id)).where(file_table.c.repo_id == repo_id)
            num_files = session.execute(stmt).scalar_one()
            if num_files == 0:
                job_id = f"repo-init-{repo_id}"
                existing_job = github_queue.fetch_job(job_id)
                if not existing_job:
                    job_creation_info = {
                        "job_id": job_id,
                        "repo_id": repo_id,
                    }
            return repo_id, job_creation_info
        else:
            # create a new repo
            stmt = insert(repo_table).values(owner=owner, name=name, branch=branch).returning(repo_table.c.id)
            result = session.execute(stmt)
            repo_id = result.scalar_one()
            session.commit()

            # start a new job to convert the repo into chunks
            # use jobId as repo-init-{repo_id}. Queue a job if a job with this id is not already running
            job_id = f"repo-init-{repo_id}"
            existing_job = github_queue.fetch_job(job_id)
            if not existing_job:
                job_creation_info = {
                    "job_id": job_id,
                    "repo_id": repo_id,
                }

            return repo_id, job_creation_info

def get_repo_files(repo_id: str, page: int = 1, page_size: int = 20):
    with Session(engine) as session:
        stmt = select(file_table).where(file_table.c.repo_id == repo_id).order_by(file_table.c.added_at.desc()).offset((page - 1) * page_size).limit(page_size)
        # get everything except raw_content
        files = session.execute(stmt).fetchall()
        files = [{"id": file.id, "path": file.path, "summary_status": file.summary_status, "chunks_status": file.chunks_status, "added_at": file.added_at} for file in files]
        total_num_files = session.execute(select(func.count(file_table.c.id))).scalar_one()
        # page size must be max 100
        if page_size > 100:
            page_size = 100
        return files, total_num_files, page, page_size
    
def get_file_details(file_id: str):
    with Session(engine) as session:
        stmt = select(file_table).where(file_table.c.id == file_id)
        file = session.execute(stmt).fetchone()
        if file:
            return {
                "id": str(file.id),
                "repo_id": str(file.repo_id),
                "path": file.path,
                "raw_content": file.raw_content,
                "summary": file.summary,
                "summary_status": file.summary_status,
                "chunks_status": file.chunks_status,
                "added_at": file.added_at.isoformat() if file.added_at else None
            }
        return None

def create_rag_request(repo_id: uuid.UUID, messages: list[dict]):
    # A rag request should have the following details:
    # repo_id (UUID)
    # messages (list of dicts) array (the last message is the user's query)
    # create a rag_request in the db
    # instantiate a new job in the rag_queue
    # return the request_id
    with Session(engine) as session:
        result = session.execute(
            insert(rag_requests_table)
            .values(request_details={"repo_id": repo_id, "messages": messages, "status": "idle"})
            .returning(rag_requests_table.c.id)
        )
        request_id = result.scalar_one()
        session.commit()

    job_creation_info = {
        "job_id": f"rag-request-{request_id}",
        "request_id": request_id,
    }

    return request_id, job_creation_info

def get_rag_request_status(request_id: str):
    with Session(engine) as session:
        stmt = select(rag_requests_table).where(rag_requests_table.c.id == request_id)
        request = session.execute(stmt).fetchone()
        if request:
            return {
                "id": str(request.id),
                "messages": request.request_details["messages"],
                "added_at": request.added_at.isoformat() if request.added_at else None,
                "response_details": request.response_details,
                "status": request.response_details["status"] if request.response_details else "idle"
            }
        return None

# RAG Action Block. Takes in user's query + current context and decides what to do next
class EmbeddingGenBlock(Block):
    def __init__(self, logging: bool = False):
        super().__init__(name="EmbeddingGenBlock", description="EmbeddingGenBlock is a block that generates an embedding for a given text.", retries=3, retry_delay=1, logging=logging)
        self.embeddings_model = Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="codestral-embed")
        self.delay = 1

    def prepare(self, context: dict):
        return context["text"]
    
    def execute(self, context, prepare_response):
        # increase delay with exponential backoff
        time.sleep(self.delay)
        self.delay *= 2
        return ["success", self.embeddings_model.generate_embeddings(prepare_response, "codestral-embed")]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        context["embedding"] = execute_response[1]
        context["status"] = execute_response[0]
        return "default"

class VectorSearchBlock(Block):
    def __init__(self, logging: bool = False):
        super().__init__(name="VectorSearchBlock", description="VectorSearchBlock is a block that searches the vector database for a given embedding.", retries=3, retry_delay=1, logging=logging)
        self.qdrant = QdrantClient(host=os.getenv("QDRANT_HOST"), port=int(os.getenv("QDRANT_PORT")))

    def prepare(self, context: dict):
        return context["embedding"]
    
    def execute(self, context, prepare_response):
        # if the embedding is not in the context, then raise an error
        if "embedding" not in context:
            return ["error", "Embedding not found in context"]
        
        # search the vector database for the embedding
        # There should be repo level filter here
        results = self.qdrant.search(collection_name="chunks", query_vector=prepare_response, limit=10, with_payload=True)

        # from qdrant extract the chunk raw_chunk_text and file_path
        chunks = [{"raw_chunk_text": result.payload["raw_chunk_text"], "file_path": result.payload["file_path"]} for result in results]
        return ["success", chunks]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["chunks"] = execute_response[1]
            context["status"] = "success"
        else:
            context["status"] = "error"
            context["error"] = execute_response[1]
        return "default"

    
class LLMBlock(Block):
    def __init__(self, logging: bool = False):
        super().__init__(name="LLMBlock", description="LLMBlock is a block that generates a response using a given prompt and context.", retries=3, retry_delay=1, logging=logging)
        self.mistral = Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="mistral-large-latest")
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
        self.llm_council = 0

    def prepare(self, context: dict):
        return [[], context["text"]] if "chunks" not in context else [context["chunks"], context["text"]]
    
    def execute(self, context, prepare_response):
        self.llm_council += 1
        self.llm_council = self.llm_council % 3

        chunks, query = prepare_response
        # if the chunks are empty, then raise an error
        if not chunks or len(chunks) == 0:
            return ["error", "No related information to answer the question. Please try again with a different question."]
        
        # if the query is empty, then raise an error
        if not query:
            return ["error", "Please provide a question to answer."]

        # merge the chunks into a single string
        chunks_str = "\n\n".join([chunk["raw_chunk_text"] for chunk in chunks])

        prompt = f"""
        USECASE:
        ----
        You are a helpful assistant that answers questions about the codebase.

        USER'S QUERY:
        ----
        {query}

        RELEVANT INFORMATION FROM THE CODEBASE TO ANSWER THE QUESTION:
        ----

        {chunks_str}

        RESPONSE:
        ----
        Please answer the user's query based on the relevant information from the codebase and codebase alone. Do not hallucinate.
        """

        # generate a response using the chunks
        llm = self.gemini if self.llm_council == 0 else self.mistral

        response = llm.generate_text([{"role": "user", "content": prompt, "type": "text"}])

        return ["success", response]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        context["response"] = execute_response[1]
        context["status"] = execute_response[0]
        return "default"

def work_on_rag_request(messages: list[dict]):
    # create a new flow run
    embedding = EmbeddingGenBlock()
    vector_search = VectorSearchBlock()
    llm = LLMBlock()
    embedding >> vector_search
    vector_search >> llm

    # create a new flow run
    flow = Chain(name="RAGFlow", starting_block=embedding)
    context = {"text": messages[-1]["content"]}
    flow.run(context)
    return context