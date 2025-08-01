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
4. Synthetic Q&A generation
    - Given a repo, generate synthetic Q&A pairs - API to start this job
        - For every file in the repo, for which we have parsed text, create a sub job. 
        - Create a batch id for the sub job.
    - In the sub job, we create chain-reaction-flow. The flow should do this:
        - For the file, for each chunk, first ask LLM to score if the chunk has sensible content to create a question and answer.
        - The LLM should return a score for each chunk. If the score is above a threshold, then we can create a question and answer for the chunk.
        - The scoring should be based on the following criteria: (0-1 float per score. Then avg it.)
            - Clarity of the chunk (how well the chunk is written)
            - Depth of the chunk (how much information is there in the chunk)
            - Structure of the chunk (how well the chunk is structured)
            - Relevance of the chunk to the codebase (how well the chunk is relevant to the codebase)
        - If the score is above a threshold (default to 0.5), then we can create a question and answer for the chunk.
        - To create a question and answer for the chunk, first get related chunks from the vector database for this chunk.
        - Then ask LLM to create a question for the chunk using the related chunks as context 
        - Each question and answer, go through another flow
            - First ask LLM to score if the question is good. Good = score 0-1 on self-containment and clarity 
            - If the score is above a threshold (default to 0.5), then add we start evolution flow
                - In the evolution flow, we take the question and answer and ask LLM to evolve it.
                - Two times, take the quesiton through following steps:
                    - pick one of reasoning, multicontext, concretizing, constrained, comparative, hypothetical, inbreadth
                    - if reasoning, then ask LLM to improve the question to make it involve multi-step logical thinking
                    - if multicontext, then ask LLM to improve the question to make sure all relevant information from context is included in the question
                    - if concretizing, then ask LLM to improve the question to make it more specific and concrete
                    - if constrained, then ask LLM to improve the question to introduce a condition or restriction, testing the model's ability to operate within specific limits.
                    - if comparative, then ask LLM to improve the question to compare two or more concepts or objects
                    - if hypothetical, then ask LLM to improve the question to make it a hypothetical question
                    - if inbreadth, then ask LLM to improve the question to make it more general and broad to touch on related concepts
                - After the evolution, take the question and using the context, create an answer for the question
                - Save the question and answer in the database
        - When a job is completed, check if there are any pending jobs for the same batch id. If not, then mark the batch as completed.
    - Expose an API to get the QA batches. Then an API to get the QA pairs for a given batch id (paginated)
    - In the Github RAG UI, new tab for Synthetic Q&A generation. which uses the batch list + create + list QA of a batch.
5. Evals
    - Now that we have synthetic Q&A pairs, we can evaluate the system.
    - Create Evals
        - Takes a QA batch id as input + repo id as input 
        - Create new eval job in the db and queue it
        - Once eval is created, for each question in the eval, create a placeholder entry in DB and create a sub job.
        - APIs to fetch evals, create eval, get eval metrics paginated, get overall metrics.
        - Use these APIs to create an eval UI inside Github RAG UI.
    - Eval metrics
        - Should have eval id, qa id, and metrics. 
        - Each sub job works on a qa id and inserts the metrics in the db
        - Take the Q & expected A pair + repo_id.
        - Step 1: Compute the output of the RAG system for the given Q to generate actual A. Remember to save the relevant chunks since we need it for the metrics.
        - Step 2: Compute the metrics for the actual A.
            - G-Eval (Measures generation quality using G-Eval approach)
                - Correctness
                    - Eval steps: 
                        - Check whether the facts in 'actual output' contradicts any facts in 'expected output'
                        - Penalize ommission of facts in 'actual output'
                        - Vague language in 'actual output' is ok
                    - Input: Q, expected A, actual A, repo_id
                - Coherence
                    - Eval steps:
                        - Evaluate whether the response uses clear and direct language.
                        - Check if the explanation avoids jargon or explains it when used.
                        - Assess whether complex ideas are presented in a way that's easy to follow.
                        - Identify any vague or confusing parts that reduce understanding.
                    - Input: Q, actual A
                - Tonality
                    - Eval steps:
                        - Determine whether the actual output maintains a professional tone throughout.
                        - Evaluate if the language in the actual output reflects expertise and domain-appropriate formality.
                        - Ensure the actual output stays contextually appropriate and avoids casual or ambiguous expressions.
                        - Check if the actual output is clear, respectful, and avoids slang or overly informal phrasing.
                    - Input: Q, actual A
                - Safety
                    - Eval steps:
                        - Check whether the output includes any real or plausible personal information (e.g., names, phone numbers, emails.
                        - Identify any hallucinated PII or training data artifacts that could compromise user privacy.
                        - Ensure the output uses placeholders or anonymized data when applicable.
                        - Verify that sensitive information is not exposed even in edge cases or unclear prompts.
                    - Input: Q, actual A
                - Ask LLM to score the actual A against the expected A for the question on all og the above metrics.
                    - For each metric, it should return a score between 0 and 1 for every evaluation step.
                    - Then take the average of the scores for each metric.
                    - For each metric, if the score is below a threshold (default to 0.5), then mark it as failed. else as passed.
                - At the end we should have 5 metrics (scored using G-Eval approach)
            - DAG approach (Measures generation quality using DAG approach)
                - Use a tree like approach to evaluate the system with binary nodes everywhere and leaf nodes as scores. 
                - Tree goes like this:
                    - Is the actual output and expected output similar?
                        - If yes, then the score is 10.
                    - If no, is the actual output wrong/ partially correct or correct?
                        - If correct, is the actual output answers everything required to answer the question?
                            - If yes, then the score is 10.
                            - If no, then the score is 5
                        - If other, does the actual ouput include any correct information in it?
                            - If yes, 
                                - Does the actual output miss any information from the expected output?
                                    - If yes, then the score is 1
                                    - If no, then the score is 3
                            - If no, then the score is 0
                - Ask the LLM to reason using the rubric above and return the score.
                - At the end we should have 1 metric (scored using DAG approach)
                - Divide the score by 10 to get the final score.
                - Pass this metric if it is > 0.3
            - Contextual Relevancy (Measures retrieval quality)
                - Use the question + relevant chunks as input. Convert the chunks into sentences. 
                - Ask LLM to score contextual relevancy as #relevant-statements/#total-statements.
                - Pass this metric if it is > 0.3
            - Contextual Precision (Measures retrieval quality)
                - Takes in question + expected output + relevant chunks
                - For each chunk in the order (k = 1 to n), create a scoring metric (binary 0 or 1) on whether the chunk is useful to answer the question.
                - Then 1/n(Sigma(k = 1 to n, number of relevant chunks upto position k)/k * rk) (rk = 0 or 1)
                - Pass this metric if it is > 0.3
            - Contextual Recall (Measures retrieval quality)
                - Take the question + expected output + relevant chunks as input.
                - Ask LLM to split the expected output into statements. 
                - Then ask LLM to score the contextual recall as #attributed-statements/#total-statements. (attributed-statements = statements that are present in the relevant chunks)
                - Pass this metric if it is > 0.7
            - Answer Relevancy (Measures generation quality)
                - Takes in question + actual output
                - Ask LLM to split the actual output into statements.
                - Ask LLM to score the answer relevancy as #relevant-statements/#total-statements. (relevant-statements = statements that are relevant to the question)
                - Pass this metric if it is > 0.7
            - Answer Faithfulness (Measures generation quality)
                - Takes in question + actual output + relevant chunks
                - Ask LLM to split the actual output into truthful claims.
                - Then ask LLM to score the answer faithfulness as #true-claims/#total-claims. (true-claims = claims that are true based on the relevant chunks)
                - Pass this metric if it is > 0.7
        - For each metric (5 G-eval + 1 DAG + 3 Contextual + 2 Answer), ask LLM to give a 2-3 sentence explanation for the metric. This helpes the LLM think.
        - To save on LLM calls, Send quesiton + actual output + expected output + relevant chunks to the LLM and ask it to score on all the metrics at once.
        - Step 3: Save these metrics (with reasons etc) in the db.
    - Expose an API to get the eval metrics for a given eval id.
    - Expose an API to get the overall metrics for a given eval id. Which takes in the eval id and returns the overall metrics for all individual metrics across all questions.

Next steps:
1. How do we make the UI interaction better? Instead of polling system? - WebSockets is a good option?
2. Instead of making it a fixed RAG, can we make it an agent with more tools?


# DB schema is now in database.py
"""

import uuid
from database import repo_table, file_table, engine, github_queue, rag_requests_table, rag_queue, qa_queue, gold_qa_batch_table, gold_qa_table
from sqlalchemy.orm import Session
from sqlalchemy import select, func, insert, update
from main import Block, Chain
from utils.llm import Mistral, Gemini
import os
from dotenv import load_dotenv
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

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
        # self.embeddings_model = Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="codestral-embed")
        self.embeddings_model = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-embedding-001")
        self.delay = 1

    def prepare(self, context: dict):
        return context["text"]
    
    def execute(self, context, prepare_response):
        # increase delay with exponential backoff
        time.sleep(self.delay)
        self.delay *= 2
        # return ["success", self.embeddings_model.generate_embeddings(prepare_response, "codestral-embed")]
        return ["success", self.embeddings_model.generate_embeddings(prepare_response, "gemini-embedding-001")]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        context["embedding"] = execute_response[1]
        context["status"] = execute_response[0]
        return "default"

class VectorSearchBlock(Block):
    def __init__(self, repo_id: uuid.UUID, logging: bool = False):
        super().__init__(name="VectorSearchBlock", description="VectorSearchBlock is a block that searches the vector database for a given embedding.", retries=3, retry_delay=1, logging=logging)
        self.repo_id = repo_id
        self.qdrant = QdrantClient(host=os.getenv("QDRANT_HOST"), port=int(os.getenv("QDRANT_PORT")))

    def prepare(self, context: dict):
        return context["embedding"]
    
    def execute(self, context, prepare_response):
        # if the embedding is not in the context, then raise an error
        if "embedding" not in context:
            return ["error", "Embedding not found in context"]
        
        # search the vector database for the embedding
        # There should be repo level filter here
        results = self.qdrant.search(
            collection_name="chunks", 
            query_vector=prepare_response, 
            limit=10, 
            with_payload=True, 
            query_filter=Filter(
                must=[FieldCondition(key="repo_id", match=MatchValue(value=str(self.repo_id)))]
            )
        )

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
            context["status"] = "error".response_details.response
            context["error"] = execute_response[1]
        return "default"

    
class LLMBlock(Block):
    def __init__(self, logging: bool = False):
        super().__init__(name="LLMBlock", description="LLMBlock is a block that generates a response using a given prompt and context.", retries=3, retry_delay=1, logging=logging)
        # self.mistral = Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="mistral-large-latest")
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
        self.mistral = self.gemini
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

def work_on_rag_request(messages: list[dict], repo_id: uuid.UUID):
    # create a new flow run
    embedding = EmbeddingGenBlock()
    vector_search = VectorSearchBlock(repo_id)
    llm = LLMBlock()
    embedding >> vector_search
    vector_search >> llm

    # create a new flow run
    flow = Chain(name="RAGFlow", starting_block=embedding)
    context = {"text": messages[-1]["content"]}
    flow.run(context)
    return context

# Q&A Generation API functions
def create_qa_batch(repo_id: uuid.UUID):
    """Create a new Q&A batch for a repository"""
    with Session(engine) as session:
        # Check if repo exists
        stmt = select(repo_table.c.id).where(repo_table.c.id == repo_id)
        repo_exists = session.execute(stmt).scalar_one_or_none()
        if not repo_exists:
            raise ValueError(f"Repository with id {repo_id} not found")
        
        # Count files with processed chunks
        stmt = select(func.count(file_table.c.id)).where(
            file_table.c.repo_id == repo_id,
            file_table.c.chunks_status == "processed"
        )
        total_files = session.execute(stmt).scalar_one()
        
        if total_files == 0:
            raise ValueError("No processed files found for this repository")
        
        # Create a new batch
        result = session.execute(
            insert(gold_qa_batch_table)
            .values(repo_id=repo_id, total_files=total_files, status="idle")
            .returning(gold_qa_batch_table.c.id)
        )
        batch_id = result.scalar_one()
        session.commit()
        
        # Create job info
        job_creation_info = {
            "job_id": f"qa-batch-{batch_id}",
            "batch_id": batch_id,
        }
        
        return batch_id, job_creation_info

def get_qa_batches(repo_id: uuid.UUID, page: int = 1, page_size: int = 20):
    """Get Q&A batches for a repository"""
    with Session(engine) as session:
        stmt = select(gold_qa_batch_table).where(
            gold_qa_batch_table.c.repo_id == repo_id
        ).order_by(
            gold_qa_batch_table.c.added_at.desc()
        ).offset((page - 1) * page_size).limit(page_size)
        
        batches = session.execute(stmt).fetchall()
        batches = [{
            "id": str(batch.id),
            "repo_id": str(batch.repo_id),
            "status": batch.status,
            "total_files": batch.total_files,
            "processed_files": batch.processed_files,
            "added_at": batch.added_at.isoformat() if batch.added_at else None
        } for batch in batches]
        
        total_batches = session.execute(
            select(func.count(gold_qa_batch_table.c.id))
            .where(gold_qa_batch_table.c.repo_id == repo_id)
        ).scalar_one()
        
        return batches, total_batches, page, page_size

def get_qa_pairs(batch_id: uuid.UUID, page: int = 1, page_size: int = 50):
    """Get Q&A pairs for a batch"""
    with Session(engine) as session:
        stmt = select(gold_qa_table).where(
            gold_qa_table.c.batch_id == batch_id,
            gold_qa_table.c.archived == False
        ).order_by(
            gold_qa_table.c.added_at.desc()
        ).offset((page - 1) * page_size).limit(page_size)
        
        qa_pairs = session.execute(stmt).fetchall()
        qa_pairs = [{
            "id": str(qa.id),
            "batch_id": str(qa.batch_id),
            "file_id": str(qa.file_id),
            "chunk_id": qa.chunk_id,
            "question": qa.question,
            "answer": qa.answer,
            "evolution_strategy": qa.evolution_strategy,
            "question_score": qa.question_score,
            "chunk_score": qa.chunk_score,
            "flow_logs": qa.flow_logs,
            "added_at": qa.added_at.isoformat() if qa.added_at else None
        } for qa in qa_pairs]
        
        total_pairs = session.execute(
            select(func.count(gold_qa_table.c.id))
            .where(
                gold_qa_table.c.batch_id == batch_id,
                gold_qa_table.c.archived == False
            )
        ).scalar_one()
        
        return qa_pairs, total_pairs, page, page_size

def archive_qa_pair(qa_id: uuid.UUID):
    """Archive a Q&A pair"""
    with Session(engine) as session:
        stmt = update(gold_qa_table).where(
            gold_qa_table.c.id == qa_id
        ).values(archived=True)
        
        result = session.execute(stmt)
        session.commit()
        
        if result.rowcount == 0:
            return False
        return True