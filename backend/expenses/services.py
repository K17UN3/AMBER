import re
import unicodedata

from .models import Category


OTHER_CATEGORY_NAME = "その他"
KEYWORD_SEPARATOR = re.compile(r"[,\n、;；]+")


def classify_category(shop_name="", raw_ocr_text=""):
    """Return one deterministic category from the configured keyword rules."""
    normalized_sources = [
        normalize_classification_text(shop_name),
        normalize_classification_text(raw_ocr_text),
    ]

    categories = Category.objects.exclude(name=OTHER_CATEGORY_NAME).order_by("id")
    for source in normalized_sources:
        if not source:
            continue
        for category in categories:
            if any(keyword in source for keyword in parse_keywords(category.keywords)):
                return category

    category, _ = Category.objects.get_or_create(
        name=OTHER_CATEGORY_NAME,
        defaults={"keywords": ""},
    )
    return category


def parse_keywords(value):
    return [
        normalized
        for keyword in KEYWORD_SEPARATOR.split(value or "")
        if (normalized := normalize_classification_text(keyword))
    ]


def normalize_classification_text(value):
    return unicodedata.normalize("NFKC", value or "").casefold()
