import requests
import json

client_id = "2760674"
# It's generally recommended to store secrets securely, not directly in code.
# Consider using environment variables or a configuration file.
client_secret = "d9e532ac-287a-4425-84ac-ddfa64b6cf02"

# Endpoint URL for getting the product list (v3)
base_Url = "https://api-seller.ozon.ru/v3/product/import"

# Define the headers
headers = {
    "Client-Id": client_id,
    "Api-Key": client_secret,
    "Content-Type": "application/json"
}

# Define the payload data according to the specified format
payload = {
  "items": [
    {   
        "attributes": [
            {
                "id": 7236,
                "complex_id": 0,
                "values": [
                    {
                        "value": "Диск Тормозной (Спереди) Hyundai Creta 15-22 / Ix35 09-15 / Sonata 01-23 / Tucson 04-21 / Kia Optima Sangsin brake арт. SD1005"
                    }
                ]
            },
            {
                "id": 9048,
                "complex_id": 0,
                "values": [
                    {
                        "value": "Диск Тормозной (Спереди) Hyundai Creta 15-22 / Ix35 09-15 / Sonata 01-23 / Tucson 04-21 / Kia Optima Sangsin brake арт. SD1005"
                    }
                ]
            },
            {
                "id": 85,
                "complex_id": 0,
                "values": [
                    {
                        "value": "Sangsin"
                    }
                ]
            }
        ],
        "type_id": 96167, # Example category ID
        "description_category_id": 17028756, # Optional: New category ID if changing
        "currency_code": "RUB", # Currency code
        "name": "Диск Тормозной (Спереди) Hyundai Creta 15-22 / Ix35 09-15 / Sonata 01-23 / Tucson 04-21 / Kia Optima Sangsin brake арт. SD1005", # Product name
        "offer_id": "Sangsin brake_SD1005", # Your unique product identifier
        "price": "3741", # Current price
        "old_price": "3741", # Old price (if applicable)
        #"vat": "0.1", # VAT rate (e.g., "0", "0.1", "0.2")
        "weight": 5, # Weight in kg
        "height": 10, # Height in cm
        "width": 20, # Width in cm
        "length": 30, # Length in cm
        "depth": 10 # Depth in cm
    }
    # Add more items here if needed
  ]
}

# Convert payload to JSON string
payload_json = json.dumps(payload)

try:
    # Send the POST request
    response = requests.post(base_Url, headers=headers, data=payload_json)
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

    # Print the response from the API
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    if response is not None:
        print("Response Text:", response.text)

except json.JSONDecodeError:
    print("Failed to decode JSON response")
    print("Response Text:", response.text)