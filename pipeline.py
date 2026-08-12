import numpy as np
import pandas as pd


FACTORY_COORDINATES = pd.DataFrame(
    [
        {"Factory": "Lot's O' Nuts", "Latitude": 32.881893, "Longitude": -111.768036},
        {"Factory": "Wicked Choccy's", "Latitude": 32.076176, "Longitude": -81.088371},
        {"Factory": "Sugar Shack", "Latitude": 48.119140, "Longitude": -96.181150},
        {"Factory": "Secret Factory", "Latitude": 41.446333, "Longitude": -90.565487},
        {"Factory": "The Other Factory", "Latitude": 35.117500, "Longitude": -89.971107},
    ]
)

PRODUCT_FACTORY_MAPPING = pd.DataFrame(
    [
        {"Product Name": "Wonka Bar - Nutty Crunch Surprise", "Factory": "Lot's O' Nuts"},
        {"Product Name": "Wonka Bar - Fudge Mallows", "Factory": "Lot's O' Nuts"},
        {"Product Name": "Wonka Bar -Scrumdiddlyumptious", "Factory": "Lot's O' Nuts"},
        {"Product Name": "Wonka Bar - Milk Chocolate", "Factory": "Wicked Choccy's"},
        {"Product Name": "Wonka Bar - Triple Dazzle Caramel", "Factory": "Wicked Choccy's"},
        {"Product Name": "Laffy Taffy", "Factory": "Sugar Shack"},
        {"Product Name": "SweeTARTS", "Factory": "Sugar Shack"},
        {"Product Name": "Nerds", "Factory": "Sugar Shack"},
        {"Product Name": "Fun Dip", "Factory": "Sugar Shack"},
        {"Product Name": "Fizzy Lifting Drinks", "Factory": "Sugar Shack"},
        {"Product Name": "Everlasting Gobstopper", "Factory": "Secret Factory"},
        {"Product Name": "Hair Toffee", "Factory": "The Other Factory"},
        {"Product Name": "Lickable Wallpaper", "Factory": "Secret Factory"},
        {"Product Name": "Wonka Gum", "Factory": "Secret Factory"},
        {"Product Name": "Kazookles", "Factory": "The Other Factory"},
    ]
)


def _to_numeric(series):
    cleaned = series.astype("string").str.replace(r"[^0-9.\\-]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def _parse_dates(series):
    try:
        return pd.to_datetime(series, dayfirst=True, format="mixed", errors="coerce")
    except (TypeError, ValueError):
        return pd.to_datetime(series, dayfirst=True, errors="coerce")


def process_dataset(df, col_mapping=None, is_nassau=True):
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    cleaned = df.copy()
    if col_mapping:
        inv_mapping = {}
        for standard, raw in col_mapping.items():
            if raw in cleaned.columns:
                inv_mapping[raw] = standard
        if inv_mapping:
            cleaned = cleaned.rename(columns=inv_mapping)

    cleaned = cleaned.loc[:, ~cleaned.columns.duplicated(keep="first")].copy()

    for column in ["Product Name", "Division"]:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].astype("string").str.strip().replace("", pd.NA)

    for column in ["Order Date", "Ship Date"]:
        if column in cleaned.columns:
            cleaned[column] = _parse_dates(cleaned[column])
    if {"Order Date", "Ship Date"}.issubset(cleaned.columns):
        cleaned["Shipping Days"] = (cleaned["Ship Date"] - cleaned["Order Date"]).dt.days

    for column in ["Sales", "Cost", "Gross Profit", "Units"]:
        if column in cleaned.columns:
            cleaned[column] = _to_numeric(cleaned[column])
    for column in ["Sales", "Cost", "Units"]:
        if column not in cleaned.columns:
            cleaned[column] = 0.0
    if "Gross Profit" not in cleaned.columns:
        cleaned["Gross Profit"] = cleaned["Sales"] - cleaned["Cost"]

    nonzero_sales = cleaned["Sales"].replace(0, np.nan)
    nonzero_units = cleaned["Units"].replace(0, np.nan)
    cleaned["Gross Margin (%)"] = cleaned["Gross Profit"].div(nonzero_sales).mul(100)
    cleaned["Profit per Unit"] = cleaned["Gross Profit"].div(nonzero_units)
    cleaned["Unit Price"] = cleaned["Sales"].div(nonzero_units)
    cleaned["Unit Cost"] = cleaned["Cost"].div(nonzero_units)

    has_product_column = "Product Name" in cleaned.columns
    has_product_matches = has_product_column and cleaned["Product Name"].isin(PRODUCT_FACTORY_MAPPING["Product Name"]).any()
    if has_product_column and (is_nassau or has_product_matches):
        cleaned = cleaned.drop(columns=[column for column in ["Factory", "Latitude", "Longitude"] if column in cleaned.columns])
        cleaned = cleaned.merge(PRODUCT_FACTORY_MAPPING, on="Product Name", how="left")
        cleaned = cleaned.merge(FACTORY_COORDINATES, on="Factory", how="left")
    return cleaned