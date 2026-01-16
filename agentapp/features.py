import pandas as pd
from typing import List, Dict
from agentapp.product_matcher import find_matching_product, MATERIAL_KEYWORDS

KEYWORDS = MATERIAL_KEYWORDS  # For backward compatibility


def build_latest_features(csv_path: str, product: str, feature_names: List[str]):
    """Return latest features for specified product as DataFrame-like row.
    Matches `comm_name` that contains product (case-insensitive).
    """
    df = pd.read_csv(csv_path)

    # Use improved product matching
    mask = find_matching_product(df, product, 'comm_name')

    if mask.sum() == 0:
        raise ValueError(f"No material match found for '{product}' in CSV indices.")

    sub = df[mask]

    # index cols that start with 'indx'
    index_cols = [c for c in sub.columns if c.startswith('indx')]
    df_long = sub.melt(id_vars=['comm_name','comm_code','comm_wt'], value_vars=index_cols,
                       var_name='month', value_name='price_index')
    df_long['month'] = df_long['month'].str.replace('indx','')
    df_long['date'] = pd.to_datetime(df_long['month'], format='%m%Y')
    df_long = df_long.sort_values('date')

    df_long['lag_1'] = df_long.groupby('comm_name')['price_index'].shift(1)
    df_long['lag_3_mean'] = df_long.groupby('comm_name')['price_index'].rolling(3).mean().reset_index(level=0, drop=True)

    df_long = df_long.dropna()
    if df_long.empty:
        raise ValueError(f"Not enough historical data to compute features for '{product}'")

    latest = df_long.sort_values('date').iloc[[-1]]
    return latest[feature_names]
