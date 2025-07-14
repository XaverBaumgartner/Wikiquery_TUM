import re
from google import genai 
from google.genai import types
from google.auth import load_credentials_from_file
from google.genai.types import HarmCategory, HarmBlockThreshold
from wikidata_utils import wikidata_search


gemini_client_plain = genai.Client(
    api_key="REPLACE THIS"
)
gemini_model_plain = "gemini-2.5-flash"

gemini_client_pretrained = genai.Client(
    vertexai=True,
    credentials= load_credentials_from_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )[0],
    project="REPLACE THIS",
    location="us-central1",
)
gemini_model_pretrained = "projects/REPLACE THIS/locations/REPLACE THIS/endpoints/REPLACE THIS"

config = types.GenerateContentConfig(
    temperature = 0.2,
    max_output_tokens = 65535, # Extremely high to assure generation will not be cut off, good for testing, maybe change before deployment?
    safety_settings = [
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=HarmBlockThreshold.BLOCK_NONE
        )
    ],
    system_instruction = (
        "You are an expert in generating SPARQL-like queries for Wikidata."
        "Your task is to translate the user's natural language query into a SPARQL query, but instead of using Wikidata IDs like Q-items or P-properties, use natural language placeholders in square brackets. For example, use [wd:Johann Sebastian Bach] instead of wd:Q1339, and [wdt:instance of] instead of wdt:P31."
        "Make sure the query results will be in human-readable format! For example, use: SELECT ?country ?countryLabel WHERE {[wd:France] [wdt:shares border with] ?country . SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". }} instead of: SELECT ?country WHERE {[wd:France] [wdt:shares border with] ?country . }"
        "The query should be formatted as a code block starting with ```sparql and ending with ```. "
        "Do not use LaTeX or any other special formatting"
        "Provide a brief explanation of the query, using natural language only. "
    )
)

def gemini(prompt, use_finetune):
    conversation = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    if use_finetune:
        model = gemini_model_pretrained
        client = gemini_client_pretrained
    else:
        model = gemini_model_plain
        client = gemini_client_plain
    return replace_id_placeholders(client.models.generate_content(
        model=model,
        config=config,
        contents=conversation
    ).text)


def replace_id_placeholders(result):
    # print(result)
    placeholders = re.findall(r'(\[.*?\])', result)
    replaced_ids = []
    unresolved_placeholders = []

    for placeholder in placeholders:
        stripped_placeholder = placeholder.strip('[]')
        if "AUTO_LANGUAGE" in stripped_placeholder:
            continue
        prefix = stripped_placeholder.split(":")[0]
        search_type = {
            "wd": "item",
            "skos": "item",
            "schema": "item",
            "wdt": "property",
            "pq": "property",
            "ps": "property",
            "p": "property",
        }.get(prefix, None)
        if not search_type:
            unresolved_placeholders.append(placeholder + " due to unknown type")
            continue
        search_term = stripped_placeholder.split(":")[1]

        search_result = wikidata_search(search_term, search_type, limit=1)
        if "search" not in search_result or not search_result["search"]:
            unresolved_placeholders.append(search_term + "of type " + search_type + " yielded no results")
            continue
        entity_id = search_result["search"][0]["id"]
        replacement = f"{prefix}:{entity_id}"
        result = re.sub(re.escape(placeholder), replacement, result, flags=re.IGNORECASE)
        replaced_ids.append(search_term + " -> " + replacement)

    if replaced_ids: result += "\n\nSome IDs were automatically replaced:\n" + ", ".join(replaced_ids)
    if unresolved_placeholders: result += "\nSome IDs could not be found:\n" + ", ".join(unresolved_placeholders)
    return result


if __name__ == "__main__":
    print(gemini("For all US presidencies that started after 1970, give the serving president and the start date", use_finetune=True))
    # print(replace_id_placeholders("SELECT ?president ?presidentLabel ?startDate WHERE {  ?president [wdt:position held] [wd:President of the United States] .?president [p:position held] ?positionStatement .  ?positionStatement [ps:P39] [wd:President of the United States] .  ?positionStatement [pq:start time] ?startDate .  FILTER (YEAR(?startDate) > 1970) .  SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". }}"))