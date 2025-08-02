from email import message
import logging
import os
from tracemalloc import start

import requests
from utils.llm import Mistral, Gemini, get_data_url_and_mimetype
from main import Block, Chain
import json
import re
import dotenv

dotenv.load_dotenv()

"""
Let's build a chain that helps a user interact with MET Museum's collection.

Blocks:
- GetObjectBlock: Get an object from the MET Museum's collection given an object ID.
- SearchForObjectsBlock: Search for objects in the MET Museum's collection given a search query.
- DepartmentBlock: Get the department of an object given an object ID. --- Unnecessary. Since it's only 21 departments. Just embed this in prompts where necessary.
- UnderstandImageBlock: Understand the image of an object given an image URL.
- ReplyBlock: Construct a reply to the user's query given the context.

Chain:
- GetObjectBlock >> UnderstandImageBlock >> AgentBlock
- SearchForObjectsBlock >> AgentBlock
- UnderstandImageBlock >> AgentBlock
- ReplyBlock >> END
- AgentBlock - "GetObjectBlock" >> "GetObjectBlock"
- AgentBlock - "SearchForObjectsBlock" >> "SearchForObjectsBlock"
- AgentBlock - "UnderstandImageBlock" >> "UnderstandImageBlock"
- AgentBlock - "ReplyBlock" >> "ReplyBlock"

"""

class Config:
    def __init__(self):
        self.api_url = "https://collectionapi.metmuseum.org/public/collection/v1"
        self.search_objects_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
        self.get_object_url = "https://collectionapi.metmuseum.org/public/collection/v1/objects/"
        self.mistral = Mistral(api_key=os.getenv("MISTRAL_API_KEY"), model="mistral-medium-latest")
        self.gemini = Gemini(api_key=os.getenv("GEMINI_API_KEY"), model="gemini-2.0-flash")
        self.departments = {
            "departments": [
                {
                "departmentId": 1,
                "displayName": "American Decorative Arts"
                },
                {
                "departmentId": 3,
                "displayName": "Ancient Near Eastern Art"
                },
                {
                "departmentId": 4,
                "displayName": "Arms and Armor"
                },
                {
                "departmentId": 5,
                "displayName": "Arts of Africa, Oceania, and the Americas"
                },
                {
                "departmentId": 6,
                "displayName": "Asian Art"
                },
                {
                "departmentId": 7,
                "displayName": "The Cloisters"
                },
                {
                "departmentId": 8,
                "displayName": "The Costume Institute"
                },
                {
                "departmentId": 9,
                "displayName": "Drawings and Prints"
                },
                {
                "departmentId": 10,
                "displayName": "Egyptian Art"
                },
                {
                "departmentId": 11,
                "displayName": "European Paintings"
                },
                {
                "departmentId": 12,
                "displayName": "European Sculpture and Decorative Arts"
                },
                {
                "departmentId": 13,
                "displayName": "Greek and Roman Art"
                },
                {
                "departmentId": 14,
                "displayName": "Islamic Art"
                },
                {
                "departmentId": 15,
                "displayName": "The Robert Lehman Collection"
                },
                {
                "departmentId": 16,
                "displayName": "The Libraries"
                },
                {
                "departmentId": 17,
                "displayName": "Medieval Art"
                },
                {
                "departmentId": 18,
                "displayName": "Musical Instruments"
                },
                {
                "departmentId": 19,
                "displayName": "Photographs"
                },
                {
                "departmentId": 21,
                "displayName": "Modern Art"
                }
            ]
        }

class GetObjectBlock(Block):
    def __init__(self, logging: bool = False):
        self.config = Config()
        super().__init__(name="GetObjectBlock", description="Get an object from the MET Museum's collection given an object ID", retries=3, logging=logging)
    
    def prepare(self, context):
        return {"object_id": context["tool_input"]["object_id"]}

    def execute(self, context, prepare_response):
        object_id = prepare_response["object_id"]

        response = requests.get(self.config.get_object_url + object_id)
        response.raise_for_status()

        return ["success", response.json()]

    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        [status, response] = execute_response

        print("GetObjectBlock response: ", response)

        if status == "success":
            # lets get important fields of the object
            response = {
                "object_id": response["objectID"],
                "is_highlight": response["isHighlight"],
                "is_public_domain": response["isPublicDomain"],
                "primary_image_url": response["primaryImage"],
                "constituents": response["constituents"],
                "department": response["department"],
                "object_name": response["title"],
                "culture": response["culture"],
                "period": response["period"],
                "artist_role": response["artistRole"],
                "artist_name": response["artistDisplayName"],
                "artist_bio": response["artistDisplayBio"],
                "credit_line": response["creditLine"],
                "city": response["city"],
                "state": response["state"],
                "country": response["country"],
                "medium": response["medium"],
                "object_date": response["objectDate"],
                "object_url": response["objectURL"],
            }

        history = context.get("history", "")
        history += f"""GetObjectBlock: {str(prepare_response)}
        Response: 
        {str(response)}
        """

        # update history in context
        context["history"] = history

        # this is for intermediary use
        context["tool_response"] = response
        context["tool_response_status"] = status

        if status == "success" and response.get("primary_image_url", "") != "":
            # Set the image URL for UnderstandImageBlock
            context["tool_input"] = {"image_url": response["primary_image_url"]}
            return "UnderstandImageBlock"
        
        return "AgentBlock"

class SearchForObjectsBlock(Block):
    def __init__(self, logging: bool = False):
        self.config = Config()
        super().__init__(name="SearchForObjectsBlock", description="Search for objects in the MET Museum's collection given a search query", retries=3, logging=logging)

    def prepare(self, context):
        return {"tool_input": context["tool_input"]}

    def execute(self, context, prepare_response):
        query = prepare_response["tool_input"]

        # split params from query
        url_part = ""
        if "query" in query:
            url_part += f"q={query['query']}&"
        if "title" in query:
            url_part += f"title={query['title']}&"
        if "artist" in query:
            url_part += f"artist={query['artist']}&"
        if "departmentId" in query:
            url_part += f"departmentId={query['departmentId']}&"
        if "tags" in query:
            url_part += f"tags={query['tags']}&"
        if "isOnView" in query:
            url_part += f"isOnView={query['isOnView']}&"
        if "medium" in query:
            url_part += f"medium={query['medium']}&"

        print(self.config.search_objects_url + "?" + url_part)

        response = requests.get(self.config.search_objects_url + "?" + url_part)
        response.raise_for_status()

        return ["success", response.json()]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        [status, response] = execute_response

        # update history in context
        history = context.get("history", "")
        history += f"""SearchForObjectsBlock: {str(prepare_response['tool_input'])}
        Response: 
        {str(response)}
        """

        context["history"] = history

        # this is for intermediary use
        context["tool_response"] = response
        context["tool_response_status"] = status

        return "AgentBlock"

class UnderstandImageBlock(Block):
    def __init__(self, logging: bool = False):
        self.config = Config()
        self.mistral = self.config.mistral
        self.gemini = self.config.gemini
        super().__init__(name="UnderstandImageBlock", description="Understand the image of an object given an image URL", retries=3, logging=logging)

    def prepare(self, context):
        self.running_tokens = 0
        return {"image_url": context["tool_input"]["image_url"]}

    def execute(self, context, prepare_response):
        self.running_tokens += 1
        self.running_tokens = self.running_tokens % 2

        image_url = prepare_response["image_url"]

        # get image data url and mimetype
        print(f"Fetching image from: {image_url}")
        data_url, mimetype = get_data_url_and_mimetype(image_url)
        print(f"Image fetched successfully. Mimetype: {mimetype}")

        # get image description
        prompt = f"""
        You are a helpful assistant that can describe images. Explain the image in 3-4 sentences.
        """

        messages = [
            {
                "role": "user",
                "content": prompt,
                "type": "text"
            },
            {
                "role": "user",
                "type": "image_url",
                "content": {
                    "dataUrl": data_url,
                    "mime": mimetype
                }
            }
        ]


        llm = self.mistral if self.running_tokens == 0 else self.gemini
        print(f"Using LLM: {llm.__class__.__name__} with model: {llm.model}")

        try:
            response = llm.generate_text(messages, model=llm.model)
            print(f"LLM response received: {response[:100]}...")
        except Exception as e:
            print(f"LLM error: {e}")
            return ["error", str(e)]

        return ["success", response]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        [status, response] = execute_response

        history = context.get("history", "")

        history += f"""UnderstandImageBlock: {prepare_response['image_url']}
        Response: 
        {str(response)}
        """

        context["history"] = history

        # this is for intermediary use
        context["tool_response"] = response
        context["tool_response_status"] = status

        return "AgentBlock"


class ReplyBlock(Block):
    def __init__(self, logging: bool = False):
        self.config = Config()
        self.mistral = self.config.mistral
        self.gemini = self.config.gemini
        super().__init__(name="ReplyBlock", description="Reply to the user's query given the context", retries=3, logging=logging)

    def prepare(self, context):
        self.running_tokens = 0
        return {"query": context["query"], "history": context["history"]}

    def execute(self, context, prepare_response):
        self.running_tokens += 1
        self.running_tokens = self.running_tokens % 2

        llm = self.mistral if self.running_tokens == 0 else self.gemini

        prompt = f"""
        You are a helpful assistant that can answer questions about the MET Museum's collection.
        You are given a query and a history of the context.
        Query: {prepare_response['query']}
        History: 
        {prepare_response['history']}

        You need to reply to the user's query based on the context.
        Reply:
        """

        messages = [
            {
                "role": "user",
                "content": prompt,
                "type": "text"
            }
        ]

        response = llm.generate_text(messages, model=llm.model, max_tokens=1000)

        return ["success", response]

    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        [status, response] = execute_response

        history = context.get("history", "")

        history += f"""ReplyBlock: {prepare_response['query']}
        Response: 
        {str(response)}
        """

        context["history"] = history

        # this is for intermediary use
        context["tool_response"] = response
        context["tool_response_status"] = status

        # end the chain
        context["answer"] = response
        return "END"

class AgentBlock(Block):
    def __init__(self, logging: bool = False):
        self.config = Config()
        self.mistral = self.config.mistral
        self.gemini = self.config.gemini
        super().__init__(name="AgentBlock", description="Agent block", retries=3, logging=logging)

    def prepare(self, context):
        self.running_tokens = 0
        return {"query": context["query"], "history": context["history"]}

    def execute(self, context, prepare_response):
        self.running_tokens += 1
        self.running_tokens = self.running_tokens % 2

        llm = self.mistral if self.running_tokens == 0 else self.gemini

        prompt = f"""
        You are a helpful assistant that can answer questions about the MET Museum's collection.
        You have few tools at your disposal.

        Here are the departments in the MET Museum's collection:
        {str(self.config.departments)}

        Tools:
        - GetObjectBlock: Get an object from the MET Museum's collection given an object ID.
        - SearchForObjectsBlock: Search for objects in the MET Museum's collection given a search query.
        - UnderstandImageBlock: Understand the image of an object given an image URL.
        - ReplyBlock: Reply to the user's query given the context.

        You need to decide which tool to use based on the query.
        Query: {prepare_response['query']}
        History so far:
        {prepare_response['history']}

        You need to decide which tool to use based on the query.
        Tool to use:
        - GetObjectBlock:
            - Tool inputs:
                - object_id: The ID of the object to get.
        - SearchForObjectsBlock:
            - Tool inputs:
                - query: The search query to use.
                - isHighlight: Whether to search for highlighted objects. True/False (optional)
                - departmentId: The ID of the department to search in. (optional)
                - isOnView: Whether to search for objects on view. True/False (optional)
                - medium: The medium of the objects to search for. (optional)
        - UnderstandImageBlock:
            - Tool inputs:
                - image_url: The URL of the image to understand.
        - ReplyBlock:
            - Tool inputs: N/A (already provided in the history)

        You need to decide which tool to use based on the query.

        Reply format:
        {{
            "reasoning": "reasoning for the tool to use" # 2-3 lines reasoning for the tool to use
            "tool": "GetObjectBlock" | "SearchForObjectsBlock" | "UnderstandImageBlock" | "ReplyBlock",
            "tool_input": {{
                "object_id": "123456" | "query": "search query" | "image_url": "image url" | N/A etc
            }},
        }}

        Example:
        {{
            "reasoning": "The user is asking about a specific object. I will use the GetObjectBlock to get the object.",
            "tool": "GetObjectBlock",
            "tool_input": {{
                "object_id": "123456"
            }}
        }}
        """

        messages = [
            {
                "role": "user",
                "content": prompt,
                "type": "text"
            }
        ]

        response = llm.generate_text(messages, model=llm.model, max_tokens=1000)

        return ["success", response]
    
    def execute_fallback(self, context, prepare_response, error):
        return ["error", error]

    def post_process(self, context, prepare_response, execute_response):
        [status, response] = execute_response

        if status == "success":
            response = re.search(r"\{.*\}", response, re.DOTALL)
            if response:
                try:
                    response = json.loads(response.group(0))
                    context["tool_input"] = response["tool_input"]
                    context["tool"] = response["tool"]
                    return response["tool"]
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON: {response.group(0)}")
                    return "ReplyBlock"
            else:
                print("No JSON found in response, defaulting to AgentBlock")
                return "ReplyBlock"
        
        # update history with the error and return reply block
        history = context.get("history", "")

        history += f"""AgentBlock: {prepare_response['query']}
        Response: 
        {str(response)}
        """

        context["history"] = history
        return "ReplyBlock"


# lets construct it
get_object_block = GetObjectBlock(logging=True)
search_for_objects_block = SearchForObjectsBlock(logging=True)
understand_image_block = UnderstandImageBlock(logging=True)
reply_block = ReplyBlock(logging=True)
agent_block = AgentBlock(logging=True)

get_object_block - "UnderstandImageBlock" >> understand_image_block
get_object_block - "AgentBlock" >> agent_block
search_for_objects_block - "AgentBlock" >> agent_block
understand_image_block - "AgentBlock" >> agent_block
agent_block - "GetObjectBlock" >> get_object_block
agent_block - "SearchForObjectsBlock" >> search_for_objects_block
agent_block - "ReplyBlock" >> reply_block
agent_block - "UnderstandImageBlock" >> understand_image_block

chain = Chain(starting_block=agent_block)
context = {
    "query": "Tell me about the european art department at the MET Museum. What are some of the most famous artworks in the department?",
    "history": ""
}
chain.run(context=context)
print(context.get("answer", "No answer found"))
print(context.get("history", "No history found"))





