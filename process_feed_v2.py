from time import sleep
import json
import logging

from app.config import (
    XML_FILE_PATH, JSON_CATEGORY_TREE_PATH, COUNTER, MAX_SIZE
)
from app.service import (
    load_category_tree, parse_xml_feed, create_api_payload
)
from app.client import (
    submit_items_to_ozon, get_task_info
)

def main():
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

    # 3. Parse XML Feed
    xml_categories, xml_offers = parse_xml_feed(XML_FILE_PATH)
    if xml_categories is None or xml_offers is None:
        exit(1)

    logging.info(f"Found {len(xml_categories)} categories and {len(xml_offers)} offers in XML.")

    # 4. Process Offers and Create Payload Items
    items_for_api = []
    counter = COUNTER
    for offer in xml_offers:
        if counter >= MAX_SIZE:
            logging.info("Reached the limit of 450 offers. Stopping processing.")
            break
        if "подвес" in offer.findtext('name').lower():
            item_payload = create_api_payload(offer, category_tree_root)
            if item_payload:
                counter += 1
                items_for_api.append(item_payload)

    logging.info(f"Successfully processed {len(items_for_api)} offers for API submission.")

    # 5. Submit to Ozon API
    task_id = submit_items_to_ozon(items_for_api)
    
    if task_id:
        logging.info(f"Retrieving task information for task_id: {task_id}...")
        sleep(10)
        task_info = get_task_info(task_id)
        if task_info:
            print(json.dumps(task_info, indent=2, ensure_ascii=False))
            total = task_info.get('result', {}).get('total', 0)
            success = 0
            logging.info("Task Info:")
            for item in task_info.get('result', {}).get('items', []):
                if item.get('status') != "imported":
                    logging.warning(f"Item {item.get('offer_id')} status: {item.get('status')}")
                else:
                    success += 1
        else:
            logging.error("Failed to retrieve task information.")

    logging.info("Feed processing finished.")
    logging.info(f"Processed {len(items_for_api)} items.")

# --- Main Execution ---
if __name__ == "__main__":
    main()
