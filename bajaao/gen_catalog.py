#!/usr/bin/env python3
"""
Generate catalog.json + sku-map.json from Bajaao CSVs,
compatible with kms-store's import-catalog.ts / upload-images.ts.

Usage:
    python3 gen_catalog.py          # writes to ./out/catalog.json + ./out/sku-map.json
"""

import csv, json, re, os
from pathlib import Path

CSV_DIR = Path(__file__).parent
OUT_DIR = CSV_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)

SKIP_FILES = {"acoustic_guitars.csv", "electric_guitars.csv", "clarinets.csv"}

CATEGORY_MAP = {
    "12-string-acoustic-guitars":    ("12-string-acoustic-guitars",    "12-String Acoustic Guitars",    "guitars"),
    "7-8-9-string-electric-guitars": ("7-8-9-string-electric-guitars", "7/8/9-String Electric Guitars", "guitars"),
    "acoustic-drum-kits":            ("acoustic-drum-kits",            "Acoustic Drum Kits",            "drums-percussion"),
    "arranger-keyboards":            ("arranger-keyboards",            "Arranger Keyboards",            "keyboards-pianos"),
    "banjos":                        ("banjos",                        "Banjos",                        "string-instruments"),
    "bass-amplifiers":               ("bass-amplifiers",               "Bass Amplifiers",               "amplifiers"),
    "bass-guitars":                  ("bass-guitars",                  "Bass Guitars",                  "guitars"),
    "cajons":                        ("cajons",                        "Cajons",                        "drums-percussion"),
    "classical-guitars":             ("classical-guitars",             "Classical Guitars",              "guitars"),
    "dholak":                        ("dholak",                        "Dholak",                        "indian-classical"),
    "digital-pianos":                ("digital-pianos",                "Digital Pianos",                "keyboards-pianos"),
    "electro-acoustic-guitars":      ("electro-acoustic-guitars",      "Electro-Acoustic Guitars",      "guitars"),
    "electronic-drum-kits":          ("electronic-drum-kits",          "Electronic Drum Kits",          "drums-percussion"),
    "flutes":                        ("flutes",                        "Flutes",                        "wind-instruments"),
    "guitar-amplifiers":             ("guitar-amplifiers",             "Guitar Amplifiers",             "amplifiers"),
    "harmonicas":                    ("harmonicas",                    "Harmonicas",                    "wind-instruments"),
    "harmoniums":                    ("harmoniums",                    "Harmoniums",                    "indian-classical"),
    "mandolins":                     ("mandolins",                     "Mandolins",                     "string-instruments"),
    "midi-keyboards":                ("midi-keyboards",                "MIDI Keyboards",                "keyboards-pianos"),
    "portable-keyboards":            ("portable-keyboards",            "Portable Keyboards",            "keyboards-pianos"),
    "santoor":                       ("santoor",                       "Santoor",                       "indian-classical"),
    "saxophones":                    ("saxophones",                    "Saxophones",                    "wind-instruments"),
    "sitars":                        ("sitars",                        "Sitars",                        "indian-classical"),
    "synthesizers":                  ("synthesizers",                  "Synthesizers",                  "keyboards-pianos"),
    "tablas":                        ("tablas",                        "Tablas",                        "indian-classical"),
    "tanpuras":                      ("tanpuras",                      "Tanpuras",                      "indian-classical"),
    "trombones":                     ("trombones",                     "Trombones",                     "wind-instruments"),
    "trumpets":                      ("trumpets",                      "Trumpets",                      "wind-instruments"),
    "ukulele":                       ("ukulele",                       "Ukulele",                       "string-instruments"),
    "veenas":                        ("veenas",                        "Veenas",                        "indian-classical"),
    "violins":                       ("violins",                       "Violins",                       "string-instruments"),
}

PARENT_CATS = {
    "guitars":           "Guitars",
    "drums-percussion":  "Drums & Percussion",
    "keyboards-pianos":  "Keyboards & Pianos",
    "string-instruments":"String Instruments",
    "amplifiers":        "Amplifiers",
    "wind-instruments":  "Wind Instruments",
    "indian-classical":  "Indian Classical",
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

def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower().strip())
    return re.sub(r"-+", "-", re.sub(r"[\s_]+", "-", s)).strip("-")[:120]

def brand_from_title(title):
    t = title.strip()
    if not t: return "Unknown"
    tl = t.lower()
    for prefix, brand in MULTI_WORD_BRANDS.items():
        if tl.startswith(prefix): return brand
    first = t.split()[0]
    return BRAND_FIXES.get(first, first)

def parse_price(p):
    c = re.sub(r"[^\d.]", "", p)
    if not c: return None
    try: return int(float(c) * 100)
    except: return None

def parse_specs(raw):
    if not raw or raw == "{}": return []
    try:
        d = eval(raw)  # it's a Python dict literal in the CSV
        return [{"label": k, "value": str(v)} for k, v in d.items() if v and str(v).strip() not in ("-", "—", "")]
    except:
        return [{"label": "Specs", "value": raw[:500]}]

# ── Build catalog ─────────────────────────────────────────────────────────────
categories = []
seen_cat_slugs = set()
for parent_slug, parent_name in PARENT_CATS.items():
    if parent_slug not in seen_cat_slugs:
        categories.append({"slug": parent_slug, "name": parent_name, "parent": None})
        seen_cat_slugs.add(parent_slug)
for key, (cat_slug, cat_name, parent_slug) in CATEGORY_MAP.items():
    if cat_slug not in seen_cat_slugs:
        categories.append({"slug": cat_slug, "name": cat_name, "parent": parent_slug})
        seen_cat_slugs.add(cat_slug)

brands = set()
products = []
sku_map = {}

csv_files = sorted(p for p in CSV_DIR.glob("*.csv") if p.name not in SKIP_FILES)

for csv_path in csv_files:
    key = csv_path.stem
    if key not in CATEGORY_MAP:
        continue

    cat_slug, cat_name, parent_slug = CATEGORY_MAP[key]

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        pid   = row.get("id", "").strip()
        title = row.get("title", "").strip()
        url   = row.get("url", "").strip()
        image = row.get("image", "").strip()
        price = row.get("price", "").strip()
        desc  = row.get("desc", "").strip()
        specs = row.get("specs", "").strip()
        if not title or not pid: continue

        brand = brand_from_title(title)
        brands.add(brand)
        handle = f"bajaao-{pid}"

        products.append({
            "handle": handle,
            "sourceUrl": url,
            "category": cat_slug,
            "brand": brand,
            "name": title[:300],
            "shortDesc": desc[:200].replace("\n", " ") if desc else None,
            "descriptionMd": desc[:2000] if desc else None,
            "specs": parse_specs(specs),
            "pricePaise": parse_price(price),
            "images": [image] if image else [],
        })

        sku_map[handle] = {
            "sku": f"BAJ-{pid}",
            "slug": f"{slugify(title)}-{pid[-6:]}",
        }

    print(f"  {csv_path.name}: {len(rows)} rows", flush=True)

catalog = {
    "categories": categories,
    "brands": sorted(brands),
    "products": products,
}

with open(OUT_DIR / "catalog.json", "w") as f:
    json.dump(catalog, f, indent=1, ensure_ascii=False)

with open(OUT_DIR / "sku-map.json", "w") as f:
    json.dump(sku_map, f, indent=1, ensure_ascii=False)

print(f"\nWrote {len(products)} products, {len(brands)} brands, {len(categories)} categories")
print(f"  → {OUT_DIR / 'catalog.json'}")
print(f"  → {OUT_DIR / 'sku-map.json'}")
print(f"\nNow run:")
print(f"  cd /Users/datak2501/leet/kms-store/apps/worker")
print(f"  npx tsx scripts/upload-images.ts --data {OUT_DIR} --remote --apply")
