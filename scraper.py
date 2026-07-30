"""
scraper.py
----------
Yahan saare "scraping modules" rahenge. Abhi ke liye ek generic product-page
scraper hai jo Meesho jaisi pages se data nikalta hai (meta description,
JSON-LD, title, images, etc).

Naya module add karna ho (e.g. pincode delivery check, price history, etc)
to bas neeche ek naya function bana ke usko app.py ke route se call kar dena.
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def fetch_page_html(url: str, timeout: int = 15) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def fetch_page_html_browser(url: str, wait_seconds: float = 8.0) -> str:
    """
    Real Chrome browser se page kholta hai. Colab environment (Linux) ke
    liye explicitly binary path aur sandbox flags diye gaye hain.
    """
    import undetected_chromedriver as uc
    import time

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Linux/Colab specific safety flags
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # FIX: Explicitly Colab ka Chromium path do aur auto-versioning on rakho
    driver = uc.Chrome(
        options=options, 
        browser_executable_path='/usr/bin/chromium-browser'
    )
    
    try:
        driver.get(url)
        # WAF challenge (Akamai) ko execute hone ka time do
        time.sleep(wait_seconds) 
        html = driver.page_source
    finally:
        driver.quit()

    return html


def parse_meta_description(soup: BeautifulSoup) -> dict:
    data = {}
    meta = soup.find("meta", attrs={"name": "description"})
    if not meta or not meta.get("content"):
        return data

    content = meta["content"]
    for line in content.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key and value:
            data[key] = value
    return data


def parse_json_ld(soup: BeautifulSoup) -> list:
    blocks = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            blocks.append(json.loads(tag.string))
        except (TypeError, json.JSONDecodeError):
            continue
    return blocks


def parse_basic_tags(soup: BeautifulSoup) -> dict:
    result = {}
    if soup.title and soup.title.string:
        result["page_title"] = soup.title.string.strip()
    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        result["og_image"] = og_image["content"]
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical and canonical.get("href"):
        result["canonical_url"] = canonical["href"]
    return result


def extract_next_data(soup: BeautifulSoup) -> dict:
    tag = soup.find("script", attrs={"id": "__NEXT_DATA__"})
    if not tag or not tag.string:
        return {}
    try:
        return json.loads(tag.string)
    except json.JSONDecodeError:
        return {}


def parse_meesho_specific_json(next_data: dict) -> dict:
    """Exact Meesho JSON structure ko map karke saari complex details nikalta hai."""
    result = {
        "all_images": [],
        "variants": [],
        "similar_products": [],
        "highlights": {},
        "mrp": None,
        "sell_price": None,
        "description": ""
    }
    
    if not next_data:
        return result

    try:
        data = next_data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("product", {}).get("details", {}).get("data", {})
        if not data:
            return result
    except AttributeError:
        return result

    # 1. Prices & Description
    result["sell_price"] = data.get("price")
    if "mrp_details" in data:
        result["mrp"] = data["mrp_details"].get("mrp")
    result["description"] = data.get("description", "")

    # 2. All Images
    result["all_images"] = data.get("images", [])

    # 3. Product Highlights (Parsed from description strings)
    if result["description"]:
        for line in result["description"].split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                # Ignore sizes multiline block to keep highlight table clean
                if key.strip().lower() != "sizes":
                    result["highlights"][key.strip()] = val.strip()

    # 4. Variants (Size, Price, Stock)
    suppliers = data.get("suppliers", [])
    if suppliers and isinstance(suppliers, list) and len(suppliers) > 0:
        inventory = suppliers[0].get("inventory", [])
        for inv in inventory:
            var_data = inv.get("variation", {})
            result["variants"].append({
                "size": var_data.get("name"),
                "price": var_data.get("final_price"),
                "in_stock": inv.get("in_stock", False)
            })

    # 5. Similar Products
    catalog = data.get("catalog", {})
    if "similarProducts" in catalog:
        for sim in catalog["similarProducts"]:
            imgs = sim.get("images", [])
            result["similar_products"].append({
                "name": sim.get("name"),
                "price": sim.get("min_price"),
                "image": imgs[0] if imgs else ""
            })

    return result


INTERESTING_KEYS = {
    "brand": "Brand",
    "rating": "Rating",
    "rating_count": "Ratings Count",
    "review_count": "Reviews Count",
    "supplier_name": "Seller",
    "catalog_id": "Catalog ID",
    "product_id": "Product ID",
}

def deep_extract_keys(obj, target_keys: dict, found: dict = None, _depth: int = 0) -> dict:
    if found is None:
        found = {}
    if _depth > 25:
        return found
    if isinstance(obj, dict):
        for key, value in obj.items():
            label = target_keys.get(str(key).lower())
            if label and label not in found and isinstance(value, (str, int, float, bool)):
                found[label] = value
            if isinstance(value, (dict, list)):
                deep_extract_keys(value, target_keys, found, _depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                deep_extract_keys(item, target_keys, found, _depth + 1)
    return found


def extract_breadcrumbs(json_ld_blocks: list) -> list:
    for block in json_ld_blocks:
        if isinstance(block, dict) and block.get("@type") == "BreadcrumbList":
            items = block.get("itemListElement", [])
            return [{"name": item.get("name"), "url": item.get("item")} for item in items]
    return []


def scrape_product_page(url: str) -> dict:
    try:
        html = fetch_page_html(url)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [403, 429]:
            print(f"[{e.response.status_code}] Blocked by bot protection. Falling back to browser...")
            html = fetch_page_html_browser(url)
        else:
            raise e

    soup = BeautifulSoup(html, "html.parser")

    meta_fields = parse_meta_description(soup)
    json_ld_blocks = parse_json_ld(soup)
    basic = parse_basic_tags(soup)
    breadcrumbs = extract_breadcrumbs(json_ld_blocks)

    next_data = extract_next_data(soup)
    
    # Generic extraction for simple keys
    deep_fields = deep_extract_keys(next_data, INTERESTING_KEYS) if next_data else {}
    
    # Specific extraction for Meesho's exact JSON structure (Variants, Exact Prices, Similar Products)
    meesho_specific = parse_meesho_specific_json(next_data)
    
    combined_fields = {**deep_fields, **meta_fields}
    
    # Set explicit MRP and Price if found in specific JSON
    if meesho_specific["sell_price"]: combined_fields["Sell Price"] = f"₹{meesho_specific['sell_price']}"
    if meesho_specific["mrp"]: combined_fields["MRP"] = f"₹{meesho_specific['mrp']}"

    return {
        "source_url": url,
        "page_title": basic.get("page_title"),
        "canonical_url": basic.get("canonical_url"),
        "og_image": basic.get("og_image"),
        "all_images": meesho_specific["all_images"],
        "variants": meesho_specific["variants"],
        "highlights": meesho_specific["highlights"],
        "similar_products": meesho_specific["similar_products"],
        "product_fields": combined_fields,
        "breadcrumbs": breadcrumbs,
        "json_ld_raw": json_ld_blocks,
        "next_data_raw": next_data,
    }

def check_pincodes_bulk(url: str, pincodes: list) -> dict:
    import undetected_chromedriver as uc
    import os
    import time
    import re
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    profile_path = os.path.abspath(os.path.join(os.getcwd(), "chrome_profile"))

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options, version_main=150)
    results = {}
    error_log = []

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        time.sleep(5) 

        for pin in pincodes:
            try:
                # 1. Input box locate karo
                input_box = wait.until(EC.presence_of_element_located((By.ID, "pin")))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", input_box)
                time.sleep(1.5)

                # 2. JavaScript ke through value set karo aur React event trigger karo (Bypasses UI mouse glitches)
                driver.execute_script("""
                    let input = arguments[0];
                    input.focus();
                    input.value = arguments[1];
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                """, input_box, pin)
                
                time.sleep(1.5) # Pincode enter hone ke baad thoda stable wait

                # 3. CHECK button click via JS
                check_btn = driver.find_element(By.XPATH, "//button[.//span[contains(text(), 'CHECK')]]")
                driver.execute_script("arguments[0].click();", check_btn)
                
                # 4. Response load hone ka wait
                time.sleep(3.5)

                # 5. Extract Price
                try:
                    price_element = driver.find_element(By.XPATH, "//h4[contains(text(), '₹')]")
                except:
                    price_element = driver.find_element(By.XPATH, "(//*[contains(text(), '₹')])[1]")
                
                digits = re.findall(r'\d+', price_element.text.replace(',', ''))
                
                if digits:
                    results[pin] = int(digits[0])
                else:
                    error_log.append(f"{pin}: Price format invalid -> {price_element.text}")
                    results[pin] = None

            except Exception as e:
                error_log.append(f"{pin} error: {type(e).__name__}")
                results[pin] = None
                
    finally:
        driver.quit()

    valid_prices = {k: v for k, v in results.items() if v is not None}
    
    if not valid_prices:
        return {"error": f"Scraping fail ho gaya. Reason: {error_log[0] if error_log else 'Unknown error'}"}

    min_price = min(valid_prices.values())
    max_price = max(valid_prices.values())
    avg_price = sum(valid_prices.values()) / len(valid_prices)

    lowest_pins = [k for k, v in valid_prices.items() if v == min_price]
    highest_pins = [k for k, v in valid_prices.items() if v == max_price]
    mid_range_pins = [k for k, v in valid_prices.items() if min_price < v < max_price]

    return {
        "raw_results": valid_prices,
        "analytics": {
            "lowest": {"price": min_price, "pincodes": lowest_pins},
            "highest": {"price": max_price, "pincodes": highest_pins},
            "average": round(avg_price, 2),
            "mid_range": {"pincodes": mid_range_pins}
        }
    }