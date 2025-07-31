import os
from uuid import uuid4
from datetime import datetime
from sqlalchemy import create_engine, Table, Column, String, DateTime, ForeignKey, text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
github_queue = Queue('github', connection=redis_conn)
rag_queue = Queue('rag', connection=redis_conn)
qa_queue = Queue('qa', connection=redis_conn)

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
- RAG_Request
    - id (auto gen uuid)
    - request_details (jsonb)
    - response_details (jsonb)
    - added_at
- GoldQABatch
    - id (auto gen uuid)
    - repo_id (foreign key to Repo.id)
    - status (idle, running, completed, failed)
    - total_files (int)
    - processed_files (int)
    - added_at
- GoldQA
    - id (auto gen uuid)
    - batch_id (foreign key to GoldQABatch.id)
    - file_id (foreign key to File.id)
    - chunk_id (str - from qdrant)
    - question (str)
    - answer (str)
    - evolution_strategy (str - reasoning, multicontext, etc)
    - question_score (float)
    - chunk_score (float)
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
rag_requests_table = Table("rag_requests", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("request_details", JSONB, nullable=True),
    Column("response_details", JSONB, nullable=True),
    Column("added_at", DateTime, nullable=False, default=datetime.utcnow),
)
gold_qa_batch_table = Table("gold_qa_batches", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("repo_id", UUID(as_uuid=True), ForeignKey("repos.id"), nullable=False),
    Column("status", String, nullable=False, default="idle"),
    Column("total_files", Integer, nullable=False, default=0),
    Column("processed_files", Integer, nullable=False, default=0),
    Column("added_at", DateTime, nullable=False, default=datetime.utcnow),
)
gold_qa_table = Table("gold_qa", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("batch_id", UUID(as_uuid=True), ForeignKey("gold_qa_batches.id"), nullable=False),
    Column("file_id", UUID(as_uuid=True), ForeignKey("files.id"), nullable=False),
    Column("chunk_id", String, nullable=False),
    Column("question", String, nullable=False),
    Column("answer", String, nullable=False),
    Column("evolution_strategy", String, nullable=True),
    Column("question_score", Float, nullable=True),
    Column("chunk_score", Float, nullable=True),
    Column("flow_logs", JSONB, nullable=True),
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
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
            on_disk_payload=True,
        )
        print("Qdrant chunks collection created successfully")
    else:
        print("Qdrant chunks collection already exists")
    return

"""
- Chunk (Qdrant)
    - id (auto gen uuid)
    - repo_id 
    - file_id
    - file_path
    - raw_chunk_text
    - vector_embeddings
    - added_at
"""
def insert_chunks(repo_id: str, file_id: str, file_path: str, chunks: list[(str, list[float])]):
    # upsert chunk into qdrant
    from qdrant_client.models import PointStruct
    
    points = []
    for chunk_text, chunk_embedding in chunks:
        point = PointStruct(
            id=str(uuid4()),  # Qdrant expects string ID
            vector=chunk_embedding,  # The embedding vector
            payload={  # All other data goes in payload
                "repo_id": str(repo_id),
                "file_id": str(file_id),
                "file_path": file_path,
                "raw_chunk_text": chunk_text,
                "added_at": datetime.utcnow().isoformat()
            }
        )
        points.append(point)
    
    # Batch upsert all points at once
    if points:
        qdrant_client.upsert(
            collection_name="chunks",
            points=points
        )

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()