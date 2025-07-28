import time
from database import task_queue, github_queue, rag_queue
from rq.decorators import job
from utils.github import get_repo_files, get_repo_file_raw
from database import repo_table, file_table, engine, insert_chunks, rag_requests_table
from sqlalchemy.orm import Session
from sqlalchemy import select, func, insert, update
from utils.llm import Mistral, Gemini
from utils.chunking import contextual_chunking
from apps.github_rag import work_on_rag_request
import os

mistral = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"))

@job('default', connection=task_queue.connection, timeout='10m')
def long_running_task(task_name: str, duration: int = 5):
    """Example of a long-running task that can be queued"""
    print(f"Starting task: {task_name}")
    time.sleep(duration)
    print(f"Completed task: {task_name}")
    return f"Task {task_name} completed after {duration} seconds"

@job('default', connection=task_queue.connection)
def process_translation_batch(texts: list[str], target_language: str):
    """Example task for batch translation processing"""
    results = []
    for text in texts:
        # Simulate translation processing
        result = f"Translated '{text}' to {target_language}"
        results.append(result)
    return results

@job('default', connection=task_queue.connection)
def process_vector_embedding(text: str, collection_name: str):
    """Example task for processing and storing vector embeddings"""
    # This would typically use an embedding model
    # For now, just simulating the process
    embedding = [0.1] * 384  # Simulated embedding
    
    # In real implementation, you would store in Qdrant
    # qdrant_client.upsert(collection_name, points=[...])
    
    return {
        "text": text,
        "collection": collection_name,
        "embedding_size": len(embedding)
    }

@job("github", connection=github_queue.connection)
def generate_file_jobs_for_repo(repo_id: str):
    # get all files for the repo using github utils. for each file, create a new DB entry if it doesn't exist.
    # then create a new job to generate the file summary and chunks (if it's a new file)
    with Session(engine) as session:
        stmt = select(repo_table).where(repo_table.c.id == repo_id)
        repo = session.execute(stmt).fetchone()
        if not repo:
            raise ValueError(f"Repo with id {repo_id} not found")

        # Only get files, not directories (type == "blob")
        all_items = get_repo_files(repo.name, repo.owner, repo.branch)
        files = [item["path"] for item in all_items if item.get("type") == "blob"]

        existing_file_paths = session.execute(select(file_table.c.path).where(file_table.c.repo_id == repo_id)).scalars().all()


        new_files = [file for file in files if file not in existing_file_paths]

        # insert all new files into the db
        inserted_files = session.execute(
            insert(file_table)
            .returning(file_table.c.id),
            [{"repo_id": repo_id, "path": file} for file in new_files]
        ).fetchall()
        session.commit()

        # create a new job to generate the file summary and chunks for each new file
        for file_id in inserted_files:
            # use jobId as file-summary-and-chunks-{file_id}. Queue a job if a job with this id is not already running
            job_id = f"file-summary-and-chunks-{file_id[0]}"
            existing_job = github_queue.fetch_job(job_id)
            if not existing_job:
                github_queue.enqueue(generate_file_summary_and_chunks, file_id=file_id[0], job_id=job_id)

@job("github", connection=github_queue.connection)
def generate_file_summary_and_chunks(file_id: str):
    # get the file from the db
    with Session(engine) as session:
        stmt = select(file_table).where(file_table.c.id == file_id)
        file = session.execute(stmt).fetchone()
        if not file:
            raise ValueError(f"File with id {file_id} not found")

        # get the repo from the db
        stmt = select(repo_table).where(repo_table.c.id == file.repo_id)
        repo = session.execute(stmt).fetchone()
        if not repo:
            raise ValueError(f"Repo with id {file.repo_id} not found")

        # get the raw content of the file using github utils if it doesn't exist
        if not file.raw_content:
            try:
                raw_content = get_repo_file_raw(repo.name, repo.owner, file.path, repo.branch)
                # Update the file with raw content
                stmt = file_table.update().where(file_table.c.id == file_id).values(raw_content=raw_content)
                session.execute(stmt)
                session.commit()
            except ValueError as e:
                # Skip directories or files without content
                print(f"Skipping file {file.path}: {str(e)}")
                # Mark as processed but with no content
                stmt = file_table.update().where(file_table.c.id == file_id).values(
                    summary_status="skipped",
                    chunks_status="skipped"
                )
                session.execute(stmt)
                session.commit()
                return
        
        # check if summary exists for the file. If it does, schedule a new job to generate the chunks
        # if it doesn't generate the summary and schedule a new job to generate the chunks
        chunk_job_id = f"file-chunks-{file_id}"
        chunk_job_exists = github_queue.fetch_job(chunk_job_id)
        if file.summary_status == "processed":
            if file.chunks_status == "processed":
                return
            else:
                if not chunk_job_exists:
                    github_queue.enqueue(generate_file_chunks, file_id=file_id, job_id=chunk_job_id)
        else:
            print(f"Generating summary for file {file.path}")
            # COMMENTING OUT MISTRAL BECAUSE OF RATE LIMITS
            # summary_response = mistral.generate_text(messages=[{"role": "user", "content": f"Generate a summary for the following file: {file.path}. We are going to use this summary at the top of file to better create chunks for the file. The summary must be short (max 6 lines). The summary should be in the same language as the file. Crispy include the information that will help RAG systems to better understand the file.", "type": "text"}], model="mistral-large-latest")
            summary_response = gemini.generate_text(messages=[{"role": "user", "content": f"Generate a summary for the following file: {file.path}. We are going to use this summary at the top of file to better create chunks for the file. The summary must be short (max 6 lines). The summary should be in the same language as the file. Crispy include the information that will help RAG systems to better understand the file.", "type": "text"}], model="gemini-2.0-flash")
            # Update the file with summary
            stmt = file_table.update().where(file_table.c.id == file_id).values(summary=summary_response, summary_status="processed")
            session.execute(stmt)
            session.commit()
            print(f"Summary generated for file {file.path}")

            # Re-fetch the file to get updated status
            stmt = select(file_table).where(file_table.c.id == file_id)
            file = session.execute(stmt).fetchone()
            
            print(f"File chunks_status after summary: {file.chunks_status}")
            if file.chunks_status == "processed":
                return
            else:
                if not chunk_job_exists:
                    print(f"Enqueuing chunks job for file {file.path}")
                    github_queue.enqueue(generate_file_chunks, file_id=file_id, job_id=chunk_job_id)
                else:
                    print(f"Chunks job already exists for file {file.path}")

@job("github", connection=github_queue.connection)
def generate_file_chunks(file_id: str):
    # get the file from the db
    with Session(engine) as session:
        stmt = select(file_table).where(file_table.c.id == file_id)
        file = session.execute(stmt).fetchone()
        if not file:
            raise ValueError(f"File with id {file_id} not found")
        
        raw_content = file.raw_content
        summary = file.summary

        # generate chunks
        chunk_texts = contextual_chunking(raw_content, 1000, "o200k_base", summary)
        chunk_embeddings = [mistral.generate_embeddings(text, "codestral-embed") for text in chunk_texts]

        # insert chunks into the db
        insert_chunks(file.repo_id, file_id, file.path, list(zip(chunk_texts, chunk_embeddings)))
        # Update the file chunks status
        stmt = file_table.update().where(file_table.c.id == file_id).values(chunks_status="processed")
        session.execute(stmt)
        session.commit()


@job("rag", connection=rag_queue.connection)
def generate_rag_response(request_id: str):
    # get the request from the db
    with Session(engine) as session:
        stmt = select(rag_requests_table).where(rag_requests_table.c.id == request_id)
        request = session.execute(stmt).fetchone()
        if not request:
            raise ValueError(f"Request with id {request_id} not found")
        
        # get the request details
        request_details = request.request_details

        messages = request_details["messages"]

        # for now, just write a response to the request as "Hello, world! This is a test response."
        context = work_on_rag_request(messages)
        
        # Extract only JSON-serializable data from the response
        response_details = {
            "response": context.get("response", ""),
            "status": context.get("status", "completed"),
            "query": context.get("text", "")
        }

        # update the request with the response details
        stmt = rag_requests_table.update().where(rag_requests_table.c.id == request_id).values(response_details=response_details)
        session.execute(stmt)
        session.commit()
