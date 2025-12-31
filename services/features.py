import pandas as pd

KEYWORDS = [
    "steel",
    "iron",
    "bars",
    "rods",
    "alloy",
    "metal"
]

def build_latest_features(csv_path: str, feature_names: list):
    """
    Builds latest feature row exactly like training pipeline
    """

    df = pd.read_csv(csv_path)

    # 1. Identify index columns
    index_cols = [c for c in df.columns if c.startswith("indx")]

    # 2. Wide → Long
    df_long = df.melt(
        id_vars=["comm_name", "comm_code", "comm_wt"],
        value_vars=index_cols,
        var_name="month",
        value_name="price_index"
    )

    df_long["month"] = df_long["month"].str.replace("indx", "")
    df_long["date"] = pd.to_datetime(df_long["month"], format="%m%Y")

    # 3. Filter construction materials
    df_long = df_long[
        df_long["comm_name"].str.lower().apply(
            lambda x: any(k in x for k in KEYWORDS)
        )
    ]

    df_long = df_long.sort_values(["comm_name", "date"])

    # 4. Feature engineering
    df_long["lag_1"] = df_long.groupby("comm_name")["price_index"].shift(1)
    df_long["lag_3_mean"] = (
        df_long.groupby("comm_name")["price_index"]
        .rolling(3)
        .mean()
        .reset_index(level=0, drop=True)
    )

    df_long = df_long.dropna()

    # 5. Take the most recent row
    latest = df_long.sort_values("date").iloc[[-1]]

    return latest[feature_names]
