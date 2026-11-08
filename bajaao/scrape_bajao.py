#!/usr/bin/env python3
"""
Scrape every product in a Bajaao (Shopify) collection.

Infinite scroll on the site is just the frontend paging through products.
Shopify exposes the same data at /collections/<handle>/products.json,
so we page through that instead of driving a browser.

Usage:
    python3 bajaao_scraper.py                       # acoustic-guitars
    python3 bajaao_scraper.py electric-guitars      # any other collection
    python3 bajaao_scraper.py acoustic-guitars --variants   # one row per variant

Outputs (in the current folder):
    <collection>.csv        flattened, spreadsheet-friendly
    <collection>_raw.json   full Shopify data, nothing dropped

No third-party packages needed (Python 3.8+ standard library only).
"""

import csv
import json
import openpyxl
import re
import sys
import time
import urllib.error
import urllib.request
from html import unescape

BASE = "https://www.bajaao.com"
PAGE_SIZE = 30
DELAY_SECONDS = 3
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def fetch_page(collection, page, retries=5):
    url = f"{BASE}/collections/{collection}/products.json?limit={PAGE_SIZE}&page={page}"
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp).get("products", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:                      # rate limited -> back off
                wait = 30 * attempt
                print(f"  429 rate-limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if e.code == 404:
                sys.exit(f"Collection '{collection}' not found (404). Check the URL handle.")
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  network error ({e}), retry {attempt}/{retries}")
            time.sleep(3 * attempt)
    raise RuntimeError(f"Failed to fetch page {page} after {retries} attempts")


def fetch_all(collection):
    products, page = [], 1
    while True:
        batch = fetch_page(collection, page)
        if not batch:
            break
        products.extend(batch)
        print(f"page {page}: +{len(batch)}  (total {len(products)})")
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        time.sleep(DELAY_SECONDS)
    # de-dupe by id, just in case pages shift while we read them
    seen, unique = set(), []
    for p in products:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
    return unique


def strip_html(html):
    text = re.sub(r"<(br|/p|/li|/div)[^>]*>", "\n", html or "", flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def to_float(x):
    try:
        return float(x) if x not in (None, "") else None
    except ValueError:
        return None


def tags_of(p):
    t = p.get("tags") or []
    return ", ".join(t) if isinstance(t, list) else str(t)


def product_rows(products):
    """One row per product, with price range across variants."""
    for p in products:
        variants = p.get("variants", [])
        prices = [v for v in (to_float(v.get("price")) for v in variants) if v is not None]
        mrps = [v for v in (to_float(v.get("compare_at_price")) for v in variants) if v is not None]
        images = [img.get("src") for img in p.get("images", []) if img.get("src")]
        yield {
            "id": p["id"],
            "title": p.get("title"),
            "brand": p.get("vendor"),
            "product_type": p.get("product_type"),
            "price_min": min(prices) if prices else None,
            "price_max": max(prices) if prices else None,
            "mrp_max": max(mrps) if mrps else None,
            "in_stock": any(v.get("available") for v in variants),
            "variant_count": len(variants),
            "skus": " | ".join(v.get("sku") or "" for v in variants if v.get("sku")),
            "tags": tags_of(p),
            "url": f"{BASE}/products/{p.get('handle')}",
            "main_image": images[0] if images else "",
            "all_images": " | ".join(images),
            "description": strip_html(p.get("body_html")),
            "published_at": p.get("published_at"),
            "updated_at": p.get("updated_at"),
        }


def variant_rows(products):
    """One row per variant (colour / size / pack etc.)."""
    for p in products:
        images = {img.get("id"): img.get("src") for img in p.get("images", [])}
        first_img = p["images"][0]["src"] if p.get("images") else ""
        for v in p.get("variants", []):
            fi = v.get("featured_image") or {}
            yield {
                "product_id": p["id"],
                "variant_id": v.get("id"),
                "title": p.get("title"),
                "variant": v.get("title"),
                "brand": p.get("vendor"),
                "product_type": p.get("product_type"),
                "sku": v.get("sku"),
                "price": to_float(v.get("price")),
                "mrp": to_float(v.get("compare_at_price")),
                "in_stock": v.get("available"),
                "url": f"{BASE}/products/{p.get('handle')}?variant={v.get('id')}",
                "image": fi.get("src") or images.get(v.get("image_id")) or first_img,
                "tags": tags_of(p),
            }


def write_excel(rows, path):
    rows = list(rows)
    if not rows:
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(rows[0].keys()))
    for row in rows:
        ws.append(list(row.values()))
    wb.save(path)
    print(f"wrote {len(rows)} rows -> {path}")


def write_csv(rows, path):
    rows = list(rows)
    if not rows:
        print("No rows to write.")
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig -> opens cleanly in Excel
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {path}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    collection = args[0] if args else "acoustic-guitars"
    per_variant = "--variants" in sys.argv

    print(f"Scraping collection: {collection}")
    products = fetch_all(collection)
    print(f"\n{len(products)} unique products")

    with open(f"{collection}_raw.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"wrote raw JSON -> {collection}_raw.json")

    if per_variant:
        rows = list(variant_rows(products))
        write_csv(rows, f"{collection}_variants.csv")
        write_excel(rows, f"{collection}_variants.xlsx")
    else:
        rows = list(product_rows(products))
        write_csv(rows, f"{collection}.csv")
        write_excel(rows, f"{collection}.xlsx")


if __name__ == "__main__":
    main()