import json

input= 'other/instruction.json'
output = 'other/vertex_data.jsonl'

with open(input, 'r', encoding='utf-8') as f:
    data = json.load(f)


with open(output, 'w', encoding='utf-8') as f:
    for qna in data:
        f.write(json.dumps(qna) + '\n')

