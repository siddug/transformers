
import requests
from ddgs import DDGS

class Search:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str):
        pass

class DuckDuckGoSearch(Search):
    def __init__(self, api_key: str = None):
        super().__init__(api_key)

    def search(self, query: str):
        results = DDGS().text(query, max_results=10)
        return "\n\n".join(map(lambda result: f"Title: {result['title']}\nURL: {result['href']}\nSnippet: {result['body']}", results))

class BraveSearch(Search):
    def __init__(self, api_key: str):
        super().__init__(api_key)

    def search(self, query: str):
        headers = {
            "x-subscription-token": self.api_key,
            "accept": "application/json",
        }
        response = requests.get(f"https://api.search.brave.com/api/v2/search?q={query}", headers=headers)

        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        results = response.json()
        web_results = results["web"]["results"]
        return "\n\n".join(map(lambda result: f"Title: {result['title']}\nURL: {result['url']}\nDescription: {result['description']}", web_results))