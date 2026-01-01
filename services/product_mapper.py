def normalize_product_name(product: str) -> str:
    """
    Maps MOSPI-style names to retail-friendly search terms
    """
    product = product.lower()

    mapping = {
        "stainless steel bars": "stainless steel rod",
        "stainless steel rods": "stainless steel rod",
        "mild steel": "ms steel",
        "tmt": "tmt bar",
        "steel structures": "structural steel",
        "angles": "steel angle",
        "channels": "steel channel",
        "sections": "steel section",
        "flat products": "steel flat",
        "long products": "steel rod"
    }

    for k, v in mapping.items():
        if k in product:
            return v

    # fallback: take first 3 words
    return " ".join(product.split()[:3])
