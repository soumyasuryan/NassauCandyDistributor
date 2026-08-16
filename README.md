# Nassau Candy Profitability Dashboard

A comprehensive Streamlit application for analyzing candy distributor profitability, product performance, and margin optimization.

## Overview

This dashboard provides insights into:
- **Product Profitability**: Identify which products drive revenue and profit
- **Division Performance**: Compare financial health across business divisions
- **Cost & Margin Analysis**: Diagnose profitability issues and margin volatility
- **Profit Concentration**: Understand the 80/20 principle of profit drivers (Pareto analysis)

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── app.py              # Main Streamlit application
│   ├── pipeline.py         # Data processing and transformation
│   └── database.py         # Supabase database operations
├── data/
│   └── nassau_candy_orders.csv  # Sample dataset
├── config/                 # Configuration files (if needed)
├── docs/                   # Documentation
├── tests/                  # Unit tests
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

1. **Clone or download the project**:
   ```bash
   cd InternshipProject
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Fill in your Supabase credentials:
     ```bash
     cp .env.example .env
     # Edit .env with your actual credentials
     ```

## Running the Application

Start the Streamlit app from the project root directory:

```bash
streamlit run src/app.py
```

The app will open in your default browser at `http://localhost:8501`

## Features

### Data Sources

1. **Nassau Candy (Default)**: Pre-loaded sample dataset
2. **Upload Custom Dataset**: Import your own CSV with flexible column mapping
3. **Load Saved History**: Access previously analyzed runs from Supabase

### Analysis Capabilities

- **Real-time Filtering**: By date range, division, and product search
- **KPI Dashboard**: Total revenue, profit, margin, units sold, and margin volatility
- **Product Classification**: Identifies stars, volume drivers, niche products, and underperformers
- **Financial Health Assessment**: Evaluates division efficiency
- **Data Export**: Save analysis runs to Supabase for historical tracking

## Configuration

### Supabase Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Create two tables:
   - `analysis_runs`: Stores summary data for each analysis
   - `run_orders`: Stores detailed order data for each run
3. Add your Supabase URL and key to `.env`

### Column Mapping

When uploading custom datasets, the app will automatically detect:
- Sales, Cost, Units, Product Name, Division
- Order Date, Ship Date (optional)

## Files Overview

| File | Purpose |
|------|---------|
| `src/app.py` | Main Streamlit UI and application logic |
| `src/pipeline.py` | Data cleaning, processing, and enrichment |
| `src/database.py` | Supabase client and database operations |
| `data/nassau_candy_orders.csv` | Sample dataset for demonstration |

## Data Processing

The pipeline automatically:
- Converts text-based numbers to numeric values
- Parses dates (flexible format support)
- Calculates derived metrics (margin %, profit per unit, etc.)
- Enriches data with factory coordinates for mapping
- Handles missing and invalid data gracefully

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY not configured"
- Ensure `.env` file exists and contains valid credentials
- Restart the Streamlit app after setting environment variables

### CSV Upload Fails
- Verify CSV has required columns or use the column mapping interface
- Check that numeric columns don't contain special characters

### Port Already in Use
```bash
streamlit run src/app.py --server.port 8502
```

## Development

### Adding New Features
1. New data processing logic → `src/pipeline.py`
2. Database operations → `src/database.py`
3. UI updates → `src/app.py`

### Running Tests
```bash
pytest tests/
```

## Dependencies

- **pandas**: Data manipulation and analysis
- **plotly**: Interactive visualizations
- **streamlit**: Web app framework
- **supabase**: Database client
- **numpy**: Numerical computing

See `requirements.txt` for specific versions.

## License

[Add your license here]

## Contact

[Add contact information if needed]

## Future Enhancements

- [ ] Advanced forecasting models
- [ ] Inventory tracking
- [ ] Supplier analysis
- [ ] Route optimization
- [ ] Mobile app version
- [ ] API endpoint for external integrations
