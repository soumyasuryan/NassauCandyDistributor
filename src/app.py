import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import database, pipeline


st.set_page_config(page_title="Nassau Candy — Profitability Dashboard", page_icon="🍬", layout="wide")


def display_error(action, error):
    st.error(f"Unable to {action}: {error}")


def read_default_dataset():
    raw = pd.read_csv("data/nassau_candy_orders.csv")
    return pipeline.process_dataset(raw, is_nassau=True)


def select_source_column(label, columns, key, required=True):
    options = columns if required else ["Not available"] + columns
    matched_index = next((i for i, col in enumerate(options) if str(col).strip().lower() == label.lower()), None)
    default_index = matched_index if matched_index is not None else 0
    selection = st.sidebar.selectbox(label, options, index=default_index, key=key)
    return None if selection == "Not available" else selection


def apply_filters(data, division, product_search, date_range):
    filtered = data.copy()
    if "Order Date" in filtered.columns and date_range and len(date_range) == 2:
        dates = pd.to_datetime(filtered["Order Date"], errors="coerce")
        start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        filtered = filtered.loc[dates.between(start_date, end_date, inclusive="both")]
    if division != "All" and "Division" in filtered.columns:
        filtered = filtered.loc[filtered["Division"].eq(division)]
    if product_search and "Product Name" in filtered.columns:
        filtered = filtered.loc[filtered["Product Name"].astype("string").str.contains(product_search, case=False, na=False, regex=False)]
    return filtered


def product_summary(data):
    required = {"Product Name", "Sales", "Gross Profit", "Units"}
    if not required.issubset(data.columns):
        return pd.DataFrame(columns=["Product Name", "Division", "Sales", "Gross Profit", "Units", "Gross Margin (%)", "Profit per Unit", "Revenue Contribution (%)", "Profit Contribution (%)", "Classification"])
    
    grouping = ["Product Name"] + (["Division"] if "Division" in data.columns else [])
    summary = data.groupby(grouping, dropna=False, as_index=False)[["Sales", "Gross Profit", "Units"]].sum()
    
    if "Division" not in summary.columns:
        summary["Division"] = "Unassigned"
        
    tot_sales = summary["Sales"].sum()
    tot_profit = summary["Gross Profit"].sum()
    
    summary["Gross Margin (%)"] = summary["Gross Profit"].div(summary["Sales"].replace(0, pd.NA)).mul(100).fillna(0.0)
    summary["Profit per Unit"] = summary["Gross Profit"].div(summary["Units"].replace(0, pd.NA)).fillna(0.0)
    summary["Revenue Contribution (%)"] = summary["Sales"].div(tot_sales if tot_sales else 1).mul(100)
    summary["Profit Contribution (%)"] = summary["Gross Profit"].div(tot_profit if tot_profit else 1).mul(100)
    
    avg_sales = summary["Sales"].median()
    avg_margin = summary["Gross Margin (%)"].median()
    
    def classify_product(row):
        is_high_sales = row["Sales"] >= avg_sales
        is_high_margin = row["Gross Margin (%)"] >= avg_margin
        if is_high_sales and is_high_margin:
            return "Star (High Sales / High Margin)"
        elif is_high_sales and not is_high_margin:
            return "Volume Driver (High Sales / Low Margin)"
        elif not is_high_sales and is_high_margin:
            return "Niche Profit (Low Sales / High Margin)"
        return "Underperformer (Low Sales / Low Profit)"

    summary["Classification"] = summary.apply(classify_product, axis=1)
    return summary.sort_values("Gross Profit", ascending=False)


def division_summary(data):
    required = {"Sales", "Gross Profit"}
    if not required.issubset(data.columns):
        return pd.DataFrame(columns=["Division", "Sales", "Gross Profit", "Average Margin (%)", "Financial Health"])
    grouping = "Division" if "Division" in data.columns else None
    if grouping is None:
        return pd.DataFrame({"Division": ["Unassigned"], "Sales": [data["Sales"].sum()], "Gross Profit": [data["Gross Profit"].sum()], "Average Margin (%)": [(data["Gross Profit"].sum() / data["Sales"].sum() * 100) if data["Sales"].sum() else 0.0]})
    
    summary = data.groupby(grouping, dropna=False, as_index=False)[["Sales", "Gross Profit"]].sum()
    summary["Average Margin (%)"] = summary["Gross Profit"].div(summary["Sales"].replace(0, pd.NA)).mul(100).fillna(0.0)
    
    overall_avg = summary["Average Margin (%)"].mean()
    summary["Financial Health"] = summary["Average Margin (%)"].apply(lambda m: "Strong Efficiency" if m >= overall_avg else "Structural Margin Issue")
    return summary.sort_values("Gross Profit", ascending=False)


st.title("🍬 Nassau Candy Distributor Profitability & Margin Performance")
st.caption("Analyze product economics, identify margin risks, and focus on the profit drivers that matter most.")

st.sidebar.header("Workspace")
source = st.sidebar.radio(
    "Data Source",
    ["🍬 Nassau Candy (Default)", "📤 Upload Custom Dataset", "📜 Load Saved History"],
)

data = None
dataset_label = source

if source == "🍬 Nassau Candy (Default)":
    try:
        data = read_default_dataset()
    except Exception as error:
        display_error("load nassau_candy_orders.csv", error)

elif source == "📤 Upload Custom Dataset":
    uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            raw_data = pd.read_csv(uploaded_file)
            st.sidebar.subheader("Column Mapping")
            columns = raw_data.columns.tolist()
            mapping = {
                "Sales": select_source_column("Sales", columns, "map_sales"),
                "Cost": select_source_column("Cost", columns, "map_cost"),
                "Units": select_source_column("Units", columns, "map_units"),
                "Product Name": select_source_column("Product Name", columns, "map_product"),
                "Division": select_source_column("Division", columns, "map_division"),
                "Order Date": select_source_column("Order Date", columns, "map_order_date", required=False),
                "Ship Date": select_source_column("Ship Date", columns, "map_ship_date", required=False),
            }
            clean_mapping = {k: v for k, v in mapping.items() if v is not None}
            data = pipeline.process_dataset(raw_data, clean_mapping, is_nassau=False)
            run_name = st.sidebar.text_input("Run Name", value="Custom Profitability Analysis")
            if st.sidebar.button("Save Run to Supabase", use_container_width=True):
                try:
                    run_id = database.save_run_to_supabase(run_name, data)
                    st.sidebar.success(f"Saved run #{run_id}.")
                except Exception as error:
                    display_error("save this analysis run", error)
        except Exception as error:
            display_error("process the uploaded CSV", error)
    else:
        st.info("Upload a CSV file to begin a custom profitability analysis.")

else:
    try:
        saved_runs = database.get_saved_runs()
        if saved_runs.empty:
            st.info("No saved analysis runs are available yet.")
        elif "run_id" not in saved_runs.columns or "run_name" not in saved_runs.columns:
            st.error("Saved run data is missing required run_id or run_name fields.")
        else:
            labels = saved_runs.apply(lambda row: f"{row['run_name']} · #{row['run_id']}", axis=1)
            selected_label = st.sidebar.selectbox("Previous Run", labels.tolist())
            selected_index = labels.tolist().index(selected_label)
            selected_run = saved_runs.iloc[selected_index]
            dataset_label = str(selected_run["run_name"])
            data = database.load_run_data(selected_run["run_id"])
    except Exception as error:
        display_error("load saved history", error)

if data is None:
    st.stop()

for column in ["Sales", "Cost", "Gross Profit", "Units", "Gross Margin (%)"]:
    if column not in data.columns:
        data[column] = 0.0
    data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)

st.sidebar.divider()
st.sidebar.header("Global Filters")
date_range = None
if "Order Date" in data.columns:
    order_dates = pd.to_datetime(data["Order Date"], errors="coerce").dropna()
    if not order_dates.empty:
        date_range = st.sidebar.date_input("Order Date Range", value=(order_dates.min().date(), order_dates.max().date()), min_value=order_dates.min().date(), max_value=order_dates.max().date())
divisions = sorted(data["Division"].dropna().astype(str).unique().tolist()) if "Division" in data.columns else []
division = st.sidebar.selectbox("Division", ["All"] + divisions)
margin_target = st.sidebar.slider("Margin Target", min_value=0, max_value=60, value=20, format="%d%%")
product_search = st.sidebar.text_input("Product Search")

filtered_data = apply_filters(data, division, product_search, date_range)
st.caption(f"Viewing {len(filtered_data):,} records from {dataset_label}.")

total_sales = filtered_data["Sales"].sum()
total_profit = filtered_data["Gross Profit"].sum()
total_units = filtered_data["Units"].sum()
overall_margin = total_profit / total_sales * 100 if total_sales else 0.0

margin_volatility = filtered_data["Gross Margin (%)"].std() if len(filtered_data) > 1 else 0.0

kpi_1, kpi_2, kpi_3, kpi_4, kpi_5 = st.columns(5)
kpi_1.metric("Total Revenue", f"${total_sales:,.2f}")
kpi_2.metric("Total Gross Profit", f"${total_profit:,.2f}")
kpi_3.metric("Overall Gross Margin", f"{overall_margin:,.2f}%")
kpi_4.metric("Total Units Sold", f"{total_units:,.0f}")
kpi_5.metric("Margin Volatility (StdDev)", f"{margin_volatility:,.2f}%")

products = product_summary(filtered_data)
divisions_data = division_summary(filtered_data)
tab_products, tab_divisions, tab_diagnostics, tab_pareto = st.tabs(["🏆 Product Profitability", "🏢 Division Performance", "📉 Cost & Margin Diagnostics", "📊 Profit Concentration (Pareto)"])
