"""
Product name normalization and mapping for Material Wise
Handles common aliases and variations in product names
"""
from typing import Optional
import pandas as pd


# Common product aliases mapping
PRODUCT_ALIASES = {
    'opc': 'ordinary portland cement',
    'opc 53': 'ordinary portland cement',
    'opc-53': 'ordinary portland cement',
    'opc 43': 'ordinary portland cement',
    'opc-43': 'ordinary portland cement',
    '53 grade cement': 'ordinary portland cement',
    '43 grade cement': 'ordinary portland cement',
    '53 grade': 'ordinary portland cement',
    '43 grade': 'ordinary portland cement',
    'ppc': 'pozzolana cement',
    'ppc cement': 'pozzolana cement',
    'portland pozzolana': 'pozzolana cement',
    'white cement': 'white cement',
    'slag cement': 'slag cement',
    'ggbs cement': 'slag cement',
    'cement blocks': 'cement blocks',
    'concrete blocks': 'cement blocks',
    'tmt': 'steel',
    'tmt bars': 'steel',
    'tmt steel': 'steel',
    'steel bars': 'steel',
    'steel rods': 'steel',
    'ms bars': 'steel',
    'mild steel': 'steel',
}


def normalize_product_name(product: str) -> str:
    """
    Normalize a product name to match CSV entries
    
    Args:
        product: Raw product name from user input
        
    Returns:
        Normalized product name that can match CSV entries
    """
    product_lower = product.lower().strip()
    
    # Check exact alias match
    if product_lower in PRODUCT_ALIASES:
        return PRODUCT_ALIASES[product_lower]
    
    # Check if any alias is contained in the product name
    for alias, target in PRODUCT_ALIASES.items():
        if alias in product_lower:
            return target
    
    # Return original if no match found
    return product_lower


def find_matching_product(df: pd.DataFrame, product: str, column: str = 'comm_name') -> pd.Series:
    """
    Find matching products in a DataFrame with flexible matching
    
    Args:
        df: DataFrame containing product data
        product: Product name to search for
        column: Column name to search in (default: 'comm_name')
        
    Returns:
        Boolean Series mask of matching rows
    """
    product_lower = product.lower().strip()
    
    # Try exact match first
    mask = df[column].str.lower().str.contains(product_lower, regex=False, na=False)
    
    if mask.sum() > 0:
        return mask
    
    # Try with normalized name
    normalized = normalize_product_name(product)
    mask = df[column].str.lower().str.contains(normalized, regex=False, na=False)
    
    if mask.sum() > 0:
        return mask
    
    # Try individual keywords (ignore short words)
    keywords = [w for w in product_lower.split() if len(w) > 3]
    for keyword in keywords:
        mask = df[column].str.lower().str.contains(keyword, regex=False, na=False)
        if mask.sum() > 0:
            return mask
    
    # Return empty mask if nothing found
    return pd.Series([False] * len(df), index=df.index)


def get_product_display_name(csv_name: str, original_query: str) -> str:
    """
    Get a user-friendly display name combining the CSV name and original query
    
    Args:
        csv_name: Name from the CSV file
        original_query: Original user query
        
    Returns:
        Combined display name
    """
    if csv_name.lower() in original_query.lower():
        return csv_name
    else:
        return f"{csv_name} (searched as: {original_query})"


# List of construction material keywords for fallback matching
MATERIAL_KEYWORDS = [
    'steel', 'iron', 'bars', 'rods', 'alloy', 'metal',
    'cement', 'concrete', 'mortar', 'plaster',
    'sand', 'aggregate', 'gravel',
    'brick', 'block', 'tile',
    'paint', 'coating', 'finish',
    'pipe', 'fitting', 'plumbing',
    'wire', 'cable', 'electrical'
]


def is_construction_material(text: str) -> bool:
    """Check if text contains construction material keywords"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in MATERIAL_KEYWORDS)
