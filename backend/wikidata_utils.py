import requests

def wikidata_search(search_term: str, type: str, limit=5):
    print(f"Searching Wikidata for term \"{search_term}\" of type {type}")
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": search_term,
        "format": "json",
        "language": "en",
        "type": type,
        "limit": limit
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def query_wikidata(query: str):
    print(f"Running SPARQL query: {query}")
    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/sparql-results+json"}
    params = {"query": query}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()