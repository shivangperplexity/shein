import logging
import requests
import json
import os
import time
import asyncio
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---

# 1. Bot credentials
BOT_TOKEN = "8313508428:AAFlmiRD2dd7aOPHdz6Pe0PykrJEkqzs4kw"
# Target Group/Channel for real-time updates
CHAT_ID = "-1003028949899" 

# Files to store data
CONFIG = {
    "PRODUCT_CODES_FILE": "product_codes.txt",
    "PRODUCT_DETAILS_FILE": "product_details.json",
    "OUT_OF_STOCK_FILE": "out_of_stock.txt",
    "NOTIFIED_OUT_OF_STOCK_FILE": "notified_out_of_stock.txt",
    "NOTIFIED_NEW_PRODUCTS_FILE": "notified_new_products.txt",
    "NOTIFIED_PRICE_CHANGES_FILE": "notified_price_changes.json",
    "POLLING_DELAY_SECONDS": 5, # Increased slightly to 5s for stability
}

# SHEIN API endpoints
CATALOG_API_URL = "https://www.sheinindia.in/api/category/sverse-5939-37961"
DELIVERY_API_URL = "https://www.sheinindia.in/api/edd/checkDeliveryDetails"

# Default Pin codes for background monitoring and /n when no pin is specified
DEFAULT_PIN_CODE_N = "411043" # Default for /n command
MONITOR_PIN_CODES = ["411043", "410206"] # Used for background alerts

# Headers and Cookies (KEEP AS IS - These are crucial for API access)
HEADERS = {
    'accept': 'application/json',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'x-tenant-id': 'SHEIN'
}

COOKIES = {
    # ... (Your long list of cookies) ...
    # Removed for brevity, but keep them in your actual script
    'V': '1',
    '_fbp': 'fb.1.1761380004446.284135199968730205',
    '_fpuuid': 'Wz5Z4g_B68bu9Ourjcxyj',
    'deviceId': 'Wz5Z4g_B68bu9Ourjcxyj',
    'jioAdsFeatureVariant': 'true',
    '_gcl_au': '1.1.165127546.1761380046',
    '_ga': 'GA1.1.417907633.1761380046',
    'recentlyViewed': '[{"id":"443317438_khaki","store":0}]',
    '_ga_D6SVDYBNVW': 'GS2.1.s1761380046$o1$g1$t1761380270$j26$l0$h738451347',
    'PC': '411043',
    'bm_ss': 'ab8e18ef4e',
    '_abck': '60E625D85DFD908B5FF38008E0453EE4~0~YAAQ0OgtF25Id96ZAQAAUjdoHA5SydMKW78Ck9rPTdZRYmKGV4n/i9viJls8o6V429RvCiECYh06kccELZVBGezaVnKOT+IbgJCkLPRV1WsyggTg2juex2pL1Gujv51HB+YuhhLhnTbCkxG+YtirToJ4OmORncmsBCTDPp98Tntbn2Bbit/nIpVgCESaEzeCgElTI6i53bJbvDfVYJG6r2jz1AwXID5WN9TS7JxAbFsdcRQsDEIF+HKq2JYKv+IHlDmQ2qBD1e31FrZGr+nlHi11Qv5NYzH6bRVjyfFcCBIV5ZF8YwVjIyW0i0xHXDPhaPUPnQtKoSTA/wXAC3ITrC9PamKEMCMf3g1tCFrf+Nh2KNSc/tYl2rT+t+t+OcVmPAHbFvz37FiQyAvRhAo5q0T5IXkQAu/kOam+whY+KPuU+aZ0pryzE56j4ylsOvXSOxfOVTEjJ1rlY3IyGBxM5PGFBWccVFpOiQ8oecuzM64wBK8K0MWBqg4uzv+AczVMLfM/62jG2PFtvsB2+qdDsiN12piLRgWaGP7FYl3jdiTnKpYdeIMx8D8EBB+CKZyv+A0QQrr8b4xXPMSDKr+ZUOzBvsg3dz+uoLLr8lfqg0a6KG3ETelA/wAVvFSeKW9tmyGTUEXyyyr7Kn+hhYZszRXxGUs1aNqKyVjvLHe+~-1~-1~-1~AAQAAAAE%2f%2f%2f%2f%2fxctXmb85lFlYg9Bd1klGUPHzOk7TBA7KcIFmdhpGqrbbu9%2fyPQgvfRI0H9E9hWJ3W%2fpTBDipxleC2ZicD70XtH2xzNbv3DFQqeO~-1',
    'ak_bmsc': '71AE0AD4194EC50C55BBB3598F6EE2B0~000000000000000000000000000000~YAAQ0OgtF29Id96ZAQAAUjdoHB3G5nDJnXFhEWe0u0xQ9rvdmnBmu6s9dmv9hOMCH/cQTsuvysrkI9zV1oZrT6Tn7XwQwV3rgyo/bIKjmTkpBV3U4OaSFe20g9AmnkJX9R6IDiK86uGhbsFt1f8ZBhQ8w7tU7Y3nUQGltn46U0o/WCcedvkJWSBgHqSfJK4cwr8p56zCP2vzaLzA13p37WLx/vBCHVr2Ed13wxt/AwnsTxnlKovNJo43y57zLLabWnW5ob7WPVzD8CENL1ZK7NemdRcsBCPaNvtYYNY2m3+nQvKa9nsuh+aMrIY/ML4ftz3cO+yGkhYGyg1A1A1O5z1tgzPX5lPmkQX9GvVG7kHJRpvDybo3RzoUj9osH3xYVEoChY1L',
    'bm_s': 'YAAQ0OgtF3BId96ZAQAAUjdoHARVVofIxjUx99wrOVHhGvQnUUqgbAQTTVZLd7AlBDn6kuqQbogNxgFcCRcE+xaUBqsI1CuUwMcdUZuxk87227n8Fxx31w12Wh4zqsXrKDZCjU68hxKfQrVi/liXvyDSzDxJSfRbmyINqb19tdzZ6rXBktlFwRpWJ1hWD8misp/Z65prem6puTXfdkmqvDs7gSlT90wpzgkdtc6PIq6yFKN3JnCdoVPktBSEizJss+pNnlHZqb0au1myhrXoHi5zy2AEWgyIspo7QI9Lk8/zzVOPJ7I/gsdGRf8lVBtY45uVXdbx9xEmbgo3+y8yUNzn9azkXA4/vc/C25vhyv2LSA+9QpRdQIO1vw0Rr9bMIs2Vgz6QXoZ01NIVk3SPhr+siMEukT3HZ81HBRPp3yAg0gO2sLcHj+S/uWiNEeRqXdKkTypcevqRilsYogBJY7/uKxIz14C6b5upIAVdB8pIdVi+JPikCGsHSY5Cd3ZKVaYQNgHmq/awuqFwcrjF4gUK5wVfGZnv060YJGnI9rXleNYTIOUtiLpnaleC0apoUDueJB8Q==',
    'bm_so': 'EBC15042E16A0E540F035E3C4A41E9C0DDF4EED1FA1F55CD062AE4AC00A7870E~YAAQ0OgtF3FId96ZAQAAUjdoHAVbyj86L3fvJLP9JFTFZ2ZjloiJeQ7oKB1bHCCWM0dWaDwP5gs1YqntJ4CcUIwlLjvPPeO5SxjdnAN4P91oHt3cIVrlT8McSFf1qe2rkGVcWpiBDYwfVVFEDsHPwFMrpDenuWmfU7TWL6RntccDNxueIlbOy5zwIWzUddhsSnoiKnLzI2p1Sn4XGfjeL7l/miJ1Xp1HKMyiZeDZg/v3pJmqdteSYLBPcK5rx0iHqIfcscuu/n0YXIJpO5I2E+MQ3yb9FRdQoz6ZpIVwWBNKgj5Fmh2b2AXstVuBvkOUWrZRKMcETPAdXsue81K2dKO4+qQwkZ73eEweJM8yRvuTCkLf/9vXNHhgetfNnrvcZbGxDb07vbx0tS/2Mb9LD4g8KJNh5pUq1YesLvEIKy3UUFWmgo7bUxTi3saGL4khryHwJQpAsl3KET6GZjF6+UH',
    'bm_sz': '5C8665A47E8F5011192B983F928E9AD0~YAAQ0OgtF3JId96ZAQAAUjdoHB00lsGECFKxBGshqI7lqoPgGZka+xI8VWgfhPVNFeea1tjenTUeVU++auEhW4rXB8O7qsmvMPmeGtBOPvII0nBV8E7pqzUfEFCu2wD5nPZpICiadf0ygojhWOkwAwNaH3czN94p1Ec4AirP7PNqaZ+3Wa0nxS8x97oJji6Vk7zAPhqwHWm/SoQiUvmcEQmrV1OU4Vg1p4UordcZ5EIXZ3hNSUCBbzQ3Nj4OnL8+DbEhPwuqIQOsuC+n4YUDGQQq4LV1MDBTiMCerr0RS7HWpG0ziTP+45agnOjHqHpROPIgNtbAgKh7ZJfR3o+/SYk9AQOJldodl5fWx/R8sik6eQY3XnOxD4Y+g=~3159091~3556419',
    'bm_lso': 'EBC15042E16A0E540F035E3C4A41E9C0DDF4EED1FA1F55CD062AE4AC00A7870E~YAAQ0OgtF3FId96ZAQAAUjdoHAVbyj86L3fvJLP9JFTFZ2ZjloiJeQ7oKB1bHCCWM0dWaDwP5gs1YqntJ4CcUIwlLjvPPeO5SxjdnAN4P91oHt3cIVrlT8McSFf1qe2rkGVcWpiBDYwfVVFEDsHPwFMrpDenuWmfU7TWL6RntccDNxueIlbOy5zwIWzUddhsSnoiKnLzI2p1Sn4XGfjeL7l/miJ1Xp1HKMyiZeDZg/v3pJmqdteSYLBPcK5rx0iHqIfcscuu/n0YXIJpO5I2E+MQ3yb9FRdQoz6ZpIVwWBNKgj5Fmh2b2AXstVuBvkOUWrZRKMcETPAdXsue81K2dKO4+qQwkZ73eEweJM8yRvuTCkLf/9vXNHhgetfNnrvcZbGxDb07vbx0tS/2Mb9LD4g8KJNh5pUq1YesLvEIKy3UUFWmgo7bUxTi3saGL4khryHwJQpAsl3KET6GZjF6+UH^1761413185100'
}

# Global variables to store data
PRODUCTS_CACHE = {} # Used for /n and /checkdelivery commands
PREVIOUS_CATALOG = {} # Used for price/new/oos comparison

# Thread pool for concurrent requests
# Using a higher number can increase speed but may also lead to rate limiting
executor = ThreadPoolExecutor(max_workers=20) # Increased workers for faster checks in /n

# --- UTILITY FUNCTIONS (UPDATED FOR CLARITY/MAINTAINABILITY) ---

def load_data(file_key, default_type):
    """Generic function to load data from file, handles different types."""
    file_path = CONFIG[file_key]
    if not os.path.exists(file_path):
        return default_type()
    
    try:
        if file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            with open(file_path, 'r') as f:
                return default_type(line.strip() for line in f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return default_type()

def save_data(file_key, data):
    """Generic function to save data to file, handles different types."""
    file_path = CONFIG[file_key]
    try:
        with open(file_path, 'w') as f:
            if file_path.endswith('.json'):
                json.dump(data, f, indent=2)
            elif isinstance(data, set):
                for item in data:
                    f.write(f"{item}\n")
            else:
                # Assuming simple text saving for other cases
                for item in data:
                    f.write(f"{item}\n")
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")

# Map keys to generic load/save functions
load_product_codes = lambda: load_data("PRODUCT_CODES_FILE", set)
save_product_codes = lambda data: save_data("PRODUCT_CODES_FILE", data)
load_product_details = lambda: load_data("PRODUCT_DETAILS_FILE", dict)
save_product_details = lambda data: save_data("PRODUCT_DETAILS_FILE", data)
load_out_of_stock = lambda: load_data("OUT_OF_STOCK_FILE", set)
save_out_of_stock = lambda data: save_data("OUT_OF_STOCK_FILE", data)
load_notified_out_of_stock = lambda: load_data("NOTIFIED_OUT_OF_STOCK_FILE", set)
save_notified_out_of_stock = lambda data: save_data("NOTIFIED_OUT_OF_STOCK_FILE", data)
load_notified_new_products = lambda: load_data("NOTIFIED_NEW_PRODUCTS_FILE", set)
save_notified_new_products = lambda data: save_data("NOTIFIED_NEW_PRODUCTS_FILE", data)
load_notified_price_changes = lambda: load_data("NOTIFIED_PRICE_CHANGES_FILE", dict)
save_notified_price_changes = lambda data: save_data("NOTIFIED_PRICE_CHANGES_FILE", data)

# --- API FUNCTIONS (NO MAJOR LOGIC CHANGE, KEPT FOR COMPLETENESS) ---

def fetch_catalog():
    """Fetch product catalog from SHEIN API with retry mechanism"""
    # ... (function body as provided by user - no change) ...
    params = {
        'fields': 'SITE',
        'currentPage': '0',
        'pageSize': '45',
        'format': 'json',
        'query': ':relevance:genderfilter:Men',
        'sortBy': 'relevance',
        'gridColumns': '5',
        'facets': 'genderfilter:Men',
        'segmentIds': '',
        'advfilter': 'true',
        'platform': 'Desktop',
        'showAdsOnNextPage': 'false',
        'is_ads_enable_plp': 'true',
        'displayRatings': 'true',
        'store': 'shein'
    }
    
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.get(CATALOG_API_URL, params=params, headers=HEADERS, cookies=COOKIES, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"Authentication error (403) on attempt {attempt + 1}/{max_retries}. Cookies may be expired.")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Please update the cookies in the script.")
                    return None
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error fetching catalog: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                return None
    
    return None

def check_delivery_availability(product_code, pin_code):
    """Check delivery availability for a product to a specific pin code"""
    # ... (function body as provided by user - no change) ...
    params = {
        'productCode': product_code,
        'postalCode': pin_code,
        'quantity': '1',
        'IsExchange': 'false'
    }
    
    try:
        response = requests.get(DELIVERY_API_URL, params=params, headers=HEADERS, cookies=COOKIES, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error checking delivery for {pin_code}: {e}")
        return None

async def check_delivery_for_pins(product_code, pin_codes):
    """Check delivery availability for a list of pin codes"""
    # ... (function body as provided by user - no change) ...
    delivery_info = {}
    
    # Create tasks for concurrent execution
    loop = asyncio.get_event_loop()
    tasks = []
    
    for pin_code in pin_codes:
        task = loop.run_in_executor(executor, check_delivery_availability, product_code, pin_code)
        tasks.append((pin_code, task))
    
    # Wait for all tasks to complete
    for pin_code, task in tasks:
        try:
            delivery_data = await task
            if delivery_data:
                status = delivery_data.get('status', {})
                status_code = status.get('statusCode', -1)
                
                if status_code == 0:
                    product_details = delivery_data.get('productDetails', [])
                    if product_details:
                        detail = product_details[0]
                        delivery_info[pin_code] = {
                            'serviceable': detail.get('servicability', False),
                            'delivery_method': detail.get('deliveryMethod', 'Unknown'),
                            'cod_eligible': detail.get('codEligible', False),
                            'reason': detail.get('reasonForNotServiceability', '')
                        }
                    else:
                        delivery_info[pin_code] = {
                            'serviceable': False,
                            'delivery_method': 'Unknown',
                            'cod_eligible': False,
                            'reason': 'No delivery information available'
                        }
                else:
                    delivery_info[pin_code] = {
                        'serviceable': False,
                        'delivery_method': 'Unknown',
                        'cod_eligible': False,
                        'reason': 'Failed to check delivery'
                    }
            else:
                delivery_info[pin_code] = {
                    'serviceable': False,
                    'delivery_method': 'Unknown',
                    'cod_eligible': False,
                    'reason': 'API error'
                }
        except Exception as e:
            logger.error(f"Error processing delivery for {pin_code}: {e}")
            delivery_info[pin_code] = {
                'serviceable': False,
                'delivery_method': 'Unknown',
                'cod_eligible': False,
                'reason': 'Processing error'
            }
    
    return delivery_info

async def check_delivery_for_all_pins(product_code):
    """Check delivery availability for all MONITOR_PIN_CODES (used for alerts)"""
    return await check_delivery_for_pins(product_code, MONITOR_PIN_CODES)

# --- HELPER FUNCTION (NO MAJOR LOGIC CHANGE, KEPT FOR COMPLETENESS) ---
def format_product_info(product, index=None, delivery_info=None):
    """Format product information for display"""
    # ... (function body as provided by user - no change) ...
    name = product.get('name', 'Unknown Product')
    code = product.get('code', 'Unknown Code')
    price = product.get('price', {}).get('formattedValue', 'Price not available')
    offer_price = product.get('offerPrice', {}).get('formattedValue', '')
    rating = product.get('averageRating', 0)
    rating_count = product.get('ratingCount', 0)
    url = f"https://www.sheinindia.in{product.get('url', '')}"
    
    # Get color from the product data
    color_group = product.get('fnlColorVariantData', {}).get('colorGroup', '')
    color = color_group.split('_')[-1] if '_' in color_group else color_group
    
    # Get primary image - try different image formats
    images = product.get('images', [])
    image_url = ''
    
    if images:
        # Try to get the best quality image
        for img in images:
            if img.get('format') == 'product' and img.get('imageType') == 'PRIMARY':
                image_url = img.get('url', '')
                break
        
        # If not found, try any other format
        if not image_url:
            for img in images:
                if img.get('url'):
                    image_url = img.get('url')
                    break
    
    # Get tags
    tags = []
    category_tags = product.get('tags', {}).get('categoryTags', [])
    for tag in category_tags:
        if tag.get('category') == 'SELLING_POINT':
            tags.append(tag.get('primary', {}).get('name', ''))
    
    # Format message
    message = ""
    
    # Add index if provided
    if index is not None:
        # The index here is i+1 from the loops, representing the product number
        message += f"📦 <b>Product #{index + 1}</b>\n\n"  
    
    message += f"<b>{name}</b>\n"
    message += f"Code: {code}\n"
    
    if color:
        message += f"Color: {color.title()}\n"
    
    if offer_price and offer_price != price:
        message += f"Price: <s>{price}</s> {offer_price}\n"
    else:
        message += f"Price: {price}\n"
    
    if rating > 0:
        message += f"Rating: {rating} ({rating_count} reviews)\n"
    
    if tags:
        message += f"Tags: {', '.join(tags)}\n"
    
    # Add delivery information if provided
    if delivery_info:
        message += f"\n<b>🚚 Delivery Status:</b>\n"
        for pin_code, info in delivery_info.items():
            message += f"\n📍 <b>{pin_code}:</b>\n"
            message += f"Serviceable: {'✅ Yes' if info['serviceable'] else '❌ No'}\n"
            if info['serviceable']:
                message += f"Delivery Method: {info['delivery_method']}\n"
                message += f"COD Available: {'✅ Yes' if info['cod_eligible'] else '❌ No'}\n"
            else:
                if info['reason']:
                    message += f"Reason: {info['reason']}\n"
    
    message += f"\n<a href='{url}'>🔗 View on SHEIN</a>"
    
    return message, image_url

# --- MONITORING FUNCTION (KEY LOGIC CHANGE) ---

async def monitor_catalog_changes(application):
    """Monitor catalog changes in real-time"""
    global PREVIOUS_CATALOG, PRODUCTS_CACHE
    
    # Load initial data
    notified_out_of_stock = load_notified_out_of_stock()
    notified_new_products = load_notified_new_products()
    notified_price_changes = load_notified_price_changes()
    existing_codes = load_product_codes()
    out_of_stock = load_out_of_stock()
    
    # Ensure PREVIOUS_CATALOG is loaded from file on start
    if not PREVIOUS_CATALOG:
        PREVIOUS_CATALOG = load_product_details()
    
    # Use a separate set to track products that are known to be OOS but haven't been notified
    # This set will be updated only when an item is permanently removed from the catalog/file
    
    while True:
        try:
            # Fetch current catalog
            catalog_data = fetch_catalog()
            if not catalog_data:
                await asyncio.sleep(CONFIG["POLLING_DELAY_SECONDS"] * 6) # Wait 30s before retrying on error
                continue
            
            current_products = catalog_data.get('products', [])
            current_codes = set(product.get('code') for product in current_products if product.get('code'))
            
            # --- 1. Detect New Products ---
            new_products = []
            for product in current_products:
                code = product.get('code')
                if code and code not in existing_codes:
                    new_products.append(product)
                    existing_codes.add(code) # Add to the master list of all ever-seen products
            
            # --- 2. Detect Removed Products (Out of Stock / Permanently Gone) ---
            # A product is considered "removed" if it was in the master list but is not in the current catalog.
            removed_products = []
            # Iterate over a copy of existing_codes to allow modification of out_of_stock set
            for code in list(existing_codes): 
                if code not in current_codes:
                    # Product is gone from the API results
                    if code in PREVIOUS_CATALOG and code not in notified_out_of_stock:
                        removed_products.append(PREVIOUS_CATALOG[code])
                        notified_out_of_stock.add(code)
                        out_of_stock.add(code)
                    
                    # Do NOT remove from existing_codes yet, let it be removed only after a few cycles 
                    # or only when we're sure it's gone permanently. For simplicity here, we'll keep 
                    # it in existing_codes for now to avoid re-notification if it reappears.
                    # The price/new check only runs on existing codes.
            
            # --- 3. Detect Price Changes and Update Catalog Details ---
            price_changes = []
            for product in current_products:
                code = product.get('code')
                if code:
                    # Check for price change
                    if code in PREVIOUS_CATALOG:
                        prev_price = PREVIOUS_CATALOG[code].get('price', {}).get('formattedValue', '')
                        curr_price = product.get('price', {}).get('formattedValue', '')
                        
                        price_change_key = f"{code}_{prev_price}_{curr_price}"
                        
                        if (prev_price and curr_price and prev_price != curr_price and 
                            price_change_key not in notified_price_changes):
                            
                            # Use the old price for the alert, and the current product details
                            price_changes.append((product, prev_price, curr_price))
                            # Mark key as notified - prevent repeat alert for this exact price transition
                            notified_price_changes[price_change_key] = datetime.now().isoformat()
                            
                    # Update PREVIOUS_CATALOG with the latest details
                    PREVIOUS_CATALOG[code] = product
            
            # --- 4. Save updated data ---
            save_product_codes(existing_codes)
            save_product_details(PREVIOUS_CATALOG)
            save_out_of_stock(out_of_stock)
            save_notified_out_of_stock(notified_out_of_stock)
            save_notified_price_changes(notified_price_changes)
            
            # Update products cache (for immediate use if user asks)
            PRODUCTS_CACHE = {str(i+1): product for i, product in enumerate(current_products)}
            
            # --- 5. Send Notifications (New Products) ---
            for product in new_products:
                code = product.get('code')
                if code and code not in notified_new_products:
                    delivery_info = await check_delivery_for_all_pins(code)  
                    message, image_url = format_product_info(product, delivery_info=delivery_info)
                    
                    try:
                        alert_message = f"🆕 <b>NEW PRODUCT ALERT!</b>\n\n{message}"
                        if image_url:
                            await application.bot.send_photo(
                                chat_id=CHAT_ID, 
                                photo=image_url,
                                caption=alert_message,
                                parse_mode='HTML'
                            )
                        else:
                            await application.bot.send_message(
                                chat_id=CHAT_ID, 
                                text=alert_message,
                                parse_mode='HTML'
                            )
                        
                        notified_new_products.add(code)
                        save_notified_new_products(notified_new_products)
                        await asyncio.sleep(0.5) 
                    except BadRequest as e:
                        logger.error(f"Telegram BadRequest for new product {code}: {e}")
                    except Exception as e:
                        logger.error(f"Error sending new product notification: {e}")
            
            # --- 6. Send Notifications (Out of Stock/Removed Products) ---
            for product in removed_products:
                code = product.get('code')
                product_name = product.get('name', 'Unknown Product')
                message = f"❌ <b>PRODUCT OUT OF STOCK!</b>\n\n"
                message += f"<b>{product_name}</b>\n"
                message += f"Code: {code}\n\n"
                message += f"This product is no longer available in the catalog."
                
                try:
                    await application.bot.send_message(
                        chat_id=CHAT_ID, 
                        text=message,
                        parse_mode='HTML'
                    )
                    await asyncio.sleep(0.5)
                except BadRequest as e:
                    logger.error(f"Telegram BadRequest for removed product {code}: {e}")
                except Exception as e:
                    logger.error(f"Error sending out of stock notification: {e}")
            
            # --- 7. Send Notifications (Price Changes) ---
            for product, old_price, new_price in price_changes:
                code = product.get('code')
                product_name = product.get('name', 'Unknown Product')
                message = f"💰 <b>PRICE CHANGE ALERT!</b>\n\n"
                message += f"<b>{product_name}</b>\n"
                message += f"Code: {code}\n\n"
                message += f"Old Price: <s>{old_price}</s>\n"
                message += f"New Price: <b>{new_price}</b>\n\n"
                message += f"<a href='https://www.sheinindia.in/p/{code}'>🔗 View on SHEIN</a>"
                
                try:
                    await application.bot.send_message(
                        chat_id=CHAT_ID, 
                        text=message,
                        parse_mode='HTML'
                    )
                    await asyncio.sleep(0.5) 
                except BadRequest as e:
                    logger.error(f"Telegram BadRequest for price change {code}: {e}")
                except Exception as e:
                    logger.error(f"Error sending price change notification: {e}")
            
            # Wait 5 seconds before next check
            await asyncio.sleep(CONFIG["POLLING_DELAY_SECONDS"])
            
        except Exception as e:
            logger.error(f"Fatal error in catalog monitoring: {e}")
            await asyncio.sleep(CONFIG["POLLING_DELAY_SECONDS"] * 6) # Wait 30s before retrying

# --- COMMAND HANDLERS (NO MAJOR LOGIC CHANGE, KEPT FOR COMPLETENESS) ---

async def deliverable_products_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show only deliverable products to a specified pincode.  
    Defaults to 411043 if no pincode is provided.
    """
    # 2. Command modification: /n or /n <pincode>
    if context.args and re.match(r'^\d{6}$', context.args[0]):
        # /n <pincode> was typed
        target_pin_codes = [context.args[0]]
        pin_display = target_pin_codes[0]
    else:
        # /n was typed (or invalid pin) - use default
        target_pin_codes = [DEFAULT_PIN_CODE_N]
        pin_display = target_pin_codes[0]

    # Send initial message
    progress_message = await update.message.reply_text(
        f"🔍 Checking deliverable products for pin code: **{pin_display}**...\n\n"
        f"⚡ Using concurrent processing for maximum speed!",
        parse_mode='Markdown'
    )
    
    catalog_data = fetch_catalog()
    if not catalog_data:
        await progress_message.edit_text("❌ Failed to fetch products. Please try again later.\n\nIf this error persists, the cookies may have expired. Please update them in the script.")
        return
    
    products = catalog_data.get('products', [])
    if not products:
        await progress_message.edit_text("❌ No products found.")
        return
    
    # Update progress
    await progress_message.edit_text(
        f"🔍 Checking delivery for {len(products)} products to **{pin_display}**...\n\n"
        f"⚡ Processing with {executor._max_workers} concurrent workers!",
        parse_mode='Markdown'
    )
    
    deliverable_products = []
    checked_count = 0
    start_time = time.time()
    
    async def check_single_product_delivery_for_pin(product, index, total, pin_codes_to_check):
        """Check delivery for a single product against the list of pin codes"""
        code = product.get('code')
        if not code:
            return None
        
        try:
            # Re-used the delivery check with the target pin code
            delivery_info = await check_delivery_for_pins(code, pin_codes_to_check)
            
            # Check if product is deliverable to ANY of the pin codes in the list (in this case, just one pin)
            is_deliverable = any(info['serviceable'] for info in delivery_info.values())
            
            if is_deliverable:
                return (product, delivery_info)
        except Exception as e:
            logger.error(f"Error checking delivery for product {code}: {e}")
        
        return None

    # Process products in batches to avoid overwhelming the API
    # NOTE: The batch logic is now inside a loop that waits for all tasks in the batch
    batch_size = 5
    for batch_start in range(0, len(products), batch_size):
        batch_end = min(batch_start + batch_size, len(products))
        batch = products[batch_start:batch_end]
        
        tasks = []
        for i, product in enumerate(batch):
            task = asyncio.create_task(
                check_single_product_delivery_for_pin(product, batch_start + i, len(products), target_pin_codes)
            )
            tasks.append(task)
        
        # Wait for all tasks in this batch to complete
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    deliverable_products.append(result)
                checked_count += 1
                
                # Update progress every 5 products or every 2 seconds
                if checked_count % 5 == 0 or time.time() - start_time > 2:
                    elapsed = time.time() - start_time
                    rate = checked_count / elapsed if elapsed > 0 else 0
                    eta = (len(products) - checked_count) / rate if rate > 0 else 0
                    
                    # Edit the progress message
                    await progress_message.edit_text(
                        f"🔍 Checking delivery for {len(products)} products to **{pin_display}**...\n\n"
                        f"✅ Checked: {checked_count}/{len(products)}\n"
                        f"📦 Deliverable: {len(deliverable_products)}\n"
                        f"⚡ Speed: {rate:.1f} products/sec\n"
                        f"⏱️ ETA: {eta:.1f} seconds",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error in task: {e}")
        
        # Small delay between batches to avoid rate limiting
        await asyncio.sleep(0.5)
    
    # Final progress update
    elapsed = time.time() - start_time
    await progress_message.edit_text(
        f"✅ Delivery check completed for **{pin_display}**!\n\n"
        f"📊 Total Products: {len(products)}\n"
        f"📦 Deliverable: {len(deliverable_products)}\n"
        f"⏱️ Time Taken: {elapsed:.1f} seconds\n"
        f"⚡ Average Speed: {len(products)/elapsed:.1f} products/sec",
        parse_mode='Markdown'
    )
    
    if not deliverable_products:
        await update.message.reply_text(f"❌ No products are deliverable to pin code **{pin_display}**.", parse_mode='Markdown')
        return
    
    # Store deliverable products in cache with indices
    global PRODUCTS_CACHE
    PRODUCTS_CACHE = {str(i+1): product for i, (product, _) in enumerate(deliverable_products)}
    
    # Send deliverable products
    await update.message.reply_text(f"📤 Sending {len(deliverable_products)} deliverable products for **{pin_display}**...", parse_mode='Markdown')
    
    for i, (product, delivery_info) in enumerate(deliverable_products):
        message, image_url = format_product_info(product, index=i, delivery_info=delivery_info)
        
        try:
            if image_url:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_url,
                    caption=message,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='HTML'
                )
            
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.error(f"Error sending product {product.get('code')}: {e}")
    
    await update.message.reply_text(f"✅ All {len(deliverable_products)} deliverable products for **{pin_display}** sent! Use /checkdelivery <number> to check delivery again.", parse_mode='Markdown')

# --- CHECK DELIVERY COMMAND HANDLER (NO MAJOR LOGIC CHANGE, KEPT FOR COMPLETENESS) ---

async def check_delivery_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check delivery availability for a product by number."""
    if not context.args:
        await update.message.reply_text("❌ Please provide a product number. Usage: /checkdelivery <number>\n\n💡 Use /products or /n first to see numbered products.")
        return
    
    product_number = context.args[0]
    
    # Check if products cache is populated
    if not PRODUCTS_CACHE:
        await update.message.reply_text("❌ No products cached. Please run /products or /n first.")
        return
    
    # Get product from cache
    product = PRODUCTS_CACHE.get(product_number)
    if not product:
        await update.message.reply_text(f"❌ Product #{product_number} not found. Please use /products or /n to see available products.")
        return
    
    code = product.get('code')
    progress_message = await update.message.reply_text(f"🔍 Checking delivery for product **#{product_number}** (*{code}*)...", parse_mode='Markdown')
    
    # Use MONITOR_PIN_CODES for /checkdelivery
    delivery_info = await check_delivery_for_all_pins(code)

    message = f"📦 <b>Product #{product_number} - {product.get('name', 'Unknown')}</b>\n"
    message += f"Code: {code}\n\n"
    message += f"<b>🚚 Delivery Status:</b>\n"
    
    # The delivery info object keys are the pins checked (MONITOR_PIN_CODES for /checkdelivery)
    for pin_code, info in delivery_info.items():
        message += f"\n📍 <b>{pin_code}:</b>\n"
        message += f"Serviceable: {'✅ Yes' if info['serviceable'] else '❌ No'}\n"
        if info['serviceable']:
            message += f"Delivery Method: {info['delivery_method']}\n"
            message += f"COD Available: {'✅ Yes' if info['cod_eligible'] else '❌ No'}\n"
        else:
            if info['reason']:
                message += f"Reason: {info['reason']}\n"
    
    try:
        await progress_message.edit_text(message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error editing message for /checkdelivery: {e}")
        await context.bot.send_message(update.effective_chat.id, "Error updating delivery status message.")

# --- OTHER COMMANDS (NO MAJOR LOGIC CHANGE, KEPT FOR COMPLETENESS) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "🛍️ Welcome to SHEIN Catalog Bot!\n\n"
        "Commands:\n"
        "/products - View all products with delivery info (for pins 411043, 410206)\n"
        "/n - View only deliverable products for **411043** (FAST)\n"
        "/n <pincode> - View deliverable products for that specific pincode\n" 
        "/checkdelivery <number> - Check delivery for product by number\n"
        "/status - Check monitoring status\n"
        "/reset - Reset notification tracking\n"
        "/help - Show this help message\n\n"
        "💡 Products are numbered for easy reference!\n"
        "🔔 Real-time monitoring is active to the group! You'll be notified of new products, out of stock items, and price changes!\n"
        f"⚡ Optimized for speed with {executor._max_workers} concurrent workers!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "🛍️ SHEIN Catalog Bot Commands:\n\n"
        "/products - View all products with delivery info (for pins 411043, 410206)\n"
        "/n - View only deliverable products for **411043** (FAST)\n"
        "/n <pincode> - View deliverable products for that specific pincode\n" 
        "/checkdelivery <number> - Check delivery for product by number\n"
        "/status - Check monitoring status\n"
        "/reset - Reset notification tracking\n"
        "/help - Show this help message\n\n"
        "💡 Use /products or /n first to see numbered products, then use /checkdelivery <number>\n"
        "🔔 Real-time monitoring is active to the group! You'll be notified of new products, out of stock items, and price changes!\n"
        f"⚡ Optimized for speed with {executor._max_workers} concurrent workers!"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check monitoring status."""
    existing_codes = load_product_codes()
    out_of_stock = load_out_of_stock()
    notified_out_of_stock = load_notified_out_of_stock()
    notified_new_products = load_notified_new_products()
    notified_price_changes = load_notified_price_changes()
    
    await update.message.reply_text(
        f"📊 <b>Monitoring Status</b>\n\n"
        f"✅ Active Products (Total Seen): {len(existing_codes)}\n"
        f"❌ Permanently Out of Stock: {len(out_of_stock)}\n"
        f"📢 Notified Out of Stock: {len(notified_out_of_stock)}\n"
        f"📢 Notified New Products: {len(notified_new_products)}\n"
        f"📢 Notified Price Changes: {len(notified_price_changes)}\n"
        f"🔄 Real-time Monitoring: Active (Polling every {CONFIG['POLLING_DELAY_SECONDS']}s)\n"
        f"📍 Monitoring Pin Codes: {', '.join(MONITOR_PIN_CODES)}\n" 
        f"👤 Notification Chat ID: {CHAT_ID} (Group/Channel)\n" 
        f"⚡ Concurrent Processing: Enabled ({executor._max_workers} workers)",
        parse_mode='HTML'
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset notification tracking files."""
    try:
        # Clear notification tracking files
        for file_key in ["NOTIFIED_OUT_OF_STOCK_FILE", "NOTIFIED_NEW_PRODUCTS_FILE", "NOTIFIED_PRICE_CHANGES_FILE"]:
            file_path = CONFIG[file_key]
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Removed file: {file_path}")
        
        await update.message.reply_text(
            "✅ <b>Notification tracking reset!</b>\n\n"
            "You will now receive notifications again for products that were previously notified."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error resetting notification tracking: {str(e)}")


async def products_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send all products one by one with images and delivery info (for MONITOR_PIN_CODES)."""
    # This remains largely the same, checking MONITOR_PIN_CODES
    progress_message = await update.message.reply_text(f"📦 Fetching all products and checking delivery for {', '.join(MONITOR_PIN_CODES)}...")
    
    catalog_data = fetch_catalog()
    if not catalog_data:
        await progress_message.edit_text("❌ Failed to fetch products. Please try again later.\n\nIf this error persists, the cookies may have expired. Please update them in the script.")
        return
    
    products = catalog_data.get('products', [])
    if not products:
        await progress_message.edit_text("❌ No products found.")
        return
    
    # Store products in cache with indices
    global PRODUCTS_CACHE
    PRODUCTS_CACHE = {str(i+1): product for i, product in enumerate(products)}
    
    await progress_message.edit_text(f"📤 Sending {len(products)} products...")
    
    for i, product in enumerate(products):
        delivery_info = await check_delivery_for_all_pins(product.get('code'))
        message, image_url = format_product_info(product, index=i, delivery_info=delivery_info)
        
        try:
            if image_url:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_url,
                    caption=message,
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='HTML'
                )
            
            await asyncio.sleep(0.3)
            
            if (i + 1) % 5 == 0:
                await progress_message.edit_text(
                    f"📤 Sending {len(products)} products...\n"
                    f"✅ Sent: {i + 1}/{len(products)}"
                )
        except Exception as e:
            logger.error(f"Error sending product {product.get('code')}: {e}")
    
    await progress_message.edit_text(f"✅ All {len(products)} products sent! Use /checkdelivery <number> to check delivery again.")

# --- MAIN SETUP ---

async def post_init(application: Application) -> None:
    """Post-initialization function to start monitoring."""
    # Start the real-time monitoring task
    application.create_task(monitor_catalog_changes(application))

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("products", products_command))
    application.add_handler(CommandHandler("n", deliverable_products_command)) 
    application.add_handler(CommandHandler("checkdelivery", check_delivery_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Initialize product codes file - ensure initial state is set
    existing_codes = load_product_codes()
    if not existing_codes:
        logger.info("Initializing product codes from API...")
        catalog_data = fetch_catalog()
        if catalog_data:
            products = catalog_data.get('products', [])
            codes = set(product.get('code') for product in products if product.get('code'))
            save_product_codes(codes)
            
            for product in products:
                code = product.get('code')
                if code:
                    PREVIOUS_CATALOG[code] = product
            save_product_details(PREVIOUS_CATALOG)
    
    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
