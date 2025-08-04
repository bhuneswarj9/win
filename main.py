import os
import json
import time
import logging
import traceback
import threading
from datetime import datetime, timedelta

import requests
import mysql.connector
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
from logging.handlers import RotatingFileHandler
import uvicorn

# === CONFIG ===
API_URL = "https://win-1-ysem.onrender.com/api/latest-draw"
LOG_FILE = "wingo_service.log"
FETCH_TIMEOUT = 30  # seconds
FETCH_INTERVAL = 60  # seconds

# === LOGGING ===
log_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# === SCRAPER ===
def scrape():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(java_script_enabled=True)
            page = context.new_page()

            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            })

            for _ in range(3):
                try:
                    page.goto("https://wingoanalyst.com/#/wingo_1m", wait_until="networkidle", timeout=20000)
                    break
                except Exception as e:
                    logger.warning("Retrying page.goto due to: %s", e)
                    time.sleep(2)
            else:
                return {"error": "Failed to load page after retries."}

            page.wait_for_selector("div[style*='text-align: center'][style*='color: black']", timeout=10000)

            cells = page.query_selector_all("div[style*='text-align: center'][style*='color: black']")
            text_cells = [cell.inner_text() for cell in cells]
            rows = [text_cells[i:i + 4] for i in range(4, len(text_cells), 4)]

            for row in rows:
                if all(x.lower() != "pending" for x in row[1:]):
                    values = row
                    break
            else:
                values = ["N/A", "N/A", "N/A", "N/A"]

            return {
                "draw_number": values[0],
                "result_number": values[1],
                "size": values[2],
                "color": values[3]
            }

        except Exception as e:
            logger.error("Scraping error: %s", str(e))
            return {"error": str(e)}
        finally:
            browser.close()
# === FASTAPI ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/latest-draw")
def get_latest_draw():
    try:
        data = scrape()
        if "error" in data:
            logger.warning("Scrape error: %s", data["error"])
            return {"status": "error", "message": data["error"]}

        inserted = insert_into_db(data)
        logger.info("Draw fetched: %s | inserted=%s", data, inserted)
        return {"status": "success", "inserted": inserted, "data": data}

    except Exception as e:
        logger.critical("API exception: %s", e)
        logger.debug(traceback.format_exc())
        return {"status": "error", "message": str(e)}

@app.get("/")
def root():
    return {"message": "Wingo API running"}

# === POLLING ===
def poll_loop():
    while True:
        try:
            response = requests.get(API_URL, timeout=FETCH_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                logger.info("Poll success: %s", data["data"])
                print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), "✔ Success:", data["data"])
            else:
                logger.warning("API error: %s", data)
                print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), "✖ API Error:", data)

        except Exception as e:
            logger.error("Polling error: %s", e)
            print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), "⚠ Polling error:", e)

        # Sleep until top of next minute
        now = datetime.now()
        next_min = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        time.sleep((next_min - now).total_seconds())

# === MAIN ===
if __name__ == "__main__":
    threading.Thread(target=poll_loop, daemon=True).start()
    print("🚀 Starting Wingo FastAPI server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
