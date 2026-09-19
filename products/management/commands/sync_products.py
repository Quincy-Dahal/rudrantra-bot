"""
products/management/commands/sync_products.py

Pulls the live product catalog from the Rudrantra Next.js site's
/api/gyaan-products sync endpoint and upserts it into this project's
simplified ProductCategory / Product / ProductVariant schema.
Requires in settings.py / .env:
    GYAAN_SYNC_URL=https://<live-site-domain>/api/gyaan-products
    GYAAN_SYNC_API_KEY=<same shared secret the Next.js route checks>

Usage:
    python manage.py sync_products
    python manage.py sync_products --dry-run
"""

import re

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.html import strip_tags

from products.models import Product, ProductCategory, ProductVariant

PAGE_SIZE_LOG_EVERY = 1  # log each page as it comes in; catalog is small


def _clean_html_text(html):
    """
    Turns simple CMS-authored HTML (headings, paragraphs, list items) into
    plain text suitable for the chatbot's system prompt.
    """
    if not html:
        return ""
    text = re.sub(r"</(li|p|h[1-6]|div)\s*>", ". ", html, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", ". ", text, flags=re.IGNORECASE)
    text = strip_tags(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*\.\s*(\.\s*)+", ". ", text)  # collapse repeated ". . "
    return text.strip(" .") + ("." if text.strip(" .") else "")


class Command(BaseCommand):
    help = "Syncs products from the live Rudrantra site into the local chatbot catalog."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and report what would change, without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        sync_url = getattr(settings, "GYAAN_SYNC_URL", None)
        sync_key = getattr(settings, "GYAAN_SYNC_API_KEY", None)
        if not sync_url or not sync_key:
            self.stderr.write(self.style.ERROR(
                "GYAAN_SYNC_URL and GYAAN_SYNC_API_KEY must be set "
                "(settings.py / .env) before running this command."
            ))
            return

        products_seen = self._fetch_all(sync_url, sync_key)
        self.stdout.write(f"Fetched {len(products_seen)} products from the live site.")

        if dry_run:
            for item in products_seen[:5]:
                self.stdout.write(f"  - {item.get('name')!r}")
            if len(products_seen) > 5:
                self.stdout.write(f"  ... and {len(products_seen) - 5} more")
            self.stdout.write(self.style.WARNING("Dry run - no changes written."))
            return

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            synced_ids = set()

            for item in products_seen:
                live_id = item.get("id")
                name = (item.get("name") or "").strip()
                if not live_id or not name:
                    continue
                synced_ids.add(live_id)

                categories = item.get("categories") or []
                category_name = categories[0]["name"] if categories else "Uncategorized"
                category, _ = ProductCategory.objects.get_or_create(name=category_name)

                fallback_meaning = _clean_html_text(
                    item.get("benefits")
                ) or (item.get("shortDescription") or "").strip()
                is_active = bool(item.get("isPublished")) and not item.get("deletedAt")

                
                product = Product.objects.filter(live_site_id=live_id).first()

                if product is None:
                    product = Product.objects.filter(
                        live_site_id__isnull=True, name__iexact=name
                    ).first()

                if product is None:
                    product = Product.objects.create(
                        live_site_id=live_id,
                        name=name,
                        category=category,
                        meaning=fallback_meaning,
                        is_active=is_active,
                    )
                    created_count += 1
                else:
                    product.live_site_id = live_id
                    product.name = name  # picks up a real-site rename
                    product.category = category
                    product.is_active = is_active
                    if not product.meaning and fallback_meaning:
                        product.meaning = fallback_meaning
                    product.save()
                    updated_count += 1

                self._sync_variants(
                    product,
                    item.get("sizes") or [],
                    item.get("lowStockThreshold") or 5,
                )

            hidden_count = (
                Product.objects.filter(is_active=True, live_site_id__isnull=False)
                .exclude(live_site_id__in=synced_ids)
                .update(is_active=False)
            )

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete: {created_count} created, {updated_count} updated, "
            f"{hidden_count} hidden (no longer on live site)."
        ))
        self.stdout.write(self.style.WARNING(
            "Note: catalog cache (once added) still needs invalidating after this run."
        ))

    def _fetch_all(self, sync_url, sync_key):
        """Pages through the live site's sync endpoint until hasMore is False."""
        products = []
        page = 1
        while True:
            response = requests.get(
                sync_url,
                params={"page": page},
                headers={"x-sync-key": sync_key},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            batch = data.get("products", [])
            products.extend(batch)

            if page % PAGE_SIZE_LOG_EVERY == 0:
                self.stdout.write(f"  fetched page {page}: {len(batch)} products")

            if not data.get("hasMore") or not batch:
                break
            page += 1

        return products

    def _sync_variants(self, product, live_sizes, low_stock_threshold):
        """Replaces this product's variants with the live site's current sizes."""
        live_labels = set()
        for size in live_sizes:
            label = (size.get("sizeName") or "Standard").strip()
            live_labels.add(label)
            ProductVariant.objects.update_or_create(
                product=product,
                label=label,
                defaults={
                    "price": self._clean_price(size.get("price")),
                    "stock_status": self._stock_status(
                        size.get("stock"), low_stock_threshold
                    ),
                },
            )

        if live_labels:
            product.variants.exclude(label__in=live_labels).delete()

    @staticmethod
    def _clean_price(price):
        """
        The live site appears to use 0 as a placeholder for "not priced
        yet" (seen on products with no real price set), not a literal
        free item - so 0 (and anything invalid/missing) maps to None,
        which price_range_display() already renders as "Contact for
        price" rather than "$0".
        """
        if price is None:
            return None
        try:
            price = float(price)
        except (TypeError, ValueError):
            return None
        return price if price > 0 else None

    @staticmethod
    def _stock_status(stock, low_stock_threshold):
        """
        Maps a raw stock count to the coarse status stored locally. `None`
        (field missing/not selected) is treated as in-stock rather than
        guessed low/out - silence about stock isn't evidence of scarcity.
        """
        if stock is None:
            return ProductVariant.StockStatus.IN_STOCK
        if stock <= 0:
            return ProductVariant.StockStatus.OUT_OF_STOCK
        if stock <= low_stock_threshold:
            return ProductVariant.StockStatus.LOW_STOCK
        return ProductVariant.StockStatus.IN_STOCK