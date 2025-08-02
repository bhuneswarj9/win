from playwright.sync_api import sync_playwright
import json

def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://wingoanalyst.com/#/wingo_30s", wait_until="networkidle")
        page.wait_for_timeout(5000)

        cells = page.query_selector_all("div[style*='text-align: center'][style*='color: black']")
        text_cells = [cell.inner_text() for cell in cells]

        rows = [text_cells[i:i+4] for i in range(4, len(text_cells), 4)]
        for row in rows:
            if all(x.lower() != "pending" for x in row[1:]):
                values = row
                break
        else:
            values = ["N/A", "N/A", "N/A", "N/A"]

        data = {
            "draw_number": values[0],
            "result_number": values[1],
            "size": values[2],
            "color": values[3]
        }

        print(json.dumps(data))

if __name__ == "__main__":
    scrape()
