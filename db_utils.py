"""
db_utils.py
-----------
Database utilities: connection, query helpers, and filter builders.
"""

import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "brand_data.db")


def get_connection():
    """Return a SQLite connection."""
    return sqlite3.connect(DB_PATH)


def db_exists():
    """Check if database and products table exist."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = get_connection()
        res = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'").fetchone()
        conn.close()
        return res is not None
    except Exception:
        return False


def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute a SQL query and return a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def _and(where: str, condition: str) -> str:
    """
    Append an extra condition to an existing WHERE clause safely.
    - If where is empty  → returns 'WHERE <condition>'
    - If where has text  → returns '<where> AND <condition>'
    This prevents the double-WHERE SQL syntax error.
    """
    if where:
        return f"{where} AND ({condition})"
    return f"WHERE ({condition})"


def build_where_clause(
    keywords=None,
    platforms=None,
    brands=None,
    price_ranges=None,
    rating_min=None,
    rating_max=None,
) -> tuple:
    """Build a dynamic WHERE clause and params tuple from sidebar filters."""
    conditions = []
    params = []

    if keywords:
        placeholders = ",".join("?" * len(keywords))
        conditions.append(f"keyword IN ({placeholders})")
        params.extend(keywords)

    if platforms:
        placeholders = ",".join("?" * len(platforms))
        conditions.append(f"platform IN ({placeholders})")
        params.extend(platforms)

    if brands:
        placeholders = ",".join("?" * len(brands))
        conditions.append(f"brand IN ({placeholders})")
        params.extend(brands)

    if price_ranges:
        placeholders = ",".join("?" * len(price_ranges))
        conditions.append(f"price_range IN ({placeholders})")
        params.extend(price_ranges)

    if rating_min is not None:
        conditions.append("rating >= ?")
        params.append(rating_min)

    if rating_max is not None:
        conditions.append("rating <= ?")
        params.append(rating_max)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, tuple(params)


def get_filter_options() -> dict:
    """Fetch unique values for sidebar filters."""
    if not db_exists():
        return {}

    conn = get_connection()
    keywords   = [r[0] for r in conn.execute("SELECT DISTINCT keyword  FROM products WHERE keyword  IS NOT NULL ORDER BY keyword").fetchall()]
    platforms  = [r[0] for r in conn.execute("SELECT DISTINCT platform FROM products WHERE platform IS NOT NULL ORDER BY platform").fetchall()]
    brands     = [r[0] for r in conn.execute("SELECT DISTINCT brand    FROM products WHERE brand    IS NOT NULL ORDER BY brand").fetchall()]
    price_rngs = [r[0] for r in conn.execute("SELECT DISTINCT price_range FROM products WHERE price_range IS NOT NULL ORDER BY price_range").fetchall()]
    conn.close()

    return {
        "keywords":     keywords,
        "platforms":    platforms,
        "brands":       brands,
        "price_ranges": price_rngs,
    }


def get_overview_kpis(where="", params=()):
    sql = f"""
        SELECT
            COUNT(*)                          AS total_products,
            ROUND(AVG(price), 2)              AS avg_price,
            ROUND(AVG(CASE WHEN rating BETWEEN 1 AND 5 THEN rating END), 2) AS avg_rating,
            SUM(reviews)                      AS total_reviews,
            ROUND(AVG(visibility_score), 2)   AS avg_visibility
        FROM products {where}
    """
    return run_query(sql, params).iloc[0]


def get_price_distribution(where="", params=()):
    w = _and(where, "price > 0")
    return run_query(f"SELECT price FROM products {w}", params)


def get_products_per_keyword(where="", params=()):
    return run_query(f"""
        SELECT keyword, COUNT(*) AS product_count
        FROM products {where}
        GROUP BY keyword ORDER BY product_count DESC
    """, params)


def get_platform_share(where="", params=()):
    return run_query(f"""
        SELECT platform, COUNT(*) AS count
        FROM products {where}
        GROUP BY platform ORDER BY count DESC
    """, params)


def get_brand_product_count(where="", params=()):
    return run_query(f"""
        SELECT brand, COUNT(*) AS product_count
        FROM products {where}
        GROUP BY brand ORDER BY product_count DESC LIMIT 20
    """, params)


def get_brand_avg_rating(where="", params=()):
    return run_query(f"""
        SELECT brand, ROUND(AVG(CASE WHEN rating BETWEEN 1 AND 5 THEN rating END), 2) AS avg_rating
        FROM products {where}
        GROUP BY brand HAVING avg_rating IS NOT NULL ORDER BY avg_rating DESC LIMIT 20
    """, params)


def get_brand_visibility(where="", params=()):
    return run_query(f"""
        SELECT brand, ROUND(AVG(visibility_score), 2) AS avg_visibility
        FROM products {where}
        GROUP BY brand ORDER BY avg_visibility DESC LIMIT 15
    """, params)


def get_top_brands_in_top10(where="", params=()):
    w = _and(where, "position > 0 AND position <= 10")
    return run_query(f"""
        SELECT brand, COUNT(*) AS top10_count
        FROM products {w}
        GROUP BY brand ORDER BY top10_count DESC LIMIT 15
    """, params)


def get_price_by_brand(where="", params=()):
    w = _and(where, "price > 0")
    return run_query(f"""
        SELECT brand, ROUND(AVG(price), 2) AS avg_price
        FROM products {w}
        GROUP BY brand ORDER BY avg_price DESC LIMIT 20
    """, params)


def get_price_range_distribution(where="", params=()):
    return run_query(f"""
        SELECT price_range, COUNT(*) AS count
        FROM products {where}
        GROUP BY price_range ORDER BY count DESC
    """, params)


def get_price_vs_ranking(where="", params=()):
    w = _and(where, "price > 0 AND position > 0")
    return run_query(f"""
        SELECT price, position, rating, brand, title
        FROM products {w}
        LIMIT 500
    """, params)


def get_discount_by_brand(where="", params=()):
    w = _and(where, "discount > 0")
    return run_query(f"""
        SELECT brand, ROUND(AVG(discount), 2) AS avg_discount
        FROM products {w}
        GROUP BY brand ORDER BY avg_discount DESC LIMIT 20
    """, params)


def get_discount_by_platform(where="", params=()):
    w = _and(where, "discount > 0")
    return run_query(f"""
        SELECT platform, ROUND(AVG(discount), 2) AS avg_discount
        FROM products {w}
        GROUP BY platform ORDER BY avg_discount DESC
    """, params)


def get_platform_product_count(where="", params=()):
    return run_query(f"""
        SELECT platform, COUNT(*) AS product_count
        FROM products {where}
        GROUP BY platform ORDER BY product_count DESC
    """, params)


def get_platform_avg_price(where="", params=()):
    w = _and(where, "price > 0")
    return run_query(f"""
        SELECT platform, ROUND(AVG(price), 2) AS avg_price
        FROM products {w}
        GROUP BY platform ORDER BY avg_price DESC
    """, params)


def get_platform_avg_rating(where="", params=()):
    return run_query(f"""
        SELECT platform, ROUND(AVG(CASE WHEN rating BETWEEN 1 AND 5 THEN rating END), 2) AS avg_rating
        FROM products {where}
        GROUP BY platform HAVING avg_rating IS NOT NULL ORDER BY avg_rating DESC
    """, params)


def get_ranking_distribution(where="", params=()):
    w = _and(where, "position > 0")
    return run_query(f"""
        SELECT position, COUNT(*) AS count
        FROM products {w}
        GROUP BY position ORDER BY position
    """, params)


def get_rating_vs_ranking(where="", params=()):
    w = _and(where, "rating BETWEEN 1 AND 5 AND position > 0")
    return run_query(f"""
        SELECT rating, position, reviews, brand, price, title
        FROM products {w}
        LIMIT 500
    """, params)


def get_visibility_by_brand(where="", params=()):
    return run_query(f"""
        SELECT brand, ROUND(AVG(visibility_score), 2) AS avg_visibility
        FROM products {where}
        GROUP BY brand ORDER BY avg_visibility DESC LIMIT 20
    """, params)


def get_top_products(where="", params=(), limit=10):
    w = _and(where, "price > 0")
    return run_query(f"""
        SELECT title, brand, ROUND(price, 2) AS price,
               rating, reviews, platform, ROUND(discount, 2) AS discount,
               ROUND(visibility_score, 2) AS visibility_score, keyword
        FROM products {w}
        ORDER BY visibility_score DESC, rating DESC
        LIMIT {limit}
    """, params)


def get_all_products(where="", params=()):
    return run_query(f"""
        SELECT title, brand, ROUND(price, 2) AS price,
               rating, reviews, platform, ROUND(discount, 2) AS discount,
               ROUND(visibility_score, 2) AS visibility_score, keyword, price_range
        FROM products {where}
        ORDER BY visibility_score DESC
    """, params)


def get_brand_kpis(where="", params=()):
    # Subqueries for rated brands need extra condition
    w_rated = _and(where, "rating BETWEEN 1 AND 5")
    sql = f"""
        SELECT
            COUNT(DISTINCT brand) AS total_brands,
            (SELECT brand FROM products {where} GROUP BY brand ORDER BY COUNT(*) DESC LIMIT 1) AS top_brand,
            (SELECT brand FROM products {w_rated} GROUP BY brand ORDER BY AVG(rating) DESC LIMIT 1) AS highest_rated_brand,
            (SELECT brand FROM products {where} GROUP BY brand ORDER BY AVG(visibility_score) DESC LIMIT 1) AS best_visibility_brand
        FROM products {where}
    """
    # params used: outer where + 3 subqueries (where, w_rated, where, where)
    n = len(params)
    return run_query(sql, params * 4 if n else ()).iloc[0]


def get_pricing_kpis(where="", params=()):
    w = _and(where, "price > 0")
    sql = f"""
        SELECT
            ROUND(AVG(price), 2) AS avg_price,
            MAX(price) AS max_price,
            MIN(CASE WHEN price > 0 THEN price END) AS min_price,
            ROUND(100.0 * SUM(CASE WHEN discount > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_discounted
        FROM products {w}
    """
    return run_query(sql, params).iloc[0]


def get_visibility_kpis(where="", params=()):
    w_pos1 = _and(where, "position = 1")
    sql = f"""
        SELECT
            ROUND(AVG(CASE WHEN rating BETWEEN 1 AND 5 THEN rating END), 2) AS avg_rating,
            ROUND(AVG(visibility_score), 2) AS avg_visibility,
            (SELECT title FROM products {w_pos1} LIMIT 1) AS best_ranked,
            ROUND(100.0 * SUM(CASE WHEN position BETWEEN 1 AND 10 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_top10
        FROM products {where}
    """
    n = len(params)
    return run_query(sql, params * 2 if n else ()).iloc[0]
