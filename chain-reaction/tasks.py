import time
from database import task_queue, github_queue, rag_queue, qa_queue, eval_queue, gold_qa_batch_table, gold_qa_table, eval_job_table, eval_metrics_table
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
        # chunk_embeddings = [mistral.generate_embeddings(text, "codestral-embed") for text in chunk_texts]
        chunk_embeddings = [gemini.generate_embeddings(text, "gemini-embedding-001") for text in chunk_texts]

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

        repo_id = request_details["repo_id"]

        # for now, just write a response to the request as "Hello, world! This is a test response."
        context = work_on_rag_request(messages, repo_id)
        
        # Extract only JSON-serializable data from the response
        response_details = {
            "response": context.get("response", ""),
            "status": context.get("status", "completed"),
            "query": context.get("text", ""),
            "timing": context.get("timing", {}),
            "chain_timing": context.get("chain_timing", {}),
            "logs": context.get("logs", [])
        }

        # update the request with the response details
        stmt = rag_requests_table.update().where(rag_requests_table.c.id == request_id).values(response_details=response_details)
        session.execute(stmt)
        session.commit()

@job("qa", connection=qa_queue.connection)
def generate_qa_batch(batch_id: str):
    """Generate Q&A pairs for all processed files in a batch"""
    with Session(engine) as session:
        # Get batch details
        stmt = select(gold_qa_batch_table).where(gold_qa_batch_table.c.id == batch_id)
        batch = session.execute(stmt).fetchone()
        if not batch:
            raise ValueError(f"Batch with id {batch_id} not found")
        
        # Update batch status to running
        stmt = update(gold_qa_batch_table).where(
            gold_qa_batch_table.c.id == batch_id
        ).values(status="running")
        session.execute(stmt)
        session.commit()
        
        # Get all files with processed chunks for this repo
        stmt = select(file_table).where(
            file_table.c.repo_id == batch.repo_id,
            file_table.c.chunks_status == "processed"
        )
        files = session.execute(stmt).fetchall()
        
        # Queue sub-jobs for each file
        for file in files:
            job_id = f"qa-file-{batch_id}-{file.id}"
            existing_job = qa_queue.fetch_job(job_id)
            if not existing_job:
                qa_queue.enqueue(
                    generate_qa_for_file,
                    batch_id=batch_id,
                    file_id=file.id,
                    job_id=job_id
                )

@job("qa", connection=qa_queue.connection)
def generate_qa_for_file(batch_id: str, file_id: str):
    """Generate Q&A pairs for a single file"""
    from apps.qa_generation import work_on_qa_generation
    
    context = work_on_qa_generation(batch_id, file_id)
    
    # Check if all files are processed
    with Session(engine) as session:
        # Get batch details
        stmt = select(gold_qa_batch_table).where(gold_qa_batch_table.c.id == batch_id)
        batch = session.execute(stmt).fetchone()
        
        # Count processed files (files that have at least one Q&A pair)
        stmt = select(func.count(func.distinct(gold_qa_table.c.file_id))).where(
            gold_qa_table.c.batch_id == batch_id
        )
        processed_files = session.execute(stmt).scalar_one()
        
        # Update processed files count
        stmt = update(gold_qa_batch_table).where(
            gold_qa_batch_table.c.id == batch_id
        ).values(processed_files=processed_files)
        session.execute(stmt)
        
        # If all files are processed, mark batch as completed
        if processed_files >= batch.total_files:
            stmt = update(gold_qa_batch_table).where(
                gold_qa_batch_table.c.id == batch_id
            ).values(status="completed")
            session.execute(stmt)
        
        session.commit()

@job("eval", connection=eval_queue.connection)
def process_eval_job(eval_job_id: str):
    """Process an eval job by creating sub-jobs for each Q&A pair"""
    with Session(engine) as session:
        # Get eval job details
        stmt = select(eval_job_table).where(eval_job_table.c.id == eval_job_id)
        eval_job = session.execute(stmt).fetchone()
        if not eval_job:
            raise ValueError(f"Eval job with id {eval_job_id} not found")
        
        # Update eval job status to running
        stmt = update(eval_job_table).where(
            eval_job_table.c.id == eval_job_id
        ).values(status="running")
        session.execute(stmt)
        session.commit()
        
        # Get all Q&A pairs for this batch
        stmt = select(gold_qa_table).where(
            gold_qa_table.c.batch_id == eval_job.qa_batch_id,
            gold_qa_table.c.archived == False
        )
        qa_pairs = session.execute(stmt).fetchall()
        
        # Create placeholder entries in eval_metrics for each Q&A pair
        for qa in qa_pairs:
            # Check if metric already exists
            stmt = select(eval_metrics_table).where(
                eval_metrics_table.c.eval_job_id == eval_job_id,
                eval_metrics_table.c.qa_id == qa.id
            )
            existing_metric = session.execute(stmt).fetchone()
            
            if not existing_metric:
                # Create placeholder entry
                stmt = insert(eval_metrics_table).values(
                    eval_job_id=eval_job_id,
                    qa_id=qa.id,
                    actual_answer="",
                    relevant_chunks=[],
                    metrics={"status": "pending"}
                )
                session.execute(stmt)
        
        session.commit()
        
        # Queue sub-jobs for each Q&A pair
        for qa in qa_pairs:
            job_id = f"eval-qa-{eval_job_id}-{qa.id}"
            existing_job = eval_queue.fetch_job(job_id)
            if not existing_job:
                eval_queue.enqueue(
                    evaluate_single_qa,
                    eval_job_id=eval_job_id,
                    qa_id=str(qa.id),
                    repo_id=str(eval_job.repo_id),
                    job_id=job_id
                )

@job("eval", connection=eval_queue.connection)
def evaluate_single_qa(eval_job_id: str, qa_id: str, repo_id: str):
    """Evaluate a single Q&A pair"""
    from apps.eval_metrics import evaluate_qa_pair
    
    # Run the evaluation
    metrics_result = evaluate_qa_pair(qa_id, repo_id)
    
    with Session(engine) as session:
        # Update the eval metrics
        stmt = update(eval_metrics_table).where(
            eval_metrics_table.c.eval_job_id == eval_job_id,
            eval_metrics_table.c.qa_id == qa_id
        ).values(
            actual_answer=metrics_result["actual_answer"],
            relevant_chunks=metrics_result["relevant_chunks"],
            metrics=metrics_result["metrics"]
        )
        session.execute(stmt)
        
        # Check if all Q&A pairs are processed
        stmt = select(func.count()).select_from(eval_metrics_table).where(
            eval_metrics_table.c.eval_job_id == eval_job_id,
            eval_metrics_table.c.metrics["status"].astext != "completed"
        )
        pending_count = session.execute(stmt).scalar_one()
        
        # Update processed count
        stmt = select(func.count()).select_from(eval_metrics_table).where(
            eval_metrics_table.c.eval_job_id == eval_job_id,
            eval_metrics_table.c.metrics["status"].astext == "completed"
        )
        processed_count = session.execute(stmt).scalar_one()
        
        stmt = update(eval_job_table).where(
            eval_job_table.c.id == eval_job_id
        ).values(processed_qa_pairs=processed_count)
        session.execute(stmt)
        
        # If all are processed, mark job as completed
        if pending_count == 0:
            from datetime import datetime
            stmt = update(eval_job_table).where(
                eval_job_table.c.id == eval_job_id
            ).values(
                status="completed",
                completed_at=datetime.utcnow()
            )
            session.execute(stmt)
        
        session.commit()
