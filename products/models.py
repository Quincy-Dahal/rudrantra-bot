"""
products/models.py
"""

from django.db import models


class ProductCategory(models.Model):

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(
        blank=True,
        help_text="Optional short blurb about this category, shown to the chatbot.",
    )

    class Meta:
        verbose_name_plural = "Product categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    A single product, e.g. "7 Mukhi Rudraksha". Pricing lives on
    ProductVariant rather than here, since most Rudraksha beads come in
    multiple sizes at different prices; a product with only one purchasable
    option (like the Siddha Mala) just gets a single variant.
    """

    live_site_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="The real site's product id, once this row has been matched to it.",
    )
    category = models.ForeignKey(
        ProductCategory, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=200)
    meaning = models.TextField(
        blank=True,
        help_text=(
            "Spiritual meaning/associations, shown to the chatbot as-is. "
            "Leave blank if this isn't documented yet - the bot is "
            "instructed not to invent meanings for undocumented products."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this product from the chatbot without deleting it.",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Controls ordering within a category (lower numbers show "
            "first) - names alone sort oddly (e.g. '10 Mukhi' before "
            "'2 Mukhi'). Leave as 0 if order doesn't matter."
        ),
    )

    class Meta:
        ordering = ["category__name", "display_order", "name"]

    def __str__(self):
        return self.name

    def price_range_display(self):
        """
        Human-readable price range across this product's variants, e.g.
        "$19-$91", "$1,000" (single price), or "Contact for price" (no
        priced variants at all).
        """
        priced = [v.price for v in self.variants.all() if v.price is not None]
        has_contact_only = self.variants.filter(price__isnull=True).exists()

        if not priced:
            return "Contact for price"

        low, high = min(priced), max(priced)
        text = f"${low:,.0f}" if low == high else f"${low:,.0f}-${high:,.0f}"
        if has_contact_only:
            text += " (some sizes: contact for price)"
        return text

    def stock_status_note(self):
        """
        "" when every variant is normal in-stock (nothing worth saying).
        A single label when all variants share one non-default status
        ("Low stock", "Out of stock"). A per-label breakdown when variants
        disagree, listing only the ones that aren't plain in-stock.
        """
        variants = list(self.variants.all())
        if not variants:
            return ""
        statuses = {v.stock_status for v in variants}
        if statuses == {ProductVariant.StockStatus.IN_STOCK}:
            return ""
        if len(statuses) == 1:
            return dict(ProductVariant.StockStatus.choices)[statuses.pop()]
        return "; ".join(
            f"{v.label}: {v.get_stock_status_display()}"
            for v in variants
            if v.stock_status != ProductVariant.StockStatus.IN_STOCK
        )


class ProductVariant(models.Model):
    """
    A specific purchasable size/option of a Product, with its own price.
    price left blank means "Contact for price" on the live site.
    """

    class StockStatus(models.TextChoices):
        IN_STOCK = "in_stock", "In stock"
        LOW_STOCK = "low_stock", "Low stock"
        OUT_OF_STOCK = "out_of_stock", "Out of stock"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    label = models.CharField(
        max_length=50,
        help_text="e.g. Small, Medium, Collector, Super Collector",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave blank for 'Contact for price'.",
    )
    stock_status = models.CharField(
        max_length=20,
        choices=StockStatus.choices,
        default=StockStatus.IN_STOCK,
        help_text="Coarse status synced from the live site - not an exact count.",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product.name} - {self.label}"