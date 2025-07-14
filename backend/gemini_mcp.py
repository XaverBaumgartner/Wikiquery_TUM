from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold
from wikidata_utils import wikidata_search, query_wikidata
from gemini import gemini_model_plain, gemini_client_plain, gemini_model_pretrained, gemini_client_pretrained, replace_id_placeholders


# Defining MCP tools
wikidata_search_decl = types.FunctionDeclaration(
    name="wikidata_search",
    description="Returns the top 10 search results for entities or properties on Wikidata as json.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "search_term": types.Schema(type="STRING", description="The search term"),
            "type": types.Schema(type="STRING", enum=["item", "property"], description="Type of entity to search for (item or property)"),
        },
        required=["search_term", "type"],
    ),
)
query_wikidata_decl = types.FunctionDeclaration(
    name="query_wikidata",
    description="Run a SPARQL query against Wikidata and return the JSON result.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "query": types.Schema(type="STRING", description="The SPARQL query string"),
        },
        required=["query"],
    ),
)

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
        "You are an expert in generating SPARQL queries for Wikidata.\n\n"
        "Strictly follow this procedure:\n"
        "1. Use the 'wikidata_search' tool to look up ALL entity and property IDs you plan on using in your query.\n"
        "2. Generate a working SPARQL query that uses these IDs! Do not use natural language placeholders, as in: SELECT ?country WHERE {[wd:France] [wdt:shares border with] ?country . }, but instead use the actual Wikidata IDs, as in SELECT ?country WHERE {wd:Q142 wdt:P47 ?country . }\n"
        "3. Make sure the query results will be provided in human-readable format! For example, use: SELECT ?country ?countryLabel WHERE {wd:Q142 wdt:P47 ?country . SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". }} instead of: SELECT ?country WHERE {wd:Q142 wdt:P47 ?country . }\n"
        "4. Use the 'query_wikidata' tool to execute your query against the database.\n"
        "5. If your query does not return the expected results, revise it and test it again. Repeat this step until the query delivers the expected results.\n"
        "6. Give your final answer, consisting of:\n"
        "   - A brief explanation of your reasoning and approach.\n"
        "   - A code block that starts with ```sparql and ends with ``` containing ONLY the SPARQL query.\n"
        "   - A comment on whether these results are reasonable and realistic, including one of the results as an example.\n\n"
        "   Do not use LaTeX or any other special formatting.\n"
    ),
    tools=[types.Tool(function_declarations=[wikidata_search_decl, query_wikidata_decl])]
)


def gemini_mcp(prompt, use_finetune):
    if use_finetune:
        model = gemini_model_pretrained
        client = gemini_client_pretrained
    else:
        model = gemini_model_plain
        client = gemini_client_plain
    conversation = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

    num_queries_tested = 0  # Track if query_wikidata was called
    iterations_untested = 0
    while True:
        # Generiere Antwort
        try:
            response = client.models.generate_content(
                model=model,
                contents=conversation,
                config=config
            )
        except Exception as e:
            error_str = str(e.args[0]) if hasattr(e, "args") and e.args else str(e)
            print(e)
            if "RESOURCE_EXHAUSTED" in error_str:
                return "Ressource exhausted: Processing Query took too many tokens"
            elif "UNAVAILABLE" in error_str:
                return "Model unavailable: The model is overloaded. Please try again later."
            else:
                return f"Fehler bei der Anfrage: {e}"

        # Verification-skip Fix: Only allow final answer if query_wikidata was called at least once. Force it to reply after too many iterations.
        if (not response.function_calls) or num_queries_tested >=6:
            if num_queries_tested >= 1:
                return replace_id_placeholders(response.text) # replace_id_placeholders should be unnecassary here, but models dont ever just follow their instructions
            else:
                print("Skipping response because not tested yet.")
                conversation.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="Please test your SPARQL query using the query_wikidata tool before answering.")]
                ))
                iterations_untested += 1
                continue
        elif num_queries_tested >= 5:
            conversation.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="Time is running out! Please deliver your final result, even if it is unfinished. Make no more function calls.")],
                ))

        # Process function calls
        for call in response.function_calls:
            # Append function call to conversation
            function_call_part = types.Part.from_function_call(
                name=call.name,
                args=call.args
            )
            function_call_content = types.Content(
                role="model", parts=[function_call_part]
            )
            conversation.append(function_call_content)
            
            # Execute function call
            if call.name == "wikidata_search":
                try:
                    result = wikidata_search(**call.args)
                except Exception as e:
                    result = {"error": str(e)}
            elif call.name == "query_wikidata":
                try:
                    num_queries_tested += 1 
                    print(num_queries_tested)
                    result = query_wikidata(**call.args)
                except Exception as e:
                    result = {"error": "Query could not be rpocessed! This is often due to using the wrong format, like [wd:Johann Sebastian Bach] instead of wd:Q1339, or P47 instead of wdt:P47" + str(e)}
            else:
                return "Internal Error: Unknown MCP function call"
            
            # Append result to conversation
            function_response_part = types.Part.from_function_response(
                name=call.name,
                response=result,
            )
            function_response_content = types.Content(
                role="tool", parts=[function_response_part]
            )
            conversation.append(function_response_content)