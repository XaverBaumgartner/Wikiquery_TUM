import csv
import json

input = 'other/lc-quad-2-synth.csv'

output = 'other/instruction.json'

results = []

with open(input, 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        question = row['llm_translation'].strip()
        sparql = row['sparql_wikidata_translated'].strip()
        if question and sparql:
            results.append({
                "input": question,
                "output": sparql
            })

with open(output, 'w', encoding='utf-8') as outputfile:
    json.dump(results, outputfile, indent=2, ensure_ascii=False)



