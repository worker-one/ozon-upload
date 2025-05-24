import requests
import json
import xml.etree.ElementTree as ET
import os
import logging

# --- Configuration ---
CLIENT_ID = "2760674"
# Consider using environment variables or a more secure method for secrets
CLIENT_SECRET = "d9e532ac-287a-4425-84ac-ddfa64b6cf02"
API_URL = "https://api-seller.ozon.ru/v3/product/import"
XML_FILE_PATH = "/home/verner/ozon-api/feed_example.xml"
JSON_CATEGORY_TREE_PATH = "/home/verner/ozon-api/category_tree.json" # Assuming this file exists
JSON_CATEGORY_MAPPING_PATH = "/home/verner/ozon-api/category_mapping.json" # Path to the mapping file

# Placeholder Attribute IDs (These might need to be dynamic based on type_id)
# 85: Brand (Vendor)
# 9048: Name (Product Title)
# Other attributes like description might also be needed with specific IDs.
BRAND_ATTRIBUTE_ID = 85
NAME_ATTRIBUTE_ID = 9048
VENDOR_ID = 7236 # This ID is used for the vendor name in the payload
QUANTIY = 7202
DANGER_CLASS = 9782
# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def load_category_tree(filepath):
    """Loads the category tree from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: Category tree file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}")
        return None

def load_category_mapping(filepath):
    """Loads the XML ID to Ozon category mapping from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            mapping_list = json.load(f)
        # Convert list of mappings to a dictionary keyed by xml_id
        mapping_dict = {item['xml_id']: item for item in mapping_list if 'xml_id' in item}
        logging.info(f"Successfully loaded {len(mapping_dict)} category mappings from {filepath}")
        return mapping_dict
    except FileNotFoundError:
        logging.error(f"Error: Category mapping file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}")
        return None
    except Exception as e:
        logging.error(f"Error loading category mapping from {filepath}: {e}")
        return None

def find_ozon_category_ids(target_name, category_node, parent_desc_cat_id=None):
    """
    Recursively searches the category tree for a matching type_name
    and returns (type_id, description_category_id).
    """
    # This function is no longer needed for the primary mapping logic
    # but might be useful for other purposes or future enhancements.
    # Keeping it for now, but it won't be called by create_api_payload.
    current_desc_cat_id = category_node.get("description_category_id", parent_desc_cat_id)

    # Check if the current node is the target type
    if category_node.get("type_name") == target_name and "type_id" in category_node:
        final_desc_cat_id = category_node.get("description_category_id") or parent_desc_cat_id
        if final_desc_cat_id:
             return category_node["type_id"], final_desc_cat_id
        else:
             logging.warning(f"Found type_id {category_node['type_id']} for '{target_name}' but couldn't determine description_category_id.")
             return category_node["type_id"], None

    # Recursively search in children
    if "children" in category_node:
        for child in category_node["children"]:
            result = find_ozon_category_ids(target_name, child, current_desc_cat_id)
            if result and result[0] is not None:  # Check if type_id was found
                return result

    return None, None # Not found in this branch

def parse_xml_feed(filepath):
    """Parses the YML feed and returns categories and offers."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        shop = root.find('shop')
        if shop is None:
            logging.error("Error: <shop> tag not found in XML.")
            return None, None

        # Extract categories: {id: name}
        categories = {}
        categories_element = shop.find('categories')
        if categories_element is not None:
            for category in categories_element.findall('category'):
                cat_id = category.get('id')
                cat_name = category.text
                if cat_id and cat_name:
                    categories[cat_id] = cat_name.strip()

        # Extract offers
        offers_element = shop.find('offers')
        if offers_element is None:
            logging.error("Error: <offers> tag not found in XML.")
            return categories, []

        offers = offers_element.findall('offer')
        return categories, offers

    except ET.ParseError:
        logging.error(f"Error: Could not parse XML file {filepath}")
        return None, None
    except FileNotFoundError:
        logging.error(f"Error: XML file not found at {filepath}")
        return None, None

def create_api_payload(offer, category_mapping, category_tree_root): # category_tree_root is no longer strictly needed here
    """Creates the item payload for the Ozon API from an XML offer using category mapping."""
    offer_data = {}
    try:
        offer_data['id'] = offer.get('id')
        offer_data['price'] = offer.findtext('price')
        offer_data['xml_category_id'] = offer.findtext('categoryId')
        offer_data['picture'] = offer.findtext('picture')
        offer_data['name'] = offer.findtext('name')
        offer_data['vendor'] = offer.findtext('vendor')
        offer_data['vendor_code'] = offer.findtext('vendorCode')
        offer_data['description'] = offer.findtext('description', '') # Use empty string if description is missing
        offer_data['count'] = offer.findtext('count')
        offer_data['dimensions_str'] = offer.findtext('dimensions') # e.g., "40/30/10"
        offer_data['weight_str'] = offer.findtext('weight') # e.g., "0.3"
        
        

        if not all([offer_data['id'], offer_data['price'], offer_data['xml_category_id'], offer_data['name'], offer_data['vendor'], offer_data['vendor_code'], offer_data['count'], offer_data['dimensions_str'], offer_data['weight_str']]):
            logging.warning(f"Offer {offer_data.get('id', 'N/A')} is missing required fields. Skipping.")
            return None

        # --- Category Mapping ---
        mapping_entry = category_mapping.get(offer_data['xml_category_id'])
        description_category_id = None
        type_id = None

        if mapping_entry:
            # Directly use IDs from the mapping file
            type_id = mapping_entry.get('type_id')
            description_category_id = mapping_entry.get('description_category_id')

            # Ozon requires both IDs. If description_category_id is null, try using type_id.
            if description_category_id is None and type_id is not None:
                description_category_id = type_id
                logging.info(f"Offer {offer_data['id']}: description_category_id was null, using type_id ({type_id}) instead.")

            # Validate that both IDs are now present and seem valid (basic check: not None)
            if type_id is None or description_category_id is None:
                logging.warning(f"Offer {offer_data['id']}: Mapping entry for XML category {offer_data['xml_category_id']} is missing 'type_id' ({type_id}) or 'description_category_id' ({description_category_id}). Skipping.")
                return None
            # Optional: Add more validation, e.g., check if they are integers
            try:
                type_id = int(type_id)
                description_category_id = int(description_category_id)
            except (ValueError, TypeError):
                 logging.warning(f"Offer {offer_data['id']}: Invalid non-integer value for type_id ('{mapping_entry.get('type_id')}') or description_category_id ('{mapping_entry.get('description_category_id')}') in mapping for XML category {offer_data['xml_category_id']}. Skipping.")
                 return None
            print(f"Offer Data: {offer_data}")  # Debugging line
        
        else:
            logging.warning(f"Offer {offer_data['id']}: Could not find mapping for XML category ID {offer_data['xml_category_id']} in {JSON_CATEGORY_MAPPING_PATH}. Skipping.")
            return None

        # Ensure both IDs are found before proceeding (redundant check, but safe)
        if not description_category_id or not type_id:
             logging.warning(f"Offer {offer_data['id']}: Failed to determine both description_category_id ({description_category_id}) and type_id ({type_id}) from mapping. Skipping.")
             return None

        logging.info(f"Offer {offer_data['id']}: Using mapping for XML Category ID {offer_data['xml_category_id']} -> type_id={type_id}, desc_cat_id={description_category_id}")

        # --- Parse Dimensions and Weight ---
        try:
            dims = [int(d) for d in offer_data['dimensions_str'].split('/')]
            if len(dims) != 3: raise ValueError("Incorrect number of dimensions")
            length, width, height = dims
            depth = height
            weight_kg = float(offer_data['weight_str'])
        except (ValueError, TypeError) as e:
            logging.warning(f"Offer {offer_data['id']}: Could not parse dimensions '{offer_data['dimensions_str']}' or weight '{offer_data['weight_str']}'. Error: {e}. Skipping.")
            return None

        # --- Construct Item Payload ---
        item = {
            "attributes": [
                {
                    "id": NAME_ATTRIBUTE_ID,
                    "complex_id": 0,
                    "values": [{"value": offer_data['name']}]
                },
                {
                    "id": BRAND_ATTRIBUTE_ID,
                    "complex_id": 0,
                    "values": [{"value": offer_data['vendor']}]
                },
                {
                    "id": VENDOR_ID,
                    "complex_id": 0,
                    "values": [{ "value": offer_data['vendor_code']}
                    ]
                },
                {
                    "id": QUANTIY,
                    "complex_id": 0,
                    "values": [{"value": offer_data['count']}]
                },
                {
                    "id": DANGER_CLASS,
                    "complex_id": 0,
                    "values": [{"value": "0"}]
                }
            ],
            "description_category_id": description_category_id,
            "type_id": type_id,
            "currency_code": "RUB",
            "name": offer_data['name'],
            "offer_id": f"{offer_data['vendor']}_{offer_data["vendor_code"]}",
            "price": offer_data['price'],
            "weight": int(weight_kg * 1000),
            "weight_unit": "g",
            "dimension_unit": "cm",
            "height": height,
            "width": width,
            "length": length,
            "depth": depth,
            "images": [offer_data['picture']] if offer_data['picture'] else [],
            "barcode": offer_data['vendor_code'],
        }
        return item

    except Exception as e:
        logging.error(f"Error processing offer {offer_data.get('id', 'N/A')}: {e}", exc_info=True)
        return None

def submit_items_to_ozon(items):
    """Submits a list of items to the Ozon API."""
    if not items:
        logging.info("No items to submit.")
        return

    headers = {
        "Client-Id": CLIENT_ID,
        "Api-Key": CLIENT_SECRET,
        "Content-Type": "application/json"
    }
    payload = {"items": items}
    payload_json = json.dumps(payload, ensure_ascii=False)

    logging.info(f"Submitting {len(items)} items to Ozon API...")

    try:
        response = requests.post(API_URL, headers=headers, data=payload_json.encode('utf-8'))
        response.raise_for_status()

        logging.info(f"API Response Status Code: {response.status_code}")
        response_data = response.json()
        logging.info(f"API Response JSON: {json.dumps(response_data, indent=2, ensure_ascii=False)}")

        task_id = response_data.get('result', {}).get('task_id')
        if task_id:
            logging.info(f"Import task created with ID: {task_id}. Check status via /v1/product/import/info")
        else:
            logging.warning("Could not find task_id in API response.")

    except requests.exceptions.RequestException as e:
        logging.error(f"API Request Failed: {e}")
        if e.response is not None:
            logging.error(f"Response Status Code: {e.response.status_code}")
            try:
                logging.error(f"Response Body: {e.response.json()}")
            except json.JSONDecodeError:
                logging.error(f"Response Body (non-JSON): {e.response.text}")
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON response from API.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during API submission: {e}", exc_info=True)

# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting feed processing...")

    # 1. Load Category Tree
    category_tree_data = load_category_tree(JSON_CATEGORY_TREE_PATH)
    if not category_tree_data:
        exit(1)

    if isinstance(category_tree_data, list):
         if len(category_tree_data) == 1:
             category_tree_root = category_tree_data[0]
             logging.info("Loaded category tree (list format, using first element as root).")
         else:
             logging.error("Category tree JSON has multiple roots in a list format. Processing logic needs adjustment.")
             exit(1)
    elif isinstance(category_tree_data, dict):
         category_tree_root = category_tree_data
         logging.info("Loaded category tree (dict format).")
    else:
        logging.error("Unknown format for category tree JSON.")
        exit(1)

    # 2. Load Category Mapping
    category_mapping = load_category_mapping(JSON_CATEGORY_MAPPING_PATH)
    if not category_mapping:
        exit(1)

    # 3. Parse XML Feed
    xml_categories, xml_offers = parse_xml_feed(XML_FILE_PATH)
    if xml_categories is None or xml_offers is None:
        exit(1)

    logging.info(f"Found {len(xml_categories)} categories and {len(xml_offers)} offers in XML.")

    # 4. Process Offers and Create Payload Items
    items_for_api = []
    for offer in xml_offers:
        item_payload = create_api_payload(offer, category_mapping, category_tree_root)
        if item_payload:
            items_for_api.append(item_payload)

    logging.info(f"Successfully processed {len(items_for_api)} offers for API submission.")

    # 5. Submit to Ozon API
    submit_items_to_ozon(items_for_api)

    logging.info("Feed processing finished.")
