import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import database
import pipeline


st.set_page_config(page_title="Nassau Candy — Profitability Dashboard", page_icon="🍬", layout="wide")


def display_error(action, error):
    st.error(f"Unable to {action}: {error}")


def read_default_dataset():
    raw = pd.read_csv("nassau_candy_orders.csv")
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

with tab_products:
    if products.empty:
        st.info("No product data matches the active filters.")
    else:
        col_left, col_right = st.columns([3, 2])
        with col_left:
            product_chart = px.bar(products, x="Gross Profit", y="Product Name", color="Division", orientation="h", text_auto=".2s", title="Gross Profit Contribution by Product")
            product_chart.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="Gross Profit ($)", yaxis_title="")
            st.plotly_chart(product_chart, use_container_width=True)
        with col_right:
            quad_chart = px.scatter(products, x="Sales", y="Gross Margin (%)", color="Classification", hover_data=["Product Name"], title="Product Quadrant Matrix (Sales vs Margin)")
            st.plotly_chart(quad_chart, use_container_width=True)
            
        leaderboard = products[["Product Name", "Division", "Sales", "Gross Profit", "Gross Margin (%)", "Profit per Unit", "Revenue Contribution (%)", "Profit Contribution (%)", "Classification"]]
        st.dataframe(
            leaderboard,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sales": st.column_config.NumberColumn("Revenue", format="$%,.2f"),
                "Gross Profit": st.column_config.NumberColumn("Gross Profit", format="$%,.2f"),
                "Gross Margin (%)": st.column_config.NumberColumn("Gross Margin", format="%.2f%%"),
                "Profit per Unit": st.column_config.NumberColumn("Profit / Unit", format="$%,.2f"),
                "Revenue Contribution (%)": st.column_config.NumberColumn("Rev Share", format="%.2f%%"),
                "Profit Contribution (%)": st.column_config.NumberColumn("Profit Share", format="%.2f%%"),
            },
        )

with tab_divisions:
    if divisions_data.empty:
        st.info("No division data matches the active filters.")
    else:
        left_chart, right_chart = st.columns(2)
        with left_chart:
            donut = px.pie(divisions_data, names="Division", values="Gross Profit", hole=0.55, title="Profit Share by Division")
            st.plotly_chart(donut, use_container_width=True)
        with right_chart:
            comparison = px.bar(divisions_data, x="Division", y=["Sales", "Gross Profit"], barmode="group", title="Revenue vs Gross Profit Imbalance by Division")
            comparison.update_layout(yaxis_title="Amount ($)")
            st.plotly_chart(comparison, use_container_width=True)
            
        st.subheader("Division Performance Summary")
        st.dataframe(
            divisions_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sales": st.column_config.NumberColumn("Revenue", format="$%,.2f"),
                "Gross Profit": st.column_config.NumberColumn("Gross Profit", format="$%,.2f"),
                "Average Margin (%)": st.column_config.NumberColumn("Avg Margin", format="%.2f%%"),
            }
        )

with tab_diagnostics:
    if filtered_data.empty:
        st.info("No records match the active filters.")
    else:
        diagnostic_data = filtered_data.copy()
        diagnostic_data["Bubble Units"] = diagnostic_data["Units"].clip(lower=0)
        hover_fields = [column for column in ["Product Name", "Division", "Gross Profit", "Factory"] if column in diagnostic_data.columns]
        scatter = px.scatter(diagnostic_data, x="Cost", y="Sales", color="Gross Margin (%)", size="Bubble Units", hover_data=hover_fields, color_continuous_scale="RdYlGn", title="Cost vs Sales Scatter Analysis")
        scatter.update_layout(xaxis_title="Cost ($)", yaxis_title="Sales ($)")
        st.plotly_chart(scatter, use_container_width=True)
        
        below_target = products.loc[products["Gross Margin (%)"] < margin_target]
        if below_target.empty:
            st.success(f"No products are below the {margin_target}% gross-margin target.")
        else:
            st.warning(f"⚠️ {len(below_target):,} Cost-Heavy / Margin-Poor Products identified below the {margin_target}% threshold requiring repricing, cost renegotiation, or discontinuation review.")
            st.dataframe(below_target[["Product Name", "Division", "Gross Margin (%)", "Gross Profit", "Sales", "Classification"]], use_container_width=True, hide_index=True, column_config={"Gross Margin (%)": st.column_config.NumberColumn("Gross Margin", format="%.2f%%"), "Gross Profit": st.column_config.NumberColumn("Gross Profit", format="$%,.2f"), "Sales": st.column_config.NumberColumn("Revenue", format="$%,.2f")})

with tab_pareto:
    pareto = products.groupby("Product Name", as_index=False)[["Sales", "Gross Profit"]].sum().sort_values("Gross Profit", ascending=False)
    total_pareto_profit = pareto["Gross Profit"].sum()
    total_pareto_sales = pareto["Sales"].sum()
    
    if pareto.empty or total_pareto_profit <= 0:
        st.info("Pareto analysis requires a positive total gross profit.")
    else:
        pareto["Cumulative Profit %"] = pareto["Gross Profit"].cumsum().div(total_pareto_profit).mul(100)
        
        pareto_sales = pareto.sort_values("Sales", ascending=False).copy()
        pareto_sales["Cumulative Sales %"] = pareto_sales["Sales"].cumsum().div(total_pareto_sales if total_pareto_sales else 1).mul(100)
        
        top_profit_count = int((pareto["Cumulative Profit %"] <= 80).sum() + 1)
        top_sales_count = int((pareto_sales["Cumulative Sales %"] <= 80).sum() + 1)
        total_products = len(pareto)
        
        figure = go.Figure()
        figure.add_trace(go.Bar(x=pareto["Product Name"], y=pareto["Gross Profit"], name="Individual Product Profit", marker_color="#8e44ad"))
        figure.add_trace(go.Scatter(x=pareto["Product Name"], y=pareto["Cumulative Profit %"], name="Cumulative Profit %", yaxis="y2", mode="lines+markers", line={"color": "#e67e22", "width": 3}))
        figure.add_shape(type="line", x0=0, x1=1, xref="paper", y0=80, y1=80, yref="y2", line=dict(color="Red", width=2, dash="dash"))
        figure.update_layout(title="Product Profit Pareto Analysis (80/20 Rule)", xaxis={"title": "Product", "tickangle": -45}, yaxis={"title": "Gross Profit ($)"}, yaxis2={"title": "Cumulative Profit (%)", "overlaying": "y", "side": "right", "range": [0, 100]}, legend={"orientation": "h", "y": 1.12})
        st.plotly_chart(figure, use_container_width=True)
        
        st.info(f"**Over-Dependency Risk Analysis:** Top **{top_profit_count:,}** of {total_products:,} products ({(top_profit_count/total_products*100):.1f}%) drive **80%** of company gross profit. Top **{top_sales_count:,}** products drive **80%** of total revenue.")