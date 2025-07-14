import sqlite3
import scipy.stats as stats
import sys
import os
import json
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from wikidata_utils import query_wikidata
from prompt_model import print_query_result, insert, export_database

db_path = "evaluation/eval.db"


def grade_benchmark():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for entry in cursor.execute("SELECT * FROM queries WHERE model == 'benchmark' and (result_size == -1 or benchmark_size == -1 or matching == -1)").fetchall():
        query_result = query_wikidata(entry[2])
        result_size = len(query_result["results"]["bindings"])
        cursor.execute("""
            INSERT OR REPLACE INTO queries (prompt, model, query, result_size, benchmark_size, matching)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (entry[0], entry[1], entry[2], result_size, result_size, result_size))
        conn.commit()
    conn.close()


def grade_all_ungraded():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    database = cursor.execute("SELECT * FROM queries WHERE result_size = -1 or benchmark_size = -1 or matching = -1").fetchall()
    # database = cursor.execute("SELECT * FROM queries WHERE model = 'gemini_reprompt'").fetchall()
    # for i in database: print(i[1], "\t", i[0], "\n") 
    # input("Press Enter to continue...")
    for entry in database:
        prompt = entry[0]
        model = entry[1]
        query = entry[2]
        benchmark = cursor.execute("SELECT * FROM queries WHERE prompt = ? AND model = 'benchmark'", (prompt,)).fetchone()
        if not benchmark:
            print(f"No benchmark found for prompt: {prompt}")
            exit(1)
        
        InvalidQuery = False
        try:
            result_dataset = query_wikidata(query)
        except Exception as e:
            InvalidQuery = e
            result_dataset = {
                "head": {"vars": []},
                "results": {"bindings": []}
            }
        benchmark_dataset = query_wikidata(benchmark[2])

        os.system('clear')
        print("Result Query:")
        print(query)
        print("Result Dataset:")
        if InvalidQuery is not False:
            print(f"Error querying Wikidata: {InvalidQuery}\n Query might be invalid or malformed.")
        else:
            print_query_result(result_dataset)
        print("\n\n")
        print("Benchmark Query:")
        print(benchmark[2])
        print("Benchmark Dataset:")
        print_query_result(benchmark_dataset)
        print(f"Prompt: {prompt}\nModel: {model}")

        result_size = len(result_dataset["results"]["bindings"])
        benchmark_size = len(benchmark_dataset["results"]["bindings"])
        print(f"Result Size: {result_size}, Benchmark Size: {benchmark_size}")

        i = 0
        print("Result Columns")
        if InvalidQuery is not False:
            print("\tNo result columns due to invalid query.")
        for var in result_dataset["head"]["vars"]:
            i += 1
            print(f"\t{i} {var}")
        i = 0
        print("Benchmark Columns:")
        for var in benchmark_dataset["head"]["vars"]:
            i += 1
            print(f"\t{i} {var}")
        
        comparing_columns = {}
        for i in range(len(benchmark_dataset["head"]["vars"])):
            comparing_columns[i] = int(input(f"Comparing benchmark column {i+1} to result column: ")) -1
        # print(f"Comparing Columns: {comparing_columns}")


        result_bindings_dict = {
            tuple(i.get(result_dataset["head"]["vars"][comparing_columns[column]], {}).get("value") for column in comparing_columns if comparing_columns[column] != -1)
            for i in result_dataset["results"]["bindings"]
        }
        # print(result_bindings_dict)
        matches = 0
        for j in benchmark_dataset["results"]["bindings"]:
            benchmark_values = tuple(
                j.get(benchmark_dataset["head"]["vars"][column], {}).get("value") for column in comparing_columns if comparing_columns[column] != -1
            )
            if benchmark_values in result_bindings_dict:
                matches += 1
            else:
                print(f"No match for: {j}")

                
        print(f"Total Matches: {matches}")
        matching = int(input("Enter matching value: ")) if input("Save to database? (Enter to continue, q to enter own value, Ctrl+C to exit)") == "q" else matches

        insert(prompt, model, query, result_size, benchmark_size, matching)

def calc_scores():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    models = cursor.execute("SELECT DISTINCT model FROM queries").fetchall()
    for model in models:
        model = model[0]
        results = cursor.execute("SELECT * FROM queries WHERE model = ?", (model,)).fetchall()

        # F1 macro
        precision_sum = 0
        recall_sum = 0
        f1_sum = 0

        # F1 micro
        total_true_positives = 0
        total_false_positives = 0
        total_false_negatives = 0

        # Average index
        jaccard_index_sum = 0

        count = 0
        for entry in results:
            if entry[3] <= -1 or entry[4] <= -1 or entry[5] <= -1 or entry[5] > entry[4]:
                print(f"Skipping entry {entry} for model {model} due to invalid grading.")
                continue

            count += 1

            # F1 macro
            precision = entry[5] / entry[3] if entry[3] > 0 else 0
            recall = entry[5] / entry[4] if entry[4] > 0 else 0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            precision_sum += precision
            recall_sum += recall
            f1_sum += f1

            # F1 micro, Global jaccard
            total_true_positives += entry[5]
            total_false_positives += entry[3] - entry[5]
            total_false_negatives += entry[4] - entry[5]

            # Average Jaccard index
            jaccard_index_sum += entry[5] / (entry[3] + entry[4] - entry[5]) if (entry[3] + entry[4] - entry[5]) > 0 else 0


        # Global Jaccard index
        global_jaccard_index = total_true_positives / (total_true_positives + total_false_positives + total_false_negatives) if (total_true_positives + total_false_positives + total_false_negatives) > 0 else 0

        # Average Jaccard index
        avg_jaccard_index = jaccard_index_sum / count if count > 0 else 0

        # F1 macro score
        avg_precision = precision_sum / count if count > 0 else 0
        avg_recall = recall_sum / count if count > 0 else 0
        avg_f1 = f1_sum / count if count > 0 else 0

        # F1 micro score
        micro_precision = total_true_positives / (total_true_positives + total_false_positives) if (total_true_positives + total_false_positives) > 0 else 0
        micro_recall = total_true_positives / (total_true_positives + total_false_negatives) if (total_true_positives + total_false_negatives) > 0 else 0
        micro_f1 = (2 * micro_precision * micro_recall) / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0

        print(f"{model}: {count} entries, average Precision: {avg_precision:.4f}, average Recall: {avg_recall:.4f}, \n\tF1 macro: {avg_f1:.4f}, F1 micro: {micro_f1:.4f}, \n\tGlobal Jaccard Index: {global_jaccard_index:.4f}, Average Jaccard Index: {avg_jaccard_index:.4f}")


def export_query_jaccard():
    result = []
    for i in range(1, 6):
        conn = sqlite3.connect(f"evaluation/eval {i}.db")
        cursor = conn.cursor()
        query_result = cursor.execute("SELECT * FROM queries WHERE model != 'benchmark'").fetchall()
        # The ONLY results with NO matches are EMPTY results!!! See results = [{"model": i[1], "prompt": i[0], "any_results": 1 if i[3] else 0, "any_matching": 1 if i[5] else 0} for i in results] then loop for any_results != any_matching
        for r in query_result: 
            result.append({"iteration": i, "model": r[1], "prompt": r[0], "jaccard_index": r[5] / (r[3] + r[4] - r[5])}) 
    json.dump(result, open("evaluation/query_jaccard.json", "w"), indent=4)

def benchmark_numbers():
    benchmark_data = json.load(open("evaluation/benchmark_queries.json"))
    prompts_with_index = {entry['prompt']: idx + 1 for idx, entry in enumerate(benchmark_data)}
    print(prompts_with_index)



def calc_statistical_significance():
    model_metrics = {}
    for iteration in range(1, 6):
        conn = sqlite3.connect(f"evaluation/eval {iteration}.db")
        cursor = conn.cursor()
        models = cursor.execute("SELECT DISTINCT model FROM queries").fetchall()
        models = [m for m in models if m[0] != 'benchmark']
        for model in models:
            model = model[0]
            results = cursor.execute("SELECT * FROM queries WHERE model = ?", (model,)).fetchall()

            if model not in model_metrics:
                model_metrics[model] = {"precision": [], "recall": [], "f1_macro": [], "f1_micro": [], "global_jaccard_index": [], "average_jaccard_index": []}

            precision_sum = 0
            recall_sum = 0
            f1_sum = 0

            total_true_positives = 0
            total_false_positives = 0
            total_false_negatives = 0

            jaccard_index_sum = 0

            count = 0
            for entry in results:
                if entry[3] <= -1 or entry[4] <= -1 or entry[5] <= -1 or entry[5] > entry[4]:
                    print(f"Skipping entry {entry} for model {model} due to invalid grading.")
                    continue

                # F1 macro
                precision = entry[5] / entry[3] if entry[3] > 0 else 0
                recall = entry[5] / entry[4] if entry[4] > 0 else 0
                f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

                precision_sum += precision
                recall_sum += recall
                f1_sum += f1
                count += 1

                # F1 micro
                total_true_positives += entry[5]
                total_false_positives += entry[3] - entry[5]
                total_false_negatives += entry[4] - entry[5]

                # Jaccard index
                jaccard_index_sum += entry[5] / (entry[3] + entry[4] - entry[5]) if (entry[3] + entry[4] - entry[5]) > 0 else 0

            # Calculate metrics
            global_jaccard_index = total_true_positives / (total_true_positives + total_false_positives + total_false_negatives) if (total_true_positives + total_false_positives + total_false_negatives) > 0 else 0
            avg_jaccard_index = jaccard_index_sum / count if count > 0 else 0
            avg_precision = precision_sum / count if count > 0 else 0
            avg_recall = recall_sum / count if count > 0 else 0
            avg_f1 = f1_sum / count if count > 0 else 0
            micro_precision = total_true_positives / (total_true_positives + total_false_positives) if (total_true_positives + total_false_positives) > 0 else 0
            micro_recall = total_true_positives / (total_true_positives + total_false_negatives) if (total_true_positives + total_false_negatives) > 0 else 0
            micro_f1 = (2 * micro_precision * micro_recall) / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0

            model_metrics[model]["precision"].append(avg_precision)
            model_metrics[model]["recall"].append(avg_recall)
            model_metrics[model]["f1_macro"].append(avg_f1)
            model_metrics[model]["f1_micro"].append(micro_f1)
            model_metrics[model]["global_jaccard_index"].append(global_jaccard_index)
            model_metrics[model]["average_jaccard_index"].append(avg_jaccard_index)

        conn.close()
    print(model_metrics)

    significant_models = {metric: [] for metric in ["precision", "recall", "f1_macro", "f1_micro", "global_jaccard_index", "average_jaccard_index"]}
    models = list(model_metrics.keys())
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            model1 = models[i]
            model2 = models[j]
            for metric in significant_models.keys():
                stat, p_value = stats.ttest_ind(model_metrics[model1][metric], model_metrics[model2][metric], equal_var=False)
                if p_value < 0.05:  # significance level: 0.05
                    better_model = model1 if stat > 0 else model2
                    significant_models[metric].append((better_model, model1, model2, p_value))

    for metric, results in significant_models.items():
        print(f"\nStatistically significant results for {metric}:")
        for better_model, model1, model2, p_value in results:
            print(f"{better_model} is significantly better than {model1 if better_model == model2 else model2} (p-value: {p_value:.4f})")
    

def get_invalid_count():
    erroneous_queries = []
    models = ['gemini_finetune', 'gemini_finetune_mcp']
    for model in models:
        total_invalid = 0
        for iteration in range(1, 6):
            conn = sqlite3.connect(f"evaluation/eval {iteration}.db")
            cursor = conn.cursor()
            results = cursor.execute("SELECT * FROM queries WHERE model = ?", (model,)).fetchall()
            results = [i for i in results if i[3] == 0]
            for r in results:
                retry = True
                while retry:
                    try:
                        query_wikidata(r[2])
                        retry = False
                    except Exception as e:
                        if "429 Client Error: Too many requests" in str(e):
                            print("Too many requests. Retrying in 1 second...")
                            time.sleep(1)
                        else:
                            total_invalid += 1
                            print(f"Invalid query for model {model} with prompt {r[0]} in iteration {iteration}:\n\t{r[2]}\n\tError: {e}")
                            erroneous_queries.append({
                                "iteration": iteration,
                                "model": model,
                                "prompt": r[0],
                                "query": r[2],
                                "error": str(e)
                            })
                            retry = False
    print(erroneous_queries)

def stat_analysis_excluding_errors():
    # Result from get_invalid_count()
    erroneous_queries = [{'iteration': 1, 'model': 'gemini_finetune', 'prompt': 'list the countries where the Summer Olympics were held between 2008 and 2022, along with the year', 'query': "\nSELECT ?country ?countryLabel ?year WHERE {\n  ?event wdt:P31 wd:Q159821 .\n  ?event wdt:P17 ?country .\n  ?event wdt:P585 ?time .\n  FILTER(YEAR(?time) >= 2008 && YEAR(?time) <= 2022) .\n  BIND(YEAR(?time) AS ?year) .\n  SERVICE wikibase:label {\n    ?country rdfs:label ?countryLabel .\n    FILTER(lang(?countryLabel) = 'en')\n  }\n}\nORDER BY ?year\n", 'error': '500 Server Error: Internal Server Error for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fcountry+%3FcountryLabel+%3Fyear+WHERE+%7B%0A++%3Fevent+wdt%3AP31+wd%3AQ159821+.%0A++%3Fevent+wdt%3AP17+%3Fcountry+.%0A++%3Fevent+wdt%3AP585+%3Ftime+.%0A++FILTER%28YEAR%28%3Ftime%29+%3E%3D+2008+%26%26+YEAR%28%3Ftime%29+%3C%3D+2022%29+.%0A++BIND%28YEAR%28%3Ftime%29+AS+%3Fyear%29+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++%3Fcountry+rdfs%3Alabel+%3FcountryLabel+.%0A++++FILTER%28lang%28%3FcountryLabel%29+%3D+%27en%27%29%0A++%7D%0A%7D%0AORDER+BY+%3Fyear%0A'}, {'iteration': 1, 'model': 'gemini_finetune', 'prompt': 'list the countries where the Winter Olympics were held between 2008 and 2022, along with the year', 'query': '\nSELECT ?eventLabel ?countryLabel ?year WHERE {\n  ?event wdt:P31 wd:Q108057428 .\n  ?event wdt:P17 ?country .\n  ?event wdt:P585 ?year .\n  FILTER(YEAR(?year) >= 2008 && YEAR(?year) <= 2022) .\n  SERVICE wikibase:label { bd:serviceParam [wikibase:language "en"] . ?event [rdfs:label] ?eventLabel . ?country [rdfs:label] ?countryLabel . }\n}\nORDER BY ASC(?year)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3FeventLabel+%3FcountryLabel+%3Fyear+WHERE+%7B%0A++%3Fevent+wdt%3AP31+wd%3AQ108057428+.%0A++%3Fevent+wdt%3AP17+%3Fcountry+.%0A++%3Fevent+wdt%3AP585+%3Fyear+.%0A++FILTER%28YEAR%28%3Fyear%29+%3E%3D+2008+%26%26+YEAR%28%3Fyear%29+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+%5Bwikibase%3Alanguage+%22en%22%5D+.+%3Fevent+%5Brdfs%3Alabel%5D+%3FeventLabel+.+%3Fcountry+%5Brdfs%3Alabel%5D+%3FcountryLabel+.+%7D%0A%7D%0AORDER+BY+ASC%28%3Fyear%29%0A'}, {'iteration': 1, 'model': 'gemini_finetune', 'prompt': 'list the countries where the Olympics were held between 2008 and 2022, along with the year', 'query': '\nSELECT ?countryLabel ?year WHERE {\n  ?olympics wdt:P31 wd:Q5389 .\n  ?olympics wdt:P625 ?country .\n  ?olympics wdt:P580 ?time .\n  BIND(YEAR(?time) AS ?year) .\n  FILTER(?year >= 2008 && ?year <= 2022) .\n  SERVICE wikibase:label {\n    ?country rdfs:label ?countryLabel .\n    FILTER(lang(?countryLabel) = "en")\n  }\n}\nORDER BY ASC(?year)\n', 'error': '500 Server Error: Internal Server Error for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3FcountryLabel+%3Fyear+WHERE+%7B%0A++%3Folympics+wdt%3AP31+wd%3AQ5389+.%0A++%3Folympics+wdt%3AP625+%3Fcountry+.%0A++%3Folympics+wdt%3AP580+%3Ftime+.%0A++BIND%28YEAR%28%3Ftime%29+AS+%3Fyear%29+.%0A++FILTER%28%3Fyear+%3E%3D+2008+%26%26+%3Fyear+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++%3Fcountry+rdfs%3Alabel+%3FcountryLabel+.%0A++++FILTER%28lang%28%3FcountryLabel%29+%3D+%22en%22%29%0A++%7D%0A%7D%0AORDER+BY+ASC%28%3Fyear%29%0A'}, {'iteration': 2, 'model': 'gemini_finetune', 'prompt': 'List of US presidents since 1970', 'query': "\nSELECT DISTINCT ?person ?personLabel WHERE {\n  ?person wdt:P39 wd:Q11696 .\n  ?person wdt:P39 ?s .\n  ?s pq:P580 ?start_time .\n  FILTER(YEAR(?start_time) >= 1970) .\n  SERVICE wikibase:label { ?person rdfs:label ?personLabel . FILTER(lang(?personLabel) = 'en') }\n}\nORDER BY ASC(?start_time)\n", 'error': '500 Server Error: Internal Server Error for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Fperson+%3FpersonLabel+WHERE+%7B%0A++%3Fperson+wdt%3AP39+wd%3AQ11696+.%0A++%3Fperson+wdt%3AP39+%3Fs+.%0A++%3Fs+pq%3AP580+%3Fstart_time+.%0A++FILTER%28YEAR%28%3Fstart_time%29+%3E%3D+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B+%3Fperson+rdfs%3Alabel+%3FpersonLabel+.+FILTER%28lang%28%3FpersonLabel%29+%3D+%27en%27%29+%7D%0A%7D%0AORDER+BY+ASC%28%3Fstart_time%29%0A'}, {'iteration': 2, 'model': 'gemini_finetune', 'prompt': 'List of non-fictional US presidents since 1970', 'query': '\nSELECT ?president ?presidentLabel ?termStartDate WHERE {\n  ?president wdt:P39 wd:Q11696 .\n  ?president [wdt:term start] ?termStartDate .\n  FILTER(YEAR(?termStartDate) >= 1970) .\n  SERVICE wikibase:label {\n    bd:serviceParam wikibase:language "en" .\n    ?president [rdfs:label] ?presidentLabel\n  }\n} ORDER BY ASC(?termStartDate)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+%3FtermStartDate+WHERE+%7B%0A++%3Fpresident+wdt%3AP39+wd%3AQ11696+.%0A++%3Fpresident+%5Bwdt%3Aterm+start%5D+%3FtermStartDate+.%0A++FILTER%28YEAR%28%3FtermStartDate%29+%3E%3D+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.%0A++++%3Fpresident+%5Brdfs%3Alabel%5D+%3FpresidentLabel%0A++%7D%0A%7D+ORDER+BY+ASC%28%3FtermStartDate%29%0A'}, {'iteration': 2, 'model': 'gemini_finetune', 'prompt': 'For all US presidencies that started after 1970, give the serving president and the start date', 'query': "\nSELECT ?president ?presidentLabel ?startDate WHERE {\n  ?s wdt:P39 wd:Q11696 .\n  ?s wdt:P1308 ?president .\n  ?s wdt:P580 ?startDate .\n  FILTER(YEAR(?startDate) > 1970) .\n  SERVICE wikibase:label {\n    ?president rdfs:label ?presidentLabel .\n    FILTER (lang(?presidentLabel) = 'en')\n  }\n}\n", 'error': '500 Server Error: Internal Server Error for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+%3FstartDate+WHERE+%7B%0A++%3Fs+wdt%3AP39+wd%3AQ11696+.%0A++%3Fs+wdt%3AP1308+%3Fpresident+.%0A++%3Fs+wdt%3AP580+%3FstartDate+.%0A++FILTER%28YEAR%28%3FstartDate%29+%3E+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++%3Fpresident+rdfs%3Alabel+%3FpresidentLabel+.%0A++++FILTER+%28lang%28%3FpresidentLabel%29+%3D+%27en%27%29%0A++%7D%0A%7D%0A'}, {'iteration': 2, 'model': 'gemini_finetune', 'prompt': 'list all physics nobel laureates from 2000 to 2010', 'query': '\nSELECT DISTINCT ?laureate ?laureateLabel WHERE {\n  ?award wdt:P31 wd:Q38104 .\n  ?award wdt:P585 ?time .\n  FILTER(YEAR(?time) >= 2000 && YEAR(?time) <= 2010) .\n  ?award [wdt:laureate] ?laureate .\n  SERVICE wikibase:label {\n    bd:serviceParam wikibase:language "en" .\n    ?laureate rdfs:label ?laureateLabel .\n  }\n}\nORDER BY ASC(?laureateLabel)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Flaureate+%3FlaureateLabel+WHERE+%7B%0A++%3Faward+wdt%3AP31+wd%3AQ38104+.%0A++%3Faward+wdt%3AP585+%3Ftime+.%0A++FILTER%28YEAR%28%3Ftime%29+%3E%3D+2000+%26%26+YEAR%28%3Ftime%29+%3C%3D+2010%29+.%0A++%3Faward+%5Bwdt%3Alaureate%5D+%3Flaureate+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.%0A++++%3Flaureate+rdfs%3Alabel+%3FlaureateLabel+.%0A++%7D%0A%7D%0AORDER+BY+ASC%28%3FlaureateLabel%29%0A'}, {'iteration': 2, 'model': 'gemini_finetune', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman! This query gives Niels Bohrs date: \nSELECT ?date\nWHERE {\nwd:Q7085 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, this query gives Richard Feynmans date: \nSELECT ?date\nWHERE {\nwd:Q39246 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, and this query gives all physics nobel laureates from 2000 to 2010: \nSELECT DISTINCT ?laureateLabel\nWHERE {\n?laureate wdt:P31 wd:Q5 ;\np:P166 ?awardStatement . \n?awardStatement ps:P166 wd:Q38104 ;\npq:P585 ?awardDate .\nFILTER (YEAR(?awardDate) >= 2000 && YEAR(?awardDate) <= 2010)\nSERVICE wikibase:label {\nbd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".\n}\n}\nORDER BY ?awardDate ?laureateLabel\n', 'query': '\nSELECT DISTINCT ?laureate ?laureateLabel WHERE {\n  # Get Niels Bohr\'s Nobel Prize in Physics award date\n  {\n    wd:Q7085 p:P166 ?s1 .\n    ?s1 ps:P166 wd:Q38104 .\n    ?s1 pq:P585 ?bohrDate .\n  }\n  # Get Richard Feynman\'s Nobel Prize in Physics award date\n  {\n    wd:Q39246 p:P166 ?s2 .\n    ?s2 ps:P166 wd:Q38104 .\n    ?s2 pq:P585 ?feynmanDate .\n  }\n\n  # Find all individuals who received the Nobel Prize in Physics\n  ?laureate p:P166 ?s3 .\n  ?s3 ps:P166 wd:Q38104 .\n  ?s3 pq:P585 ?awardDate .\n\n  # Filter laureates whose award date is after Bohr\'s and before Feynman\'s\n  FILTER(?awardDate > ?bohrDate && ?awardDate < ?feynmanDate)\n\n  SERVICE wikibase:label {\n    bd:serviceParam wikibase:language "en".\n    ?laureate [rdfs:label] ?laureateLabel .\n  }\n}\nORDER BY ?awardDate ?laureateLabel\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Flaureate+%3FlaureateLabel+WHERE+%7B%0A++%23+Get+Niels+Bohr%27s+Nobel+Prize+in+Physics+award+date%0A++%7B%0A++++wd%3AQ7085+p%3AP166+%3Fs1+.%0A++++%3Fs1+ps%3AP166+wd%3AQ38104+.%0A++++%3Fs1+pq%3AP585+%3FbohrDate+.%0A++%7D%0A++%23+Get+Richard+Feynman%27s+Nobel+Prize+in+Physics+award+date%0A++%7B%0A++++wd%3AQ39246+p%3AP166+%3Fs2+.%0A++++%3Fs2+ps%3AP166+wd%3AQ38104+.%0A++++%3Fs2+pq%3AP585+%3FfeynmanDate+.%0A++%7D%0A%0A++%23+Find+all+individuals+who+received+the+Nobel+Prize+in+Physics%0A++%3Flaureate+p%3AP166+%3Fs3+.%0A++%3Fs3+ps%3AP166+wd%3AQ38104+.%0A++%3Fs3+pq%3AP585+%3FawardDate+.%0A%0A++%23+Filter+laureates+whose+award+date+is+after+Bohr%27s+and+before+Feynman%27s%0A++FILTER%28%3FawardDate+%3E+%3FbohrDate+%26%26+%3FawardDate+%3C+%3FfeynmanDate%29%0A%0A++SERVICE+wikibase%3Alabel+%7B%0A++++bd%3AserviceParam+wikibase%3Alanguage+%22en%22.%0A++++%3Flaureate+%5Brdfs%3Alabel%5D+%3FlaureateLabel+.%0A++%7D%0A%7D%0AORDER+BY+%3FawardDate+%3FlaureateLabel%0A'}, {'iteration': 3, 'model': 'gemini_finetune', 'prompt': 'List of non-fictional US presidents since 1970', 'query': '\nSELECT DISTINCT ?president ?presidentLabel WHERE {\n  wd:Q11696 wdt:P1308 ?president .\n  ?president [wdt:term start] ?term_start_date .\n  ?president wdt:P31 wd:Q5 .\n  FILTER(YEAR(?term_start_date) >= 1970) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . ?president rdfs:label ?presidentLabel }\n}\nORDER BY ?term_start_date\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Fpresident+%3FpresidentLabel+WHERE+%7B%0A++wd%3AQ11696+wdt%3AP1308+%3Fpresident+.%0A++%3Fpresident+%5Bwdt%3Aterm+start%5D+%3Fterm_start_date+.%0A++%3Fpresident+wdt%3AP31+wd%3AQ5+.%0A++FILTER%28YEAR%28%3Fterm_start_date%29+%3E%3D+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.+%3Fpresident+rdfs%3Alabel+%3FpresidentLabel+%7D%0A%7D%0AORDER+BY+%3Fterm_start_date%0A'}, {'iteration': 3, 'model': 'gemini_finetune', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman! This query gives Niels Bohrs date: \nSELECT ?date\nWHERE {\nwd:Q7085 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, this query gives Richard Feynmans date: \nSELECT ?date\nWHERE {\nwd:Q39246 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, and this query gives all physics nobel laureates from 2000 to 2010: \nSELECT DISTINCT ?laureateLabel\nWHERE {\n?laureate wdt:P31 wd:Q5 ;\np:P166 ?awardStatement . \n?awardStatement ps:P166 wd:Q38104 ;\npq:P585 ?awardDate .\nFILTER (YEAR(?awardDate) >= 2000 && YEAR(?awardDate) <= 2010)\nSERVICE wikibase:label {\nbd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".\n}\n}\nORDER BY ?awardDate ?laureateLabel\n', 'query': '\nSELECT DISTINCT ?laureate ?laureateLabel ?awardDate\nWHERE {\n  # Get Niels Bohr\'s Nobel Prize in Physics award date\n  BIND((SELECT ?date WHERE { wd:Q7085 p:P166 ?s . ?s ps:P166 wd:Q38104 . ?s pq:P585 ?date }) AS ?bohrDate)\n\n  # Get Richard Feynman\'s Nobel Prize in Physics award date\n  BIND((SELECT ?date WHERE { wd:Q39246 p:P166 ?s . ?s ps:P166 wd:Q38104 . ?s pq:P585 ?date }) AS ?feynmanDate)\n\n  # Find all Nobel Prize in Physics laureates and their award dates\n  ?laureate p:P166 ?s2 .\n  ?s2 ps:P166 wd:Q38104 ;\n      pq:P585 ?awardDate .\n\n  # Filter based on dates: after Bohr\'s date and before Feynman\'s date\n  FILTER(?awardDate > ?bohrDate && ?awardDate < ?feynmanDate)\n\n  # Get the human-readable label for the laureate\n  SERVICE wikibase:label {\n    bd:serviceParam wikibase:language "en".\n    ?laureate rdfs:label ?laureateLabel .\n  }\n}\nORDER BY ?awardDate ?laureateLabel\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Flaureate+%3FlaureateLabel+%3FawardDate%0AWHERE+%7B%0A++%23+Get+Niels+Bohr%27s+Nobel+Prize+in+Physics+award+date%0A++BIND%28%28SELECT+%3Fdate+WHERE+%7B+wd%3AQ7085+p%3AP166+%3Fs+.+%3Fs+ps%3AP166+wd%3AQ38104+.+%3Fs+pq%3AP585+%3Fdate+%7D%29+AS+%3FbohrDate%29%0A%0A++%23+Get+Richard+Feynman%27s+Nobel+Prize+in+Physics+award+date%0A++BIND%28%28SELECT+%3Fdate+WHERE+%7B+wd%3AQ39246+p%3AP166+%3Fs+.+%3Fs+ps%3AP166+wd%3AQ38104+.+%3Fs+pq%3AP585+%3Fdate+%7D%29+AS+%3FfeynmanDate%29%0A%0A++%23+Find+all+Nobel+Prize+in+Physics+laureates+and+their+award+dates%0A++%3Flaureate+p%3AP166+%3Fs2+.%0A++%3Fs2+ps%3AP166+wd%3AQ38104+%3B%0A++++++pq%3AP585+%3FawardDate+.%0A%0A++%23+Filter+based+on+dates%3A+after+Bohr%27s+date+and+before+Feynman%27s+date%0A++FILTER%28%3FawardDate+%3E+%3FbohrDate+%26%26+%3FawardDate+%3C+%3FfeynmanDate%29%0A%0A++%23+Get+the+human-readable+label+for+the+laureate%0A++SERVICE+wikibase%3Alabel+%7B%0A++++bd%3AserviceParam+wikibase%3Alanguage+%22en%22.%0A++++%3Flaureate+rdfs%3Alabel+%3FlaureateLabel+.%0A++%7D%0A%7D%0AORDER+BY+%3FawardDate+%3FlaureateLabel%0A'}, {'iteration': 4, 'model': 'gemini_finetune', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman', 'query': '\nSELECT DISTINCT ?laureate ?laureateLabel WHERE {\n  ?laureate wdt:P166 ?statement .\n  ?statement wdt:P166 wd:Q38104 .\n  ?statement wdt:P585 ?awardDate .\n\n  wd:Q7085 wdt:P166 ?bohrStatement .\n  ?bohrStatement wdt:P166 wd:Q38104 .\n  ?bohrStatement wdt:P585 ?bohrAwardDate .\n\n  wd:Q39246 wdt:P166 ?feynmanStatement .\n  ?feynmanStatement wdt:P166 wd:Q38104 .\n  ?feynmanStatement wdt:P585 ?feynmanAwardDate .\n\n  FILTER(?awardDate > ?bohrAwardDate)\n  FILTER(?awardDate < ?feynmanAwardDate)\n\n  SERVICE wikibase:label {\n    bd:serviceParam [wikibase:language] "en" .\n    ?laureate [rdfs:label] ?laureateLabel .\n  }\n}\nORDER BY ASC(?awardDate)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Flaureate+%3FlaureateLabel+WHERE+%7B%0A++%3Flaureate+wdt%3AP166+%3Fstatement+.%0A++%3Fstatement+wdt%3AP166+wd%3AQ38104+.%0A++%3Fstatement+wdt%3AP585+%3FawardDate+.%0A%0A++wd%3AQ7085+wdt%3AP166+%3FbohrStatement+.%0A++%3FbohrStatement+wdt%3AP166+wd%3AQ38104+.%0A++%3FbohrStatement+wdt%3AP585+%3FbohrAwardDate+.%0A%0A++wd%3AQ39246+wdt%3AP166+%3FfeynmanStatement+.%0A++%3FfeynmanStatement+wdt%3AP166+wd%3AQ38104+.%0A++%3FfeynmanStatement+wdt%3AP585+%3FfeynmanAwardDate+.%0A%0A++FILTER%28%3FawardDate+%3E+%3FbohrAwardDate%29%0A++FILTER%28%3FawardDate+%3C+%3FfeynmanAwardDate%29%0A%0A++SERVICE+wikibase%3Alabel+%7B%0A++++bd%3AserviceParam+%5Bwikibase%3Alanguage%5D+%22en%22+.%0A++++%3Flaureate+%5Brdfs%3Alabel%5D+%3FlaureateLabel+.%0A++%7D%0A%7D%0AORDER+BY+ASC%28%3FawardDate%29%0A'}, {'iteration': 4, 'model': 'gemini_finetune', 'prompt': 'list the countries where the Olympics were held between 2008 and 2022, along with the year', 'query': "\nSELECT ?country ?countryLabel ?year WHERE {\n  ?event wdt:P31 wd:Q5389 .\n  ?event wdt:P625 ?country .\n  ?event wdt:P585 ?year .\n  FILTER(YEAR(?year) >= 2008 && YEAR(?year) <= 2022) .\n  SERVICE wikibase:label {\n    ?country rdfs:label ?countryLabel .\n    FILTER(lang(?countryLabel) = 'en')\n  }\n}\nORDER BY ASC(?year)\n", 'error': '500 Server Error: Internal Server Error for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fcountry+%3FcountryLabel+%3Fyear+WHERE+%7B%0A++%3Fevent+wdt%3AP31+wd%3AQ5389+.%0A++%3Fevent+wdt%3AP625+%3Fcountry+.%0A++%3Fevent+wdt%3AP585+%3Fyear+.%0A++FILTER%28YEAR%28%3Fyear%29+%3E%3D+2008+%26%26+YEAR%28%3Fyear%29+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++%3Fcountry+rdfs%3Alabel+%3FcountryLabel+.%0A++++FILTER%28lang%28%3FcountryLabel%29+%3D+%27en%27%29%0A++%7D%0A%7D%0AORDER+BY+ASC%28%3Fyear%29%0A'}, {'iteration': 5, 'model': 'gemini_finetune', 'prompt': 'List of non-fictional US presidents since 1970', 'query': '\nSELECT ?president ?presidentLabel WHERE {\n  ?president wdt:P39 wd:Q11696 .\n  ?president wdt:P31 wd:Q5 .\n  ?president [wdt:term start] ?termStart .\n  FILTER(YEAR(?termStart) >= 1970) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". ?president rdfs:label ?presidentLabel }\n}\nORDER BY ASC(?termStart)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+WHERE+%7B%0A++%3Fpresident+wdt%3AP39+wd%3AQ11696+.%0A++%3Fpresident+wdt%3AP31+wd%3AQ5+.%0A++%3Fpresident+%5Bwdt%3Aterm+start%5D+%3FtermStart+.%0A++FILTER%28YEAR%28%3FtermStart%29+%3E%3D+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%3Fpresident+rdfs%3Alabel+%3FpresidentLabel+%7D%0A%7D%0AORDER+BY+ASC%28%3FtermStart%29%0A'}, {'iteration': 5, 'model': 'gemini_finetune', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman', 'query': '\nSELECT DISTINCT ?laureate ?laureateLabel WHERE {\n  # Get the date of Niels Bohr\'s Nobel Prize in Physics\n  [wd:Nobel Prize in Physics 1922] wdt:P585 ?bohr_date .\n\n  # Get the date of Richard Feynman\'s Nobel Prize in Physics\n  [wd:Nobel Prize in Physics 1965] wdt:P585 ?feynman_date .\n\n  # Find all people who received a Nobel Prize in Physics\n  ?laureate wdt:P166 ?award_item .\n  ?award_item wdt:P31 wd:Q38104 .\n  ?award_item wdt:P585 ?award_date .\n\n  # Filter laureates whose award date is after Bohr\'s and before Feynman\'s\n  FILTER(?award_date > ?bohr_date) .\n  FILTER(?award_date < ?feynman_date) .\n\n  # Get the human-readable label for the laureate\n  SERVICE wikibase:label {\n    bd:serviceParam wikibase:language "en" .\n    ?laureate rdfs:label ?laureateLabel .\n  }\n}\nORDER BY ASC(?laureateLabel)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Flaureate+%3FlaureateLabel+WHERE+%7B%0A++%23+Get+the+date+of+Niels+Bohr%27s+Nobel+Prize+in+Physics%0A++%5Bwd%3ANobel+Prize+in+Physics+1922%5D+wdt%3AP585+%3Fbohr_date+.%0A%0A++%23+Get+the+date+of+Richard+Feynman%27s+Nobel+Prize+in+Physics%0A++%5Bwd%3ANobel+Prize+in+Physics+1965%5D+wdt%3AP585+%3Ffeynman_date+.%0A%0A++%23+Find+all+people+who+received+a+Nobel+Prize+in+Physics%0A++%3Flaureate+wdt%3AP166+%3Faward_item+.%0A++%3Faward_item+wdt%3AP31+wd%3AQ38104+.%0A++%3Faward_item+wdt%3AP585+%3Faward_date+.%0A%0A++%23+Filter+laureates+whose+award+date+is+after+Bohr%27s+and+before+Feynman%27s%0A++FILTER%28%3Faward_date+%3E+%3Fbohr_date%29+.%0A++FILTER%28%3Faward_date+%3C+%3Ffeynman_date%29+.%0A%0A++%23+Get+the+human-readable+label+for+the+laureate%0A++SERVICE+wikibase%3Alabel+%7B%0A++++bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.%0A++++%3Flaureate+rdfs%3Alabel+%3FlaureateLabel+.%0A++%7D%0A%7D%0AORDER+BY+ASC%28%3FlaureateLabel%29%0A'}, {'iteration': 5, 'model': 'gemini_finetune', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman! This query gives Niels Bohrs date: \nSELECT ?date\nWHERE {\nwd:Q7085 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, this query gives Richard Feynmans date: \nSELECT ?date\nWHERE {\nwd:Q39246 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, and this query gives all physics nobel laureates from 2000 to 2010: \nSELECT DISTINCT ?laureateLabel\nWHERE {\n?laureate wdt:P31 wd:Q5 ;\np:P166 ?awardStatement . \n?awardStatement ps:P166 wd:Q38104 ;\npq:P585 ?awardDate .\nFILTER (YEAR(?awardDate) >= 2000 && YEAR(?awardDate) <= 2010)\nSERVICE wikibase:label {\nbd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".\n}\n}\nORDER BY ?awardDate ?laureateLabel\n', 'query': '\nSELECT DISTINCT ?laureate ?laureateLabel WHERE {\n  # Get Niels Bohr\'s Nobel Prize in Physics award date\n  BIND((SELECT ?date WHERE { wd:Q7085 p:P166 ?s . ?s ps:P166 wd:Q38104 . ?s pq:P585 ?date }) AS ?bohrDate)\n\n  # Get Richard Feynman\'s Nobel Prize in Physics award date\n  BIND((SELECT ?date WHERE { wd:Q39246 p:P166 ?s . ?s ps:P166 wd:Q38104 . ?s pq:P585 ?date }) AS ?feynmanDate)\n\n  # Find all humans who received the Nobel Prize in Physics\n  ?laureate wdt:P31 wd:Q5 ;\n            p:P166 ?s .\n  ?s ps:P166 wd:Q38104 ;\n     pq:P585 ?awardDate .\n\n  # Filter by date range: after Bohr and before Feynman\n  FILTER(?awardDate > ?bohrDate && ?awardDate < ?feynmanDate)\n\n  # Get laureate label in English\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". ?laureate rdfs:label ?laureateLabel }\n}\nORDER BY ?awardDate ?laureateLabel\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Flaureate+%3FlaureateLabel+WHERE+%7B%0A++%23+Get+Niels+Bohr%27s+Nobel+Prize+in+Physics+award+date%0A++BIND%28%28SELECT+%3Fdate+WHERE+%7B+wd%3AQ7085+p%3AP166+%3Fs+.+%3Fs+ps%3AP166+wd%3AQ38104+.+%3Fs+pq%3AP585+%3Fdate+%7D%29+AS+%3FbohrDate%29%0A%0A++%23+Get+Richard+Feynman%27s+Nobel+Prize+in+Physics+award+date%0A++BIND%28%28SELECT+%3Fdate+WHERE+%7B+wd%3AQ39246+p%3AP166+%3Fs+.+%3Fs+ps%3AP166+wd%3AQ38104+.+%3Fs+pq%3AP585+%3Fdate+%7D%29+AS+%3FfeynmanDate%29%0A%0A++%23+Find+all+humans+who+received+the+Nobel+Prize+in+Physics%0A++%3Flaureate+wdt%3AP31+wd%3AQ5+%3B%0A++++++++++++p%3AP166+%3Fs+.%0A++%3Fs+ps%3AP166+wd%3AQ38104+%3B%0A+++++pq%3AP585+%3FawardDate+.%0A%0A++%23+Filter+by+date+range%3A+after+Bohr+and+before+Feynman%0A++FILTER%28%3FawardDate+%3E+%3FbohrDate+%26%26+%3FawardDate+%3C+%3FfeynmanDate%29%0A%0A++%23+Get+laureate+label+in+English%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%3Flaureate+rdfs%3Alabel+%3FlaureateLabel+%7D%0A%7D%0AORDER+BY+%3FawardDate+%3FlaureateLabel%0A'}, {'iteration': 1, 'model': 'gemini_finetune_mcp', 'prompt': 'List of non-fictional US presidents since 1970', 'query': '\nSELECT ?president ?presidentLabel WHERE {\n  ?president [position held] ?s .\n  ?s [position held] wd:Q11696 .\n  ?s [start time] ?x filter(YEAR(?x) >= 1970) .\n  ?president [instance of] wd:Q5 .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\nORDER BY ASC(?x)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+WHERE+%7B%0A++%3Fpresident+%5Bposition+held%5D+%3Fs+.%0A++%3Fs+%5Bposition+held%5D+wd%3AQ11696+.%0A++%3Fs+%5Bstart+time%5D+%3Fx+filter%28YEAR%28%3Fx%29+%3E%3D+1970%29+.%0A++%3Fpresident+%5Binstance+of%5D+wd%3AQ5+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0AORDER+BY+ASC%28%3Fx%29%0A'}, {'iteration': 1, 'model': 'gemini_finetune_mcp', 'prompt': 'When did Niels Bohr win a Nobel Prize?', 'query': '\nSELECT ?value ?valueLabel WHERE { wd:Q7085 P166 ?s . ?s P166 wd:Q7191 . ?s P585 ?value . SERVICE wikibase:label { bd:serviceParam wikibase:language "en". ?value rdfs:label ?valueLabel } }\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fvalue+%3FvalueLabel+WHERE+%7B+wd%3AQ7085+P166+%3Fs+.+%3Fs+P166+wd%3AQ7191+.+%3Fs+P585+%3Fvalue+.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%3Fvalue+rdfs%3Alabel+%3FvalueLabel+%7D+%7D%0A'}, {'iteration': 1, 'model': 'gemini_finetune_mcp', 'prompt': 'list the countries where the Olympics were held between 2008 and 2022, along with the year', 'query': '\nSELECT ?country ?countryLabel ?year WHERE {\n  ?event [instance of] [Summer Olympic Games] .\n  ?event [country] ?country .\n  ?event [point in time] ?datetime .\n  BIND(YEAR(?datetime) AS ?year) .\n  FILTER(?year >= 2008 && ?year <= 2022) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\nUNION\n{\n  ?event [instance of] [Winter Olympic Games] .\n  ?event [country] ?country .\n  ?event [point in time] ?datetime .\n  BIND(YEAR(?datetime) AS ?year) .\n  FILTER(?year >= 2008 && ?year <= 2022) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fcountry+%3FcountryLabel+%3Fyear+WHERE+%7B%0A++%3Fevent+%5Binstance+of%5D+%5BSummer+Olympic+Games%5D+.%0A++%3Fevent+%5Bcountry%5D+%3Fcountry+.%0A++%3Fevent+%5Bpoint+in+time%5D+%3Fdatetime+.%0A++BIND%28YEAR%28%3Fdatetime%29+AS+%3Fyear%29+.%0A++FILTER%28%3Fyear+%3E%3D+2008+%26%26+%3Fyear+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0AUNION%0A%7B%0A++%3Fevent+%5Binstance+of%5D+%5BWinter+Olympic+Games%5D+.%0A++%3Fevent+%5Bcountry%5D+%3Fcountry+.%0A++%3Fevent+%5Bpoint+in+time%5D+%3Fdatetime+.%0A++BIND%28YEAR%28%3Fdatetime%29+AS+%3Fyear%29+.%0A++FILTER%28%3Fyear+%3E%3D+2008+%26%26+%3Fyear+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0A'}, {'iteration': 2, 'model': 'gemini_finetune_mcp', 'prompt': 'List of US presidents since 1970', 'query': '\nSELECT ?item ?itemLabel WHERE { ?item [position held] wd:Q11696 . ?item [start time] ?x FILTER(YEAR(?x) >= 1970) . SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fitem+%3FitemLabel+WHERE+%7B+%3Fitem+%5Bposition+held%5D+wd%3AQ11696+.+%3Fitem+%5Bstart+time%5D+%3Fx+FILTER%28YEAR%28%3Fx%29+%3E%3D+1970%29+.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D+%7D%0A'}, {'iteration': 2, 'model': 'gemini_finetune_mcp', 'prompt': 'List of non-fictional US presidents since 1970', 'query': '\nSELECT ?president ?presidentLabel ?startTime WHERE {\n  ?president [position held] wd:Q11696 .\n  ?president [instance of] wd:Q5 .\n  ?president [start time] ?startTime .\n  FILTER(xsd:dateTime(?startTime) >= "1970-01-01T00:00:00Z") .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\nORDER BY ASC(?startTime)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+%3FstartTime+WHERE+%7B%0A++%3Fpresident+%5Bposition+held%5D+wd%3AQ11696+.%0A++%3Fpresident+%5Binstance+of%5D+wd%3AQ5+.%0A++%3Fpresident+%5Bstart+time%5D+%3FstartTime+.%0A++FILTER%28xsd%3AdateTime%28%3FstartTime%29+%3E%3D+%221970-01-01T00%3A00%3A00Z%22%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0AORDER+BY+ASC%28%3FstartTime%29%0A'}, {'iteration': 2, 'model': 'gemini_finetune_mcp', 'prompt': 'When did Richard Feynman win a Nobel Prize?', 'query': "\nSELECT ?award ?awardLabel ?time WHERE { wd:Q39246 P166 ?s . ?s P585 ?time . ?s P166 ?award . ?award rdfs:label ?awardLabel . FILTER(CONTAINS(lcase(?awardLabel), 'nobel prize')) . FILTER (lang(?awardLabel) = 'en') } LIMIT 25\n", 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Faward+%3FawardLabel+%3Ftime+WHERE+%7B+wd%3AQ39246+P166+%3Fs+.+%3Fs+P585+%3Ftime+.+%3Fs+P166+%3Faward+.+%3Faward+rdfs%3Alabel+%3FawardLabel+.+FILTER%28CONTAINS%28lcase%28%3FawardLabel%29%2C+%27nobel+prize%27%29%29+.+FILTER+%28lang%28%3FawardLabel%29+%3D+%27en%27%29+%7D+LIMIT+25%0A'}, {'iteration': 2, 'model': 'gemini_finetune_mcp', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman', 'query': '\nSELECT DISTINCT ?subject ?subjectLabel WHERE {\n  ?subject [award received] ?s .\n  ?s [award received] wd:Q38104 .\n  ?s [point in time] ?date .\n  FILTER(YEAR(?date) > 1922) .\n  FILTER(YEAR(?date) < 1965) .\n  FILTER(?subject != wd:Q7085) .\n  FILTER(?subject != wd:Q39246) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }\n}\nORDER BY ASC(?subjectLabel)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Fsubject+%3FsubjectLabel+WHERE+%7B%0A++%3Fsubject+%5Baward+received%5D+%3Fs+.%0A++%3Fs+%5Baward+received%5D+wd%3AQ38104+.%0A++%3Fs+%5Bpoint+in+time%5D+%3Fdate+.%0A++FILTER%28YEAR%28%3Fdate%29+%3E+1922%29+.%0A++FILTER%28YEAR%28%3Fdate%29+%3C+1965%29+.%0A++FILTER%28%3Fsubject+%21%3D+wd%3AQ7085%29+.%0A++FILTER%28%3Fsubject+%21%3D+wd%3AQ39246%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+%7D%0A%7D%0AORDER+BY+ASC%28%3FsubjectLabel%29%0A'}, {'iteration': 2, 'model': 'gemini_finetune_mcp', 'prompt': 'list the countries where the Summer Olympics were held between 2008 and 2022, along with the year', 'query': '\nSELECT DISTINCT ?location ?locationLabel ?year WHERE {\n  ?event wdt:P276 ?location .\n  ?event wdt:P585 ?pointInTime .\n  ?event instance of wd:Q159821 .\n  FILTER(YEAR(?pointInTime) >= 2008 && YEAR(?pointInTime) <= 2022) .\n  BIND(YEAR(?pointInTime) AS ?year) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\nORDER BY ASC(?year)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Flocation+%3FlocationLabel+%3Fyear+WHERE+%7B%0A++%3Fevent+wdt%3AP276+%3Flocation+.%0A++%3Fevent+wdt%3AP585+%3FpointInTime+.%0A++%3Fevent+instance+of+wd%3AQ159821+.%0A++FILTER%28YEAR%28%3FpointInTime%29+%3E%3D+2008+%26%26+YEAR%28%3FpointInTime%29+%3C%3D+2022%29+.%0A++BIND%28YEAR%28%3FpointInTime%29+AS+%3Fyear%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0AORDER+BY+ASC%28%3Fyear%29%0A'}, {'iteration': 3, 'model': 'gemini_finetune_mcp', 'prompt': 'List of non-fictional US presidents', 'query': '\nSELECT ?item ?itemLabel WHERE { ?item wdt:P39 wd:Q11696 . ?item instance of wd:Q5 . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . } }\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fitem+%3FitemLabel+WHERE+%7B+%3Fitem+wdt%3AP39+wd%3AQ11696+.+%3Fitem+instance+of+wd%3AQ5+.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.+%7D+%7D%0A'}, {'iteration': 3, 'model': 'gemini_finetune_mcp', 'prompt': 'List of non-fictional US presidents since 1970', 'query': "\nSELECT DISTINCT ?sbj ?sbj_label WHERE { ?sbj [position held] wd:Q11696 . ?sbj [start time] ?obj . ?sbj [instance of] wd:Q5 . FILTER(YEAR(?obj) >= 1970) . SERVICE wikibase:label { ?sbj rdfs:label ?sbj_label . FILTER (lang(?sbj_label) = 'en') } } LIMIT 25\n", 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Fsbj+%3Fsbj_label+WHERE+%7B+%3Fsbj+%5Bposition+held%5D+wd%3AQ11696+.+%3Fsbj+%5Bstart+time%5D+%3Fobj+.+%3Fsbj+%5Binstance+of%5D+wd%3AQ5+.+FILTER%28YEAR%28%3Fobj%29+%3E%3D+1970%29+.+SERVICE+wikibase%3Alabel+%7B+%3Fsbj+rdfs%3Alabel+%3Fsbj_label+.+FILTER+%28lang%28%3Fsbj_label%29+%3D+%27en%27%29+%7D+%7D+LIMIT+25%0A'}, {'iteration': 3, 'model': 'gemini_finetune_mcp', 'prompt': 'For all US presidencies that started after 1970, give the serving president and the start date', 'query': '\nSELECT ?president ?presidentLabel ?start_date WHERE {\n  ?president P39 wd:Q11696 .\n  ?president P580 ?start_date .\n  FILTER(YEAR(?start_date) > 1970) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\nORDER BY ASC(?start_date)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+%3Fstart_date+WHERE+%7B%0A++%3Fpresident+P39+wd%3AQ11696+.%0A++%3Fpresident+P580+%3Fstart_date+.%0A++FILTER%28YEAR%28%3Fstart_date%29+%3E+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0AORDER+BY+ASC%28%3Fstart_date%29%0A'}, {'iteration': 3, 'model': 'gemini_finetune_mcp', 'prompt': 'list all physics nobel laureates from 2000 to 2010', 'query': '\nSELECT ?laureate ?laureateLabel WHERE {\n    wd:Q38104 P1346 ?laureate .\n    wd:Q38104 P585 ?point_in_time .\n    FILTER(YEAR(?point_in_time) >= 2000 && YEAR(?point_in_time) <= 2010) .\n    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Flaureate+%3FlaureateLabel+WHERE+%7B%0A++++wd%3AQ38104+P1346+%3Flaureate+.%0A++++wd%3AQ38104+P585+%3Fpoint_in_time+.%0A++++FILTER%28YEAR%28%3Fpoint_in_time%29+%3E%3D+2000+%26%26+YEAR%28%3Fpoint_in_time%29+%3C%3D+2010%29+.%0A++++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.+%7D%0A%7D%0A'}, {'iteration': 3, 'model': 'gemini_finetune_mcp', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman', 'query': '\nSELECT ?laureate ?laureateLabel WHERE {\n  ?laureate [award received] ?s .\n  ?s [award received] wd:Q38104 .\n  ?s [point in time] ?date .\n  FILTER(YEAR(?date) > 1922) .\n  FILTER(YEAR(?date) < 1965) .\n  FILTER(?laureate != wd:Q7085) .\n  FILTER(?laureate != wd:Q39246) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Flaureate+%3FlaureateLabel+WHERE+%7B%0A++%3Flaureate+%5Baward+received%5D+%3Fs+.%0A++%3Fs+%5Baward+received%5D+wd%3AQ38104+.%0A++%3Fs+%5Bpoint+in+time%5D+%3Fdate+.%0A++FILTER%28YEAR%28%3Fdate%29+%3E+1922%29+.%0A++FILTER%28YEAR%28%3Fdate%29+%3C+1965%29+.%0A++FILTER%28%3Flaureate+%21%3D+wd%3AQ7085%29+.%0A++FILTER%28%3Flaureate+%21%3D+wd%3AQ39246%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0A'}, {'iteration': 4, 'model': 'gemini_finetune_mcp', 'prompt': 'List of US presidents since 1970', 'query': '\nSELECT ?president ?presidentLabel WHERE { ?president [position held] wd:Q11696 . ?president [start time] ?value . FILTER(YEAR(?value) >= 1970) . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . ?president rdfs:label ?presidentLabel } }\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+WHERE+%7B+%3Fpresident+%5Bposition+held%5D+wd%3AQ11696+.+%3Fpresident+%5Bstart+time%5D+%3Fvalue+.+FILTER%28YEAR%28%3Fvalue%29+%3E%3D+1970%29+.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.+%3Fpresident+rdfs%3Alabel+%3FpresidentLabel+%7D+%7D%0A'}, {'iteration': 4, 'model': 'gemini_finetune_mcp', 'prompt': 'List of non-fictional US presidents since 1970', 'query': "\nSELECT DISTINCT ?sbj ?sbjLabel WHERE {\n  ?sbj P39 Q11696 .\n  ?sbj P39 ?s .\n  ?s P580 ?x filter(YEAR(?x) >= 1970) .\n  ?sbj instance of Q5 .\n  FILTER NOT EXISTS { ?sbj instance of Q95074 }\n  SERVICE wikibase:label { ?sbj rdfs:label ?sbjLabel . FILTER (lang(?sbjLabel) = 'en') }\n}\nLIMIT 25\n", 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Fsbj+%3FsbjLabel+WHERE+%7B%0A++%3Fsbj+P39+Q11696+.%0A++%3Fsbj+P39+%3Fs+.%0A++%3Fs+P580+%3Fx+filter%28YEAR%28%3Fx%29+%3E%3D+1970%29+.%0A++%3Fsbj+instance+of+Q5+.%0A++FILTER+NOT+EXISTS+%7B+%3Fsbj+instance+of+Q95074+%7D%0A++SERVICE+wikibase%3Alabel+%7B+%3Fsbj+rdfs%3Alabel+%3FsbjLabel+.+FILTER+%28lang%28%3FsbjLabel%29+%3D+%27en%27%29+%7D%0A%7D%0ALIMIT+25%0A'}, {'iteration': 4, 'model': 'gemini_finetune_mcp', 'prompt': 'For all US presidencies that started after 1970, give the serving president and the start date', 'query': '\nSELECT ?president ?presidentLabel ?startDate WHERE {\n  ?president P39 wd:Q11696 .\n  ?president p:P39 ?s .\n  ?s ps:P39 wd:Q11696 .\n  ?s pq:P580 ?startDate .\n  FILTER(YEAR(?startDate) > 1970) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+%3FstartDate+WHERE+%7B%0A++%3Fpresident+P39+wd%3AQ11696+.%0A++%3Fpresident+p%3AP39+%3Fs+.%0A++%3Fs+ps%3AP39+wd%3AQ11696+.%0A++%3Fs+pq%3AP580+%3FstartDate+.%0A++FILTER%28YEAR%28%3FstartDate%29+%3E+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0A'}, {'iteration': 4, 'model': 'gemini_finetune_mcp', 'prompt': 'When did Niels Bohr win a Nobel Prize?', 'query': '\nSELECT ?value ?valueLabel WHERE { wd:Q7085 wdt:P166 ?s . ?s P585 ?value . ?s P166 wd:Q7191 . SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fvalue+%3FvalueLabel+WHERE+%7B+wd%3AQ7085+wdt%3AP166+%3Fs+.+%3Fs+P585+%3Fvalue+.+%3Fs+P166+wd%3AQ7191+.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D+%7D%0A'}, {'iteration': 4, 'model': 'gemini_finetune_mcp', 'prompt': 'list the grand children of Queen Elisabeth II', 'query': '\nSELECT ?grandchild ?grandchildLabel WHERE { wd:Q9682 P40 ?child . ?child P40 ?grandchild . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . ?grandchild rdfs:label ?grandchildLabel } }\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fgrandchild+%3FgrandchildLabel+WHERE+%7B+wd%3AQ9682+P40+%3Fchild+.+%3Fchild+P40+%3Fgrandchild+.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.+%3Fgrandchild+rdfs%3Alabel+%3FgrandchildLabel+%7D+%7D%0A'}, {'iteration': 4, 'model': 'gemini_finetune_mcp', 'prompt': 'list the countries where the Summer Olympics were held between 2008 and 2022, along with the year', 'query': "\nSELECT ?country ?countryLabel ?olympicGames ?olympicGamesLabel ?time WHERE {\n  ?olympicGames wdt:P31 wd:Q159821 .\n  ?olympicGames wdt:P276 ?location .\n  ?location wdt:P17 ?country .\n  ?olympicGames wdt:P580 ?time .\n  FILTER(YEAR(?time) >= 2008 && YEAR(?time) <= 2022) .\n  SERVICE wikibase:label {\n    ?country rdfs:label ?countryLabel .\n    ?olympicGames rdfs:label ?olympicGamesLabel .\n    FILTER (lang(?countryLabel) = 'en') .\n    FILTER (lang(?olympicGamesLabel) = 'en')\n  }\n}\n", 'error': '500 Server Error: Internal Server Error for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fcountry+%3FcountryLabel+%3FolympicGames+%3FolympicGamesLabel+%3Ftime+WHERE+%7B%0A++%3FolympicGames+wdt%3AP31+wd%3AQ159821+.%0A++%3FolympicGames+wdt%3AP276+%3Flocation+.%0A++%3Flocation+wdt%3AP17+%3Fcountry+.%0A++%3FolympicGames+wdt%3AP580+%3Ftime+.%0A++FILTER%28YEAR%28%3Ftime%29+%3E%3D+2008+%26%26+YEAR%28%3Ftime%29+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++%3Fcountry+rdfs%3Alabel+%3FcountryLabel+.%0A++++%3FolympicGames+rdfs%3Alabel+%3FolympicGamesLabel+.%0A++++FILTER+%28lang%28%3FcountryLabel%29+%3D+%27en%27%29+.%0A++++FILTER+%28lang%28%3FolympicGamesLabel%29+%3D+%27en%27%29%0A++%7D%0A%7D%0A'}, {'iteration': 4, 'model': 'gemini_finetune_mcp', 'prompt': 'list the countries where the Olympics were held between 2008 and 2022, along with the year', 'query': '\nSELECT ?country ?countryLabel ?year WHERE {\n  { ?s [instance of] wd:Q159821 . }\n  UNION\n  { ?s [instance of] wd:Q9606 . }\n  ?s [country] ?country .\n  ?s [point in time] ?date .\n  BIND(YEAR(?date) AS ?year) .\n  FILTER(?year >= 2008 && ?year <= 2022) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fcountry+%3FcountryLabel+%3Fyear+WHERE+%7B%0A++%7B+%3Fs+%5Binstance+of%5D+wd%3AQ159821+.+%7D%0A++UNION%0A++%7B+%3Fs+%5Binstance+of%5D+wd%3AQ9606+.+%7D%0A++%3Fs+%5Bcountry%5D+%3Fcountry+.%0A++%3Fs+%5Bpoint+in+time%5D+%3Fdate+.%0A++BIND%28YEAR%28%3Fdate%29+AS+%3Fyear%29+.%0A++FILTER%28%3Fyear+%3E%3D+2008+%26%26+%3Fyear+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D%0A%7D%0A'}, {'iteration': 5, 'model': 'gemini_finetune_mcp', 'prompt': 'For all US presidencies that started after 1970, give the serving president and the start date', 'query': '\nSELECT ?president ?presidentLabel ?start_date WHERE {\n  ?president [position held] ?s .\n  ?s [position held] wd:Q11696 .\n  ?s [start time] ?start_date .\n  FILTER(YEAR(?start_date) > 1970) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". ?president rdfs:label ?presidentLabel }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fpresident+%3FpresidentLabel+%3Fstart_date+WHERE+%7B%0A++%3Fpresident+%5Bposition+held%5D+%3Fs+.%0A++%3Fs+%5Bposition+held%5D+wd%3AQ11696+.%0A++%3Fs+%5Bstart+time%5D+%3Fstart_date+.%0A++FILTER%28YEAR%28%3Fstart_date%29+%3E+1970%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%3Fpresident+rdfs%3Alabel+%3FpresidentLabel+%7D%0A%7D%0A'}, {'iteration': 5, 'model': 'gemini_finetune_mcp', 'prompt': 'When did Niels Bohr win a Nobel Prize?', 'query': '\nSELECT ?award ?awardLabel ?pointInTime WHERE {\n  wd:Q7085 wdt:P166 ?s .\n  ?s P166 ?award .\n  ?s P585 ?pointInTime .\n  SERVICE wikibase:label {\n    bd:serviceParam wikibase:language "en".\n  }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Faward+%3FawardLabel+%3FpointInTime+WHERE+%7B%0A++wd%3AQ7085+wdt%3AP166+%3Fs+.%0A++%3Fs+P166+%3Faward+.%0A++%3Fs+P585+%3FpointInTime+.%0A++SERVICE+wikibase%3Alabel+%7B%0A++++bd%3AserviceParam+wikibase%3Alanguage+%22en%22.%0A++%7D%0A%7D%0A'}, {'iteration': 5, 'model': 'gemini_finetune_mcp', 'prompt': 'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman', 'query': '\nSELECT DISTINCT ?sbj ?sbjLabel ?award_date WHERE {\n  ?sbj [award received] ?s .\n  ?s [award received] [Nobel Prize in Physics] .\n  ?s [point in time] ?award_date .\n  FILTER(YEAR(?award_date) > 1922 && YEAR(?award_date) < 1965) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }\n}\nORDER BY ASC(?award_date)\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+DISTINCT+%3Fsbj+%3FsbjLabel+%3Faward_date+WHERE+%7B%0A++%3Fsbj+%5Baward+received%5D+%3Fs+.%0A++%3Fs+%5Baward+received%5D+%5BNobel+Prize+in+Physics%5D+.%0A++%3Fs+%5Bpoint+in+time%5D+%3Faward_date+.%0A++FILTER%28YEAR%28%3Faward_date%29+%3E+1922+%26%26+YEAR%28%3Faward_date%29+%3C+1965%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+%7D%0A%7D%0AORDER+BY+ASC%28%3Faward_date%29%0A'}, {'iteration': 5, 'model': 'gemini_finetune_mcp', 'prompt': 'list the countries where the Winter Olympics were held between 2008 and 2022, along with the year', 'query': '\nSELECT ?event ?eventLabel ?country ?countryLabel WHERE {\n  ?event [instance of] wd:Q82414 .\n  ?event wdt:P17 ?country .\n  ?event [point in time] ?time .\n  FILTER(YEAR(?time) >= 2008 && YEAR(?time) <= 2022) .\n  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }\n}\n', 'error': '400 Client Error: Bad Request for url: https://query.wikidata.org/sparql?query=%0ASELECT+%3Fevent+%3FeventLabel+%3Fcountry+%3FcountryLabel+WHERE+%7B%0A++%3Fevent+%5Binstance+of%5D+wd%3AQ82414+.%0A++%3Fevent+wdt%3AP17+%3Fcountry+.%0A++%3Fevent+%5Bpoint+in+time%5D+%3Ftime+.%0A++FILTER%28YEAR%28%3Ftime%29+%3E%3D+2008+%26%26+YEAR%28%3Ftime%29+%3C%3D+2022%29+.%0A++SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22+.+%7D%0A%7D%0A'}]

    finetune_errors = {}
    finetune_mcp_errors = {}
    for e in erroneous_queries:
        if e["model"] == "gemini_finetune":
            finetune_errors[e["iteration"]] = finetune_errors.get(e["iteration"], 0) + 1
        if e["model"] == "gemini_finetune_mcp":
            finetune_mcp_errors[e["iteration"]] = finetune_mcp_errors.get(e["iteration"], 0) + 1
    print(f"Finetune errors: {finetune_errors}")
    print(f"Finetune MCP errors: {finetune_mcp_errors}")


if __name__ == "__main__":
    # Uncomment the following lines to run the grading functions
    # grade_benchmark()
    # grade_all_ungraded()
    # export_database()
    # calc_scores()
    # calc_statistical_significance()
    # export_query_jaccard()
    # benchmark_numbers()
    # get_invalid_count()
    stat_analysis_excluding_errors()
    # print(query_wikidata("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 . } LIMIT 10"))
