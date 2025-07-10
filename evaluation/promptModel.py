import sys
import os
import json
import sqlite3
from tabulate import tabulate
import textwrap
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from gemini import gemini
from gemini_mcp import gemini_mcp
from server import extract_query
from wikidata_utils import query_wikidata

db_path = "evaluation/eval.db"

def initialize_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queries (
        prompt TEXT,
        model TEXT,
        query TEXT,
        result_size INTEGER,
        benchmark_size INTEGER,
        matching INTEGER,
        PRIMARY KEY (prompt, model)
    )
    """)
    conn.commit()
    conn.close()

def insert(prompt, model, query, result_size, benchmark_size, matching):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO queries (prompt, model, query, result_size, benchmark_size, matching)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (prompt, model, query, result_size, benchmark_size, matching))
    conn.commit()
    conn.close()

def export_database():
    # Database to JSON
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM queries")
    results = cursor.fetchall()
    data = [
        {
            "prompt": row[0],
            "model": row[1],
            "query": row[2],
            "result_size": row[3],
            "benchmark_size": row[4],
            "matching": row[5]
        }
        for row in results
    ]
    conn.close()
    # Export to file for redundancy
    with open("evaluation/db_export.json", "w") as f:
        json.dump(data, f, indent=4)

    # Print in table format
    def wrap_text(value, max_width=40):
        if isinstance(value, str):
            return "\n".join(textwrap.wrap(value, width=max_width))
        return value
    headers = ["prompt", "model", "query", "result_size", "benchmark_size", "matching"]
    rows = [[
            wrap_text(entry["prompt"]), 
            wrap_text(entry["model"]), 
            wrap_text(entry["query"]),
            entry["result_size"],
            entry["benchmark_size"],
            entry["matching"]
        ] for entry in data
    ]
    result = tabulate(rows, headers=headers, tablefmt="grid")
    with open("evaluation/db_export_table.txt", "w") as f:
        f.write(result)
    # print(result)

def print_query_result(data):
    headers = data['head']['vars']
    rows = []
    for binding in data['results']['bindings']:
        row = []
        for header in headers:
            value = binding.get(header, {}).get('value', 'N/A')
            row.append(value)
        rows.append(row)
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def format_query(query):
    resString = str(json.dumps(query))
    print_query_result(query_wikidata(json.loads(resString)))
    print("\n" + resString + "\n")

def promptModel():
    def benchmark_model_function(prompt):
        with open("evaluation/benchmark_queries.json", "r") as f:
            benchmark_queries = json.load(f)
        for query in benchmark_queries:
            if query["prompt"] == prompt:
                return query["query"]
        raise ValueError(f"Prompt '{prompt}' not found in benchmark queries.")
    configs = [
        {
            "model_name": "benchmark",
            "model_function": benchmark_model_function
        },
        {
            "model_name": "gemini",
            "model_function": lambda prompt: extract_query(gemini(prompt, use_finetune=False))
        },
        {
            "model_name": "gemini_mcp",
            "model_function": lambda prompt: extract_query(gemini_mcp(prompt, use_finetune=False))
        },
        {
            "model_name": "gemini_finetune",
            "model_function": lambda prompt: extract_query(gemini(prompt, use_finetune=True))
        },
        {
            "model_name": "gemini_finetune_mcp",
            "model_function": lambda prompt: extract_query(gemini_mcp(prompt, use_finetune=True))
        }
    ]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open("evaluation/benchmark_queries.json", "r") as f:
        benchmark_queries = json.load(f)

    anyfails = []

    for config in configs:
        model_name = config["model_name"]
        model_function = config["model_function"]

        for i in range(len(benchmark_queries)):
            try:
                print(f"Processing prompt {i + 1}/{len(benchmark_queries)}: ", end="")
                i = benchmark_queries[i]
                if cursor.execute("SELECT * FROM queries WHERE prompt = ? and model = ?", (i["prompt"], model_name)).fetchone():
                    print(f"{i['prompt']} already exists in the database for model {model_name}. Skipping.")
                    continue
                print(f"Generating {model_name} query for prompt: {i['prompt']}")
                query = model_function(i["prompt"])
                # print(f"Generated query: {query}")
                if query is None: raise ValueError("Query is empty")
                insert(i["prompt"], model_name, query, -1, -1, -1)
            except Exception as e:
                print(f"Error processing prompt: {i['prompt']}")
                print(e)
                anyfails.append((model_name, i["prompt"]))

    if anyfails: 
        print(f"Some prompts failed to be processed: {anyfails}")
    else:
        print("All prompts processed successfully.")


if __name__ == "__main__":
    # initialize_database()
    ########################### Covert Query Format ###########################
    #     query = """
    # SELECT DISTINCT ?presidentLabel WHERE {
    #   ?president wdt:P31 wd:Q5 .
    #   ?president p:P39 ?positionStatement .
    #   ?positionStatement ps:P39 wd:Q11696 .
    #   ?positionStatement pq:P580 ?termStart .
    #   OPTIONAL { ?positionStatement pq:P582 ?termEnd . }
    #   FILTER (
    #     ?termStart >= "1970-01-01T00:00:00Z"^^xsd:dateTime ||
    #     (
    #       ?termStart < "1970-01-01T00:00:00Z"^^xsd:dateTime &&
    #       ( !BOUND(?termEnd) || ?termEnd >= "1970-01-01T00:00:00Z"^^xsd:dateTime )
    #     )
    #   )
    #   SERVICE wikibase:label {
    #     bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en" .
    #   }
    # }
    # ORDER BY ?termStart
    #     """
    #     format_query(query)
    
    ########################### Custom Database Command ###########################
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Set result_size, benchmark_size, matching to -1 for all queries
    # cursor.execute("UPDATE queries SET result_size = -1, benchmark_size = -1, matching = -1 WHERE model = 'vertex'")

    # For all entries with model='vertex', set benchmark_size to the same value that this prompt has with model='benchmark'
    # cursor.execute("""
    # UPDATE queries
    # SET benchmark_size = (
    #     SELECT benchmark_size 
    #     FROM queries AS subquery 
    #     WHERE subquery.prompt = queries.prompt AND subquery.model = 'benchmark'
    #     LIMIT 1
    # )
    # WHERE model = 'vertex'
    # """)

    # Delete all queries that are from a different model than 'benchmark'
    # cursor.execute("DELETE FROM queries WHERE model != 'benchmark'")

    conn.commit()
    conn.close()

    ########################### Run Model ###########################
    promptModel()
    
    ########################### Print Database ###########################
    export_database()





# Hinzuzufügende Tests:
"""
SELECT ?item WHERE {
  ?item owl:nothing ?property .
}




SELECT ?country ?countryLabel ?population ?formationDate ?currency ?currencyLabel WHERE {

wd:Q183 wdt:P47 ?country .

OPTIONAL { ?country wdt:P1082 ?population . }
OPTIONAL { ?country wdt:P571 ?formationDate . }
OPTIONAL { ?country wdt:P38 ?currency . }

SERVICE wikibase:label {
bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en" .
}
}




1. Filterung nach spezifischen Eigenschaften
Prompt: "Liste alle Nobelpreisträger für Physik seit 2000."
Prompt: "Liste alle Städte mit mehr als 1 Million Einwohnern."
2. Verwendung von Zeitintervallen
Prompt: "Liste alle Filme, die zwischen 1990 und 2000 veröffentlicht wurden."
Prompt: "Liste alle Monarchen, die zwischen 1800 und 1900 regiert haben."
3. Hierarchische Beziehungen
Prompt: "Liste alle Kinder und Enkelkinder von Königin Victoria."
Prompt: "Liste alle Unterorganisationen der Vereinten Nationen."
4. Geografische Einschränkungen
Prompt: "Liste alle Länder in Afrika mit Englisch als Amtssprache."
Prompt: "Liste alle Städte in Deutschland mit einer Universität."
5. Exklusion von irrelevanten Daten
Prompt: "Liste alle Schauspieler, die in Filmen mit einem IMDb-Rating über 8.0 mitgespielt haben, aber keine Regisseure sind."
Prompt: "Liste alle Tiere, die keine Säugetiere sind."
6. Kombination von Bedingungen
Prompt: "Liste alle Wissenschaftler, die sowohl einen Nobelpreis gewonnen haben als auch eine Universität gegründet haben."
Prompt: "Liste alle Musiker, die sowohl in einer Band gespielt haben als auch Soloalben veröffentlicht haben."
7. Sortierung und Aggregation
Prompt: "Liste die 10 größten Städte der Welt nach Einwohnerzahl."
Prompt: "Liste die häufigsten Berufe von US-Präsidenten vor ihrer Amtszeit."
8. Erkennung von Mehrdeutigkeiten
Prompt: "Liste alle Personen mit dem Namen 'John Smith' und ihre Berufe."
Prompt: "Liste alle Orte mit dem Namen 'Springfield' und ihre Länder."
9. Verwendung von Labels in verschiedenen Sprachen
Prompt: "Liste alle Länder mit ihrem Namen auf Deutsch und Englisch."
Prompt: "Liste alle Gemälde von Leonardo da Vinci mit ihrem Titel auf Französisch."
10. Erkennung und Umgang mit fehlenden Daten
Prompt: "Liste alle Schauspieler, deren Geburtsdatum bekannt ist."
Prompt: "Liste alle Länder, deren Hauptstadt nicht angegeben ist."
11. Verwendung von externen Referenzen
Prompt: "Liste alle Bücher, die auf Wikipedia als Bestseller gelistet sind."
Prompt: "Liste alle Filme, die auf IMDb eine Bewertung über 9.0 haben."
12. Verknüpfung von Daten aus verschiedenen Domänen
Prompt: "Liste alle Musiker, die in Filmen mitgespielt haben."
Prompt: "Liste alle Wissenschaftler, die in der Politik tätig waren."
"""