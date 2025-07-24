from main import Block
from utils.search import DuckDuckGoSearch, BraveSearch
from utils.llm import Mistral, Gemini
import os
from dotenv import load_dotenv
import json

load_dotenv()


# One node, that decides whether to search or draft answer
# One node that searches and comes back
# One node that drafts answer

class Search(Block):
    def __init__(self, retries: int = 1):
        super().__init__(name="SearchNode", description="SearchNode is a block that searches the web for information.", retries=retries)

        # setup for search engines
        self.search_engines = [
            DuckDuckGoSearch(),
            BraveSearch(api_key=os.getenv("BRAVE_API_KEY"))
        ]
        self.rotate_token = 0

    def prepare(self, context: dict):
        # nothing much to do here. we will be called hopefull with a query
        return context["sub_query"]
    
    def execute(self, context, prepare_response):
        if prepare_response is None:
            # Nothing to query here
            return "No query to search for"
        
        # rotate search engines
        self.rotate_token = (self.rotate_token + 1) % len(self.search_engines)
        search_engine = self.search_engines[self.rotate_token]

        return search_engine.search(prepare_response)

    def execute_fallback(self, context, prepare_response, error):
        return "Error: " + str(error)

    def post_process(self, context, prepare_response, execute_response):
        # we save the search results in the context
        context["research_context"] = f"""{"" if "research_context" not in context or context["research_context"] is None else context["research_context"]}
        
        SEARCH: {context["sub_query"]}
        RESULTS:
        {execute_response}"""

        return "default"

class Draft(Block):
    def __init__(self, retries: int = 1):
        super().__init__(name="Draft", description="Draft is a block that drafts an answer.", retries=retries)

        self.llms = [
            Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="mistral-large-latest"),
            Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
        ]
        self.rotate_token = 0
    
    def prepare(self, context: dict):
        return {
            "research_context": context["research_context"],
            "query": context["query"]
        }

    def execute(self, context, prepare_response):
        if prepare_response is None:
            # Nothing to draft here
            return "No query to draft for"
        
        # rotate llms
        self.rotate_token = (self.rotate_token + 1) % len(self.llms)
        llm = self.llms[self.rotate_token]

        prompt = f"""
        You are a helpful assistant that drafts an answer to a question.
        The question is: {prepare_response["query"]}
        The research context is: 
        {prepare_response["research_context"]}

        Please draft an answer to the question based on the research context.
        Please be concise and to the point.
        Please be accurate and to the point.
        """

        return llm.generate_text(messages=[
            {
                "role": "user",
                "content": prompt,
                "type": "text"
            }
        ])
    
    def execute_fallback(self, context, prepare_response, error):
        return "Error: " + str(error)
    
    def post_process(self, context, prepare_response, execute_response):
        # we save the draft in the context
        context["draft"] = execute_response
        return None

class Main(Block):
    def __init__(self):
        super().__init__(name="Main", description="Main is a block that combines the draft and the search results to form an answer.")

        self.llms = [
            Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="mistral-large-latest"),
            Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
        ]
        self.rotate_token = 0
    
    def prepare(self, context):
        return {
            "research_context": "research_context" in context and context["research_context"] or None,
            "draft": "draft" in context and context["draft"] or None,
        }

    def execute(self, context, prepare_response):
        if prepare_response is None:
            # Nothing to draft here
            return "No query to draft for"
        
        # rotate llms
        self.rotate_token = (self.rotate_token + 1) % len(self.llms)
        llm = self.llms[self.rotate_token]

        prompt = f"""
        ### INSTRUCTIONS ###
        You are a helpful assistant that uses the search tools to answer user's query. Your job is to decide whether to search more or stop since we have enough information to answer the query.

        ### CONTEXT ###
        The user's query is: {context["query"]}
        Research so far: 
        
        {"Research yet to start" if prepare_response["research_context"] is None else prepare_response["research_context"]}

        ### ACTIONS ###
        1. search 
           - description: if you think we need to search more. Pick this when we don't have enough information to answer the query.
           - parameters:
             - query: the query to search for

        2. stop
           - description: if you think we have enough information to answer the query. Pick this when we have enough information to answer the query.

        ### RESPONSE ###
        FORMAT: JSON
        thinking: string. Reasoning about why you picked the action.
        action: "search" | "stop"
        action_parameters: object | null

        EXAMPLE:
        {{
            "thinking": "I think we need to search more because we don't have enough information to answer the query.",
            "action": "search",
            "action_parameters": {{"query": "the query to search in browser for"}}
        }}

        OR

        {{
            "thinking": "I think we have enough information to answer the query.",
            "action": "stop",
            "action_parameters": null
        }}

        """

        response = llm.generate_text(messages=[
            {
                "role": "user",
                "content": prompt,
                "type": "text"
            }
        ])

        try:
            return llm.parse_response(response)
        except Exception as e:
            return {
                "thinking": f"""Error parsing response: {str(e)} \n\n Response: {response}""",
                "action": "error",
                "action_parameters": {
                    "error": str(e)
                }
            }

    def execute_fallback(self, context, prepare_response, error):
        return {
            "thinking": "Error: " + str(error),
            "action": "error",
            "action_parameters": {
                "error": str(error)
            }
        }

    def post_process(self, context, prepare_response, execute_response):
        if execute_response["action"] == "search":
            context["sub_query"] = execute_response["action_parameters"]["query"]
            return "search" # we search
        elif execute_response["action"] == "stop":
            return "draft" # we draft
        else:
            context["error"] = execute_response["action_parameters"]["error"]
            return "error" # we stop