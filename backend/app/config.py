import logging

DEFAULT_CLIENT_ID = "2760674"
DEFAULT_CLIENT_SECRET = "d9e532ac-287a-4425-84ac-ddfa64b6cf02"
API_URL = "https://api-seller.ozon.ru/v3/product/import"
XML_FILE_PATH = "./tmp/feed_example.xml"
JSON_CATEGORY_TREE_PATH = "./data/category_tree.json"

BRAND_ATTRIBUTE_ID = 85
NAME_ATTRIBUTE_ID = 9048
VENDOR_ID = 7236
QUANTIY = 7202
DANGER_CLASS = 9782
QUANTIY_IN_PACK = 8513

COUNTER = 0
MAX_SIZE = 300
SIMILARITY_THRESHOLD = 0.5
BATCH_SIZE = 50
FEED_OFFSET = 19000

# Updated to include Fuzzy as an option
SEARCH_ALGORITHM = "tfidf" # "Fuzzy"  # "Levenshtein" or "SequenceMatcher" or "Fuzzy"
KEYWORD_FILTER = "защита"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Configuration loaded successfully.")
logging.info(f"SIMILARITY_THRESHOLD: {SIMILARITY_THRESHOLD}")
logging.info(f"SEARCH_ALGORITHM: {SEARCH_ALGORITHM}")
