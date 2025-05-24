import json
from sentence_transformers import SentenceTransformer, util

with open("category_tree.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    
"""
{
  "result": [
    {
      "description_category_id": 17027495,
      "category_name": "Автотовары",
      "disabled": false,
      "children": [
        {
          "description_category_id": 200001532,
          "category_name": "Запчасти для грузовых автомобилей и спецтехники",
          "disabled": false,
          "children": [
            {
              "type_name": "Ремкомплект гидроцилиндра",
              "type_id": 971093558,
              "disabled": false,
              "children": []
            },
            {
              "type_name": "Ремкомплект рулевой рейки",
              "type_id": 971093559,
              "disabled": false,
              "children": []
            }
        ]

        }
        ]
...
"""

search_key = "Подшипник 17/40/12, Шариковый GMB арт. 6203-2RS"

def find_most_similar_type(data, search_key):
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    search_emb = model.encode(search_key, convert_to_tensor=True)

    candidates = []

    def traverse(node, parent_category_id=None):
        if isinstance(node, dict):
            if "type_name" in node:
                candidates.append({
                    "type_name": node["type_name"],
                    "description_category_id": parent_category_id,
                    "type_id": node.get("type_id")
                })
            if "children" in node:
                for child in node["children"]:
                    traverse(child, node.get("description_category_id", parent_category_id))
        elif isinstance(node, list):
            for item in node:
                traverse(item, parent_category_id)

    traverse(data["result"], None)

    type_names = [c["type_name"] for c in candidates]
    type_embs = model.encode(type_names, convert_to_tensor=True)
    similarities = util.cos_sim(search_emb, type_embs)[0]

    # Get the top 5 most similar entries
    top_indices = similarities.topk(5).indices.tolist()
    
    top_matches = []
    for idx in top_indices:
        match = candidates[idx]
        match["similarity"] = float(similarities[idx])
        top_matches.append(match)

    return top_matches

result = find_most_similar_type(data, search_key)
print(result)
