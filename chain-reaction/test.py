from main import Chain
from apps.translator import Translator
from apps.grounded_gpt import Search, Draft, Main
from utils.chunking import naive_chunking, sentence_chunking, paragraph_chunking, contextual_chunking
from utils.llm import Mistral, Gemini
import os
from dotenv import load_dotenv

load_dotenv()

# test code
if __name__ == "__main__":  # Fixed: __ not **

    # Simple block
    # telugu = Translator(language="Telugu")
    # context = {
    #     "text": "Hello, how are you?"
    # }
    # telugu.run(context=context)
    # print(context)

    # Simple chain telugu -> hindi
    # hindi = Translator(language="Hindi")
    # telugu >> "default" >> hindi
    # context = {
    #     "text": "I like music"
    # }
    # chain = Chain(starting_block=telugu)
    # chain.run(context=context)
    # print(context)

    # Simple chain with search
    # search = Search(retries=3)
    # draft = Draft(retries=3)
    # main = Main()
    # search >> main
    # main - "draft" >> draft
    # main - "search" >> search
    # context = {
    #     "query": "What is the capital of India?"
    # }
    # chain = Chain(starting_block=main)
    # chain.run(context=context)
    # print(context)

    # Chunking test
#     text = """Hello, how are you? I am fine. I like music. I like to play guitar. I like to sing. 

# I like to dance. I like to read. I like to write. I like to code. I like to travel. I like to eat. I like to sleep. I like to play games. I like to watch movies. I like to watch TV. I like to listen to music. I like to watch YouTube. I like to watch Netflix. I like to watch Amazon Prime. I like to watch Disney+."""
#     model = "gpt-4o-mini"

#     def pretty_print_chunks(title, chunks):
#         print(f"{title} ({len(chunks)} chunks):")
#         for i, chunk in enumerate(chunks, 1):
#             print(f"  Chunk {i}: {repr(chunk)}")
#         print("-" * 40)

#     naive_chunks = naive_chunking(text, max_chunk_size=50, model=model)
#     sentence_chunks = sentence_chunking(text, max_chunk_size=50, model=model)
#     paragraph_chunks = paragraph_chunking(text, max_chunk_size=50, model=model)
#     contextual_chunks = contextual_chunking(text, max_chunk_size=50, model=model, summary='Summary of the text')


    # Embedding test

    # mistral = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    # gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"))

    # text = "Hello, how are you? I am fine. I like music. I like to play guitar. I like to sing. I like to dance. I like to read. I like to write. I like to code. I like to travel. I like to eat. I like to sleep. I like to play games. I like to watch movies. I like to watch TV. I like to listen to music. I like to watch YouTube. I like to watch Netflix. I like to watch Amazon Prime. I like to watch Disney+."
    # print(mistral.generate_embeddings(text, model="mistral-embed"))
    # print(gemini.generate_embeddings(text, model="gemini-embedding-001"))

    # add a new job to the rq queue
    from tasks import long_running_task, process_translation_batch, process_vector_embedding
    from database import task_queue
    
    # Example 1: Add a long-running task to the queue
    job1 = long_running_task.delay("Sample Translation Job", 3)
    print(f"Job 1 queued with ID: {job1.id}")
    
    # Example 2: Add a batch translation task
    texts_to_translate = ["Hello world", "How are you?", "Good morning"]
    job2 = process_translation_batch.delay(texts_to_translate, "Spanish")
    print(f"Job 2 queued with ID: {job2.id}")
    
    # Example 3: Add a vector embedding task
    job3 = process_vector_embedding.delay("Sample text for embedding", "documents")
    print(f"Job 3 queued with ID: {job3.id}")
    
    # Wait for jobs to complete and get results
    print("Waiting for jobs to complete...")
    import time
    
    # Wait for job completion with timeout
    timeout = 10  # seconds
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if job1.is_finished and job2.is_finished and job3.is_finished:
            break
        time.sleep(0.5)
    
    result1 = job1.result
    result2 = job2.result
    result3 = job3.result
    
    print(f"Job 1 result: {result1}")
    print(f"Job 2 result: {result2}")
    print(f"Job 3 result: {result3}")