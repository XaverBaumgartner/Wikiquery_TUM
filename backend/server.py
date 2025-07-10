from flask import Flask, request, jsonify
from flask_cors import CORS 
app = Flask(__name__)
CORS(app)

from gemini import gemini
from gemini_mcp import gemini_mcp
# from gemini_finetune_mcp import gemini_finetune_mcp

# Examples & tests
testmessage = r"""
Diese SPARQL-Abfrage findet alle Personen, die als Kinder von Johann Sebastian Bach in Wikidata gelistet sind, und sucht dann für jedes dieser Kinder die zugehörige Mutter. Schließlich ruft sie die Namen der Kinder und ihrer Mütter ab, um sie in der Ergebnisliste anzuzeigen.

```sparql
SELECT ?child ?childLabel ?mother ?motherLabel
WHERE {
  wd:Q1339 wdt:P40 ?child .       # Finde die Kinder von Johann Sebastian Bach (Q1339)
  ?child wdt:P25 ?mother .         # Finde die Mutter jedes Kindes
  SERVICE wikibase:label {         # Hole die Labels (Namen) für Kind und Mutter
    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". # Bevorzuge automatische Sprache oder Englisch
    ?child rdfs:label ?childLabel .
    ?mother rdfs:label ?motherLabel .
  }
}
```

Die Abfrage liefert eine Liste von Kindern von Johann Sebastian Bach zusammen mit ihren jeweiligen Müttern. Die Variablen ?child und ?mother repräsentieren die Wikidata-Items für das Kind und die Mutter, während ?childLabel und ?motherLabel die zugehörigen Namen (Labels) liefern, dank des wikibase:label Service. Es werden nur Kinder gelistet, für die auch eine Mutter in Wikidata verzeichnet ist."""


@app.route('/userInput', methods=['GET'])
def user_query():
    model = request.args.get('model', '')
    prompt = request.args.get('prompt', '')
    if len(prompt) > 20000:
        return jsonify(message='Query was too long to process. Is this an attack?'), 200

    message = f'Invalid model "{model}"'
    match model:
        case 'gemini':
            message = gemini(prompt, use_finetune=False)
        case 'gemini_mcp':
            message = gemini_mcp(prompt, use_finetune=False)
        case 'gemini_finetune':
            message = gemini(prompt, use_finetune=True)
        case 'gemini_finetune_mcp':
            message = gemini_mcp(prompt, use_finetune=True)
        case 'test':
            message = testmessage

    query = extract_query(message)
    return jsonify(message=message, query=query), 200

def extract_query(message):
    if isinstance(message, str) and "```sparql" in message:
        try:
            return message.split("```sparql")[1].split("```")[0]
        except IndexError:
            return None
    return None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)