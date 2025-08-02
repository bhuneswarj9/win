from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import mysql.connector
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to connect to DB
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="12345678",
        database="wingo"
    )

@app.get("/api/latest-draw")
def get_latest_draw():
    try:
        # Run the scraping script
        result = subprocess.run(
            ["python", "scrape_latest.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return {"status": "error", "message": "Scraper failed"}

        data = json.loads(result.stdout)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Prevent duplicate draw numbers
        cursor.execute("SELECT COUNT(*) FROM results WHERE draw_number = %s", (data["draw_number"],))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO results (draw_number, result_number, size, color, created_at) VALUES (%s, %s, %s, %s, %s)",
                (data["draw_number"], data["result_number"], data["size"], data["color"], datetime.now())
            )
            conn.commit()
            inserted = True
        else:
            inserted = False

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "inserted": inserted,
            "data": data
        }

    except Exception as e:
        return {"status": "error", "message": f"API error: {str(e)}"}
@app.get("/")
def read_root():
    return {"message": "Wingo API is running"}
