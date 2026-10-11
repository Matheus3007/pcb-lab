"""JLCPCB catalog lookups (anonymous public parts-search endpoint).

Results are cached in lib/jlc_cache.json so builds are reproducible offline; refresh
with `python -m pcbkit parts --refresh`. Stock and price are only meaningful at refresh time.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

SEARCH_URL = (
    "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
)
CACHE = Path(__file__).resolve().parents[2] / "lib" / "jlc_cache.json"

# componentLibraryType values seen from the API
TIERS = {"base": "basic", "expand": "extended"}


def _load_cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def _save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")


def fetch(lcsc: str) -> dict:
    r = requests.post(
        SEARCH_URL,
        json={"keyword": lcsc, "currentPage": 1, "pageSize": 10},
        timeout=20,
    )
    r.raise_for_status()
    items = r.json()["data"]["componentPageInfo"]["list"] or []
    hit = next((i for i in items if i.get("componentCode") == lcsc), None)
    if hit is None:
        raise LookupError(f"{lcsc} not found in JLC catalog")
    prices = sorted(hit.get("componentPrices") or [], key=lambda p: p["startNumber"])
    tier = TIERS.get(hit.get("componentLibraryType"), hit.get("componentLibraryType"))
    if tier == "extended" and hit.get("preferredComponentFlag"):
        tier = "preferred"
    return {
        "lcsc": lcsc,
        "mpn": hit.get("componentModelEn"),
        "manufacturer": hit.get("componentBrandEn"),
        "package": hit.get("componentSpecificationEn"),
        "description": hit.get("describe") or hit.get("erpComponentName"),
        "tier": tier,
        "stock": hit.get("stockCount"),
        "unit_price_usd": prices[0]["productPrice"] if prices else None,
        "datasheet": hit.get("dataManualUrl"),
        "datasheet_file_id": hit.get("dataManualFileAccessId"),
        "category": hit.get("componentTypeEn"),
        "fetched": time.strftime("%Y-%m-%d"),
    }


DATASHEET_URL = "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/{}"


def lookup(lcsc: str, refresh: bool = False) -> dict:
    cache = _load_cache()
    if refresh or lcsc not in cache or "datasheet_file_id" not in cache[lcsc]:
        cache[lcsc] = fetch(lcsc)
        _save_cache(cache)
    return cache[lcsc]


def datasheet(lcsc: str, dest: Path) -> Path:
    """Download the datasheet PDF through JLC's file endpoint (LCSC's own links return HTML)."""
    info = lookup(lcsc)
    if not info.get("datasheet_file_id"):
        raise LookupError(f"{lcsc}: JLC has no datasheet file")
    if not dest.exists():
        r = requests.get(DATASHEET_URL.format(info["datasheet_file_id"]), timeout=60,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            raise LookupError(f"{lcsc}: datasheet download did not return a PDF")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
    return dest


if __name__ == "__main__":
    import sys

    for code in sys.argv[1:]:
        try:
            print(json.dumps(lookup(code, refresh=True)))
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"lcsc": code, "error": str(e)}))
