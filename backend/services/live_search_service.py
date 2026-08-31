"""
live_search_service.py
Fetches real product data from Google Shopping via SerpApi,
then maps results into our Product / PlatformListing schema.
"""
from __future__ import annotations

import os
import re
import hashlib
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY", "")

# Platform domain → internal key mapping
PLATFORM_MAP: dict[str, tuple[str, str]] = {
    "amazon.in":          ("amazon",          "Amazon"),
    "flipkart.com":       ("flipkart",        "Flipkart"),
    "croma.com":          ("croma",           "Croma"),
    "reliancedigital.in": ("reliance_digital", "Reliance Digital"),
    "tatacliq.com":       ("tatacliq",        "Tata CLiQ"),
    "vijaysales.com":     ("vijay_sales",     "Vijay Sales"),
    "myntra.com":         ("myntra",          "Myntra"),
    "meesho.com":         ("meesho",          "Meesho"),
    "snapdeal.com":       ("snapdeal",        "Snapdeal"),
    "nykaa.com":          ("nykaa",           "Nykaa"),
    "ajio.com":           ("ajio",            "Ajio"),
    "decathlon.in":       ("decathlon",       "Decathlon"),
    "bigbasket.com":      ("bigbasket",       "BigBasket"),
    "blinkit.com":        ("blinkit",         "Blinkit"),
    "zepto.com":          ("zepto",           "Zepto"),
    "swiggy.com":         ("swiggy",          "Swiggy Instamart"),
    "jiomart.com":        ("jiomart",         "JioMart"),
    "healthkart.com":     ("healthkart",      "Healthkart"),
    "samsung.com":        ("samsung_shop",    "Samsung Shop"),
    "apple.com":          ("apple",           "Apple Store"),
}

def _map_platform(source: str) -> tuple[str, str]:
    """Map a merchant/source string to (platform_key, platform_display)."""
    source_lower = source.lower()
    for domain, mapping in PLATFORM_MAP.items():
        if domain in source_lower:
            return mapping
    # Generic fallback: slugify the source name
    slug = re.sub(r"[^a-z0-9]+", "_", source_lower).strip("_")
    display = source.strip().title()
    return slug, display

def _extract_price(price_str: str) -> int:
    """Extract integer INR price from strings like '₹24,499' or '$299'."""
    digits = re.sub(r"[^\d]", "", price_str)
    return int(digits) if digits else 0

def _make_product_id(query: str, title: str) -> str:
    """Deterministic slug-style ID for a live product."""
    combined = f"{query}-{title}"
    slug = re.sub(r"[^a-z0-9]+", "-", combined.lower()).strip("-")
    # Keep it short — max 60 chars, append short hash for uniqueness
    h = hashlib.md5(combined.encode()).hexdigest()[:6]
    return f"{slug[:54]}-{h}"

def _build_search_url(platform_key: str, query: str) -> str:
    """Build a real search URL for the platform."""
    q = query.replace(" ", "+")
    urls = {
        "amazon":          f"https://www.amazon.in/s?k={q}",
        "flipkart":        f"https://www.flipkart.com/search?q={q}",
        "croma":           f"https://www.croma.com/searchB?q={q}",
        "reliance_digital":f"https://www.reliancedigital.in/search?q={q}",
        "tatacliq":        f"https://www.tatacliq.com/search/?text={q}",
        "vijay_sales":     f"https://www.vijaysales.com/search/{q}",
        "myntra":          f"https://www.myntra.com/search?q={q}",
        "meesho":          f"https://www.meesho.com/search?q={q}",
        "snapdeal":        f"https://www.snapdeal.com/search?keyword={q}",
        "nykaa":           f"https://www.nykaa.com/search/result/?q={q}",
        "ajio":            f"https://www.ajio.com/s/{q.replace('+','-')}",
        "decathlon":       f"https://www.decathlon.in/search?Ntt={q}",
        "bigbasket":       f"https://www.bigbasket.com/ps/?q={q}",
        "blinkit":         f"https://blinkit.com/s/?q={q}",
        "zepto":           f"https://www.zeptonow.com/search?q={q}",
        "swiggy":          f"https://www.swiggy.com/instamart/search?query={q}",
        "jiomart":         f"https://www.jiomart.com/search/{q}",
        "healthkart":      f"https://www.healthkart.com/search?q={q}",
        "samsung_shop":    f"https://www.samsung.com/in/search/?searchvalue={q}",
        "apple":           f"https://www.apple.com/in/search/{q}",
    }
    return urls.get(platform_key, f"https://www.google.com/search?q={q}+buy+india")

def search_live(query: str) -> list[dict]:
    """
    Call SerpApi Google Shopping for `query`, return a list of Product dicts
    ready to be passed into the agent pipeline.
    Each dict contains all fields expected by the Product schema.
    Returns [] on error or if no results.
    """
    if not SERPAPI_KEY:
        logger.warning("SERPAPI_API_KEY not set — skipping live search")
        return []

    try:
        from serpapi import GoogleSearch
    except ImportError:
        logger.error("google-search-results not installed")
        return []

    try:
        params = {
            "engine": "google_shopping",
            "q": query,
            "gl": "in",       # India geo
            "hl": "en",
            "currency": "INR",
            "num": 20,
            "api_key": SERPAPI_KEY,
        }
        results = GoogleSearch(params).get_dict()
        shopping_results = results.get("shopping_results", [])

        if not shopping_results:
            logger.info(f"SerpApi returned no shopping results for '{query}'")
            return []

        # Group results by similar titles so we get multiple platforms per product card
        # We'll use the first 3 words of the title as a grouping key to merge similar variants
        grouped_products = {}
        for item in shopping_results:
            title = item.get("title", "").strip()
            if not title:
                continue
            price_raw = item.get("price", "")
            price = _extract_price(str(price_raw))
            if price == 0:
                continue

            # Group results by similar titles so we get multiple platforms per product card
            words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()
            base_key = " ".join(words[:4]) if len(words) >= 4 else " ".join(words)

            # Use fuzzy matching to see if it matches an existing group
            group_key = None
            if grouped_products:
                from thefuzz import fuzz
                for existing_key in grouped_products.keys():
                    if fuzz.token_set_ratio(base_key, existing_key) >= 75:
                        group_key = existing_key
                        break
            
            if not group_key:
                group_key = base_key

            source = item.get("source", "Unknown")
            link = item.get("link", "") or item.get("product_link", "")
            thumbnail = item.get("thumbnail", "")
            rating_raw = item.get("rating", 0)
            reviews_raw = item.get("reviews", 0)
            delivery_raw = item.get("delivery", "Check site for delivery")

            platform_key, platform_display = _map_platform(source)

            # Check if we already have this platform for this group (keep cheapest)
            if group_key not in grouped_products:
                grouped_products[group_key] = {
                    "title": title,
                    "thumbnail": thumbnail,
                    "platforms": {}
                }
            
            existing_platforms = grouped_products[group_key]["platforms"]
            if platform_key not in existing_platforms or price < existing_platforms[platform_key]["price"]:
                existing_platforms[platform_key] = {
                    "platform": platform_key,
                    "platform_display": platform_display,
                    "price": price,
                    "original_price": price,
                    "discount_percent": 0,
                    "url": link or _build_search_url(platform_key, query),
                    "in_stock": True,
                    "delivery": str(delivery_raw) if delivery_raw else "Check site for delivery",
                    "rating": float(rating_raw) if rating_raw else 0.0,
                    "total_reviews": int(reviews_raw) if reviews_raw else 0,
                    "offers": [],
                    "reviews": [],
                    "seller": source,
                    "warranty": None,
                }

        # Build Product-shaped dicts
        products: list[dict] = []
        for group_key, data in list(grouped_products.items())[:6]: # Return top 6 distinct products
            title = data["title"]
            platform_list = list(data["platforms"].values())
            
            # Skip products that only have 1 platform if we have others, to prefer multi-platform
            if len(platform_list) == 0:
                continue
                
            cheapest = min(platform_list, key=lambda p: p["price"])
            price = cheapest["price"]
            product_id = _make_product_id(query, title)

            brand = title.split()[0] if title else "Unknown"

            # Detect a rough category
            q_lower = query.lower()
            if any(k in q_lower for k in ["phone", "mobile", "smartphone", "poco", "redmi", "oneplus", "pixel", "galaxy"]):
                category = "electronics"
            elif any(k in q_lower for k in ["laptop", "macbook", "notebook", "chromebook"]):
                category = "electronics"
            elif any(k in q_lower for k in ["headphone", "earphone", "earbud", "airpod", "tws", "iem"]):
                category = "electronics"
            elif any(k in q_lower for k in ["shoe", "racket", "bat", "yoga", "dumbbell", "protein", "sport"]):
                category = "sports"
            elif any(k in q_lower for k in ["vegetable", "fruit", "dairy", "grocery", "kitchen"]):
                category = "groceries_kitchen"
            else:
                category = "electronics"

            product = {
                "id": product_id,
                "name": title,
                "brand": brand,
                "category": category,
                "subcategory": None,
                "image_url": data["thumbnail"],
                "description": f"{title} — live search result across {len(platform_list)} platforms",
                "search_keywords": query.lower().split(),
                "specs": [],
                "platforms": platform_list,
                "price_history": [{"date": "2026-08-01", "platform": cheapest["platform"], "price": price}],
                "best_price": price,
                "best_platform": cheapest["platform"],
                "lowest_ever_price": price,
                "lowest_ever_date": "2026-08-01",
                "ai_verdict": None,
                "buy_recommendation": "compare",
                "is_live": True,
            }
            products.append(product)

        logger.info(f"SerpApi returned {len(products)} grouped products for '{query}'")
        return products

    except Exception as e:
        logger.error(f"SerpApi error: {e}")
        return []
