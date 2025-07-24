#!/usr/bin/env python
import os
import sys
from rq import Worker, Queue, Connection
from database import redis_conn

if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(list(map(Queue, ['default'])))
        worker.work()