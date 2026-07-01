#!/bin/bash

echo "Creating Python virtual environment..."
# Create the virtual environment named 'venv':
python3 -m venv venv

echo "Activating virtual environment..."
# Activate the environment
source venv/bin/activate

echo "Installing dependencies from requirements.txt..."
# Upgrade pip and install the blueprint:
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete! To start working, run: source venv/bin/activate"
