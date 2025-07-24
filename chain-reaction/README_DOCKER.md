# Docker Setup for Chain Reaction

This project includes a complete Docker setup with FastAPI, PostgreSQL, Qdrant, Redis, MinIO, and Next.js UI.

## Services

- **FastAPI**: Main application server (port 8000)
- **PostgreSQL**: Relational database (port 5432)
- **Qdrant**: Vector database (ports 6333, 6334)
- **Redis**: Cache and job queue (port 6379)
- **Worker**: RQ worker for background jobs
- **MinIO**: S3-compatible object storage (port 9000, console on 9001)
- **Next.js**: Web UI (port 3000)

## Quick Start

1. Copy the environment file:
```bash
cp .env.example .env
```

2. Build and start all services:
```bash
docker-compose up --build
```

3. Access the services:
- Next.js UI: http://localhost:3000
- FastAPI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- MinIO Console: http://localhost:9001 (login: minioadmin/minioadmin)

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Task Queue Examples

1. Enqueue a long-running task:
```bash
curl -X POST http://localhost:8000/tasks/enqueue \
  -H "Content-Type: application/json" \
  -d '{"task_name": "example_task", "duration": 10}'
```

2. Check task status:
```bash
curl http://localhost:8000/tasks/{job_id}
```

3. Batch translation task:
```bash
curl -X POST http://localhost:8000/tasks/batch-translate \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello", "World"], "target_language": "Spanish"}'
```

4. Vector embedding task:
```bash
curl -X POST http://localhost:8000/tasks/vector-embedding \
  -H "Content-Type: application/json" \
  -d '{"text": "Sample text for embedding", "collection_name": "documents"}'
```

### S3 File Operations

1. Upload a file:
```bash
curl -X POST http://localhost:8000/files/upload \
  -F "file=@/path/to/your/file.txt"
```

2. List files:
```bash
curl http://localhost:8000/files
```

3. Download a file:
```bash
curl http://localhost:8000/files/filename.txt -o downloaded.txt
```

4. Delete a file:
```bash
curl -X DELETE http://localhost:8000/files/filename.txt
```

## Development

To run in development mode with hot reload:
```bash
docker-compose up
```

To run only specific services:
```bash
docker-compose up postgres redis qdrant
```

## Stopping Services

```bash
docker-compose down
```

To remove volumes as well:
```bash
docker-compose down -v
```