import requests
import json

client_id = "2760674"
# It's generally recommended to store secrets securely, not directly in code.
# Consider using environment variables or a configuration file.
client_secret = "d9e532ac-287a-4425-84ac-ddfa64b6cf02"

base_url = "https://api-seller.ozon.ru/v1/description-category/tree"

def get_category_tree(lang: str):
    """
    Fetches the category tree from the Ozon Seller API.

    Args:
        lang (str): Language code for the response (e.g., 'ru', 'en').

    Returns:
        dict: The JSON response from the API containing the category tree,
              or None if the request failed.
    """
    headers = {
        "Client-Id": client_id,
        "Api-Key": client_secret,
        "Content-Type": "application/json"
    }

    params = {
        "language": lang
    }

    try:
        response = requests.post(base_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON response.")
        return None
    
print("Attempting to retrieve category tree...")
lang = "RU"  # Example language code
category_tree_data = get_category_tree(lang)

if category_tree_data:
    print("Category Tree Data:")
    # Save as JSON file
    with open("category_tree.json", "w", encoding="utf-8") as f:
        json.dump(category_tree_data, f, ensure_ascii=False, indent=4)
else:
    print("Failed to retrieve category tree data.")
