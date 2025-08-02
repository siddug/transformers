from dotenv import load_dotenv
import os
load_dotenv()

from utils.llm import Mistral, Gemini
from main import Block, Chain
import requests
import re
import json

"""
Blocks:
1. Book Search Block
2. Agent Block
"""

class OpenLibraryConfig:
    def __init__(self):
        # self.api_key = os.environ.get("OPENLIBRARY_API_KEY")
        self.api_url = "https://openlibrary.org/search.json"
        self.author_search_url = "https://openlibrary.org/search/authors.json"

config = OpenLibraryConfig()

class BookSearchBlock(Block):
    def __init__(self, logging: bool = False):
        super().__init__(name="BookSearchBlock", description="A block that can search for books", retries=3, logging=logging)

    def prepare(self, context):
        return {
            "query": context.get("query", ""),
            "title": context.get("title", ""),
            "author": context.get("author", ""),
            "sort": context.get("sort", ""),
        }

    def execute(self, context, prepare_response):
        params = {}
        if prepare_response["query"]:
            params["q"] = prepare_response["query"]
        if prepare_response["title"]:
            params["title"] = prepare_response["title"]
        if prepare_response["author"]:
            params["author"] = prepare_response["author"]
        if prepare_response["sort"]:
            params["sort"] = prepare_response["sort"]
        
        print(f"Searching OpenLibrary with params: {params}")
        
        try:
            response = requests.get(config.api_url, params=params)
            response.raise_for_status()
            data = response.json()
            return ["success", data]
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return ["error", f"Request failed: {str(e)}"]
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response text: {response.text[:500]}")
            return ["error", f"Invalid JSON response: {str(e)}"]

    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            docs = execute_response[1].get("docs", [])
            if docs:
                results = []
                for i, doc in enumerate(docs[:10]):  # Limit to top 10 results
                    title = doc.get('title', 'Unknown Title')
                    authors = doc.get('author_name', ['Unknown Author'])
                    first_publish = doc.get('first_publish_year', 'Unknown')
                    isbn = doc.get('isbn', ['N/A'])[0] if doc.get('isbn') else 'N/A'
                    
                    result = f"{i+1}. {title} by {', '.join(authors[:2])}"
                    if first_publish != 'Unknown':
                        result += f" ({first_publish})"
                    results.append(result)
                
                context["readable_results"] = "\n".join(results)
            else:
                context["readable_results"] = "No results found"
        else:
            context["readable_results"] = f"Error retrieving results: {execute_response[1]}"

        # Build search description
        search_desc = []
        if prepare_response.get("query"):
            search_desc.append(f"query: {prepare_response['query']}")
        if prepare_response.get("title"):
            search_desc.append(f"title: {prepare_response['title']}")
        if prepare_response.get("author"):
            search_desc.append(f"author: {prepare_response['author']}")
        
        search_info = " AND ".join(search_desc) if search_desc else "empty search"
        
        context["context_so_far"] = context["context_so_far"] + f"\n\nBook Search Results for {search_info}:\n" + context["readable_results"]
        return "default"

class AnswerBlock(Block):
    def __init__(self, logging: bool = False):
        super().__init__(name="AnswerBlock", description="A block that can answer questions", retries=3, logging=logging)
        self.mistral = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))
        self.gemini = Gemini(api_key=os.environ.get("GEMINI_API_KEY"))

    def prepare(self, context):
        self.token = 0
        return {
            "user_query": context.get("user_query", ""),
            "context_so_far": context.get("context_so_far", ""),
        }

    def execute(self, context, prepare_response):
        prompt = f"""
        You are answering a user's query based on all the context so far.
        User Query: {prepare_response["user_query"]}
        Context So Far: {prepare_response["context_so_far"]}
        Answer:
        """
        self.token += 1
        self.token = self.token % 2

        if self.token == 0:
            response = self.mistral.generate_text(messages=[{"role": "user", "content": prompt, "type": "text"}])
        else:
            response = self.gemini.generate_text(messages=[{"role": "user", "content": prompt, "type": "text"}])

        return ["success", response]


    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["answer"] = execute_response[1]
        else:
            context["answer"] = f"Error answering question: {execute_response[1]}"
        return "default"

class AgentBlock(Block):
    def __init__(self, logging: bool = False):
        super().__init__(name="AgentBlock", description="A block that can answer questions", retries=3, logging=logging)
        self.mistral = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"), model="mistral-large-latest")
        self.gemini = Gemini(api_key=os.environ.get("GEMINI_API_KEY"), model="gemini-2.0-flash")

    def prepare(self, context):
        self.token = 0
        return {
            "user_query": context.get("user_query", ""),
            "context_so_far": context.get("context_so_far", ""),
        }

    def execute(self, context, prepare_response):
        prompt = f"""
        You are an agent that can answer questions about books using the OpenLibrary API.
        
        User Query: {prepare_response["user_query"]}
        Context So Far: {prepare_response["context_so_far"]}
        
        IMPORTANT: You MUST use BookSearchBlock FIRST if you haven't searched yet or need more information.
        
        Available tools:
        1. BookSearchBlock - Use this to search OpenLibrary for books. You MUST use this tool at least once before answering.
           Inputs (use only one at a time):
           - query: general search query (avoid complex queries like "books similar to X")
           - title: search by exact book title
           - author: search by author name (e.g., "Ted Chiang" not "books by Ted Chiang")
           - sort: sort results (relevance, title, author)
           
           For similarity requests: First search for the author or the specific book, then analyze results
           For genre requests: Search for genre in query. Ignore the sort parameter.
        
        2. AnswerBlock - Use this ONLY AFTER you have searched for books and have results in the context.
        
        Decision Logic:
        - If "Context So Far" is empty or doesn't contain book search results → USE BookSearchBlock
        - If "Context So Far" contains book results and you can answer the user's query → USE AnswerBlock
        - If you need more specific results → USE BookSearchBlock with refined query
        
        Response format (JSON):
        {{
            "tool": "BookSearchBlock" or "AnswerBlock",
            "input": {{
                "query": "string",
                "title": "string", 
                "author": "string",
                "sort": "string"
            }}
        }}
        """

        self.token += 1
        self.token = self.token % 2

        print("Prompt: ", prompt)

        if self.token == 0:
            print("Using Mistral")
            response = self.mistral.generate_text(model="mistral-large-latest", messages=[{"role": "user", "content": prompt, "type": "text"}])
        else:
            print("Using Gemini")
            response = self.gemini.generate_text(model="gemini-2.0-flash", messages=[{"role": "user", "content": prompt, "type": "text"}])

        # search for {.*} in the response to parse the JSON (non-greedy was too restrictive)
        response = re.search(r"\{.*\}", response, re.DOTALL)
        if response:
            try:
                response = json.loads(response.group(0))
            except json.JSONDecodeError:
                print(f"Failed to parse JSON: {response.group(0)}")
                response = {"tool": "BookSearchBlock", "input": {"query": prepare_response["user_query"]}}
        else:
            print("No JSON found in response, defaulting to BookSearchBlock")
            response = {"tool": "BookSearchBlock", "input": {"query": prepare_response["user_query"]}}
        return ["success", response]

    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        if execute_response[0] == "success":
            context["tool_input"] = execute_response[1]["input"]
            # set the tool's input query, title, author, and sort in the context
            context["query"] = execute_response[1]["input"].get("query", "")
            context["title"] = execute_response[1]["input"].get("title", "")
            context["author"] = execute_response[1]["input"].get("author", "")
            context["sort"] = execute_response[1]["input"].get("sort", "")
            # user's query and context so far will already be present in the context
            return execute_response[1]["tool"]
        else:
            context["answer"] = f"Error answering question: {str(execute_response[1])}"
            return "default"

book_search_block = BookSearchBlock(logging=True)
answer_block = AnswerBlock(logging=True)
agent_block = AgentBlock(logging=True)
chain = Chain(starting_block=agent_block)
agent_block - "BookSearchBlock" >> book_search_block
agent_block - "AnswerBlock" >> answer_block
book_search_block >> agent_block

context = {"user_query": "What are the top rated books in fantasy genre?", "context_so_far": ""}
chain.run(context=context)
print(context.get("answer", ""))
