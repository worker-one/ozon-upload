import json
import logging
import xml.etree.ElementTree as ET
import uuid
import urllib.parse
from .config import (
    BRAND_ATTRIBUTE_ID, NAME_ATTRIBUTE_ID, VENDOR_ID, QUANTIY, DANGER_CLASS, QUANTIY_IN_PACK,
    SIMILARITY_THRESHOLD, SEARCH_ALGORITHM
)

from .tdidf import TfidfComparer

tfidf_comparer = TfidfComparer()

# Store pending interactive decisions for web UI
pending_interactive_decisions = {}

def load_category_tree(filepath):
    # ...existing code from process_feed_v2.py: load_category_tree...
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: Category tree file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}")
        return None

def download_xml_feed(url: str, filepath: str):
    # ...existing code from process_feed_v2.py: download_xml_feed...
    import requests
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Check if it is tar file
        with open(filepath, 'w') as f:
            f.write(response.content.decode('utf-8'))
        logging.info(f"XML feed downloaded successfully to {filepath}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading XML feed: {e}")

def parse_xml_feed(filepath: str):
    # ...existing code from process_feed_v2.py: parse_xml_feed...
    logging.info(f"Parsing XML feed from {filepath}")
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        shop = root.find('shop')
        if shop is None:
            logging.error("Error: <shop> tag not found in XML.")
            return None, None

        categories = {}
        categories_element = shop.find('categories')
        if categories_element is not None:
            for category in categories_element.findall('category'):
                cat_id = category.get('id')
                cat_name = category.text
                if cat_id and cat_name:
                    categories[cat_id] = cat_name.strip()

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

def interactive_category_decision(original_offer_xml, offer_data, top_result, type_id, description_category_id, similarity, search_results=None, web_callback=None):
    # If web_callback is provided, use it for web-based interaction
    if web_callback:
        # Create a URL-safe decision ID using offer ID and a unique suffix
        base_id = offer_data.get('id', 'unknown')
        # Replace problematic characters that might cause URL issues
        safe_base_id = urllib.parse.quote(str(base_id), safe='')
        # Add a short UUID suffix to ensure uniqueness
        unique_suffix = str(uuid.uuid4())[:8]
        decision_id = f"{safe_base_id}_{unique_suffix}"
        
        pending_interactive_decisions[decision_id] = {
            "original_offer_xml": original_offer_xml, # Store the XML element
            "offer_data_dict": offer_data,
            "top_result": top_result,
            "type_id": type_id,
            "description_category_id": description_category_id,
            "similarity": similarity,
            "search_results": search_results
        }
        logging.info(f"Created interactive decision with ID: {decision_id} for offer: {offer_data.get('id')}")
        return "WAITING_FOR_USER", decision_id

    print(f"\nOffer Name: {offer_data['name']}")
    print("Top 5 suggested categories:")
    options = []
    if search_results is None:
        options = [top_result]
    else:
        options = search_results[:5]
    for idx, res in enumerate(options, 1):
        print(f"{idx} type_name: {res.get('type_name')}, similarity: {res.get('similarity', 0):.2f}")
    print("0. Enter custom values")
    print("s. Skip this offer")

    while True:
        user_input = input("Choose an option (1-5, 0 for custom, s to skip): ")


        if user_input == 's':
            logging.warning(f"Offer {offer_data['id']}: User skipped category selection. Skipping.")
            return None, None
        elif user_input == '0':
            try:
                new_type_id = input("Enter new type_id: ")
                type_id = int(new_type_id)
                new_description_category_id = input("Enter new description_category_id: ")
                description_category_id = int(new_description_category_id)
                return type_id, description_category_id
            except ValueError:
                print("Invalid input. Please enter integer values for type_id and description_category_id.")
        elif user_input in {'1', '2', '3', '4', '5'}:
            idx = int(user_input) - 1
            if 0 <= idx < len(options):
                sel = options[idx]
                try:
                    type_id = int(sel.get('type_id'))
                    description_category_id = int(sel.get('description_category_id') or sel.get('type_id'))
                    return type_id, description_category_id
                except (ValueError, TypeError):
                    print("Invalid type_id or description_category_id in selected option. Try another.")
            else:
                print("Invalid selection. Try again.")
        else:
            print("Invalid input. Try again.")

def create_api_payload(offer, category_tree_root, web_callback=None, chosen_type_id=None, chosen_description_category_id=None):
    # ...existing code from process_feed_v2.py: create_api_payload...
    # Note: You may need to import find_most_similar_type, preprocess_cyrillic from their module.
    from .search import find_most_similar_type, find_most_similar_type_levenshtein, preprocess_cyrillic, find_most_similar_type_fuzzy, find_most_similar_type_tfidf
    from .tdidf import TfidfComparer

    offer_data = {}
    try:
        offer_data['id'] = offer.get('id')
        offer_data['price'] = offer.findtext('price')
        offer_data['xml_category_id'] = offer.findtext('categoryId')
        offer_data['picture'] = offer.findtext('picture')
        offer_data['name'] = offer.findtext('name')
        offer_data['vendor'] = offer.findtext('vendor')
        offer_data['vendor_code'] = offer.findtext('vendorCode')
        offer_data['description'] = offer.findtext('description', '')
        offer_data['count'] = offer.findtext('count')
        offer_data['dimensions_str'] = offer.findtext('dimensions')
        offer_data['weight_str'] = offer.findtext('weight')

        if not all([offer_data['id'], offer_data['price'], offer_data['xml_category_id'], offer_data['name'], offer_data['vendor'], offer_data['vendor_code'], offer_data['count'], offer_data['dimensions_str'], offer_data['weight_str']]):
            logging.warning(f"Offer {offer_data.get('id', 'N/A')} is missing required fields. Skipping.")
            return None

        final_type_id = None
        final_description_category_id = None

        if chosen_type_id is not None or chosen_description_category_id is not None:
            logging.info(f"Offer {offer_data['id']}: Received chosen_type_id='{chosen_type_id}', chosen_description_category_id='{chosen_description_category_id}' from prior interaction.")
            try:
                if chosen_type_id is None and chosen_description_category_id is None:
                    logging.info(f"Offer {offer_data['id']}: User chose to skip this offer via web interaction.")
                    return None

                temp_type_id = int(chosen_type_id) if chosen_type_id is not None else None
                temp_desc_cat_id = int(chosen_description_category_id) if chosen_description_category_id is not None else None

                if temp_type_id is None or temp_desc_cat_id is None:
                    logging.warning(f"Offer {offer_data['id']}: Incomplete category IDs from web interaction (type_id: {temp_type_id}, desc_cat_id: {temp_desc_cat_id}). Skipping.")
                    return None
                
                final_type_id = temp_type_id
                final_description_category_id = temp_desc_cat_id
                logging.info(f"Offer {offer_data['id']}: Using pre-selected type_id={final_type_id}, description_category_id={final_description_category_id}.")

            except (ValueError, TypeError) as e:
                logging.warning(f"Offer {offer_data['id']}: Invalid category IDs '{chosen_type_id}', '{chosen_description_category_id}' from web interaction. Error: {e}. Skipping.")
                return None
        else:
            # Determine search name and execute search
            search_results = []
            name_used_for_search = ""

            if SEARCH_ALGORITHM == "tfidf":
                name_used_for_search = offer_data['name'] # Raw name for TF-IDF
                if not tfidf_comparer.vectorizer:
                    logging.error(f"Offer {offer_data['id']}: TF-IDF vectorizer not loaded. Cannot use TF-IDF search.")
                    # search_results remains empty, will be handled by subsequent logic
                else:
                    search_results = find_most_similar_type_tfidf(category_tree_root, name_used_for_search, tfidf_comparer)
            else:
                name_used_for_search = preprocess_cyrillic(offer_data['name'])
                if SEARCH_ALGORITHM == "Levenshtein":
                    search_results = find_most_similar_type_levenshtein(category_tree_root, name_used_for_search)
                elif SEARCH_ALGORITHM == "Fuzzy":
                    search_results = find_most_similar_type_fuzzy(category_tree_root, name_used_for_search)
                else: # Default SequenceMatcher
                    search_results = find_most_similar_type(category_tree_root, name_used_for_search)
            
            #logging.info(f"Offer {offer_data['id']}: Using '{SEARCH_ALGORITHM}' with name for search: '{name_used_for_search}'")

            if search_results and len(search_results) > 0:
                top_result = search_results[0]
                type_id_from_search = top_result.get('type_id')
                desc_cat_id_from_search = top_result.get('description_category_id')
                similarity = top_result.get('similarity', 0)

                if desc_cat_id_from_search is None and type_id_from_search is not None:
                    desc_cat_id_from_search = type_id_from_search
                    logging.info(f"Offer {offer_data['id']}: description_category_id was null from search, using type_id ({type_id_from_search}) instead.")
                
                try:
                    type_id_from_search = int(type_id_from_search) if type_id_from_search is not None else None
                    desc_cat_id_from_search = int(desc_cat_id_from_search) if desc_cat_id_from_search is not None else None
                except (ValueError, TypeError):
                    logging.warning(f"Offer {offer_data['id']}: Invalid non-integer value for type_id ('{type_id_from_search}') or description_category_id ('{desc_cat_id_from_search}') from search. Skipping.")
                    return None

                if type_id_from_search is None or desc_cat_id_from_search is None:
                    logging.warning(f"Offer {offer_data['id']}: Search returned invalid/incomplete category IDs. Skipping.")
                    return None

                logging.info(f"Offer {offer_data['name'][:40]}... ->'{top_result['type_name']}' (sim={similarity:.2f})")

                if similarity < SIMILARITY_THRESHOLD:
                    result = interactive_category_decision(
                        offer, # Pass the original XML offer element
                        offer_data, 
                        top_result, 
                        type_id_from_search, 
                        desc_cat_id_from_search, 
                        similarity, 
                        search_results, 
                        web_callback=web_callback
                    )
                    if isinstance(result, tuple) and result[0] == "WAITING_FOR_USER":
                        return {"interactive_decision_id": result[1]}
                    
                    # Result from console interaction
                    final_type_id, final_description_category_id = result
                    if final_type_id is None or final_description_category_id is None: # User skipped in console mode
                        return None
                else:
                    final_type_id = type_id_from_search
                    final_description_category_id = desc_cat_id_from_search
            else:
                logging.warning(f"Offer {offer_data['id']}: Could not find a similar type_name for '{offer_data['name']}'. Skipping.")
                return None

        if final_type_id is None or final_description_category_id is None:
            logging.warning(f"Offer {offer_data['id']}: Failed to determine category IDs (final_type_id={final_type_id}, final_desc_cat_id={final_description_category_id}). Skipping.")
            return None

        try:
            # Ensure they are integers before use
            final_type_id = int(final_type_id)
            final_description_category_id = int(final_description_category_id)
        except (ValueError, TypeError) as e:
            logging.error(f"Offer {offer_data['id']}: final_type_id ('{final_type_id}') or final_description_category_id ('{final_description_category_id}') are not valid integers before use. Error: {e}. Skipping.")
            return None
            
        # The rest of the original create_api_payload logic, using final_type_id and final_description_category_id
        # ... (code for dimensions, weight, name truncation) ...
        try:
            dims = [int(d) for d in offer_data['dimensions_str'].split('/')]
            if len(dims) != 3: raise ValueError("Incorrect number of dimensions")
            length, width, height = dims
            depth = height
            weight_kg = float(offer_data['weight_str'])
        except (ValueError, TypeError) as e:
            #logging.warning(f"Offer {offer_data['id']}: Could not parse dimensions '{offer_data['dimensions_str']}' or weight '{offer_data['weight_str']}'. Error: {e}. Skipping.")
            return None

        offer_name = offer_data['name']
        if "арт." in offer_name:
            offer_name = offer_name.split("арт.")[0].strip()
        if len(offer_name) > 80:
            last_slash = offer_name.rfind('/')
            if last_slash != -1:
                offer_name = offer_name[:last_slash].strip()
                #logging.warning(f"Offer {offer_data['id']}: Offer name truncated to 80 characters: '{offer_name}'")
        if len(offer_name) > 80:
            last_slash = offer_name.rfind('/')
            if last_slash != -1:
                offer_name = offer_name[:last_slash].strip()
                #logging.warning(f"Offer {offer_data['id']}: Offer name truncated to 80 characters: '{offer_name}'")
        if len(offer_name) > 80:
            offer_name = offer_name[:80].strip()
            #logging.warning(f"Offer {offer_data['id']}: Offer name truncated to 80 characters: '{offer_name}'")

        item = {
            "attributes": [
                {
                    "id": NAME_ATTRIBUTE_ID,
                    "complex_id": 0,
                    "values": [{"value": offer_name}]
                },
                {
                    "id": BRAND_ATTRIBUTE_ID,
                    "complex_id": 0,
                    "values": [{"value": offer_data['vendor']}]
                },
                {
                    "id": VENDOR_ID,
                    "complex_id": 0,
                    "values": [{ "value": offer_data['vendor_code']}]
                },
                {
                    "id": QUANTIY,
                    "complex_id": 0,
                    "values": [{"value": offer_data['count']}]
                }
                # {
                #     "id": DANGER_CLASS,
                #     "complex_id": 0,
                #     "values": [{"value": "0"}]
                # },
                # {
                #     "id": QUANTIY_IN_PACK,
                #     "complex_id": 0,
                #     "values": [{"value": "1"}]
                # }
            ],
            "description_category_id": final_description_category_id,
            "type_id": final_type_id,
            "currency_code": "RUB",
            "name": offer_name,
            "offer_id": f"{offer_data['vendor']}_{offer_data['vendor_code']}",
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
