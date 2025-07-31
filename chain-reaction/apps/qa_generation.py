"""
Q&A Generation using Chain-Reaction Framework

This module implements the synthetic Q&A generation flow for Github repositories.
For each chunk in a file, it:
1. Scores the chunk for suitability
2. Generates questions if score is above threshold
3. Evolves questions using various strategies
4. Generates answers using context
"""

import uuid
import random
import time
from database import engine, gold_qa_table
from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from main import Block, Chain
from utils.llm import Mistral, Gemini
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

load_dotenv()

# Evolution strategies
EVOLUTION_STRATEGIES = [
    "reasoning",
    "multicontext",
    "concretizing",
    "constrained",
    "comparative",
    "hypothetical",
    "inbreadth"
]

class ChunkScoringBlock(Block):
    """Scores chunks for their suitability to generate Q&A pairs"""
    
    def __init__(self, logging: bool = False):
        super().__init__(
            name="ChunkScoringBlock",
            description="Scores chunks based on clarity, depth, structure, and relevance",
            retries=3,
            retry_delay=1,
            logging=logging
        )
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
    
    def prepare(self, context: dict):
        return context.get("chunks", [])
    
    def execute(self, context, prepare_response):
        chunks = prepare_response
        scored_chunks = []
        
        for chunk in chunks:
            prompt = f"""
            Score the following code chunk for its suitability to generate meaningful Q&A pairs.
            
            CHUNK:
            {chunk['text']}
            
            Score each criterion from 0 to 1:
            1. Clarity: How well-written and understandable is the chunk?
            2. Depth: How much meaningful information does the chunk contain?
            3. Structure: How well-structured is the chunk?
            4. Relevance: How relevant is this chunk to understanding the codebase?
            
            Return ONLY a JSON object with this format:
            {{
                "clarity": 0.8,
                "depth": 0.7,
                "structure": 0.9,
                "relevance": 0.8,
                "overall": 0.8
            }}
            """
            
            response = self.gemini.generate_text([{"role": "user", "content": prompt, "type": "text"}])
            
            try:
                import json
                # Clean the response to extract JSON
                response_text = response.strip()
                # Try to find JSON in the response
                if "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_str = response_text[json_start:json_end]
                    scores = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
                
                chunk['scores'] = scores
                chunk['overall_score'] = scores.get('overall', 
                    (scores.get('clarity', 0) + scores.get('depth', 0) + 
                     scores.get('structure', 0) + scores.get('relevance', 0)) / 4)
                print(f"Chunk scored: {chunk['overall_score']:.2f} - {chunk['text'][:50]}...")
            except Exception as e:
                print(f"Error parsing scores: {e}, Response: {response}")
                # Default scores if parsing fails
                chunk['scores'] = {
                    "clarity": 0.5,
                    "depth": 0.5,
                    "structure": 0.5,
                    "relevance": 0.5,
                    "overall": 0.5
                }
                chunk['overall_score'] = 0.5
            
            scored_chunks.append(chunk)
            time.sleep(0.5)  # Rate limiting
        
        return ["success", scored_chunks]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["scored_chunks"] = execute_response[1]
            # Filter chunks with score above threshold
            threshold = context.get("score_threshold", 0.5)
            context["suitable_chunks"] = [
                chunk for chunk in execute_response[1]
                if chunk['overall_score'] >= threshold
            ]
            print(f"ChunkScoringBlock: {len(execute_response[1])} chunks scored, {len(context['suitable_chunks'])} suitable (threshold: {threshold})")
            if context["suitable_chunks"]:
                print(f"Sample scores: {[chunk['overall_score'] for chunk in execute_response[1][:3]]}")
        return "default"

class QuestionGenerationBlock(Block):
    """Generates questions for suitable chunks using related context"""
    
    def __init__(self, repo_id: uuid.UUID, logging: bool = False):
        super().__init__(
            name="QuestionGenerationBlock",
            description="Generates questions using chunk and related context",
            retries=3,
            retry_delay=1,
            logging=logging
        )
        self.repo_id = repo_id
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
        self.mistral = Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="codestral-embed")
        self.qdrant = QdrantClient(host=os.getenv("QDRANT_HOST"), port=int(os.getenv("QDRANT_PORT")))
    
    def prepare(self, context: dict):
        return context.get("suitable_chunks", [])
    
    def execute(self, context, prepare_response):
        chunks = prepare_response
        qa_pairs = []
        
        if not chunks:
            print(f"QuestionGenerationBlock: No suitable chunks received")
            return ["success", []]
        
        print(f"QuestionGenerationBlock: Processing {len(chunks)} chunks")
        
        for chunk in chunks:
            # Get related chunks using vector search
            # embedding = self.mistral.generate_embeddings(chunk['text'], "codestral-embed")
            embedding = self.gemini.generate_embeddings(chunk['text'], "gemini-embedding-001")
            
            results = self.qdrant.search(
                collection_name="chunks",
                query_vector=embedding,
                limit=5,
                with_payload=True,
                query_filter=Filter(
                    must=[FieldCondition(key="repo_id", match=MatchValue(value=str(self.repo_id)))]
                )
            )
            
            # Build context from related chunks
            related_context = "\n\n".join([
                f"File: {result.payload['file_path']}\n{result.payload['raw_chunk_text']}"
                for result in results[1:]  # Skip the first one as it's likely the same chunk
            ])
            
            prompt = f"""
            Generate a high-quality question about the following code chunk.
            
            TARGET CHUNK:
            {chunk['text']}
            
            RELATED CONTEXT FROM CODEBASE:
            {related_context}
            
            Requirements:
            1. The question should be answerable using the target chunk and related context
            2. The question should be clear and self-contained
            3. The question should be relevant to understanding the codebase
            4. Focus on "how", "why", or "what" questions that require understanding
            
            Return ONLY the question text, nothing else.
            """
            
            question = self.gemini.generate_text([{"role": "user", "content": prompt, "type": "text"}], model = "gemini-2.0-flash")
            
            qa_pairs.append({
                "chunk": chunk,
                "question": question.strip(),
                "related_context": related_context
            })
            
            time.sleep(0.5)  # Rate limiting
        
        return ["success", qa_pairs]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["qa_pairs"] = execute_response[1]
        return "default"

class QuestionScoringBlock(Block):
    """Scores generated questions for quality"""
    
    def __init__(self, logging: bool = False):
        super().__init__(
            name="QuestionScoringBlock",
            description="Scores questions for self-containment and clarity",
            retries=3,
            retry_delay=1,
            logging=logging
        )
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
    
    def prepare(self, context: dict):
        return context.get("qa_pairs", [])
    
    def execute(self, context, prepare_response):
        qa_pairs = prepare_response
        scored_qa_pairs = []
        
        if not qa_pairs:
            return ["success", []]
        
        for qa in qa_pairs:
            prompt = f"""
            Score the following question for quality.
            
            QUESTION: {qa['question']}
            
            Score each criterion from 0 to 1:
            1. Self-containment: Can the question be understood without additional context?
            2. Clarity: Is the question clear and unambiguous?
            
            Return ONLY a JSON object with this format:
            {{
                "self_containment": 0.8,
                "clarity": 0.9,
                "overall": 0.85
            }}
            """
            
            response = self.gemini.generate_text([{"role": "user", "content": prompt, "type": "text"}])
            
            try:
                import json
                # Clean the response to extract JSON
                response_text = response.strip()
                if "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_str = response_text[json_start:json_end]
                    scores = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
                
                qa['question_score'] = scores.get('overall', 
                    (scores.get('self_containment', 0) + scores.get('clarity', 0)) / 2)
            except Exception as e:
                print(f"Error parsing question scores: {e}, Response: {response}")
                qa['question_score'] = 0.5
            
            scored_qa_pairs.append(qa)
            time.sleep(0.5)  # Rate limiting
        
        return ["success", scored_qa_pairs]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            # Filter questions with score above threshold
            threshold = context.get("question_threshold", 0.5)
            context["good_qa_pairs"] = [
                qa for qa in execute_response[1]
                if qa['question_score'] >= threshold
            ]
        return "default"

class QuestionEvolutionBlock(Block):
    """Evolves questions using various strategies"""
    
    def __init__(self, logging: bool = False):
        super().__init__(
            name="QuestionEvolutionBlock",
            description="Evolves questions to make them more complex and comprehensive",
            retries=3,
            retry_delay=1,
            logging=logging
        )
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
    
    def prepare(self, context: dict):
        return context.get("good_qa_pairs", [])
    
    def get_evolution_prompt(self, strategy: str, question: str):
        base_prompt = """Rewrite this question to be clear and concise, like a developer would ask it.
        Keep it natural but focused.
        
        Original question: {question}
        
        Evolution approach: {strategy_instruction}
        
        Return only the evolved question."""
        
        strategy_instructions = {
            "reasoning": "Make it require step-by-step debugging or analysis",
            "multicontext": "Include how this relates to other parts of the codebase", 
            "concretizing": "Focus on specific implementation details or code behavior",
            "constrained": "Add a specific constraint like performance, memory, or edge cases",
            "comparative": "Compare this approach with alternative implementations",
            "hypothetical": "Ask what would happen if we modified or removed this code",
            "inbreadth": "Expand to cover related functionality or patterns"
        }
        
        return base_prompt.format(
            question=question,
            strategy_instruction=strategy_instructions[strategy]
        )
    
    def execute(self, context, prepare_response):
        qa_pairs = prepare_response
        evolved_qa_pairs = []
        
        if not qa_pairs:
            return ["success", []]
        
        for qa in qa_pairs:
            # Randomly select 2 evolution strategies
            strategies = random.sample(EVOLUTION_STRATEGIES, 2)
            evolved_question = qa['question']
            
            for strategy in strategies:
                prompt = self.get_evolution_prompt(strategy, evolved_question)
                prompt += "\n\nReturn ONLY the improved question, nothing else."
                
                evolved_question = self.gemini.generate_text([{
                    "role": "user",
                    "content": prompt,
                    "type": "text"
                }])
                time.sleep(0.5)  # Rate limiting
            
            qa['evolved_question'] = evolved_question.strip()
            qa['evolution_strategy'] = "+".join(strategies)
            evolved_qa_pairs.append(qa)
        
        return ["success", evolved_qa_pairs]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["evolved_qa_pairs"] = execute_response[1]
        return "default"

class AnswerGenerationBlock(Block):
    """Generates answers for evolved questions using context"""
    
    def __init__(self, logging: bool = False):
        super().__init__(
            name="AnswerGenerationBlock",
            description="Generates comprehensive answers using chunk and related context",
            retries=3,
            retry_delay=1,
            logging=logging
        )
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
    
    def prepare(self, context: dict):
        return context.get("evolved_qa_pairs", [])
    
    def execute(self, context, prepare_response):
        qa_pairs = prepare_response
        final_qa_pairs = []
        
        if not qa_pairs:
            return ["success", []]
        
        for qa in qa_pairs:
            prompt = f"""
            Answer the following question about the codebase.
            
            QUESTION: {qa['evolved_question']}
            
            TARGET CODE:
            {qa['chunk']['text']}
            
            RELATED CONTEXT:
            {qa['related_context']}
            
            Provide a comprehensive, accurate answer based on the code and context provided.
            Be specific and include relevant details from the code.
            """
            
            answer = self.gemini.generate_text([{"role": "user", "content": prompt, "type": "text"}])
            
            qa['answer'] = answer.strip()
            final_qa_pairs.append(qa)
            
            time.sleep(0.5)  # Rate limiting
        
        return ["success", final_qa_pairs]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["final_qa_pairs"] = execute_response[1]
        return "default"

class SaveQABlock(Block):
    """Saves Q&A pairs to the database"""
    
    def __init__(self, batch_id: uuid.UUID, file_id: uuid.UUID, logging: bool = False):
        super().__init__(
            name="SaveQABlock",
            description="Saves generated Q&A pairs to database",
            retries=3,
            retry_delay=1,
            logging=logging
        )
        self.batch_id = batch_id
        self.file_id = file_id
    
    def prepare(self, context: dict):
        return context.get("final_qa_pairs", [])
    
    def execute(self, context, prepare_response):
        qa_pairs = prepare_response
        
        with Session(engine) as session:
            for qa in qa_pairs:
                # Extract logs for this Q&A pair
                flow_logs = {
                    "timing": context.get("timing", {}),
                    "chain_timing": context.get("chain_timing", {}),
                    "logs": context.get("logs", []),
                    "chunk_text": qa['chunk']['text'][:200] + "..." if len(qa['chunk']['text']) > 200 else qa['chunk']['text'],
                    "related_context": qa.get('related_context', '')[:500] + "..." if len(qa.get('related_context', '')) > 500 else qa.get('related_context', ''),
                    "original_question": qa.get('question', ''),
                    "scores": qa['chunk'].get('scores', {})
                }
                
                stmt = insert(gold_qa_table).values(
                    batch_id=self.batch_id,
                    file_id=self.file_id,
                    chunk_id=qa['chunk']['id'],
                    question=qa['evolved_question'],
                    answer=qa['answer'],
                    evolution_strategy=qa['evolution_strategy'],
                    question_score=qa['question_score'],
                    chunk_score=qa['chunk']['overall_score'],
                    flow_logs=flow_logs
                )
                session.execute(stmt)
            session.commit()
        
        return ["success", len(qa_pairs)]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", str(error)]
    
    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["saved_count"] = execute_response[1]
        return "default"

def work_on_qa_generation(batch_id: uuid.UUID, file_id: uuid.UUID):
    """Main function to generate Q&A pairs for a file"""
    
    # Get file chunks from Qdrant
    qdrant = QdrantClient(host=os.getenv("QDRANT_HOST"), port=int(os.getenv("QDRANT_PORT")))
    
    # Get repo_id from file
    with Session(engine) as session:
        from database import file_table
        stmt = select(file_table.c.repo_id).where(file_table.c.id == file_id)
        repo_id = session.execute(stmt).scalar_one()
    
    # Search for chunks belonging to this file
    results = qdrant.scroll(
        collection_name="chunks",
        scroll_filter=Filter(
            must=[
                FieldCondition(key="file_id", match=MatchValue(value=str(file_id))),
                FieldCondition(key="repo_id", match=MatchValue(value=str(repo_id)))
            ]
        ),
        limit=100,
        with_payload=True
    )
    
    chunks = [{
        "id": point.id,
        "text": point.payload["raw_chunk_text"],
        "file_path": point.payload["file_path"]
    } for point in results[0]]
    
    print(f"work_on_qa_generation: Found {len(chunks)} chunks for file {file_id}")
    
    if not chunks:
        return {"status": "no_chunks", "message": "No chunks found for file"}
    
    # Create the chain
    chunk_scoring = ChunkScoringBlock(logging=False)
    question_gen = QuestionGenerationBlock(repo_id, logging=False)
    question_scoring = QuestionScoringBlock(logging=False)
    question_evolution = QuestionEvolutionBlock(logging=False)
    answer_gen = AnswerGenerationBlock(logging=False)
    save_qa = SaveQABlock(batch_id, file_id)
    
    # Connect blocks
    chunk_scoring >> question_gen
    question_gen >> question_scoring
    question_scoring >> question_evolution
    question_evolution >> answer_gen
    answer_gen >> save_qa
    
    # Create and run the chain
    flow = Chain(name="QAGenerationFlow", starting_block=chunk_scoring)
    context = {
        "chunks": chunks,
        "score_threshold": 0.3,  # Lowered from 0.5 to be more inclusive
        "question_threshold": 0.3  # Lowered from 0.5 to be more inclusive
    }
    
    flow.run(context)
    
    # Log final results
    print(f"\nQA Generation Summary for file {file_id}:")
    print(f"- Chunks processed: {len(context.get('chunks', []))}")
    print(f"- Suitable chunks: {len(context.get('suitable_chunks', []))}")
    print(f"- QA pairs generated: {len(context.get('qa_pairs', []))}")
    print(f"- Good QA pairs: {len(context.get('good_qa_pairs', []))}")
    print(f"- Final QA pairs saved: {context.get('saved_count', 0)}")
    
    return context