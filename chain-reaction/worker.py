#!/usr/bin/env python
import os
import sys
import multiprocessing
from rq import Worker, Queue
from database import redis_conn

def start_worker(queues):
    """Start a worker for the given queues"""
    worker = Worker(queues, connection=redis_conn)
    worker.work()

if __name__ == '__main__':
    # Create separate processes for each worker
    workers = [
        multiprocessing.Process(target=start_worker, args=(['default', 'github'],)),
        multiprocessing.Process(target=start_worker, args=(['rag'],)),
        multiprocessing.Process(target=start_worker, args=(['qa'],))
    ]
    
    # Start all workers
    for w in workers:
        w.start()
    
    # Wait for all workers to complete
    for w in workers:
        w.join()