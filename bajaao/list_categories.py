import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        await Stealth().apply_stealth_async(ctx)
        pg = await ctx.new_page()
        await pg.goto("https://www.bajaao.com/collections", wait_until="domcontentloaded")
        await pg.wait_for_timeout(3000)

        # Scroll to load all categories
        for _ in range(20):
            await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await pg.wait_for_timeout(1000)

        links = await pg.evaluate("""() => {
            return Array.from(document.querySelectorAll('a'))
                .filter(a => a.href.includes('/collections/'))
                .map(a => {
                    const t = a.innerText.trim().split('\\n')[0];
                    const h = a.href.split('?')[0];
                    return {text: t, href: h};
                })
                .filter(a => a.text.length > 2 && a.text.length < 60);
        }""")

        seen = set()
        for l in links:
            if l["href"] not in seen:
                seen.add(l["href"])
                print(f'{l["text"][:55]:55s} {l["href"]}')

        await pg.close()
        await browser.close()

asyncio.run(check())
