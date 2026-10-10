# Brand Visibility Intelligence Dashboard

> End-to-end E-commerce Analytics Dashboard built with **Python · Streamlit · SQLite · Plotly**

![Dashboard Preview](screenshots/dashboard_overview.jpg)

---

## 📑 Project Deliverables
- 📊 **Interactive Dashboard:** `app.py` (Streamlit + Plotly)
- 📝 **Technical Project Report (Word):** [`Brand_Visibility_Intelligence_Project_Report.docx`](Brand_Visibility_Intelligence_Project_Report.docx)
- 📖 **Comprehensive Analytics Report (Markdown):** [`PROJECT_REPORT.md`](PROJECT_REPORT.md)
- 🧹 **Cleaned Production Dataset:** [`data/brand_clean_dataset.csv`](data/brand_clean_dataset.csv)
- 🗄️ **Relational Database:** `brand_data.db` (SQLite)
- 📸 **Visual Screenshots:** [`screenshots/`](screenshots/)

---

## 📁 Project Structure

```
Dashboard/
├── app.py                        ← Main Streamlit dashboard (6 tabs)
├── etl_pipeline.py               ← Full ETL: load CSV → clean → feature engineer → SQLite
├── db_utils.py                   ← SQL query helpers for all dashboard tabs
├── requirements.txt              ← Python dependencies
├── .env.example                  ← Copy to .env and add your SerpAPI key
├── .streamlit/
│   └── config.toml               ← Dark theme configuration
└── data/
    ├── brand_dirty_dataset.csv   ← ⬅ Place your dirty CSV here
    ├── brand_clean_dataset.csv   ← Auto-generated after ETL
    └── generate_sample_data.py   ← Run this to generate demo data if needed
```

---

## 🚀 Quick Start

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Add your data
Place your `brand_dirty_dataset.csv` in the `data/` folder.

> **No CSV yet?** Run the sample data generator:
> ```bash
> python data/generate_sample_data.py
> ```

### Step 3 — (Optional) Configure SerpAPI
Copy `.env.example` → `.env` and add your SerpAPI key:
```env
SERPAPI_KEY=your_key_here
```
Get a free key at: https://serpapi.com/

### Step 4 — Run the ETL Pipeline
```bash
python etl_pipeline.py
```
This will:
- Load and clean the dirty dataset
- Optionally fetch live data from SerpAPI
- Engineer features (brand, discount %, visibility score, price range)
- Save cleaned data to `brand_data.db` (SQLite)

### Step 5 — Launch the Dashboard
```bash
streamlit run app.py
```
Open your browser to **http://localhost:8501**

---

## 📊 Dashboard Features

| Tab | KPIs | Charts |
|-----|------|--------|
| 🌐 Overview | Total Products, Avg Price, Avg Rating, Total Reviews, Avg Visibility | Price histogram, Platform pie, Products per keyword |
| 🏷️ Brand Insights | Total Brands, Top Brand, Highest Rated, Best Visibility | Brand count, Brand avg rating, Top-10 brands, Visibility score |
| 💰 Pricing | Avg Price, Max Price, Min Price, % Discounted | Price by brand, Price range pie, Price vs Rank scatter, Discount by brand/platform |
| 🏪 Platform | Total Platforms, Best Rating, Cheapest, Most Products | Product count, Avg rating, Avg price per platform |
| 👁️ Visibility | Avg Rating, Avg Visibility, Best Ranked, % Top-10 | Ranking distribution, Visibility by brand, Rating vs Ranking bubble |
| 🔍 Explorer | Filtered KPIs | Searchable table, Top-10 products, Rating vs Price, Reviews vs Price scatter |

All tabs support **dynamic sidebar filters**: Keyword · Platform · Brand · Price Range · Rating Range

---

## 🔧 ETL Pipeline Steps

1. **Load CSV** — `brand_dirty_dataset.csv`
2. **Data Cleaning**:
   - Convert messy prices (₹, "Not Available") to float
   - Fix invalid ratings (outside 1–5 range)
   - Normalize platform names (Amazon/AMAZON/amazon → Amazon)
   - Remove duplicates (title + price)
   - Impute missing values with medians
3. **SerpAPI Extraction** — Fetch live Google Shopping results (if key configured)
4. **Merge** — Combine CSV and API data using `pd.concat()`
5. **Feature Engineering**:
   - `brand` — Extracted from product title
   - `visibility_score` — Inverse of search rank position (0–100)
   - `price_range` — Categorized buckets (Budget/Mid/Premium/Luxury)
   - `discount` — `(raw_price - price) / raw_price × 100`
6. **Store to SQLite** — `brand_data.db`, table: `products`

---

## 📦 Dataset Columns

| Column | Type | Description |
|--------|------|-------------|
| keyword | str | Search term used (e.g., "laptop") |
| title | str | Product name/title |
| price | float | Final price after discount |
| raw_price | float | Original price before discount |
| rating | float | User rating (1–5) |
| reviews | int | Number of customer reviews |
| platform | str | E-commerce platform (Amazon, Flipkart, etc.) |
| position | int | Search result position |
| delivery | str | Delivery type |
| brand | str | Extracted brand name |
| discount | float | Discount percentage |
| visibility_score | float | Visibility score (0–100) |
| price_range | str | Price category bucket |

---

## 📋 Project Deliverables Checklist

- [x] ETL Pipeline (API + CSV extraction, cleaning, transformation)
- [x] Data Cleaning (all 20+ checks from project document)
- [x] Feature Engineering (brand, visibility, discount, price range)
- [x] SQL Storage (SQLite with dynamic querying)
- [x] EDA (30 business questions answered via charts)
- [x] Interactive Streamlit Dashboard (6 tabs, 20+ charts)
- [x] Sidebar Filters connected to SQL queries
- [ ] Project Report (PDF)
- [ ] GitHub Repository
