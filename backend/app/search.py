from difflib import SequenceMatcher
import re
from typing import Any, Dict, List, Optional
# Import the fuzzywuzzy library for fuzzy string matching
from fuzzywuzzy import fuzz
from .tdidf import TfidfComparer # Added import


def preprocess_cyrillic(text: str) -> str:
  # Remove all digits and latin letters, keep only cyrillic and spaces
  return re.sub(r'[^а-яА-ЯёЁ\s]', '', text).replace('арт', "").replace("  ", "").strip()

def levenshtein_distance(s1: str, s2: str) -> int:
  """
  Calculate the Levenshtein distance between two strings.
  
  The Levenshtein distance is a metric for measuring the difference between two strings
  by counting the minimum number of single-character operations (insertions, deletions,
  or substitutions) required to change one string into another.
  
  Args:
      s1: First string
      s2: Second string
      
  Returns:
      An integer representing the Levenshtein distance
  """
  if len(s1) < len(s2):
    return levenshtein_distance(s2, s1)

  if len(s2) == 0:
    return len(s1)

  previous_row = range(len(s2) + 1)
  for i, c1 in enumerate(s1):
    current_row = [i + 1]
    for j, c2 in enumerate(s2):
      insertions = previous_row[j + 1] + 1
      deletions = current_row[j] + 1
      substitutions = previous_row[j] + (c1 != c2)
      current_row.append(min(insertions, deletions, substitutions))
    previous_row = current_row

  return previous_row[-1]

def find_most_similar_type(
  data: Dict[str, Any], 
  search_key: str
) -> List[Dict[str, Optional[Any]]]:
  matches: List[Dict[str, Optional[Any]]] = []

  def traverse(node: Any, parent_category_id: Optional[Any] = None) -> None:
    nonlocal matches
    if isinstance(node, dict):
      if "type_name" in node:
        ratio = SequenceMatcher(None, search_key.lower(), node["type_name"].lower()).ratio()
        matches.append({
          "type_name": node["type_name"],
          "description_category_id": parent_category_id,
          "type_id": node.get("type_id"),
          "similarity": ratio
        })
      if "children" in node:
        for child in node["children"]:
          traverse(child, node.get("description_category_id", parent_category_id))
    elif isinstance(node, list):
      for item in node:
        traverse(item, parent_category_id)

  traverse(data["result"], None)

  matches = sorted(matches, key=lambda x: x["similarity"], reverse=True)[:10]
  return matches

def find_most_similar_type_levenshtein(
  data: Dict[str, Any], 
  search_key: str
) -> List[Dict[str, Optional[Any]]]:
  matches: List[Dict[str, Optional[Any]]] = []

  def traverse(node: Any, parent_category_id: Optional[Any] = None) -> None:
    nonlocal matches
    if isinstance(node, dict):
      if "type_name" in node:
        # Calculate Levenshtein distance
        distance = levenshtein_distance(search_key.lower(), node["type_name"].lower())
        
        # Convert distance to similarity score (shorter distance = higher similarity)
        max_len = max(len(search_key), len(node["type_name"]))
        similarity = 1 - (distance / max_len) if max_len > 0 else 0
        
        matches.append({
          "type_name": node["type_name"],
          "description_category_id": parent_category_id,
          "type_id": node.get("type_id"),
          "similarity": similarity
        })
      if "children" in node:
        for child in node["children"]:
          traverse(child, node.get("description_category_id", parent_category_id))
    elif isinstance(node, list):
      for item in node:
        traverse(item, parent_category_id)

  traverse(data["result"], None)

  matches = sorted(matches, key=lambda x: x["similarity"], reverse=True)[:10]
  return matches

def find_most_similar_type_fuzzy(
  data: Dict[str, Any], 
  search_key: str
) -> List[Dict[str, Optional[Any]]]:
  """
  Find the most similar type using fuzzy string matching from the fuzzywuzzy library.
  
  This function uses the token_set_ratio algorithm which is good for cases where
  word order and exact string composition don't matter as much as the actual content.
  
  Args:
      data: The category tree data
      search_key: The search string to find matches for
      
  Returns:
      List of dictionaries containing matches sorted by similarity
  """
  matches: List[Dict[str, Optional[Any]]] = []

  def traverse(node: Any, parent_category_id: Optional[Any] = None) -> None:
    nonlocal matches
    if isinstance(node, dict):
      if "type_name" in node:
        # Use token_set_ratio which handles partial string matches well
        similarity = fuzz.token_set_ratio(search_key.lower(), node["type_name"].lower()) / 100.0
        
        matches.append({
          "type_name": node["type_name"],
          "description_category_id": parent_category_id,
          "type_id": node.get("type_id"),
          "similarity": similarity
        })
      if "children" in node:
        for child in node["children"]:
          traverse(child, node.get("description_category_id", parent_category_id))
    elif isinstance(node, list):
      for item in node:
        traverse(item, parent_category_id)

  traverse(data["result"], None)

  matches = sorted(matches, key=lambda x: x["similarity"], reverse=True)[:10]
  return matches

def find_most_similar_type_tfidf(
  data_tree: Dict[str, Any],
  search_key: str,
  comparer: TfidfComparer
) -> List[Dict[str, Optional[Any]]]:
  """
  Find the most similar type using TF-IDF and cosine similarity.
  
  Args:
      data_tree: The category tree data.
      search_key: The search string (raw, TfidfComparer will preprocess).
      comparer: An instance of TfidfComparer.
      
  Returns:
      List of dictionaries containing matches sorted by similarity.
  """
  matches: List[Dict[str, Optional[Any]]] = []

  # Ensure comparer is usable
  if comparer.vectorizer is None:
      # logging.error("TF-IDF vectorizer not available in find_most_similar_type_tfidf") # Consider adding logging if needed here
      return []

  def traverse(node: Any, parent_category_id: Optional[Any] = None) -> None:
    nonlocal matches
    if isinstance(node, dict):
      if "type_name" in node and node["type_name"]: # Ensure type_name is not empty
        # TfidfComparer.compare_strings handles preprocessing of both search_key and node["type_name"]
        similarity = comparer.compare_strings(search_key, node["type_name"])
        
        matches.append({
          "type_name": node["type_name"],
          "description_category_id": parent_category_id,
          "type_id": node.get("type_id"),
          "similarity": similarity
        })
      if "children" in node:
        for child in node["children"]:
          traverse(child, node.get("description_category_id", parent_category_id))
    elif isinstance(node, list):
      for item in node:
        traverse(item, parent_category_id)

  traverse(data_tree["result"], None)

  matches = sorted(matches, key=lambda x: x["similarity"], reverse=True)[:10]
  return matches
