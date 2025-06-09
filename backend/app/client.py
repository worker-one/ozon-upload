import requests
import json
import logging
from time import sleep
from typing import Optional

from .config import API_URL, DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET

class OzonApiClient:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.client_secret = client_secret or DEFAULT_CLIENT_SECRET
        self.api_url = API_URL
        self.batch_size = 50
        self.headers = {
            'Client-Id': self.client_id,
            'Api-Key': self.client_secret,
            'Content-Type': 'application/json'
        }
        logging.info(f"OzonApiClient initialized with client_id: {self.client_id}")

    def submit_items(self, items):
        if not items:
            logging.info("No items to submit.")
            return

        task_id = None
        total = len(items)
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            payload = {"items": batch}
            payload_json = json.dumps(payload, ensure_ascii=False)

            logging.info(f"Submitting batch {i // self.batch_size + 1} ({len(batch)} items) to Ozon API...")

            try:
                response = requests.post(self.api_url, headers=self.headers, data=payload_json.encode('utf-8'))
                response.raise_for_status()

                logging.info(f"API Response Status Code: {response.status_code}")
                response_data = response.json()
                logging.info(f"API Response JSON: {json.dumps(response_data, indent=2, ensure_ascii=False)}")

                batch_task_id = response_data.get('result', {}).get('task_id')
                if batch_task_id:
                    logging.info(f"Import task created with ID: {batch_task_id}. Check status via /v1/product/import/info")
                    task_id = batch_task_id
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

            if i + self.batch_size < total:
                logging.info("Waiting 5 seconds before submitting the next batch...")
                sleep(15)

        return task_id

    def get_task_info(self, task_id):
        payload = {
            "task_id": int(task_id) if isinstance(task_id, str) and task_id.isdigit() else task_id
        }
        try:
            base_url = "https://api-seller.ozon.ru/v1/product/import/info"
            response = requests.post(base_url, headers=self.headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
