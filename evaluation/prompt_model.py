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

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


    # cursor.execute("UPDATE queries SET result_size = -1, benchmark_size = -1, matching = -1 WHERE model = 'vertex'")


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


    # cursor.execute("DELETE FROM queries WHERE model != 'benchmark'")

    conn.commit()
    conn.close()

    promptModel()
    
    export_database()