import json

original= 'other/vertex_data.jsonl'

data = []
with open(original, 'r', encoding='utf-8') as f:
     for line in f:
        line = line.strip() 
        if line != '':  
            item = json.loads(line)
            data.append(item)


split = int(len(data) * 0.8)

train = data[:split]
valid = data[split:]

trainFile= 'other/vertexTrain.jsonl'
with open(trainFile, 'w', encoding='utf-8') as f:
    for item in train:
        format = {
            "contents": [
                {"role": "user", "parts": [{"text": item["input"]}]},
                {"role": "model", "parts": [{"text": item["output"]}]}
            ]
        }
        f.write(json.dumps(format) + '\n')

validFile= 'other/vertexValid.jsonl'
with open(validFile, 'w', encoding='utf-8') as f:
    for item in valid:
        format = {
            "contents": [
                {"role": "user", "parts": [{"text": item["input"]}]},
                {"role": "model", "parts": [{"text": item["output"]}]}
            ]
        }
        f.write(json.dumps(format) + '\n')


