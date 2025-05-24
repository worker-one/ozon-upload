import json
import xml.etree.ElementTree as ET
import os
import re
import logging
def preprocess_cyrillic(text: str) -> str:
  # Remove all digits and latin letters, keep only cyrillic and spaces
  return re.sub(r'[^а-яА-ЯёЁ\s]', '', text).replace('арт', "").replace("  ", "").strip()


def extract_from_json_recursive(data_node, extracted_texts):
    if isinstance(data_node, dict):
        if 'category_name' in data_node:
            extracted_texts.append(data_node['category_name'])
        if 'type_name' in data_node:
            extracted_texts.append(data_node['type_name'])
        if 'children' in data_node and isinstance(data_node['children'], list):
            for child in data_node['children']:
                extract_from_json_recursive(child, extracted_texts)
    elif isinstance(data_node, list):
        for item in data_node:
            extract_from_json_recursive(item, extracted_texts)

def extract_text_from_json(file_path):
    texts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'result' in data:
            extract_from_json_recursive(data['result'], texts)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {file_path}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
    return texts


def parse_xml_feed(filepath: str):
    # ...existing code from process_feed_v2.py: parse_xml_feed...
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
        names = []
        for offer in offers:
            name = offer.find('name')
            if name is not None and name.text:
                names.append(preprocess_cyrillic(name.text.strip()))
            else:
                logging.warning("Warning: <name> tag not found or empty in offer.")
        return names
    
    except ET.ParseError:
        logging.error(f"Error: Could not parse XML file {filepath}")
        return None, None
    except FileNotFoundError:
        logging.error(f"Error: XML file not found at {filepath}")
        return None, None

def main():
    # Define base directory relative to the script's location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    json_file_path = os.path.join(base_dir, 'data', 'category_tree.json')
    xml_file_path = os.path.join(base_dir, 'data', 'feed_example.xml')
    
    output_dir = os.path.join(base_dir, '..', 'processed_data')
    corpus_file_path = os.path.join(output_dir, 'corpus.txt')

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Ensure data directory and files exist (for local testing)
    # In a real scenario, these files would be provided.
    # For this example, let's assume they exist.
    # os.makedirs(os.path.join(base_dir, '..', 'data'), exist_ok=True)
    # if not os.path.exists(json_file_path):
    #     print(f"Warning: {json_file_path} does not exist. Creating a dummy file.")
    #     # Create a dummy JSON if it doesn't exist for the script to run
    #     dummy_json_content = {"result": [{"category_name": "Dummy Category", "children": [{"type_name": "Dummy Type"}]}]}
    #     with open(json_file_path, 'w', encoding='utf-8') as f_json:
    #         json.dump(dummy_json_content, f_json)

    # if not os.path.exists(xml_file_path):
    #     print(f"Warning: {xml_file_path} does not exist. Creating a dummy file.")
    #     # Create a dummy XML if it doesn't exist
    #     dummy_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    #     <yml_catalog date="2025-05-12T20:03:07+03:00">
    #         <shop>
    #             <name>dummy_shop</name>
    #             <offers>
    #                 <offer id="1"><name>Dummy Product 1</name></offer>
    #             </offers>
    #         </shop>
    #     </yml_catalog>"""
    #     with open(xml_file_path, 'w', encoding='utf-8') as f_xml:
    #         f_xml.write(dummy_xml_content)
            
    json_texts = extract_text_from_json(json_file_path)
    xml_texts = parse_xml_feed(xml_file_path)
    
    corpus = json_texts + xml_texts
    
    # remove duplicates
    corpus = list(set(corpus))
    
    # lower case
    corpus = [text.lower() for text in corpus]
    
    # remove empty strings
    corpus = [text for text in corpus if text]
    
    if not corpus:
        print("No text could be extracted. Corpus is empty.")
        return

    with open(corpus_file_path, 'w', encoding='utf-8') as f:
        for line in corpus:
            f.write(line + '\n')
            
    print(f"Corpus successfully created with {len(corpus)} documents.")
    print(f"Corpus saved to: {corpus_file_path}")

if __name__ == '__main__':
    main()
