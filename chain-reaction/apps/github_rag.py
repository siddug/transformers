"""
The idea - Given a github repo, give an interface for the user to ask questions about the codebase.

Implementation:
1. Ingestion API - 
    - Given a github repo, get the files and folder structure of the codebase
    - Ignore all the files that are not relevant to the codebase (like .git, .env, etc.)
    - For each file, 
        - Summarize the file
        - Schedule a RQ job to convert the file into chunks, 
        - Convert the chunks into vector embeddings
        - Store the summary, chunks, file path and Github repo url and vector embeddings in the database
    - Expose this as an API
        - In the API, we should see total number of files, how many of them are being processed, how many are processed, how many are failed (per file)
2. Repo API - 
    - List files and folders in the repo
    - Get relevant chunks of the repo for a given text with metadata
    - Get a particular file from the repo
2. RAG API - 
    - Using chain-reaction framework, create a RAG agent that takes in User's query
    - Blocks: 
        - Action block - takes in user's query + current context and decides what to do next
        - LLM block - takes in user's query + current context and generates a response
        - Vector search block - takes in a query and searches the vector database for relevant chunks
        - Links:
            - Action - "search" >> Vector search block
            - Action - "answer" >> LLM block
            - Vector search block >> Action
            - LLM block >> END
    - Expose the flow as an API
    - Since this might take time, make blocks and flow's async
    - Each flow run - maintain it as a job in the database with status updates (current block, status, etc.)
    - Expose the job status as an API
3. UI - 
    - NextJS app that accepts a github repo url
    - Take user to Github repo page
    - User can see the files and folders in the repo with status of the files (processing, processed, failed)
    - User can ask questions about the codebase
    - For each question, create a flow run and show the status of the flow run

Next steps:
1. How do we eval this? (Checkout NDCG and Relevancy + Synthetic Q&A generation)
    - What's NDCG?
    - In the retreival step, how do we calculate Contextual Relevancy/ Recall/ Precision?
    - In the generation step, how do we calculate Answer Relevancy/ Faithfulness?
    - How do we generate synthetic Q&A so that we can evaluate the system?
2. What are the generic metrics that we can use to evaluate the system? So I can benchmark RAG against agents?
    - G-eval on the system (custom criteria + eval steps + threshold and using llms to score); Tonality, Safety, Coherence, Answer correctness
    - DAG on the system (graph based evaluation of the system)
3. How do we make the UI interaction better? Instead of polling system? - WebSockets is a good option.
4. Instead of making it a fixed RAG, can we make it an agent with more tools?


PG DB schema:
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

Qdrant DB schema:
- Chunk
    - repo_id 
    - file_id
    - file_path
    - raw_chunk_text
    - vector_embeddings
    - added_at
"""


