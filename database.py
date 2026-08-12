import os

import pandas as pd
import streamlit as st
from supabase import create_client


def _get_setting(name):
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.environ.get(name)


def get_supabase_client():
    supabase_url = _get_setting("SUPABASE_URL")
    supabase_key = _get_setting("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured in Streamlit secrets or environment variables.")
    return create_client(supabase_url, supabase_key)


def _numeric_series(df, column):
    return pd.to_numeric(df.get(column, pd.Series(0, index=df.index)), errors="coerce").fillna(0.0)


def save_run_to_supabase(run_name, df_clean):
    if not isinstance(df_clean, pd.DataFrame):
        raise TypeError("df_clean must be a pandas DataFrame.")
    if not isinstance(run_name, str) or not run_name.strip():
        raise ValueError("run_name must be a non-empty string.")

    client = get_supabase_client()
    sales = _numeric_series(df_clean, "Sales")
    gross_profit = _numeric_series(df_clean, "Gross Profit")
    gross_margin = pd.to_numeric(df_clean.get("Gross Margin (%)", pd.Series(index=df_clean.index, dtype=float)), errors="coerce")
    summary = {
        "run_name": run_name.strip(),
        "total_sales": float(sales.sum()),
        "total_profit": float(gross_profit.sum()),
        "avg_margin": float(gross_margin.mean()) if gross_margin.notna().any() else 0.0,
        "total_records": int(len(df_clean)),
    }
    response = client.table("analysis_runs").insert(summary).execute()
    records = getattr(response, "data", None) or []
    if not records or records[0].get("run_id") is None:
        raise RuntimeError("Supabase did not return a run_id for the saved analysis.")
    run_id = records[0]["run_id"]

    order_frame = pd.DataFrame({
        "product_name": df_clean.get("Product Name", pd.Series("", index=df_clean.index)).fillna("").astype(str),
        "division": df_clean.get("Division", pd.Series("", index=df_clean.index)).fillna("").astype(str),
        "sales": sales,
        "cost": _numeric_series(df_clean, "Cost"),
        "gross_profit": gross_profit,
        "units": _numeric_series(df_clean, "Units"),
        "gross_margin": gross_margin.fillna(0.0),
        "factory": df_clean.get("Factory", pd.Series("", index=df_clean.index)).where(lambda value: value.notna(), None),
    })
    order_frame.insert(0, "run_id", run_id)
    payload = order_frame.where(pd.notna(order_frame), None).to_dict(orient="records")
    for start in range(0, len(payload), 500):
        client.table("run_orders").insert(payload[start:start + 500]).execute()
    return run_id


def get_saved_runs():
    response = get_supabase_client().table("analysis_runs").select("*").order("created_at", desc=True).execute()
    return pd.DataFrame(getattr(response, "data", None) or [])


def load_run_data(run_id):
    if run_id is None or run_id == "":
        raise ValueError("run_id is required.")
    response = get_supabase_client().table("run_orders").select("*").eq("run_id", run_id).execute()
    df = pd.DataFrame(getattr(response, "data", None) or [])
    column_names = {
        "product_name": "Product Name",
        "division": "Division",
        "sales": "Sales",
        "cost": "Cost",
        "gross_profit": "Gross Profit",
        "units": "Units",
        "gross_margin": "Gross Margin (%)",
        "factory": "Factory",
    }
    df = df.rename(columns=column_names)
    for column in ["Sales", "Cost", "Gross Profit", "Units", "Gross Margin (%)"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    if "Gross Profit" not in df.columns:
        df["Gross Profit"] = pd.Series(dtype=float)
    if "Units" not in df.columns:
        df["Units"] = pd.Series(dtype=float)
    df["Profit per Unit"] = df["Gross Profit"].div(df["Units"].replace(0, pd.NA))
    return df
