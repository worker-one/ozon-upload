from time import sleep
import json
import logging

from .config import (
    XML_FILE_PATH, JSON_CATEGORY_TREE_PATH, COUNTER, MAX_SIZE, FEED_OFFSET, KEYWORD_FILTER,
)
from .service import (
    load_category_tree, parse_xml_feed, create_api_payload
)
from .client import OzonApiClient

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI server with Uvicorn.")
    uvicorn.run("backend.app.router:app", host="0.0.0.0", port=8000, reload=True)
