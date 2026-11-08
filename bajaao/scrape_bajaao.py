#!/usr/bin/env python3
"""
Generic Bajaao collection scraper with resume support.

Usage:
    python3 scrape_bajaao.py classical-guitars
    python3 scrape_bajaao.py ukulele bass-guitars harmoniums
    python3 scrape_bajaao.py --all

Re-run the same command to resume after a crash/disconnect.
Progress is saved per-category in <slug>.progress.json.

Outputs per category:
    <slug>.csv
    <slug>.xlsx
"""

import asyncio
import csv
import json
import os
import random
import sys
import openpyxl
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

CONCURRENCY = 2
STEALTH = Stealth()

ALL_CATEGORIES = [
    "classical-guitars",
    "electro-acoustic-guitars",
    "bass-guitars",
    "7-8-9-string-electric-guitars",
    "12-string-acoustic-guitars",
    "ukulele",
    "acoustic-drum-kits",
    "electronic-drum-kits",
    "cajons",
    "portable-keyboards",
    "digital-pianos",
    "synthesizers",
    "midi-keyboards",
    "arranger-keyboards",
    "guitar-amplifiers",
    "bass-amplifiers",
    "harmoniums",
    "sitars",
    "tablas",
    "tanpuras",
    "veenas",
    "dholak",
    "flutes",
    "santoor",
    "violins",
    "banjos",
    "mandolins",
    "harmonicas",
    "saxophones",
    "trumpets",
    "trombones",
    "clarinets",
]

JS_EXTRACT = """() => {
    const price = document.querySelector('.price__regular')?.innerText?.trim() || null;
    const desc = document.querySelector('.main-product-description')?.innerText?.trim() || null;
    const table = document.querySelector('table.bjs-table');
    const specs = table
        ? Object.fromEntries(
            Array.from(table.querySelectorAll('tr')).slice(1)
                .map(r => [r.querySelector('th.bjs-key'), r.querySelector('td.bjs-value')])
                .filter(([k, v]) => k && v)
                .map(([k, v]) => [k.innerText.trim(), v.innerText.trim()])
          )
        : {};
    return { price, desc, specs };
}"""

FIELDNAMES = ["id", "title", "url", "image", "price", "desc", "specs"]


def progress_path(slug):
    return f"{slug}.progress.json"


def load_progress(slug):
    path = progress_path(slug)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_progress(slug, data):
    with open(progress_path(slug), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def remove_progress(slug):
    path = progress_path(slug)
    if os.path.exists(path):
        os.remove(path)


def write_outputs(slug, products):
    rows = list(products.values())

    csv_path = f"{slug}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows)} rows -> {csv_path}")

    xlsx_path = f"{slug}.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(FIELDNAMES)
    for row in rows:
        ws.append([
            json.dumps(row.get(k)) if isinstance(row.get(k), dict) else row.get(k)
            for k in FIELDNAMES
        ])
    wb.save(xlsx_path)
    print(f"  Wrote {len(rows)} rows -> {xlsx_path}")


async def collect_products(slug, ctx):
    """Scroll the collection page and return product dict keyed by URL."""
    url = f"https://www.bajaao.com/collections/{slug}"
    page = await ctx.new_page()
    await page.goto(url, wait_until="domcontentloaded")
    try:
        await page.wait_for_selector(
            "#wizzy-shopify-collection-page-wrapper .wizzy-result-product",
            timeout=30000,
        )
    except Exception:
        print(f"  No products found for {slug}, skipping.")
        await page.close()
        return {}

    products = {}
    unchanged_rounds = 0
    while unchanged_rounds < 3:
        cards = await page.locator(
            "#wizzy-shopify-collection-page-wrapper .wizzy-result-product"
        ).evaluate_all("""
            cards => cards.map(card => {
                const link = card.querySelector('a[href*="/products/"]');
                const img = card.querySelector('img');
                return {
                    id: card.getAttribute('data-id'),
                    title: card.getAttribute('title'),
                    url: link?.href || null,
                    image: img?.src || img?.dataset.src || null
                };
            })
        """)

        previous_count = len(products)
        for product in cards:
            if not product["url"]:
                continue
            title = (product.get("title") or "").strip()
            if not title or title.upper() == "TEST PRODUCT":
                continue
            if any(x in title.lower() for x in ["open box", "b stock", "b-stock", "refurbished"]):
                continue
            products[product["url"]] = product

        current_count = len(products)
        print(f"  Collected: {current_count} products")
        unchanged_rounds = unchanged_rounds + 1 if current_count == previous_count else 0

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2500)

    await page.close()
    return products


async def fetch_details(slug, products, ctx):
    """Fetch price/desc/specs for each product. Saves progress after each fetch."""
    done_urls = {u for u, p in products.items() if p.get("price")}
    remaining = [u for u in products if u not in done_urls]

    if not remaining:
        print(f"  All {len(products)} details already fetched.")
        return

    print(f"  Resuming details: {len(done_urls)} done, {len(remaining)} remaining")

    queue = asyncio.Queue()
    for u in remaining:
        await queue.put(u)
    completed = len(done_urls)
    total = len(products)

    async def worker():
        nonlocal completed
        pg = await ctx.new_page()
        while True:
            u = await queue.get()
            if u is None:
                queue.task_done()
                break
            try:
                resp = await pg.goto(u, wait_until="domcontentloaded", timeout=20000)
                await pg.wait_for_timeout(random.randint(1500, 3000))
                if resp and resp.status == 403:
                    print(f"  CF challenge, waiting...")
                    await pg.wait_for_timeout(5000)
                    await pg.goto(u, wait_until="domcontentloaded", timeout=20000)
                    await pg.wait_for_timeout(2000)
                result = await pg.evaluate(JS_EXTRACT)
                products[u].update(result)
                completed += 1
                print(f"  Details: {completed}/{total}")
                # Save progress every 10 products
                if completed % 10 == 0:
                    save_progress(slug, {"products": products})
            except Exception as e:
                print(f"  ERROR {u.split('/')[-1][:50]}: {e}")
            finally:
                queue.task_done()
        await pg.close()

    workers = asyncio.gather(*[worker() for _ in range(CONCURRENCY)])
    await queue.join()
    for _ in range(CONCURRENCY):
        await queue.put(None)
    await workers

    # Final save
    save_progress(slug, {"products": products})


async def scrape_category(slug, ctx):
    print(f"\n{'='*60}\n  {slug}\n{'='*60}")

    progress = load_progress(slug)

    if progress and "products" in progress:
        products = progress["products"]
        print(f"  Resumed from checkpoint: {len(products)} products")
    else:
        products = await collect_products(slug, ctx)
        if not products:
            return
        save_progress(slug, {"products": products})
        print(f"  Collection saved: {len(products)} products")

    await fetch_details(slug, products, ctx)

    write_outputs(slug, products)
    remove_progress(slug)
    print(f"  ✓ {slug} complete ({len(products)} products)")


async def main(categories):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        await STEALTH.apply_stealth_async(ctx)

        for slug in categories:
            # Skip if final output already exists and no progress file (already done)
            if os.path.exists(f"{slug}.csv") and not os.path.exists(progress_path(slug)):
                print(f"\n  Skipping {slug} (already completed)")
                continue
            await scrape_category(slug, ctx)

        await browser.close()

    print(f"\n{'='*60}\nAll done. Scraped {len(categories)} categories.\n{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_bajaao.py <slug> [slug2 ...] | --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        cats = ALL_CATEGORIES
    elif sys.argv[1] == "--force":
        # --force <slug> removes progress and re-scrapes
        cats = sys.argv[2:]
        for c in cats:
            remove_progress(c)
            for ext in [".csv", ".xlsx"]:
                if os.path.exists(f"{c}{ext}"):
                    os.remove(f"{c}{ext}")
    else:
        cats = sys.argv[1:]

    asyncio.run(main(cats))
