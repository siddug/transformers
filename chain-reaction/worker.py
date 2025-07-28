#!/usr/bin/env python
import os
import sys
from rq import Worker, Queue
from database import redis_conn

if __name__ == '__main__':
    worker = Worker(['default', 'github'], connection=redis_conn)
    worker.work()