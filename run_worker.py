from rq import Worker, Queue, Connection
import redis
import sys
import os

listen = ['default']
redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:30006')
conn = redis.from_url(redis_url)

if __name__ == "__main__":
    with Connection(conn):
        worker = Worker([Queue(name, default_timeout=600) for name in listen])
        worker.work()