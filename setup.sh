#!/bin/bash
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
echo "Environment setup complete. To run the app, type:"
echo "source venv/bin/activate && streamlit run app.py"
