import requests
import json

client_id = "2760674"
# It's generally recommended to store secrets securely, not directly in code.
# Consider using environment variables or a configuration file.
client_secret = "d9e532ac-287a-4425-84ac-ddfa64b6cf02"

# Endpoint URL for getting the product list (v3)
base_Url = "https://api-seller.ozon.ru/v3/product/list"

def get_product_list(limit=100, last_id="", product_filter=None):
    """
    Fetches a list of products from the Ozon Seller API.

    Args:
        limit (int): Number of items per page (max 1000).
        last_id (str): ID of the last item from the previous page for pagination.
        product_filter (dict, optional): Filter criteria for products. Defaults to None.

    Returns:
        dict: The JSON response from the API containing the product list result,
              or None if the request failed.
    """
    headers = {
        "Client-Id": client_id,
        "Api-Key": client_secret,
        "Content-Type": "application/json"
    }

    # Construct the request body according to the API documentation
    payload = {
        "filter": product_filter if product_filter else {},
        "last_id": last_id,
        "limit": min(limit, 1000) # Ensure limit doesn't exceed 1000
    }

    try:
        response = requests.post(base_Url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        # Optionally log the error details: response.status_code, response.text
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON response.")
        return None

def main():
    print("Attempting to retrieve product list...")
    # Example: Get the first page of products (default limit 100)
    product_data = get_product_list(limit=10) # Requesting only 10 for brevity

    if product_data and 'result' in product_data:
        result = product_data['result']
        items = result.get('items', [])
        total_products = result.get('total', 0)
        last_id = result.get('last_id', '')

        print(f"Successfully retrieved {len(items)} products (Total: {total_products}).")
        print("Product List:")
        if items:
            for item in items:
                # Adjust keys based on the actual fields returned by the API for each item
                # Common identifiers are 'product_id' and 'offer_id'
                product_id = item.get('product_id', 'N/A')
                offer_id = item.get('offer_id', 'N/A')
                print(f"  Product ID: {product_id}, Offer ID: {offer_id}")
        else:
            print("  No products found on this page.")

        if last_id:
            print(f"  Last ID for pagination: {last_id}")
            # Here you could add logic to fetch the next page using this last_id
            # e.g., next_page_data = get_product_list(limit=10, last_id=last_id)
        else:
             print("  This is the last page.")

    else:
        print("Failed to retrieve product list or response format is unexpected.")

if __name__ == "__main__":
    main()