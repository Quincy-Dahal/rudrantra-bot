"""
products/knowledge.py
"""

from django.core.cache import cache

from .models import Product

# Cached indefinitely rather than on a TTL - the catalog only
# actually changes when sync_products runs, so time-based expiry would
# either serve stale data between syncs or rebuild needlessly often. The
# sync command explicitly deletes this key when it finishes, which is the
# only thing that should ever invalidate it.
CATALOG_CACHE_KEY = "product_catalog_text"


def build_product_catalog_text():
    """
    Returns the cached catalog text, building and caching it on a miss.
    See _build_product_catalog_text() for the actual content.
    """
    return cache.get_or_set(CATALOG_CACHE_KEY, _build_product_catalog_text, timeout=None)


def _build_product_catalog_text():
    """
    Returns a formatted text block listing every active product, grouped by
    category order, with price ranges, meanings, and a coarse stock note -
    the same shape the chatbot's system prompt has always expected, just
    generated fresh from the database each call instead of hardcoded.
    """
    lines = [
        "RUDRANTRA PRODUCT CATALOG",
        "All products are lab-certified and Vedic-energized. Many are sold "
        "in multiple size/option variants at different prices; ranges below "
        "span the cheapest to priciest available option. \"Contact for "
        "price\" means no listed price is available for that option. These "
        "tiers generally reflect size and rarity (larger, rarer items cost "
        "more), but exact measurements per tier aren't published - if asked "
        "for precise sizing, say plainly that exact measurements aren't "
        "listed rather than guessing a number or inventing an explanation, "
        "and offer to connect the customer with the team.",
        "",
        "Stock status shown per product (In stock / Low stock / Out of "
        "stock) is a snapshot from the last sync, not real-time - it can "
        "lag behind actual changes by hours. Treat \"Out of stock\" and "
        "\"Low stock\" as reasonably trustworthy signals worth passing "
        "along, but don't guarantee availability or exact quantities for a "
        "size marked in-stock; for a time-sensitive or large order, suggest "
        "confirming on the product page or via WhatsApp before the customer "
        "commits. If no stock note appears for a product, treat it as "
        "normally available.",
        "",
    ]

    undocumented = []

    products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("variants")
        .order_by("category__name", "display_order", "name")
    )

    for product in products:
        price = product.price_range_display()
        stock_note = product.stock_status_note()
        stock_suffix = f" [{stock_note}]" if stock_note else ""

        if product.meaning:
            lines.append(f"{product.name} - {product.meaning} {price}{stock_suffix}.")
        else:
            lines.append(f"{product.name} - {price}{stock_suffix}.")
            undocumented.append(product.name)

    if undocumented:
      lines.append("")
      lines.append(
          "For products with no detailed meaning listed above ("
          + ", ".join(undocumented)
          + "), you can give the price if asked, but don't mention "
          "meaning, symbolism, or lore at all for these - and don't tell "
          "the customer you're avoiding inventing it either, just skip "
          "straight to recommending a free consultation."
      )

    return "\n".join(lines)