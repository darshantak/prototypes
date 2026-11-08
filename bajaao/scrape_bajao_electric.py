#!/usr/bin/env python3
"""
Scrape electric guitars from Bajaao using Playwright (handles Wizzy infinite scroll).

Usage:
    python3 scrape_bajao_electric.py

Outputs:
    electric_guitars.csv
    electric_guitars.xlsx
"""

import asyncio
import csv
import json
import random
import openpyxl
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

URL = "https://www.bajaao.com/collections/electric-guitars"
CONCURRENCY = 2
stealth = Stealth()


async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        await stealth.apply_stealth_async(ctx)
        page = await ctx.new_page()

        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_selector(
            "#wizzy-shopify-collection-page-wrapper .wizzy-result-product",
            timeout=60000
        )

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
            print(f"Collected: {current_count} products")

            unchanged_rounds = unchanged_rounds + 1 if current_count == previous_count else 0

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2500)

        # Fetch detail pages concurrently — each worker owns its page exclusively
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

        urls = list(products.keys())
        queue = asyncio.Queue()
        for url in urls:
            await queue.put(url)
        completed = 0

        async def worker():
            nonlocal completed
            pg = await ctx.new_page()
            while True:
                url = await queue.get()
                if url is None:
                    queue.task_done()
                    break
                try:
                    resp = await pg.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await pg.wait_for_timeout(random.randint(1500, 3000))
                    # retry once if Cloudflare challenge
                    if resp and resp.status == 403:
                        print(f"  CF challenge, waiting...")
                        await pg.wait_for_timeout(5000)
                        resp = await pg.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await pg.wait_for_timeout(2000)
                    result = await pg.evaluate(JS_EXTRACT)
                    products[url].update(result)
                    completed += 1
                    print(f"Details fetched: {completed}/{len(urls)}")
                except Exception as e:
                    print(f"ERROR {url.split('/')[-1][:50]}: {e}")
                finally:
                    queue.task_done()
            await pg.close()

        workers = asyncio.gather(*[worker() for _ in range(CONCURRENCY)])
        await queue.join()
        for _ in range(CONCURRENCY):
            await queue.put(None)
        await workers

        await browser.close()

    rows = list(products.values())
    fieldnames = ["id", "title", "url", "image", "price", "desc", "specs"]

    with open("electric_guitars.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> electric_guitars.csv")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(fieldnames)
    for row in rows:
        ws.append([json.dumps(row.get(k)) if isinstance(row.get(k), dict) else row.get(k) for k in fieldnames])
    wb.save("electric_guitars.xlsx")
    print(f"wrote {len(rows)} rows -> electric_guitars.xlsx")

    print(f"Finished. Total unique products: {len(rows)}")


asyncio.run(scrape())
