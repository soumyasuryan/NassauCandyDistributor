#!/bin/bash
# Start the Nassau Candy Dashboard
# This script activates the virtual environment and starts the Streamlit app

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the Streamlit app
echo "Starting Nassau Candy Dashboard..."
streamlit run src/app.py
