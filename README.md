# About the project
This project was completed as part of the Practical Course 'Data Engineering' within the Data Engineering Research Group at the TUM School of Computation, Information and Technology (Technical University of Munich). For a full explanation, our motivation, the research questions and main findings, please consult the [`Written Report`](</Written Report: Wikiquery.pdf>).

# Result Analysis
The following is a more detailed description of the results in the [`Written Report`](</Written Report: Wikiquery.pdf>), including explanations and data that shuold be published for the sake of completeness, but would be beyond the scope of the Written Report and/or make it too long.

---

This json includes the scores (average precision, average recall, F1 micro and macro, global and average Jaccard index) the models were able to reach in each of the 5 iterations:
```json
{'gemini': {'precision': [0.6145833333333334, 0.35401785714285716, 0.5, 0.68125, 0.4318181818181818], 'recall': [0.5625, 0.34375, 0.4625, 0.65, 0.4], 'f1_macro': [0.5776515151515151, 0.3421474358974359, 0.4758771929824562, 0.6604166666666667, 0.4104010025062657], 'f1_micro': [0.7325581395348837, 0.578616352201258, 0.6351931330472104, 0.9348914858096828, 0.5197215777262181], 'global_jaccard_index': [0.5779816513761468, 0.40707964601769914, 0.46540880503144655, 0.877742946708464, 0.3510971786833856], 'average_jaccard_index': [0.5520833333333334, 0.32276785714285716, 0.4625, 0.6448863636363636, 0.3943181818181818]}, 'gemini_finetune': {'precision': [0.16964285714285715, 0.23214285714285715, 0.29464285714285715, 0.125, 0.23214285714285715], 'recall': [0.1875, 0.25, 0.28125, 0.125, 0.25], 'f1_macro': [0.17708333333333331, 0.23958333333333331, 0.28125, 0.125, 0.23958333333333331], 'f1_micro': [0.5327510917030568, 0.5066666666666666, 0.5198237885462554, 0.3394255874673629, 0.5066666666666666], 'global_jaccard_index': [0.3630952380952381, 0.3392857142857143, 0.35119047619047616, 0.20440251572327045, 0.3392857142857143], 'average_jaccard_index': [0.16964285714285715, 0.23214285714285715, 0.26339285714285715, 0.125, 0.23214285714285715]}, 'gemini_finetune_mcp': {'precision': [0.49375, 0.4375, 0.35714285714285715, 0.47901785714285716, 0.5], 'recall': [0.4326388888888889, 0.3451388888888889, 0.31875, 0.4388888888888889, 0.4388888888888889], 'f1_macro': [0.4339673913043478, 0.3568840579710145, 0.3134469696969697, 0.42819816053511706, 0.44021739130434784], 'f1_micro': [0.625, 0.4411764705882353, 0.3770883054892601, 0.725563909774436, 0.55125284738041], 'global_jaccard_index': [0.45454545454545453, 0.2830188679245283, 0.2323529411764706, 0.5693215339233039, 0.3805031446540881], 'average_jaccard_index': [0.42752525252525253, 0.3451388888888889, 0.3008928571428572, 0.41790674603174605, 0.4388888888888889]}, 'gemini_mcp': {'precision': [0.8579545454545454, 0.7827110389610389, 0.6808512759170654, 0.8267045454545454, 0.6761363636363636], 'recall': [0.8625, 0.80625, 0.7375, 0.8625, 0.675], 'f1_macro': [0.8598057644110275, 0.7928571428571428, 0.6909781449893391, 0.8389724310776941, 0.675281954887218], 'f1_micro': [0.8776223776223777, 0.7885304659498207, 0.807131280388979, 0.8655172413793104, 0.8405797101449275], 'global_jaccard_index': [0.7819314641744548, 0.650887573964497, 0.6766304347826086, 0.7629179331306991, 0.725], 'average_jaccard_index': [0.8474431818181818, 0.7775974025974025, 0.6714762759170654, 0.8161931818181818, 0.665625]}}
```
This data can be visualized with a boxplot:

![Stat 1](<evaluation/Distribution of Performance Metrics across Models (5 Iterations).jpg>)

Also, it can be calculated what models are statistically significantly better (p < 0.5) than other models, for each score:
```
Precision:
gemini_mcp is significantly better than gemini_finetune (p-value: 0.0000)
gemini_mcp is significantly better than gemini_finetune_mcp (p-value: 0.0002)
gemini_finetune_mcp is significantly better than gemini_finetune (p-value: 0.0003)
gemini is significantly better than gemini_finetune (p-value: 0.0039)
gemini_mcp is significantly better than gemini (p-value: 0.0101)

Recall:
gemini_mcp is significantly better than gemini_finetune (p-value: 0.0000)
gemini_mcp is significantly better than gemini_finetune_mcp (p-value: 0.0000)
gemini_finetune_mcp is significantly better than gemini_finetune (p-value: 0.0018)
gemini_mcp is significantly better than gemini (p-value: 0.0025)
gemini is significantly better than gemini_finetune (p-value: 0.0053)

F1 macro:
gemini_mcp is significantly better than gemini_finetune (p-value: 0.0000)
gemini_mcp is significantly better than gemini_finetune_mcp (p-value: 0.0001)
gemini_finetune_mcp is significantly better than gemini_finetune (p-value: 0.0013)
gemini_mcp is significantly better than gemini (p-value: 0.0048)
gemini is significantly better than gemini_finetune (p-value: 0.0048)

F1 micro:
gemini_mcp is significantly better than gemini_finetune_mcp (p-value: 0.0078)
gemini_mcp is significantly better than gemini_finetune (p-value: 0.0001)

Global Jaccard Index:
gemini_mcp is significantly better than gemini_finetune (p-value: 0.0000)
gemini_mcp is significantly better than gemini_finetune_mcp (p-value: 0.0030)

Average Jaccard Index:
gemini_mcp is significantly better than gemini_finetune (p-value: 0.0000)
gemini_mcp is significantly better than gemini_finetune_mcp (p-value: 0.0001)
gemini_finetune_mcp is significantly better than gemini_finetune (p-value: 0.0011)
gemini_mcp is significantly better than gemini (p-value: 0.0046)
gemini is significantly better than gemini_finetune (p-value: 0.0059)
```
```Note: These are computer-generated, rounded values. (p-value: 0.0000) should be interpreted as (p < 0.0001).```

This shows that Gemini (MCP) outperforms all other models in both important metrics for this grading (Average Jaccard & F1 macro) with p < 0.005, which is far lower than the usual p < 0.5 threshhold for statistical significance.

---

The following are the query responses of all the models for all testing prompts. They were graded by running them and comparing their results to those of the benchmark queries, calculating the size of the intersect of the two sets and dividing it by the size of their union (so-called 'Jaccard index').

![Stat jaccard](<evaluation/Jaccard Index for Prompts by Model across 5 Iterations.jpg>)

These are the prompts used for testing, along with explanations of the challenges or specific requirements for each.

1.  **Children of Johann Sebastian Bach**  
    *Explanation:* This query is an example from the Wikidata tutorial page and is likely included in most LLMs' training data.

2.  **List of US presidents**  
    *Explanation:* Fictional presidents should not be included. This requires filtering for instances of "human" or similar properties.

3.  **List of non-fictional US presidents**  
    *Explanation:* Similar to 'List of US presidents,' but this prompt is more explicit to increase the LLM's chances of understanding the task's filtering requirement.

4.  **List of US presidents since 1970**  
    *Explanation:* This requires filtering based on time constraints (start of term, not birthdate). Richard Nixon should be included even though he was elected prior to 1970. This prompt requires an understanding of context-dependent filtering.

5.  **List of non-fictional US presidents since 1970**  
    *Explanation:* See the explanation for "List of US presidents since 1970" regarding time constraints and contextual filtering, combined with the "non-fictional" requirement.

6.  **For all US presidencies that started after 1970, give the serving president and the start date**  
    *Explanation:* This prompt should include Donald Trump twice, as it asks for "presidencies" rather than distinct "presidents," which is different from the previous queries.

7.  **List all physics Nobel laureates from 2000 to 2010**  
    *Explanation:* This requires understanding time intervals, specifically that "2000" refers to the year.

8.  **When did Niels Bohr win a Nobel Prize?**  
    *Explanation:* This requires understanding that entities are not instances of their own class. Therefore, filtering by `instanceOf` 'Nobel Prize in Physics' will not work, while constructs like `subclassOf` 'Nobel Prize' are appropriate.

9.  **When did Richard Feynman win a Nobel Prize?**  
    *Explanation:* See the explanation for Niels Bohr; it presents the same challenge regarding class instance relationships.

10. **List all physics Nobel laureates who won their prize after Niels Bohr but before Richard Feynman**  
    *Explanation:* This is a high-complexity query. It requires subdividing the problem into multiple parts, solving each part (e.g., finding Bohr's Nobel date, Feynman's Nobel date), and then combining the results to filter the list of laureates.

11. **List all physics Nobel laureates who won their prize after Niels Bohr but before Richard Feynman! This query gives Niels Bohrs date: `SELECT ?date WHERE { wd:Q7085 p:P166 ?statement . ?statement ps:P166 ?award . ?award wdt:P279 wd:Q7191 . ?statement pq:P585 ?date . }`, this query gives Richard Feynmans date: `SELECT ?date WHERE { wd:Q39246 p:P166 ?statement . ?statement ps:P166 ?award . ?award wdt:P279 wd:Q7191 . ?statement pq:P585 ?date . }`, and this query gives all physics Nobel laureates from 2000 to 2010: `SELECT DISTINCT ?laureateLabel WHERE { ?laureate wdt:P31 wd:Q5 ; p:P166 ?awardStatement . ?awardStatement ps:P166 wd:Q38104 ; pq:P585 ?awardDate . FILTER (YEAR(?awardDate) >= 2000 && YEAR(?awardDate) <= 2010) SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". } } ORDER BY ?awardDate ?laureateLabel`**  
    *Explanation:* This query still requires combining different partial results, but it provides the necessary sub-queries, thereby reducing the need for the LLM to subdivide or solve any problems independently.

12. **List the grandchildren of Queen Elizabeth II**  
    *Explanation:* This requires understanding that "grandchild" is not a direct property of the entity. Instead, it's a relationship that requires two steps: first finding the children, then finding their children.

13. **List the countries where the Summer Olympics were held between 2008 and 2022, along with the year**  
    *Explanation:* This prompt requests two different properties (country and year) of the same entity (Summer Olympics events).

14. **List the countries where the Winter Olympics were held between 2008 and 2022, along with the year**  
    *Explanation:* Similar to the previous prompt, this also requests two different properties (country and year) of the same entity (Winter Olympics events).

15. **List the countries where the Olympics were held between 2008 and 2022, along with the year**  
    *Explanation:* This query requires understanding that "Olympics" can refer to both Summer and Winter Olympics, and both types should be included in the results.

16. **List the countries where the Summer- or Winter Olympics were held between 2008 and 2022, along with the year**  
    *Explanation:* Similar to the previous prompt, this also requires understanding that both Summer and Winter Olympics should be included. However, it provides a slight hint to the LLM by explicitly mentioning "Summer- or Winter Olympics."

It can easily be seen that most queries solve the problem either perfectly or not at all, while partially correct results are quite rare.  
The only results with no matches are empty results, which suggests that a model fundamentally misunderstanding the user’s intent is not currently a bottleneck in LLM natural language to SPARQL translation.

---

The training data used to finetune the models is given in a format containing natural language placeholders
```json
{
   "input": "Is Kevin Costner the owner of Fielders Stadium?",
   "output": "ASK WHERE { [Kevin Costner] [owner of] [Fielders Stadium] }"
}
```
while a real, corresponding SPARQL query looks like this:
```sparql
ASK WHERE { wd:Q11930 wdt:P1830 wd:Q5447154 }
```
Since the prefixes, like wd: or pq:, carry semantic meaning, it is not possible for our post-processing script to infer them when injecting the IDs. Therefore, for the Gemini (Finetuned) approach, the model is prompted to generate responses in the format 
```sparql
ASK WHERE { wd:[Kevin Costner] wdt:[owner of] wd:[Fielders Stadium] }
```
so there is a slight format difference between the format of the data it was trained on and that it is supposed to generate.  
The Finetune (MCP) model will generate complete SPARQL queries in their final format, as it can do its own entity matching. It, too, uses the model trained on this data, as finetuning it with complete SPARQL queries containing IDs that have no meaning without knowing what entities they stand for is rather pointless.  

Sometimes, the finetuned models act against their given instructions and return queries in the wrong format: Finetune (MCP) will sometimes answer with queries containing placeholders instead of actual IDs, and Gemini (Finetuned) will generate queries with missing prefixes. These will fail upon execution and are therefore treated like queries with empty results.  
This, of course, raises the question of whether the finetuned models are just as performant as the other ones, with the lower grades being results of invalid query generation caused by the format difference.  
Finetune errors (iteration : number of errors): `{1: 3, 2: 5, 3: 2, 4: 2, 5: 3}`  
Finetune MCP errors (iteration : number of errors): `{1: 3, 2: 5, 3: 5, 4: 7, 5: 4}`  
Recalculating the average jaccard indices, excluding these erroneous queries, gives the following results for each iteration:
```
{
	'gemini': [0.5520833333333334, 0.32276785714285716, 0.4625, 0.6448863636363636, 0.3943181818181818]
	'gemini_finetune': [0.16964285714285715*16/(16-3), 0.23214285714285715*16/(16-5), 0.26339285714285715*16/(16-2), 0.125*16/(16-2), 0.23214285714285715*16/(16-3)]
	'gemini_finetune_mcp': [0.42752525252525253*16/(16-3), 0.3451388888888889*16/(16-5), 0.3008928571428572*16/(16-5), 0.41790674603174605*16/(16-7), 0.4388888888888889*16/(16-4)]
	'gemini_mcp': [0.8474431818181818, 0.7775974025974025, 0.6714762759170654, 0.8161931818181818, 0.665625]
}
```
... which comes down to:  
```
gemini_mcp > gemini_finetune (p<0.0001)  
gemini_finetune_mcp > gemini_finetune (p=0.0013)  
gemini_mcp > gemini (p=0.0033)  
gemini > gemini_finetune (p=0.0109)  
gemini_mcp > gemini_finetune_mcp (p=0.0150)  
```
This means that the finetuning really did hurt the model's ability to write sensible queries that return accurate and precise results, and that the finetuned models' lower scores can not be explained away with erroneous queries that may or may not result from being in the wrong format (Not all malformed queries were caused by ill-formatted placeholders!).

---

The benchmark queries and the model responses are available in the `sqlite3` database files in the evaluation folder:  
[`eval 1.db`](<evaluation/eval 1.db>) for the 1st iteration  
[`eval 2.db`](<evaluation/eval 2.db>) for the 2nd iteration  
[`eval 3.db`](<evaluation/eval 3.db>) for the 3rd iteration  
[`eval 4.db`](<evaluation/eval 4.db>) for the 4th iteration  
[`eval 5.db`](<evaluation/eval 5.db>) for the 5th iteration  

All data was collected wit [`prompt_model.py`](evaluation/prompt_model.py) and analyzed with [`grade.py`](evaluation/grade.py).

# Code

Interesting **Frontend** code is in [`App.tsx`](frontend/src/App.tsx).

Interesting **Backend** code can be found in:
* [`backend/server.py`](backend/server.py)
* [`backend/gemini.py`](backend/gemini.py)
* [`backend/gemini_mcp.py`](backend/gemini_mcp.py)

The **Evaluation** code used to generate and grade the results can be found in:
* [`evaluation/promptModel.py`](evaluation/promptModel.py)
* [`evaluation/grading.py`](evaluation/grading.py)

The web app is currently being hosted on [Wikiquery.org](https://www.wikiquery.org)

# Running the code yourself
__Prerequisites__

You will need your own Google API keys, since we cannot publish ours to Gihub due to scrapers. For a key to the finetuned model, just write us a mail. To use your own key for plain gemini, replace the 'REPLACE THIS' text in gemini.py with your key. For your own vertex API model, do the same with the credentials.json file (either in [`backend/credentials.json`](backend/credentials.json) or in [`credentials.json`](credentials.json), as different python interpreters handle relative paths differently. For us, hosting with the built-in flask server required one location, while the gunicorn server required the other).  
In [`App.tsx`](frontend/src/App.tsx), 
```TypeScript
const backendUrl = "https://api.wikiquery.org";
```
needs to be updated with the URL of your backend.

__Frontend:__

Make sure you have `npm` installed, then head to [`frontend`](frontend/).
Install:
```bash
npm install
```
After installing, it can be run with:
```bash
npm run dev
```
__Backend:__

Make sure you have `python3` installed (including `pip`), then head to [`backend`](backend/).
```bash
pip install -r requirements.txt
```
After installing, it can be run with:
```bash
python3 server.py
```
For deployment in production, a proper WSGI server like [gunicorn](https://gunicorn.org/) is strongly recommended.

# Credits
The finetuning dataset is a column subset of [lc_quad_synth](https://huggingface.co/datasets/timschwa/lc_quad_synth), which is an improved version of Lc-quad 2.0.
```
Tim Schwabe, Louisa Siebel, Patrik Valach, and Maribel Acosta. 
Q-NL Verifier: Leveraging Synthetic Data for Robust Knowledge Graph Question Answering. 
arXiv preprint arXiv:2503.01385, 2025.
```
```
Mohnish Dubey, Debayan Banerjee, Abdelrahman Abdelkawi, and Jens Lehmann.
Lc-quad 2.0: A large dataset for complex question answering over wikidata and dbpedia.
In Proceedings of the 18th International Semantic Web Conference (ISWC).
Springer, 2019.
```
We are using the llm_translation column as the input and the sparql_wikidata column as an output. The resulting dataset we used for finetuning can be found in [instruction.json](other/instruction.json).
