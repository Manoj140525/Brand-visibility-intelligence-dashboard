"""
Generate a realistic 'dirty' brand dataset for testing.
Run this script ONLY if you don't have the real brand_dirty_dataset.csv.
"""

import pandas as pd
import numpy as np
import random
import os

random.seed(42)
np.random.seed(42)

keywords = ["laptop", "smartphone", "headphones", "smartwatch", "tablet",
            "iphone", "shoes", "camera", "gaming chair", "monitor"]

brands = ["Apple", "Samsung", "Sony", "Dell", "HP", "Lenovo", "ASUS", "Nike",
          "Bose", "Canon", "LG", "OnePlus", "Xiaomi", "Realme", "Boat",
          "JBL", "Sennheiser", "Logitech", "Razer", "MSI"]

platforms = ["Amazon", "Flipkart", "Walmart", "eBay", "Best Buy",
             "AMAZON", "amazon", "flipkart", "FLIPKART"]  # intentionally inconsistent

noise_titles = [
    "{brand} {model} Smartphone 6GB RAM 128GB Storage",
    "{brand} {model} Laptop 16GB RAM 512GB SSD",
    "{brand} {model} Wireless Headphones Noise Cancelling!!!",
    "{brand} {model} Smart Watch GPS Fitness Tracker",
    "{brand} {model} Bluetooth Speaker Portable",
    "{brand} {model} Running Shoes Lightweight ##",
    "{brand} {model} DSLR Camera 24MP 4K Video",
    "{brand} {model} Gaming Chair Ergonomic Lumbar Support",
    "{brand} {model} 4K Monitor 27inch 144Hz",
    "{brand} {model} Wireless Earbuds ANC"
]

models = ["Pro", "Max", "Ultra", "Plus", "Air", "X", "S22", "S23", "14", "15", "16"]

records = []
n = 600

for i in range(n):
    brand = random.choice(brands)
    keyword = random.choice(keywords)
    model = random.choice(models)
    title_template = random.choice(noise_titles)
    title = title_template.format(brand=brand, model=model)

    base_price = random.uniform(500, 150000)
    has_discount = random.random() > 0.4
    if has_discount:
        raw_price = round(base_price * random.uniform(1.05, 1.4), 2)
        price = round(base_price, 2)
    else:
        raw_price = round(base_price, 2)
        price = round(base_price, 2)

    # Intentional dirty data
    if random.random() < 0.08:
        price = "Not Available"
    elif random.random() < 0.05:
        price = -abs(price) if isinstance(price, float) else price
    elif random.random() < 0.04:
        price = f"Rs.{price}"

    if random.random() < 0.07:
        raw_price = None
    elif random.random() < 0.04:
        raw_price = "many"

    rating = round(random.uniform(1.0, 5.0), 1)
    if random.random() < 0.1:
        rating = None
    elif random.random() < 0.05:
        rating = random.choice([0, 6, -1])

    reviews = random.randint(10, 50000)
    if random.random() < 0.08:
        reviews = "many"
    elif random.random() < 0.05:
        reviews = None

    platform = random.choice(platforms)
    if random.random() < 0.05:
        platform = None

    delivery = random.choice(["Free Delivery", "Paid Delivery", "Not Available", None, "FREE", "free delivery"])

    position = random.randint(1, 50)

    records.append({
        "keyword": keyword,
        "title": title,
        "price": price,
        "raw_price": raw_price,
        "rating": rating,
        "Reviews": reviews,
        "platform": platform,
        "delivery": delivery,
        "position": position
    })

# Add some full duplicate rows
for _ in range(30):
    records.append(random.choice(records))

df = pd.DataFrame(records)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand_dirty_dataset.csv")
df.to_csv(out_path, index=False)
print(f"Generated dirty dataset with {len(df)} rows -> {out_path}")
