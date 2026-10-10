"""
etl_pipeline.py
---------------
Full ETL Pipeline:
  1. Load & clean brand_dirty_dataset.csv
  2. (Optional) Fetch data from SerpAPI
  3. Merge both datasets
  4. Feature engineering (brand extraction, visibility score, price range, discount)
  5. Store cleaned data in SQLite database
"""

import os
import re
import json
import sqlite3
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
DB_PATH    = os.path.join(BASE_DIR, "brand_data.db")
CSV_PATH   = os.path.join(DATA_DIR, "brand_dirty_dataset.csv")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

SEARCH_KEYWORDS = ["laptop", "smartphone", "headphones", "smartwatch", "tablet"]

KNOWN_BRANDS = [
    "Apple", "Samsung", "Sony", "Dell", "HP", "Lenovo", "ASUS", "Nike",
    "Bose", "Canon", "LG", "OnePlus", "Xiaomi", "Realme", "Boat",
    "JBL", "Sennheiser", "Logitech", "Razer", "MSI", "Acer", "Motorola",
    "Google", "Huawei", "Intel", "AMD", "Nvidia", "Microsoft", "Adidas",
    "Puma", "Nikon", "Panasonic", "Philips", "Whirlpool"
]


# ─── Step 1: Clean Price ───────────────────────────────────────────────────────
def clean_price(val):
    """Convert messy price strings to float, or return NaN."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    # Remove currency symbols, text
    s = re.sub(r'[^\d.]', '', s)
    if not s:
        return np.nan
    try:
        v = float(s)
        return v if v > 0 else np.nan
    except ValueError:
        return np.nan


def clean_reviews(val):
    """Convert reviews to integer, or return 0."""
    if pd.isna(val):
        return 0
    s = str(val).strip().lower()
    if s in ("many", "lots", "unknown", ""):
        return 0
    s = re.sub(r'[^\d]', '', s)
    return int(s) if s else 0


def clean_rating(val):
    """Validate rating is between 1-5."""
    try:
        v = float(val)
        return v if 1.0 <= v <= 5.0 else np.nan
    except (ValueError, TypeError):
        return np.nan


def standardize_platform(val):
    """Normalize platform names."""
    if pd.isna(val) or str(val).strip() == "":
        return "Unknown"
    v = str(val).strip().title()
    mapping = {
        "Amazon": "Amazon", "Flipkart": "Flipkart", "Walmart": "Walmart",
        "Ebay": "eBay", "Best Buy": "Best Buy", "Myntra": "Myntra",
        "Meesho": "Meesho", "Snapdeal": "Snapdeal"
    }
    return mapping.get(v, v)


def extract_brand(title, known_brands=KNOWN_BRANDS):
    """Extract brand name from product title."""
    if pd.isna(title):
        return "Unknown"
    t = str(title)
    for brand in known_brands:
        if brand.lower() in t.lower():
            return brand
    words = t.strip().split()
    return words[0].title() if words else "Unknown"


def clean_title(val):
    """Remove special characters and normalize product titles."""
    if pd.isna(val):
        return ""
    t = str(val)
    t = re.sub(r'[!@#$%^&*()]{2,}', '', t)   # Remove repeated special chars
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def categorize_price(price):
    """Categorize price into ranges."""
    if pd.isna(price):
        return "Unknown"
    if price < 1000:
        return "Budget (<1K)"
    elif price < 10000:
        return "Mid (1K-10K)"
    elif price < 50000:
        return "Premium (10K-50K)"
    else:
        return "Luxury (50K+)"


def compute_discount(price, raw_price):
    """Calculate discount percentage."""
    try:
        p, r = float(price), float(raw_price)
        if r > p > 0:
            return round(((r - p) / r) * 100, 2)
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def compute_visibility_score(position, max_pos=50):
    """Higher rank (lower position number) = higher visibility score (0–100)."""
    try:
        pos = int(position)
        return round(max(0, (1 - (pos - 1) / max_pos) * 100), 2)
    except (ValueError, TypeError):
        return 0.0


# ─── Step 2: Load & Clean CSV ─────────────────────────────────────────────────
def load_and_clean_csv(path):
    print(f"\n[ETL] Loading CSV: {path}")
    if not os.path.exists(path):
        print(f"  [WARN] CSV not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path, dtype=str)
    print(f"  Raw shape: {df.shape}")

    # Standardize column names
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    # Rename 'reviews' if it exists with capital
    if 'reviews' not in df.columns and 'Reviews' in df.columns:
        df.rename(columns={'Reviews': 'reviews'}, inplace=True)

    # Clean fields
    df['price']     = df['price'].apply(clean_price) if 'price' in df.columns else np.nan
    df['raw_price'] = df['raw_price'].apply(clean_price) if 'raw_price' in df.columns else np.nan
    df['rating']    = df['rating'].apply(clean_rating) if 'rating' in df.columns else np.nan
    df['reviews']   = df['reviews'].apply(clean_reviews) if 'reviews' in df.columns else 0
    df['platform']  = df['platform'].apply(standardize_platform) if 'platform' in df.columns else "Unknown"
    df['title']     = df['title'].apply(clean_title) if 'title' in df.columns else ""

    # Fill missing prices with median
    median_price = df['price'].median()
    df['price'] = df['price'].fillna(median_price)
    median_raw  = df['raw_price'].fillna(df['price']).median()
    df['raw_price'] = df['raw_price'].fillna(median_raw)

    # Fill missing ratings with median
    median_rating = df['rating'].median()
    df['rating'] = df['rating'].fillna(median_rating)

    # Remove duplicates
    before = len(df)
    df.drop_duplicates(subset=['title', 'price'], keep='first', inplace=True)
    print(f"  Removed {before - len(df)} duplicates. Shape now: {df.shape}")

    df['source'] = 'csv'
    return df


# ─── Step 3: Fetch from SerpAPI ───────────────────────────────────────────────
def fetch_from_serpapi(keywords, api_key):
    if not api_key:
        print("  [WARN] No SerpAPI key. Skipping API extraction.")
        return pd.DataFrame()

    all_records = []
    for kw in keywords:
        print(f"  Fetching SerpAPI for keyword: '{kw}'")
        params = {
            "engine": "google_shopping",
            "q": kw,
            "api_key": api_key,
            "num": 40,
            "gl": "in",
            "hl": "en"
        }
        try:
            resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("shopping_results", [])
            for item in results:
                all_records.append({
                    "keyword":   kw,
                    "title":     item.get("title", ""),
                    "price":     item.get("extracted_price", np.nan),
                    "raw_price": item.get("old_price", item.get("extracted_price", np.nan)),
                    "rating":    item.get("rating", np.nan),
                    "reviews":   item.get("reviews", 0) or 0,
                    "platform":  item.get("source", "Unknown"),
                    "position":  item.get("position", 0),
                    "delivery":  item.get("delivery", "Unknown"),
                })
        except Exception as e:
            print(f"  [ERROR] SerpAPI fetch failed for '{kw}': {e}")

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    df['platform'] = df['platform'].apply(standardize_platform)
    df['rating']   = df['rating'].apply(clean_rating)
    df['title']    = df['title'].apply(clean_title)
    df['source']   = 'api'
    print(f"  Fetched {len(df)} records from SerpAPI.")
    return df


# ─── Step 4: Merge + Feature Engineering ─────────────────────────────────────
def merge_and_engineer(df_csv, df_api):
    frames = [f for f in [df_csv, df_api] if not f.empty]
    if not frames:
        raise ValueError("No data available. Please provide CSV or configure SerpAPI key.")

    df = pd.concat(frames, ignore_index=True)

    # Ensure required columns exist
    for col in ['keyword', 'title', 'price', 'raw_price', 'rating', 'reviews',
                'platform', 'position', 'delivery']:
        if col not in df.columns:
            df[col] = np.nan if col in ('price', 'raw_price', 'rating') else (0 if col in ('reviews', 'position') else "Unknown")

    # Feature engineering
    df['brand']           = df['title'].apply(extract_brand)
    df['discount']        = df.apply(lambda r: compute_discount(r['price'], r['raw_price']), axis=1)
    df['visibility_score']= df['position'].apply(compute_visibility_score)
    df['price_range']     = df['price'].apply(categorize_price)
    df['delivery']        = df['delivery'].fillna("Unknown").apply(lambda x: str(x).strip().title())

    # Final numeric coercion
    df['price']     = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    df['raw_price'] = pd.to_numeric(df['raw_price'], errors='coerce').fillna(df['price'])
    df['rating']    = pd.to_numeric(df['rating'], errors='coerce')
    df['reviews']   = pd.to_numeric(df['reviews'], errors='coerce').fillna(0).astype(int)
    df['position']  = pd.to_numeric(df['position'], errors='coerce').fillna(0).astype(int)
    df['discount']  = pd.to_numeric(df['discount'], errors='coerce').fillna(0)

    # Drop rows with no title
    df = df[df['title'].str.strip() != ""]
    df.reset_index(drop=True, inplace=True)

    print(f"\n[ETL] Final merged dataset: {df.shape}")
    return df


# ─── Step 5: Store in SQLite ──────────────────────────────────────────────────
def store_to_sqlite(df, db_path):
    print(f"\n[ETL] Saving to SQLite: {db_path}")
    conn = sqlite3.connect(db_path)
    df.to_sql("products", conn, if_exists="replace", index=True, index_label="id")
    conn.commit()

    # Verify
    count = pd.read_sql("SELECT COUNT(*) as n FROM products", conn).iloc[0]['n']
    conn.close()
    print(f"  Stored {count} records in 'products' table.")


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_pipeline():
    print("=" * 60)
    print("  BRAND VISIBILITY ETL PIPELINE")
    print("=" * 60)

    os.makedirs(DATA_DIR, exist_ok=True)

    # Check if CSV exists; if not, generate sample data
    if not os.path.exists(CSV_PATH):
        print(f"\n[ETL] brand_dirty_dataset.csv not found. Generating sample data...")
        gen_script = os.path.join(DATA_DIR, "generate_sample_data.py")
        if os.path.exists(gen_script):
            import subprocess
            subprocess.run(["python", gen_script], check=True)
        else:
            print("  [ERROR] No CSV and no generator found. Please add brand_dirty_dataset.csv to data/")
            return

    df_csv = load_and_clean_csv(CSV_PATH)
    df_api = fetch_from_serpapi(SEARCH_KEYWORDS, SERPAPI_KEY)
    df     = merge_and_engineer(df_csv, df_api)

    # Save clean CSV
    clean_csv = os.path.join(DATA_DIR, "brand_clean_dataset.csv")
    df.to_csv(clean_csv, index=False)
    print(f"[ETL] Clean CSV saved: {clean_csv}")

    store_to_sqlite(df, DB_PATH)
    print("\n[ETL] Pipeline complete!")
    return df


if __name__ == "__main__":
    run_pipeline()
