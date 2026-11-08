#!/usr/bin/env python3
"""
Upload remaining Bajaao CSV files to Cloudflare D1 + Cloudinary.
Skips acoustic_guitars.csv, electric_guitars.csv, clarinets.csv.

Usage:
    python3 upload_to_d1.py                  # full run
    python3 upload_to_d1.py --dry-run        # no writes
    python3 upload_to_d1.py --no-images      # skip Cloudinary upload
    python3 upload_to_d1.py --only-images    # only upload images for products already in DB
"""

import csv, hashlib, json, os, re, sys, time, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode

# ── Config ────────────────────────────────────────────────────────────────────
CF_API_TOKEN  = os.environ.get("CF_API_TOKEN", "<your-cloudflare-api-token>")
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "<your-cloudflare-account-id>")
DB_ID         = os.environ.get("CF_DB_ID", "<your-d1-database-id>")

CLOUDINARY_CLOUD  = "duprxb8u"
CLOUDINARY_KEY    = "999638925491841"
CLOUDINARY_SECRET = "RJ9cozKrt33vrIMnIiL7pBujEEI"
CLOUDINARY_FOLDER = "kms"

CSV_DIR  = Path(__file__).parent
DRY_RUN  = "--dry-run" in sys.argv
NO_IMGS  = "--no-images" in sys.argv
ONLY_IMGS = "--only-images" in sys.argv

D1_API = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{DB_ID}"

SKIP_FILES = {"acoustic_guitars.csv", "electric_guitars.csv", "clarinets.csv"}

CATEGORY_MAP = {
    "12-string-acoustic-guitars":    ("12-String Acoustic Guitars",    "Guitars"),
    "7-8-9-string-electric-guitars": ("7/8/9-String Electric Guitars", "Guitars"),
    "acoustic-drum-kits":            ("Acoustic Drum Kits",            "Drums & Percussion"),
    "arranger-keyboards":            ("Arranger Keyboards",            "Keyboards & Pianos"),
    "banjos":                        ("Banjos",                        "String Instruments"),
    "bass-amplifiers":               ("Bass Amplifiers",               "Amplifiers"),
    "bass-guitars":                  ("Bass Guitars",                  "Guitars"),
    "cajons":                        ("Cajons",                        "Drums & Percussion"),
    "classical-guitars":             ("Classical Guitars",             "Guitars"),
    "dholak":                        ("Dholak",                        "Indian Classical"),
    "digital-pianos":                ("Digital Pianos",                "Keyboards & Pianos"),
    "electro-acoustic-guitars":      ("Electro-Acoustic Guitars",      "Guitars"),
    "electronic-drum-kits":          ("Electronic Drum Kits",          "Drums & Percussion"),
    "flutes":                        ("Flutes",                        "Wind Instruments"),
    "guitar-amplifiers":             ("Guitar Amplifiers",             "Amplifiers"),
    "harmonicas":                    ("Harmonicas",                    "Wind Instruments"),
    "harmoniums":                    ("Harmoniums",                    "Indian Classical"),
    "mandolins":                     ("Mandolins",                     "String Instruments"),
    "midi-keyboards":                ("MIDI Keyboards",                "Keyboards & Pianos"),
    "portable-keyboards":            ("Portable Keyboards",            "Keyboards & Pianos"),
    "santoor":                       ("Santoor",                       "Indian Classical"),
    "saxophones":                    ("Saxophones",                    "Wind Instruments"),
    "sitars":                        ("Sitars",                        "Indian Classical"),
    "synthesizers":                  ("Synthesizers",                  "Keyboards & Pianos"),
    "tablas":                        ("Tablas",                        "Indian Classical"),
    "tanpuras":                      ("Tanpuras",                      "Indian Classical"),
    "trombones":                     ("Trombones",                     "Wind Instruments"),
    "trumpets":                      ("Trumpets",                      "Wind Instruments"),
    "ukulele":                       ("Ukulele",                       "String Instruments"),
    "veenas":                        ("Veenas",                        "Indian Classical"),
    "violins":                       ("Violins",                       "String Instruments"),
}

MULTI_WORD_BRANDS = {
    "cf martin": "CF Martin", "d'angelico": "D'Angelico", "dv mark": "DV Mark",
    "line 6": "Line 6", "mark bass": "Markbass", "music man": "Music Man",
    "native instruments": "Native Instruments", "michael kelly": "Michael Kelly",
    "sterling by": "Sterling by Music Man", "ik multimedia": "IK Multimedia",
    "ns design": "NS Design", "g&l": "G&L", "adam audio": "ADAM Audio",
    "audio-technica": "Audio-Technica", "carry-on": "Carry-on",
}
BRAND_FIXES = {"CAS-CTX870IN": "Casio", "Hohnerr": "Hohner", "Dw": "DW", "DW": "DW"}

# ── Helpers ───────────────────────────────────────────────────────────────────
def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower().strip())
    return re.sub(r"-+", "-", re.sub(r"[\s_]+", "-", s)).strip("-")[:120]

def parse_price(p):
    c = re.sub(r"[^\d.]", "", p)
    if not c: return None
    try: return int(float(c) * 100)
    except: return None

def brand_from_title(title):
    t = title.strip()
    if not t: return "Unknown"
    tl = t.lower()
    for prefix, brand in MULTI_WORD_BRANDS.items():
        if tl.startswith(prefix): return brand
    first = t.split()[0]
    return BRAND_FIXES.get(first, first)

def esc(s):
    """Escape for SQL string literal."""
    return s.replace("'", "''")

def log(msg, end="\n"):
    print(msg, end=end, flush=True)

# ── D1 API ────────────────────────────────────────────────────────────────────
def d1_query(sql):
    body = json.dumps({"sql": sql}).encode()
    req = Request(f"{D1_API}/query", data=body,
                  headers={"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"})
    with urlopen(req) as resp:
        data = json.loads(resp.read())
    if not data.get("success"):
        raise RuntimeError(f"D1 error: {data.get('errors')}")
    r = data.get("result", [])
    return r[0].get("results", []) if r else []

def d1_batch(statements):
    """Send multiple statements via /raw as a single semicolon-joined SQL string."""
    joined = "\n".join(s.rstrip(";") + ";" for s in statements)
    body = json.dumps({"sql": joined}).encode()
    req = Request(f"{D1_API}/raw", data=body, method="POST",
                  headers={"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"})
    with urlopen(req) as resp:
        data = json.loads(resp.read())
    if not data.get("success"):
        raise RuntimeError(f"D1 batch error: {data.get('errors')}")
    return data

# ── Cloudinary ────────────────────────────────────────────────────────────────
def cloudinary_sign(params: dict) -> str:
    """Generate Cloudinary API signature."""
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
    to_sign = sorted_params + CLOUDINARY_SECRET
    return hashlib.sha1(to_sign.encode()).hexdigest()

def cloudinary_upload_url(image_url: str, public_id: str, transformation: str = None) -> dict | None:
    """Upload an image to Cloudinary by URL. Returns {public_id, width, height, format} or None."""
    timestamp = str(int(time.time()))
    params = {
        "public_id": public_id,
        "timestamp": timestamp,
        "folder": CLOUDINARY_FOLDER,
    }
    if transformation:
        params["transformation"] = transformation

    params["signature"] = cloudinary_sign(params)
    params["api_key"] = CLOUDINARY_KEY
    params["file"] = image_url

    data = urlencode(params).encode()
    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD}/image/upload"
    req = Request(url, data=data, method="POST")
    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read())
        return {
            "public_id": result["public_id"],
            "width": result.get("width", 0),
            "height": result.get("height", 0),
            "format": result.get("format", "jpg"),
        }
    except HTTPError as e:
        body = e.read().decode() if hasattr(e, "read") else ""
        log(f"    Cloudinary error: {e} {body[:200]}")
        return None

# ── Load existing data ────────────────────────────────────────────────────────
log("Fetching existing categories, brands, products…")
existing_cats   = {r["slug"]: r["id"] for r in d1_query("SELECT id, slug FROM categories")}
existing_brands = {r["slug"]: r["id"] for r in d1_query("SELECT id, slug FROM brands")}
sku_rows        = d1_query("SELECT id, sku FROM products")
existing_skus   = {r["sku"] for r in sku_rows}
sku_to_product_id = {r["sku"]: r["id"] for r in sku_rows}
existing_imgs   = {r["product_id"] for r in d1_query("SELECT DISTINCT product_id FROM product_images")}
log(f"  {len(existing_cats)} categories, {len(existing_brands)} brands, {len(existing_skus)} products, {len(existing_imgs)} with images")

cat_cache, brand_cache = {}, {}

def ensure_category(name, parent_name=None):
    slug = slugify(name)
    if slug in cat_cache: return cat_cache[slug]
    if slug in existing_cats:
        cat_cache[slug] = existing_cats[slug]
        return existing_cats[slug]
    parent_id = ensure_category(parent_name) if parent_name else None
    nid = str(uuid.uuid4())
    pid_sql = f"'{parent_id}'" if parent_id else "NULL"
    sql = (f"INSERT OR IGNORE INTO categories (id,name,slug,parent_id,sort_order,is_active,created_at,updated_at) "
           f"VALUES ('{nid}','{esc(name)}','{slug}',{pid_sql},0,1,"
           f"strftime('%Y-%m-%dT%H:%M:%fZ','now'),strftime('%Y-%m-%dT%H:%M:%fZ','now'))")
    log(f"  + category: {name}")
    if not DRY_RUN: d1_query(sql)
    cat_cache[slug] = nid
    existing_cats[slug] = nid
    return nid

def ensure_brand(name):
    slug = slugify(name)
    if slug in brand_cache: return brand_cache[slug]
    if slug in existing_brands:
        brand_cache[slug] = existing_brands[slug]
        return existing_brands[slug]
    nid = str(uuid.uuid4())
    sql = (f"INSERT OR IGNORE INTO brands (id,name,slug,is_active,created_at,updated_at) "
           f"VALUES ('{nid}','{esc(name)}','{slug}',1,"
           f"strftime('%Y-%m-%dT%H:%M:%fZ','now'),strftime('%Y-%m-%dT%H:%M:%fZ','now'))")
    log(f"  + brand: {name}")
    if not DRY_RUN: d1_query(sql)
    brand_cache[slug] = nid
    existing_brands[slug] = nid
    return nid

# ── Process CSVs ──────────────────────────────────────────────────────────────
csv_files = sorted(p for p in CSV_DIR.glob("*.csv") if p.name not in SKIP_FILES)
total_products = 0
total_images = 0

for csv_path in csv_files:
    key = csv_path.stem
    if key not in CATEGORY_MAP:
        log(f"SKIP: {csv_path.name}")
        continue

    cat_name, parent_name = CATEGORY_MAP[key]
    log(f"\n── {csv_path.name} → {cat_name} ──")
    cat_id = ensure_category(cat_name, parent_name)

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # Build product insert statements
    product_rows = []  # (sku, product_id, sql, title, image_url)
    for row in rows:
        pid   = row.get("id", "").strip()
        title = row.get("title", "").strip()
        price = row.get("price", "").strip()
        desc  = row.get("desc", "").strip()
        specs = row.get("specs", "").strip()
        img   = row.get("image", "").strip()
        if not title or not pid: continue

        sku = f"BAJ-{pid}"
        if sku in existing_skus: continue  # already in DB

        brand_id    = ensure_brand(brand_from_title(title))
        base_slug   = slugify(title)
        slug        = f"{base_slug}-{pid[-6:]}"  # append variant ID suffix for uniqueness
        price_paise = parse_price(price)
        short_desc  = esc(desc[:200].replace("\n", " ")) if desc else ""
        desc_md     = esc(desc[:2000]) if desc else ""
        specs_json  = esc(json.dumps([{"label": "Specs", "value": specs[:500]}])) if specs else "[]"

        product_id = str(uuid.uuid4())
        sql = (
            f"INSERT OR IGNORE INTO products "
            f"(id,sku,slug,name,category_id,brand_id,short_desc,description_md,specs_json,"
            f"price_paise,show_price,stock_status,is_featured,is_published,sort_order,created_at,updated_at) "
            f"VALUES ('{product_id}','{esc(sku)}','{esc(slug)}','{esc(title[:300])}',"
            f"'{cat_id}','{brand_id}','{short_desc}','{desc_md}','{specs_json}',"
            f"{'NULL' if price_paise is None else price_paise},"
            f"{'0' if price_paise is None else '1'},'in_stock',0,1,0,"
            f"strftime('%Y-%m-%dT%H:%M:%fZ','now'),strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
        )
        product_rows.append((sku, product_id, sql, title, img))

    new_count = len(product_rows)
    log(f"  {new_count} new products (skipped {len(rows) - new_count} existing)")

    if DRY_RUN or not product_rows:
        total_products += new_count
        continue

    if not ONLY_IMGS:
        # Insert products in batches via /raw
        BATCH = 30
        for i in range(0, len(product_rows), BATCH):
            batch = [r[2] for r in product_rows[i:i + BATCH]]
            try:
                d1_batch(batch)
            except Exception as e:
                log(f"  batch {i} error: {e}, retrying one-by-one…")
                for s in batch:
                    try:
                        d1_query(s)
                    except Exception as e2:
                        log(f"    FAIL: {str(e2)[:100]}")
            done = min(i + BATCH, len(product_rows))
            log(f"  ✓ {done}/{len(product_rows)} products", end="\r" if done < len(product_rows) else "\n")
        for sku, _, _, _, _ in product_rows:
            existing_skus.add(sku)

    # Upload images to Cloudinary + insert into product_images
    if not NO_IMGS:
        img_count = 0
        # For --only-images, build list from ALL rows (lookup product_id by sku)
        if ONLY_IMGS and not product_rows:
            img_candidates = []
            for row in rows:
                pid   = row.get("id", "").strip()
                title = row.get("title", "").strip()
                img   = row.get("image", "").strip()
                if not pid or not title or not img: continue
                sku = f"BAJ-{pid}"
                if sku in sku_to_product_id:
                    img_candidates.append((sku, sku_to_product_id[sku], None, title, img))
            else:
                img_candidates = product_rows
        else:
            img_candidates = product_rows
        for sku, product_id, _, title, image_url in img_candidates:
            if not image_url or product_id in existing_imgs:
                continue

            image_id = str(uuid.uuid4())
            full_public_id = f"products/{product_id}/{image_id}-full"
            thumb_public_id = f"products/{product_id}/{image_id}-thumb"

            # Upload full size
            full_result = cloudinary_upload_url(image_url, full_public_id, "c_limit,w_1500,q_auto,f_webp")
            if not full_result:
                continue

            # Upload thumb
            thumb_result = cloudinary_upload_url(image_url, thumb_public_id, "c_fill,w_400,h_400,q_auto,f_webp")
            if not thumb_result:
                continue

            w = full_result["width"]
            h = full_result["height"]
            full_key = f"products/{product_id}/{image_id}-full.webp"
            thumb_key = f"products/{product_id}/{image_id}-thumb.webp"
            alt = esc(title[:200])

            img_sql = (
                f"INSERT OR IGNORE INTO product_images "
                f"(id,product_id,full_key,thumb_key,width,height,alt,sort_order,created_at) "
                f"VALUES ('{image_id}','{product_id}','{full_key}','{thumb_key}',"
                f"{w},{h},'{alt}',0,strftime('%Y-%m-%dT%H:%M:%fZ','now'))"
            )
            try:
                d1_query(img_sql)
                img_count += 1
                existing_imgs.add(product_id)
            except Exception as e:
                log(f"    img DB error: {e}")

            if img_count % 10 == 0:
                log(f"  📷 {img_count} images uploaded…")

        if img_count:
            log(f"  📷 {img_count} images total")
        total_images += img_count

    total_products += new_count

log(f"\n{'='*50}")
log(f"Total: {total_products} products, {total_images} images")
log(f"{'(DRY RUN)' if DRY_RUN else 'Done!'}")
