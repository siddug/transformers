import time
from database import task_queue
from rq.decorators import job

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