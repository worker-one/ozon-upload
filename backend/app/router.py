import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

from .config import (
    XML_FILE_PATH, JSON_CATEGORY_TREE_PATH, MAX_SIZE, FEED_OFFSET, KEYWORD_FILTER, SEARCH_ALGORITHM,
    DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET
)
from .service import (
    load_category_tree, parse_xml_feed, create_api_payload, download_xml_feed,
    pending_interactive_decisions as service_pending_decisions,
    tfidf_comparer
)
from .client import OzonApiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ozon Upload API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_STATE = {
    "ozon_client": None,
    "category_tree_root": None,
    "all_xml_offers": [],
    "feed_offset": FEED_OFFSET,
    "keyword_filter": KEYWORD_FILTER,
    "max_size": MAX_SIZE,
    "current_offer_idx_in_all_xml": 0,
    "processed_item_count_for_api": 0,
    "items_for_api": [],
    "pending_decision_id": None,
    "status_message": "Ожидание",
    "ozon_submission_task_id": None,
    "ozon_task_info": None,
    "is_initialized": False,
    "error_message": None,
    "current_xml_file_path": None,
    "client_id": None,
    "client_secret": None,
}

class StartProcessingRequest(BaseModel):
    client_id: str
    client_secret: str
    feed_url: Optional[str] = None
    feed_offset: Optional[int] = None
    max_items: Optional[int] = None
    keyword: Optional[str] = None

class DecisionPayload(BaseModel):
    chosen_type_id: int
    chosen_description_category_id: int

class OfferSuggestion(BaseModel):
    type_id: int
    description_category_id: Optional[int] = None
    type_name: str
    similarity: Optional[float] = None

class OfferDetailsForDecision(BaseModel):
    offer_id: str
    name: str
    suggestions: List[OfferSuggestion]
    current_similarity: float

class ProcessingStatusResponse(BaseModel):
    status_message: str
    pending_decision_id: Optional[str] = None
    decision_details: Optional[OfferDetailsForDecision] = None
    processed_item_count_for_api: int
    total_offers_to_consider: int
    current_offer_index_overall: int
    items_ready_for_submission: int
    ozon_submission_task_id: Optional[str] = None
    ozon_task_info: Optional[Any] = None
    error_message: Optional[str] = None

def ensure_tfidf_initialized_if_needed(category_tree_root_data):
    if SEARCH_ALGORITHM == "tfidf" and hasattr(tfidf_comparer, "is_ready") and not tfidf_comparer.is_ready():
        all_type_names = []
        def extract_names(node):
            if isinstance(node, dict):
                if 'type_name' in node and node['type_name']:
                    all_type_names.append(node['type_name'])
                if 'children' in node and isinstance(node['children'], list):
                    for child in node['children']:
                        extract_names(child)
            elif isinstance(node, list):
                for item in node:
                    extract_names(item)
        extract_names(category_tree_root_data)
        if all_type_names:
            tfidf_comparer.fit(all_type_names)

def _reset_session_state():
    logger.info("Resetting session state.")
    service_pending_decisions.clear()

    APP_STATE["ozon_client"] = None # Will be re-created by start-processing
    APP_STATE["all_xml_offers"] = []
    APP_STATE["feed_offset"] = FEED_OFFSET # Reset to default
    APP_STATE["keyword_filter"] = KEYWORD_FILTER # Reset to default
    APP_STATE["max_size"] = MAX_SIZE # Reset to default
    APP_STATE["current_offer_idx_in_all_xml"] = 0
    APP_STATE["processed_item_count_for_api"] = 0
    APP_STATE["items_for_api"] = []
    APP_STATE["pending_decision_id"] = None
    APP_STATE["status_message"] = "Сессия сброшена. Готово к новой конфигурации."
    APP_STATE["ozon_submission_task_id"] = None
    APP_STATE["ozon_task_info"] = None
    APP_STATE["is_initialized"] = False # Crucial: requires new /start-processing
    APP_STATE["error_message"] = None
    APP_STATE["current_xml_file_path"] = XML_FILE_PATH # Reset to default
    APP_STATE["client_id"] = None # Will be set by next /start-processing
    APP_STATE["client_secret"] = None # Will be set by next /start-processing
    # Category tree and TF-IDF model (if loaded) persist globally

def _initialize_state(client_id: str, client_secret: str, feed_url: Optional[str] = None):
    # Store credentials for Ozon client
    APP_STATE["client_id"] = client_id
    APP_STATE["client_secret"] = client_secret
    APP_STATE["ozon_client"] = OzonApiClient(client_id=client_id, client_secret=client_secret)
    
    APP_STATE["category_tree_root"] = load_category_tree(JSON_CATEGORY_TREE_PATH)
    if not APP_STATE["category_tree_root"]:
        APP_STATE["status_message"] = "Ошибка: Не удалось загрузить дерево категорий."
        APP_STATE["error_message"] = "Не удалось загрузить дерево категорий."
        APP_STATE["is_initialized"] = False
        return False
    
    ensure_tfidf_initialized_if_needed(APP_STATE["category_tree_root"])
    
    # Determine XML file path
    xml_file_path = XML_FILE_PATH
    if feed_url:
        logger.info(f"Downloading XML feed from URL: {feed_url}")
        try:
            download_xml_feed(feed_url, XML_FILE_PATH)
            APP_STATE["current_xml_file_path"] = xml_file_path
        except Exception as e:
            APP_STATE["status_message"] = f"Ошибка: {str(e)}"
            APP_STATE["error_message"] = str(e)
            APP_STATE["is_initialized"] = False
            return False
    
    _, xml_offers = parse_xml_feed(XML_FILE_PATH)
    if xml_offers is None:
        APP_STATE["status_message"] = "Ошибка: Не удалось разобрать XML фид."
        APP_STATE["error_message"] = "Не удалось разобрать XML фид."
        APP_STATE["is_initialized"] = False
        return False
    
    APP_STATE["all_xml_offers"] = xml_offers
    APP_STATE["items_for_api"] = []
    APP_STATE["current_offer_idx_in_all_xml"] = APP_STATE["feed_offset"]
    APP_STATE["processed_item_count_for_api"] = 0
    APP_STATE["pending_decision_id"] = None
    APP_STATE["status_message"] = "Инициализировано. Готово к обработке."
    APP_STATE["ozon_submission_task_id"] = None
    APP_STATE["ozon_task_info"] = None
    APP_STATE["is_initialized"] = True
    APP_STATE["error_message"] = None
    return True

def _get_decision_details(decision_id: str) -> Optional[OfferDetailsForDecision]:
    if decision_id in service_pending_decisions:
        data = service_pending_decisions[decision_id]
        suggestions = []
        raw_suggestions = data.get("search_results", [])
        if not raw_suggestions and data.get("top_result"):
            raw_suggestions = [data.get("top_result")]
        for s_item in raw_suggestions[:5]:
            if s_item:
                suggestions.append(OfferSuggestion(
                    type_id=s_item.get('type_id'),
                    description_category_id=s_item.get('description_category_id', s_item.get('type_id')),
                    type_name=s_item.get('type_name', "Unknown Type Name"),
                    similarity=s_item.get('similarity')
                ))
        return OfferDetailsForDecision(
            offer_id=data["offer_data_dict"]["id"],
            name=data["offer_data_dict"]["name"],
            suggestions=suggestions,
            current_similarity=data["similarity"]
        )
    return None

def _trigger_next_step():
    if not APP_STATE["is_initialized"]:
        APP_STATE["status_message"] = "Ошибка: Система не инициализирована."
        APP_STATE["error_message"] = "Система не инициализирована. Сначала вызовите /start-processing."
        return
    if APP_STATE["pending_decision_id"]:
        APP_STATE["status_message"] = f"Ожидается решение для товара ID: {APP_STATE['pending_decision_id']}"
        return
    if APP_STATE["processed_item_count_for_api"] >= APP_STATE["max_size"]:
        APP_STATE["status_message"] = f"Достигнуто максимальное количество товаров ({APP_STATE['max_size']}). Готово к отправке."
        return
    
    # Use iterative approach instead of recursive to avoid stack overflow
    while (APP_STATE["current_offer_idx_in_all_xml"] < len(APP_STATE["all_xml_offers"]) and 
           APP_STATE["processed_item_count_for_api"] < APP_STATE["max_size"] and 
           not APP_STATE["pending_decision_id"]):
        
        offer_xml_element = APP_STATE["all_xml_offers"][APP_STATE["current_offer_idx_in_all_xml"]]
        
        # Apply keyword filter
        if APP_STATE["keyword_filter"]:
            offer_name_element = offer_xml_element.find('name')
            if offer_name_element is None or APP_STATE["keyword_filter"].lower() not in offer_name_element.text.lower():
                APP_STATE["current_offer_idx_in_all_xml"] += 1
                continue  # Skip this offer and continue to next iteration
        
        item_payload_or_decision = create_api_payload(
            offer=offer_xml_element,
            category_tree_root=APP_STATE["category_tree_root"],
            web_callback=True
        )
        
        if item_payload_or_decision is None:
            APP_STATE["current_offer_idx_in_all_xml"] += 1
            continue  # Skip this offer and continue to next iteration
        
        if isinstance(item_payload_or_decision, dict) and "interactive_decision_id" in item_payload_or_decision:
            decision_id = item_payload_or_decision["interactive_decision_id"]
            APP_STATE["pending_decision_id"] = decision_id
            APP_STATE["status_message"] = f"Ожидается решение для товара ID: {decision_id}"
            return  # Stop processing and wait for decision
        
        # Successfully processed offer
        APP_STATE["items_for_api"].append(item_payload_or_decision)
        APP_STATE["processed_item_count_for_api"] += 1
        APP_STATE["current_offer_idx_in_all_xml"] += 1
        APP_STATE["status_message"] = f"Товар обработан. Всего товаров для API: {APP_STATE['processed_item_count_for_api']}"
    
    # Set final status message based on why we exited the loop
    if APP_STATE["processed_item_count_for_api"] >= APP_STATE["max_size"]:
        APP_STATE["status_message"] = f"Достигнуто максимальное количество товаров ({APP_STATE['max_size']}). Готово к отправке."
    elif APP_STATE["current_offer_idx_in_all_xml"] >= len(APP_STATE["all_xml_offers"]):
        APP_STATE["status_message"] = "Все товары из фида рассмотрены. Готово к отправке."

@app.post("/start-processing", response_model=ProcessingStatusResponse)
async def start_processing(request_params: StartProcessingRequest):
    # Update state with new parameters
    APP_STATE["feed_offset"] = request_params.feed_offset if request_params.feed_offset is not None else FEED_OFFSET
    APP_STATE["max_size"] = request_params.max_items if request_params.max_items is not None else MAX_SIZE
    APP_STATE["keyword_filter"] = request_params.keyword if request_params.keyword else KEYWORD_FILTER
    
    # # If url to feed is provided, download it
    # if request_params.feed_url:
    #     if not request_params.feed_url.startswith("http"):
    #         raise HTTPException(status_code=400, detail="Некорректный URL фида. Должен начинаться с 'http' или 'https'.")
    #     APP_STATE["current_xml_file_path"] = None
    #     logger.info(f"Downloading XML feed from URL: {request_params.feed_url}")
    #     if not download_xml_feed(request_params.feed_url):
    #         APP_STATE["status_message"] = "Ошибка: Не удалось загрузить XML фид."
    #         APP_STATE["error_message"] = "Не удалось загрузить XML фид по указанному URL."
    #         raise HTTPException(status_code=500, detail=APP_STATE["error_message"])
    # else:
    #     # Use default XML file path if no feed URL is provided
    #     APP_STATE["current_xml_file_path"] = XML_FILE_PATH
    
    if not _initialize_state(
        client_id=request_params.client_id,
        client_secret=request_params.client_secret,
        feed_url=request_params.feed_url
    ):
        raise HTTPException(status_code=500, detail=APP_STATE["error_message"] or "Ошибка инициализации.")
    
    _trigger_next_step()
    return get_processing_status()

@app.get("/processing-status", response_model=ProcessingStatusResponse)
async def get_processing_status_endpoint():
    return get_processing_status()

def get_processing_status():
    decision_details_obj = None
    if APP_STATE["pending_decision_id"]:
        decision_details_obj = _get_decision_details(APP_STATE["pending_decision_id"])
    total_offers_in_xml = len(APP_STATE.get("all_xml_offers", []))
    offers_after_offset = 0
    if total_offers_in_xml > 0:
        offers_after_offset = total_offers_in_xml - APP_STATE["feed_offset"]
        offers_after_offset = max(0, offers_after_offset)
    return ProcessingStatusResponse(
        status_message=APP_STATE["status_message"],
        pending_decision_id=APP_STATE["pending_decision_id"],
        decision_details=decision_details_obj,
        processed_item_count_for_api=APP_STATE["processed_item_count_for_api"],
        total_offers_to_consider=offers_after_offset,
        current_offer_index_overall=APP_STATE["current_offer_idx_in_all_xml"],
        items_ready_for_submission=len(APP_STATE["items_for_api"]),
        ozon_submission_task_id=APP_STATE["ozon_submission_task_id"],
        ozon_task_info=APP_STATE["ozon_task_info"],
        error_message=APP_STATE["error_message"]
    )

@app.post("/reset-session-state", response_model=ProcessingStatusResponse)
async def reset_session_state_endpoint():
    _reset_session_state()
    return get_processing_status()

@app.post("/submit-decision/{decision_id:path}", response_model=ProcessingStatusResponse)
async def submit_decision(decision_id: str, payload: DecisionPayload):
    logger.info(f"Received submit-decision request for decision_id: '{decision_id}'")
    logger.info(f"Current pending decisions: {list(service_pending_decisions.keys())}")
    
    if not APP_STATE["is_initialized"]:
        raise HTTPException(status_code=400, detail="Система не инициализирована.")
    if APP_STATE["pending_decision_id"] != decision_id:
        logger.warning(f"Decision ID mismatch. Expected: '{APP_STATE['pending_decision_id']}', Received: '{decision_id}'")
        raise HTTPException(status_code=400, detail="Несоответствие ID решения или нет ожидающего решения.")
    if decision_id not in service_pending_decisions:
        logger.error(f"Decision ID '{decision_id}' not found in pending decisions. Available: {list(service_pending_decisions.keys())}")
        raise HTTPException(status_code=404, detail="Контекст решения не найден в сервисе.")
    
    decision_context = service_pending_decisions.pop(decision_id)
    original_offer_xml = decision_context["original_offer_xml"]
    
    # Ensure description_category_id has a fallback to type_id if not provided
    description_category_id = payload.chosen_description_category_id
    if description_category_id is None:
        description_category_id = payload.chosen_type_id
    
    logger.info(f"Processing decision for offer: {decision_context['offer_data_dict'].get('id')} with type_id: {payload.chosen_type_id}, desc_cat_id: {description_category_id}")
    
    item_payload = create_api_payload(
        offer=original_offer_xml,
        category_tree_root=APP_STATE["category_tree_root"],
        web_callback=False,
        chosen_type_id=payload.chosen_type_id,
        chosen_description_category_id=description_category_id
    )
    
    APP_STATE["pending_decision_id"] = None
    
    if item_payload:
        APP_STATE["items_for_api"].append(item_payload)
        APP_STATE["processed_item_count_for_api"] += 1
        logger.info(f"Successfully processed decision. Items ready: {len(APP_STATE['items_for_api'])}")
    
    APP_STATE["current_offer_idx_in_all_xml"] += 1
    _trigger_next_step()
    return get_processing_status()

@app.post("/skip-offer/{decision_id:path}", response_model=ProcessingStatusResponse)
async def skip_offer(decision_id: str):
    logger.info(f"Received skip-offer request for decision_id: '{decision_id}'")
    
    if not APP_STATE["is_initialized"]:
        raise HTTPException(status_code=400, detail="Система не инициализирована.")
    if APP_STATE["pending_decision_id"] != decision_id:
        logger.warning(f"Decision ID mismatch for skip. Expected: '{APP_STATE['pending_decision_id']}', Received: '{decision_id}'")
        raise HTTPException(status_code=400, detail="Несоответствие ID решения или нет ожидающего решения для пропуска.")
    if decision_id in service_pending_decisions:
        service_pending_decisions.pop(decision_id)
        logger.info(f"Skipped offer with decision_id: '{decision_id}'")
    
    APP_STATE["pending_decision_id"] = None
    APP_STATE["current_offer_idx_in_all_xml"] += 1
    _trigger_next_step()
    return get_processing_status()

@app.post("/submit-to-ozon")
async def submit_to_ozon_api():
    if not APP_STATE["is_initialized"]:
        raise HTTPException(status_code=400, detail="Система не инициализирована.")
    if APP_STATE["pending_decision_id"]:
        raise HTTPException(status_code=400, detail="Невозможно отправить, товар ожидает решения.")
    if not APP_STATE["items_for_api"]:
        return {"message": "Нет товаров для отправки.", "task_id": None}
    
    # Ensure client is initialized with current credentials
    if not APP_STATE["ozon_client"] or not APP_STATE["client_id"] or not APP_STATE["client_secret"]:
        raise HTTPException(status_code=400, detail="Клиент Ozon не инициализирован.")
    
    task_id = APP_STATE["ozon_client"].submit_items(APP_STATE["items_for_api"])
    # Convert task_id to string to match Pydantic model expectations
    APP_STATE["ozon_submission_task_id"] = str(task_id) if task_id is not None else None
    if task_id:
        APP_STATE["status_message"] = f"Отправлено в Ozon. ID задачи: {task_id}"
    else:
        APP_STATE["status_message"] = "Не удалось отправить в Ozon."
        APP_STATE["error_message"] = "Не удалось получить task_id от отправки в Ozon."
        raise HTTPException(status_code=500, detail="Не удалось отправить в Ozon или получить ID задачи.")
    return {"task_id": str(task_id) if task_id is not None else None, "message": APP_STATE["status_message"]}

@app.get("/ozon-task-info/{task_id}")
async def get_ozon_task_info(task_id: str):
    if not APP_STATE["ozon_client"]:
        raise HTTPException(status_code=400, detail="Клиент Ozon не инициализирован.")
    
    task_info = APP_STATE["ozon_client"].get_task_info(task_id)
    if task_info:
        APP_STATE["ozon_task_info"] = task_info
    else:
        raise HTTPException(status_code=404, detail=f"Не удалось получить информацию о задаче для task_id: {task_id}")
    return task_info
