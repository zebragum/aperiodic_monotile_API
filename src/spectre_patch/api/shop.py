"""Printful storefront support for the /apparel shop.

Flow
----
1. ``GET /v1/shop/products`` serves a cached, public-safe catalog built from
   Printful sync products (the products already configured in the Printful
   dashboard). Retail prices come from Printful, never from the client.
2. ``POST /v1/shop/checkout`` validates the cart against the live catalog,
   persists it as a ``shop_orders`` row, and opens Stripe Checkout with
   US-only shipping address collection.
3. After payment, the Stripe webhook (or the success-page claim fallback)
   submits the order to Printful using the stored cart plus the address
   Stripe collected. Auto-confirm is opt-in via settings; the default keeps
   Printful orders as drafts so nothing charges the fulfillment wallet
   until the store owner flips the switch.

Only ``httpx`` is used, matching the existing Stripe integration.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx
from fastapi import HTTPException

logger = logging.getLogger("spectre_patch.shop")

PRINTFUL_API = "https://api.printful.com"

CATALOG_TTL_SECONDS = 1800.0
MAX_CART_LINES = 20
MAX_LINE_QUANTITY = 10


class PrintfulError(HTTPException):
    """Customer-safe wrapper; raw Printful responses stay in the server log."""

    def __init__(self, status_code: int = 502, detail: str | None = None) -> None:
        super().__init__(
            status_code=status_code,
            detail=detail or "The fulfillment provider rejected the request. Please try again shortly.",
        )


def _headers(api_key: str, store_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if store_id:
        headers["X-PF-Store-Id"] = store_id
    return headers


async def printful_get(api_key: str, path: str, *, store_id: str | None = None) -> dict:
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(
            f"{PRINTFUL_API}/{path.lstrip('/')}",
            headers=_headers(api_key, store_id),
        )
    if resp.status_code >= 400:
        logger.error("printful GET %s failed status=%s body=%s", path, resp.status_code, resp.text[:2000])
        raise PrintfulError()
    return resp.json()


async def printful_post(
    api_key: str,
    path: str,
    body: dict,
    *,
    store_id: str | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=40.0) as client:
        resp = await client.post(
            f"{PRINTFUL_API}/{path.lstrip('/')}",
            json=body,
            headers=_headers(api_key, store_id),
        )
    if resp.status_code >= 400:
        logger.error("printful POST %s failed status=%s body=%s", path, resp.status_code, resp.text[:2000])
        raise PrintfulError()
    return resp.json()


# ------------------------------------------------------------------ catalog --

def _variant_image(variant: dict, product_thumbnail: str | None) -> str | None:
    """Prefer the printed-mockup preview; fall back to the product thumbnail."""

    preview = None
    for f in variant.get("files") or []:
        if f.get("type") == "preview" and f.get("preview_url"):
            return str(f["preview_url"])
        if f.get("preview_url"):
            preview = str(f["preview_url"])
    return preview or product_thumbnail


def _public_variant(variant: dict, product_thumbnail: str | None) -> dict | None:
    try:
        price = f"{float(variant.get('retail_price') or 0.0):.2f}"
    except (TypeError, ValueError):
        return None
    if float(price) <= 0:
        return None
    if variant.get("synced") is False:
        return None
    if str(variant.get("availability_status") or "active") != "active":
        return None
    return {
        "id": int(variant["id"]),
        "name": str(variant.get("name") or ""),
        "size": str(variant.get("size") or "").strip() or None,
        "color": str(variant.get("color") or "").strip() or None,
        "price": price,
        "currency": str(variant.get("currency") or "USD"),
        "image": _variant_image(variant, product_thumbnail),
    }


class CatalogCache:
    """Serve the storefront from memory; refresh from Printful at most once per TTL."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._fetched_at = 0.0
        self._products: list[dict] = []
        self._variant_index: dict[int, dict] = {}

    def _fresh(self) -> bool:
        return bool(self._products) and (time.time() - self._fetched_at) < CATALOG_TTL_SECONDS

    async def _refresh_guarded(self, api_key: str, store_id: str | None) -> None:
        async with self._lock:
            if self._fresh():
                return
            try:
                await self._refresh(api_key, store_id)
            except Exception as e:
                # Keep serving the stale catalog; the next request retries.
                logger.warning("shop catalog refresh failed, keeping stale data: %r", e)
                if not self._products:
                    raise

    async def products(self, api_key: str, store_id: str | None) -> list[dict]:
        if self._fresh():
            return self._products
        if self._products:
            # Stale-while-revalidate: shoppers get the cached catalog
            # instantly and the ~1-call-per-product rebuild runs behind it.
            asyncio.create_task(self._refresh_guarded(api_key, store_id))
            return self._products
        await self._refresh_guarded(api_key, store_id)
        return self._products

    async def variant(self, api_key: str, store_id: str | None, sync_variant_id: int) -> dict | None:
        await self.products(api_key, store_id)
        return self._variant_index.get(int(sync_variant_id))

    async def _refresh(self, api_key: str, store_id: str | None) -> None:
        # /sync/products works for every store type (Shopify-connected stores
        # reject /store/products, which is reserved for Manual Order / API
        # platform stores). Both return the same sync product shape.
        summaries: list[dict] = []
        offset = 0
        while True:
            listing = await printful_get(
                api_key,
                f"/sync/products?limit=100&offset={offset}",
                store_id=store_id,
            )
            page = listing.get("result") or []
            summaries.extend(page)
            paging = listing.get("paging") or {}
            offset += len(page)
            if not page or offset >= int(paging.get("total") or 0):
                break

        products: list[dict] = []
        variant_index: dict[int, dict] = {}
        # Printful rate-limits bursts; cap concurrent detail fetches.
        gate = asyncio.Semaphore(8)

        async def load_detail(summary: dict) -> dict | None:
            if summary.get("is_ignored") or not summary.get("synced"):
                return None
            async with gate:
                detail = await printful_get(api_key, f"/sync/products/{summary['id']}", store_id=store_id)
            result = detail.get("result") or {}
            sync_product = result.get("sync_product") or {}
            thumbnail = sync_product.get("thumbnail_url") or summary.get("thumbnail_url")
            variants = []
            for raw in result.get("sync_variants") or []:
                pub = _public_variant(raw, thumbnail)
                if pub is not None:
                    variants.append(pub)
            if not variants:
                return None
            prices = sorted(float(v["price"]) for v in variants)
            return {
                "id": int(sync_product.get("id") or summary["id"]),
                "name": str(sync_product.get("name") or summary.get("name") or "Untitled"),
                "thumbnail_url": thumbnail,
                "price_min": f"{prices[0]:.2f}",
                "price_max": f"{prices[-1]:.2f}",
                "currency": variants[0]["currency"],
                "variants": variants,
            }

        details = await asyncio.gather(*(load_detail(s) for s in summaries), return_exceptions=True)
        for item in details:
            if isinstance(item, BaseException):
                logger.warning("shop catalog: skipping product after fetch error: %r", item)
                continue
            if item is None:
                continue
            products.append(item)
            for v in item["variants"]:
                variant_index[v["id"]] = {**v, "product_name": item["name"]}

        self._products = products
        self._variant_index = variant_index
        self._fetched_at = time.time()
        logger.info("shop catalog refreshed: products=%d variants=%d", len(products), len(variant_index))

    def invalidate(self) -> None:
        self._fetched_at = 0.0


catalog_cache = CatalogCache()


# --------------------------------------------------------------------- cart --

async def validate_cart(
    api_key: str,
    store_id: str | None,
    raw_items: object,
) -> list[dict]:
    """Resolve client cart lines against the live catalog.

    Returns normalized lines: ``{sync_variant_id, quantity, name, price, currency, image}``.
    Prices always come from the catalog, so a tampered client cannot set them.
    """

    if not isinstance(raw_items, list) or not raw_items:
        raise HTTPException(status_code=422, detail="Cart must be a non-empty list of items")
    if len(raw_items) > MAX_CART_LINES:
        raise HTTPException(status_code=422, detail=f"Cart cannot exceed {MAX_CART_LINES} lines")

    lines: list[dict] = []
    seen: set[int] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=422, detail="Each cart item must be an object")
        try:
            sync_variant_id = int(raw.get("sync_variant_id"))
            quantity = int(raw.get("quantity", 1))
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=422, detail="Cart items need sync_variant_id and quantity") from e
        if quantity < 1 or quantity > MAX_LINE_QUANTITY:
            raise HTTPException(status_code=422, detail=f"Quantity must be between 1 and {MAX_LINE_QUANTITY}")
        if sync_variant_id in seen:
            raise HTTPException(status_code=422, detail="Duplicate cart line for the same variant")
        seen.add(sync_variant_id)

        variant = await catalog_cache.variant(api_key, store_id, sync_variant_id)
        if variant is None:
            raise HTTPException(
                status_code=409,
                detail="An item in your cart is no longer available. Refresh the shop and try again.",
            )
        lines.append(
            {
                "sync_variant_id": sync_variant_id,
                "quantity": quantity,
                "name": variant.get("product_name") or variant["name"],
                "variant_name": variant["name"],
                "price": variant["price"],
                "currency": variant["currency"],
                "image": variant.get("image"),
            }
        )
    return lines


def cart_amount_cents(lines: list[dict]) -> int:
    return sum(round(float(line["price"]) * 100) * int(line["quantity"]) for line in lines)


# ------------------------------------------------------------------- orders --

def build_printful_recipient(session: dict) -> dict:
    """Map a paid Stripe Checkout session to a Printful recipient block."""

    collected = session.get("collected_information") or {}
    shipping = collected.get("shipping_details") or session.get("shipping_details") or {}
    customer = session.get("customer_details") or {}
    address = shipping.get("address") or customer.get("address") or {}
    name = shipping.get("name") or customer.get("name") or ""
    email = customer.get("email") or session.get("customer_email") or ""
    recipient = {
        "name": str(name)[:120],
        "address1": str(address.get("line1") or "")[:120],
        "address2": str(address.get("line2") or "")[:120],
        "city": str(address.get("city") or "")[:80],
        "state_code": str(address.get("state") or "")[:8],
        "country_code": str(address.get("country") or "US")[:2],
        "zip": str(address.get("postal_code") or "")[:16],
        "email": str(email)[:160],
    }
    if not recipient["address2"]:
        recipient.pop("address2")
    if not (recipient["name"] and recipient["address1"] and recipient["city"] and recipient["zip"]):
        raise HTTPException(
            status_code=409,
            detail="The checkout session is missing a complete shipping address.",
        )
    return recipient


async def submit_printful_order(
    api_key: str,
    store_id: str | None,
    *,
    shop_order_id: str,
    recipient: dict,
    cart_lines: list[dict],
    auto_confirm: bool,
) -> dict:
    """Create the Printful order for a paid checkout. Returns the order result."""

    body = {
        "external_id": shop_order_id,
        "recipient": recipient,
        "items": [
            {
                "sync_variant_id": line["sync_variant_id"],
                "quantity": line["quantity"],
                "retail_price": line["price"],
            }
            for line in cart_lines
        ],
    }
    path = "/orders?confirm=1" if auto_confirm else "/orders"
    payload = await printful_post(api_key, path, body, store_id=store_id)
    return payload.get("result") or {}
