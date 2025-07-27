import os
from uuid import uuid4
from datetime import datetime
from sqlalchemy import create_engine, Table, Column, String, DateTime, ForeignKey, text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import redis
from rq import Queue

# PostgreSQL configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/chain_reaction")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = Base.metadata

# Qdrant configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = redis.from_url(REDIS_URL)
task_queue = Queue(connection=redis_conn)

# DB table setup. On init, create the tables if they don't exist
"""
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
"""
repo_table = Table("repos", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("owner", String, nullable=False),
    Column("name", String, nullable=False),
    Column("branch", String, nullable=False),
    Column("added_at", DateTime, nullable=False, default=datetime.utcnow),
)
file_table = Table("files", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("repo_id", UUID(as_uuid=True), ForeignKey("repos.id"), nullable=False),
    Column("path", String, nullable=False),
    Column("raw_content", String, nullable=True),
    Column("summary", String, nullable=True),
    Column("summary_status", String, nullable=False, default="pending"),
    Column("chunks_status", String, nullable=False, default="pending"),
    Column("added_at", DateTime, nullable=False, default=datetime.utcnow),
)

def create_tables():
    """Create the tables if they don't exist"""
    # First ensure UUID extension is available in PostgreSQL
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
        conn.commit()
    
    # Create the tables
    metadata.create_all(bind=engine)
    print("Tables created successfully!")

def drop_tables():
    # Drop the tables if they exist
    metadata.drop_all(bind=engine)


# create qdrant chunks collection if it doesn't exist. put this in a function and run it on startup
def create_qdrant_chunks_collection():
    if not qdrant_client.collection_exists(collection_name="chunks"):
        qdrant_client.create_collection(
            collection_name="chunks",
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            on_disk_payload=True,
        )
        print("Qdrant chunks collection created successfully")
    else:
        print("Qdrant chunks collection already exists")
    return

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()