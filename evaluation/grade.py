import sqlite3
import scipy.stats as stats
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from wikidata_utils import query_wikidata
from promptModel import print_query_result, insert, export_database

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
            # Create tuple of benchmark values for comparison
            benchmark_values = tuple(
                j.get(benchmark_dataset["head"]["vars"][column], {}).get("value") for column in comparing_columns if comparing_columns[column] != -1
            )
            # Check if benchmark values exist in result bindings dictionary
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


        # Calculate global Jaccard index
        global_jaccard_index = total_true_positives / (total_true_positives + total_false_positives + total_false_negatives) if (total_true_positives + total_false_positives + total_false_negatives) > 0 else 0

        # Calculate average Jaccard index
        avg_jaccard_index = jaccard_index_sum / count if count > 0 else 0

        # Calculate F1 macro score
        avg_precision = precision_sum / count if count > 0 else 0
        avg_recall = recall_sum / count if count > 0 else 0
        avg_f1 = f1_sum / count if count > 0 else 0

        # Calculate F1 micro score
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
    


if __name__ == "__main__":
    # Uncomment the following lines to run the grading functions
    # grade_benchmark()
    # grade_all_ungraded()
    # export_database()
    # calc_scores()
    calc_statistical_significance()
    # export_query_jaccard()
    # benchmark_numbers()
    # print(query_wikidata("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 . } LIMIT 10"))


"""
{
    'head': {
        'vars': ['item']
    },
    'results': {
        'bindings': [
            {
                'item': 
                    {
                        'type': 'uri', 
                        'value': 'http://www.wikidata.org/entity/L1150603'
                }
            },
            {
                'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/L1150609'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/L739810'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q23'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q42'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q76'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q80'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q91'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q157'}}, {'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q181'}}]}}
"""